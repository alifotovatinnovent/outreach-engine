"""CRM sync adapters (HubSpot, Pipedrive). Stub-level — flesh out as needed."""
from __future__ import annotations

import logging

import httpx

from ..config import settings
from ..models import Account, Lead

log = logging.getLogger(__name__)


class HubSpotAdapter:
    name = "hubspot"

    def __init__(self):
        self.token = settings.hubspot_token

    @property
    def enabled(self) -> bool:
        return bool(self.token)

    def upsert_company(self, account: Account) -> str | None:
        """Create or update a HubSpot Company. Returns HubSpot company ID."""
        if not self.enabled:
            return None
        url = "https://api.hubapi.com/crm/v3/objects/companies"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        body = {
            "properties": {
                "name": account.name,
                "domain": account.domain or "",
                "industry": account.industry or "",
                "numberofemployees": account.headcount or 0,
            },
        }
        try:
            r = httpx.post(url, headers=headers, json=body, timeout=30.0)
            if r.status_code in (200, 201):
                return r.json().get("id")
            log.warning("HubSpot upsert_company %s: %s", r.status_code, r.text[:200])
        except Exception as e:
            log.exception("HubSpot upsert_company failed: %s", e)
        return None

    def upsert_contact(self, lead: Lead, company_id: str | None = None) -> str | None:
        if not self.enabled:
            return None
        url = "https://api.hubapi.com/crm/v3/objects/contacts"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        first, *rest = (lead.full_name or "").split()
        last = " ".join(rest)
        body = {
            "properties": {
                "email": lead.email or "",
                "firstname": first,
                "lastname": last,
                "jobtitle": lead.title or "",
                "linkedin_url": lead.linkedin_url or "",
                "phone": lead.phone or "",
            },
        }
        try:
            r = httpx.post(url, headers=headers, json=body, timeout=30.0)
            if r.status_code in (200, 201):
                contact_id = r.json().get("id")
                if company_id and contact_id:
                    self._associate(contact_id, company_id)
                return contact_id
            log.warning("HubSpot upsert_contact %s: %s", r.status_code, r.text[:200])
        except Exception as e:
            log.exception("HubSpot upsert_contact failed: %s", e)
        return None

    def _associate(self, contact_id: str, company_id: str) -> None:
        url = (
            f"https://api.hubapi.com/crm/v4/objects/contacts/{contact_id}"
            f"/associations/default/companies/{company_id}"
        )
        try:
            httpx.put(
                url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=30.0,
            )
        except Exception:  # noqa: BLE001
            log.exception("HubSpot association failed")


hubspot = HubSpotAdapter()
