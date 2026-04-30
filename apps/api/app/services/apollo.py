"""Apollo.io REST client.

Apollo's REST API: https://docs.apollo.io/reference/

Auth: pass API key via `X-Api-Key` header.

Endpoints we use:
  POST /api/v1/mixed_companies/search   — find an org by name/domain
  POST /api/v1/mixed_people/search      — search people in an org with seniority filter
  POST /api/v1/people/match             — enrich a single person (email, etc.)
  POST /api/v1/people/bulk_match        — enrich many at once
"""
from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import settings

log = logging.getLogger(__name__)

APOLLO_BASE = "https://api.apollo.io"

# Apollo seniority taxonomy (https://docs.apollo.io/reference/people-search)
SENIORITY_LEVELS = ["c_suite", "founder", "owner", "partner", "vp", "head", "director", "senior", "manager"]

# What we consider "senior decision-maker" by default
DEFAULT_SENIORITIES = ["c_suite", "founder", "owner", "partner", "vp", "head", "director"]


class ApolloError(RuntimeError):
    pass


class ApolloClient:
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.apollo_api_key
        if not self.api_key:
            raise ApolloError("APOLLO_API_KEY not set")
        self._client = httpx.AsyncClient(
            base_url=APOLLO_BASE,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={
                "Cache-Control": "no-cache",
                "Content-Type": "application/json",
                "X-Api-Key": self.api_key,
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "ApolloClient":
        return self

    async def __aexit__(self, *_):
        await self.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        r = await self._client.post(path, json=payload)
        if r.status_code == 429:
            raise ApolloError("Rate limited (429). Slow down or upgrade plan.")
        if r.status_code >= 400:
            raise ApolloError(f"Apollo {path} returned {r.status_code}: {r.text[:300]}")
        return r.json()

    # ---------------- Public methods ----------------

    async def find_organization(self, name: str) -> dict[str, Any] | None:
        """Find the canonical Apollo org for a company name. Returns org dict or None."""
        data = await self._post(
            "/api/v1/mixed_companies/search",
            {"q_organization_name": name, "page": 1, "per_page": 5},
        )
        orgs = (data.get("organizations") or []) + (data.get("accounts") or [])
        if not orgs:
            return None
        # Best match: prefer exact name match, then largest headcount
        name_lower = name.lower()
        orgs_sorted = sorted(
            orgs,
            key=lambda o: (
                0 if (o.get("name") or "").lower() == name_lower else 1,
                -(o.get("estimated_num_employees") or 0),
            ),
        )
        return orgs_sorted[0]

    async def search_people(
        self,
        organization_id: str | None = None,
        organization_name: str | None = None,
        seniorities: list[str] | None = None,
        per_page: int = 25,
        page: int = 1,
    ) -> dict[str, Any]:
        """Search people at an org filtered by seniority. Returns {'people': [...], 'pagination': {...}}."""
        payload: dict[str, Any] = {
            "page": page,
            "per_page": per_page,
            "person_seniorities": seniorities or DEFAULT_SENIORITIES,
        }
        if organization_id:
            payload["organization_ids"] = [organization_id]
        elif organization_name:
            payload["q_organization_name"] = organization_name
        else:
            raise ApolloError("Need organization_id or organization_name")

        return await self._post("/api/v1/mixed_people/search", payload)

    async def search_all_senior_people(
        self,
        organization_id: str,
        seniorities: list[str] | None = None,
        max_results: int = 200,
    ) -> list[dict[str, Any]]:
        """Paginate through senior leaders at an org."""
        out: list[dict[str, Any]] = []
        page = 1
        while len(out) < max_results:
            data = await self.search_people(
                organization_id=organization_id,
                seniorities=seniorities,
                per_page=50,
                page=page,
            )
            people = data.get("people") or []
            if not people:
                break
            out.extend(people)
            pagination = data.get("pagination") or {}
            if page >= (pagination.get("total_pages") or page):
                break
            page += 1
        return out[:max_results]

    async def enrich_person(
        self,
        first_name: str | None = None,
        last_name: str | None = None,
        organization_name: str | None = None,
        linkedin_url: str | None = None,
        email: str | None = None,
        reveal_personal_emails: bool = False,
    ) -> dict[str, Any] | None:
        """Enrich a single person. Returns their full Apollo record (with email if available)."""
        payload: dict[str, Any] = {"reveal_personal_emails": reveal_personal_emails}
        if linkedin_url:
            payload["linkedin_url"] = linkedin_url
        if email:
            payload["email"] = email
        if first_name and last_name:
            payload["first_name"] = first_name
            payload["last_name"] = last_name
        if organization_name:
            payload["organization_name"] = organization_name

        data = await self._post("/api/v1/people/match", payload)
        return data.get("person")

    async def bulk_enrich_people(
        self,
        people: list[dict[str, Any]],
        reveal_personal_emails: bool = False,
    ) -> list[dict[str, Any]]:
        """Bulk enrich. Each entry: {first_name, last_name, organization_name} or {linkedin_url}."""
        if not people:
            return []
        data = await self._post(
            "/api/v1/people/bulk_match",
            {
                "details": people,
                "reveal_personal_emails": reveal_personal_emails,
            },
        )
        return data.get("matches") or []
