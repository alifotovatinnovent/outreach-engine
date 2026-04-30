"""Intelligence pipeline: company name → ranked leader list ready for draft generation.

Pipeline stages:
  1. Resolve organization (Apollo)
  2. Pull all senior leaders (Apollo paginated)
  3. Enrich each with email + LinkedIn (Apollo bulk_match)
  4. Score leaders by seniority + relevance
  5. Assign tier (1/2/3/parked) based on score + mutual count
  6. Persist to DB
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from ..models import Account, Lead, TierEnum
from .apollo import ApolloClient, DEFAULT_SENIORITIES

log = logging.getLogger(__name__)


SENIORITY_SCORE = {
    "c_suite": 100,
    "founder": 95,
    "owner": 90,
    "partner": 85,
    "vp": 75,
    "head": 65,
    "director": 55,
    "senior": 35,
    "manager": 20,
}


def _seniority_from_apollo(p: dict[str, Any]) -> str | None:
    """Apollo returns seniority as a string in `seniority` field."""
    return p.get("seniority")


def _score_lead(person: dict[str, Any], mutual_count: int = 0) -> float:
    """0-100 composite score: seniority + warm-path strength."""
    sen = _seniority_from_apollo(person) or "manager"
    base = SENIORITY_SCORE.get(sen, 10)
    # Warm path bonus: each mutual is worth ~0.5 points, capped at +30
    warm = min(30, mutual_count * 0.5)
    # Verified email bonus: +5
    email_bonus = 5 if (person.get("email_status") in ("verified", "likely_to_engage")) else 0
    return base + warm + email_bonus


def _tier_from_score(score: float, mutual_count: int) -> TierEnum:
    if score >= 85 and mutual_count >= 5:
        return TierEnum.TIER_1
    if score >= 60 and mutual_count >= 3:
        return TierEnum.TIER_1
    if score >= 60:
        return TierEnum.TIER_2
    if score >= 40:
        return TierEnum.TIER_3
    return TierEnum.PARKED


async def research_account(db: Session, company_name: str) -> Account:
    """Run the full pipeline for a company. Idempotent: re-running updates the account row."""
    async with ApolloClient() as apollo:
        # 1) Resolve org
        org = await apollo.find_organization(company_name)
        if not org:
            raise ValueError(f"Apollo could not resolve company: {company_name!r}")

        # 2) Persist account (upsert by name+apollo_org_id)
        account = (
            db.query(Account)
            .filter(Account.apollo_org_id == org.get("id"))
            .one_or_none()
        )
        if not account:
            account = Account(
                name=org.get("name") or company_name,
                apollo_org_id=org.get("id"),
                domain=org.get("primary_domain") or org.get("website_url"),
                industry=org.get("industry"),
                headcount=org.get("estimated_num_employees"),
                summary=org.get("short_description"),
                research_blob=org,
            )
            db.add(account)
        else:
            account.name = org.get("name") or account.name
            account.domain = org.get("primary_domain") or account.domain
            account.industry = org.get("industry") or account.industry
            account.headcount = org.get("estimated_num_employees") or account.headcount
            account.summary = org.get("short_description") or account.summary
            account.research_blob = org
        db.flush()

        # 3) Pull senior leaders
        log.info("Pulling senior leaders for org %s (%s)", org.get("name"), org.get("id"))
        people = await apollo.search_all_senior_people(
            organization_id=org["id"],
            seniorities=DEFAULT_SENIORITIES,
            max_results=200,
        )
        log.info("Got %d senior leaders", len(people))

        # 4) Bulk enrich (gets emails)
        enrich_input = [
            {
                "first_name": p.get("first_name"),
                "last_name": p.get("last_name"),
                "organization_name": org.get("name"),
                "linkedin_url": p.get("linkedin_url"),
            }
            for p in people
            if p.get("first_name") and p.get("last_name")
        ]
        enriched = await apollo.bulk_enrich_people(enrich_input, reveal_personal_emails=False)
        # Index enriched by linkedin_url for merge
        enriched_by_li = {e.get("linkedin_url"): e for e in enriched if e.get("linkedin_url")}

        # 5) Persist leads
        existing = {l.apollo_person_id: l for l in account.leads if l.apollo_person_id}
        for p in people:
            pid = p.get("id")
            if not pid:
                continue
            merged = {**p, **(enriched_by_li.get(p.get("linkedin_url"), {}) or {})}
            score = _score_lead(merged, mutual_count=0)
            tier = _tier_from_score(score, mutual_count=0)
            lead = existing.get(pid)
            if not lead:
                lead = Lead(
                    account_id=account.id,
                    apollo_person_id=pid,
                    full_name=f"{p.get('first_name','')} {p.get('last_name','')}".strip(),
                )
                db.add(lead)
            lead.title = merged.get("title")
            lead.seniority = merged.get("seniority")
            lead.department = (merged.get("departments") or [None])[0]
            lead.email = merged.get("email")
            lead.email_status = merged.get("email_status")
            lead.phone = (merged.get("phone_numbers") or [{}])[0].get("sanitized_number")
            lead.linkedin_url = merged.get("linkedin_url")
            lead.location = ", ".join(filter(None, [
                merged.get("city"), merged.get("state"), merged.get("country")
            ])) or None
            lead.bio = merged.get("headline")
            lead.score = int(score)
            lead.tier = tier
            lead.recent_signals = {
                "headline": merged.get("headline"),
                "twitter_url": merged.get("twitter_url"),
                "github_url": merged.get("github_url"),
            }

        db.commit()
        db.refresh(account)
        return account
