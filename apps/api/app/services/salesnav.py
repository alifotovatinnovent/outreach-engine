"""LinkedIn Sales Nav helpers.

CRITICAL: We do NOT automate sends through LinkedIn. That gets accounts banned
and is against ToS. This module only:

  - Imports a CSV of mutual connections that the user exports from Sales Nav.
  - Resolves matches against existing leads in the DB so we know warm paths exist.
  - Generates a "send-ready" payload (subject + body + lead URL) for the user
    to copy-paste manually.

CSV format expected:
  Sales Nav lets you export saved leads to CSV. Columns we use:
    - First Name, Last Name, Title, Company, Location, LinkedIn URL

Drop your CSV into the dashboard upload (POST /accounts/{id}/import_mutuals)
and we'll wire mutuals to leads by name match.
"""
from __future__ import annotations

import csv
import io
import logging
from typing import Iterable

from sqlalchemy.orm import Session

from ..models import Lead, Mutual

log = logging.getLogger(__name__)


def _normalize(s: str | None) -> str:
    return (s or "").strip().lower()


def import_mutuals_csv(db: Session, lead: Lead, csv_text: str) -> list[Mutual]:
    """Parse a Sales Nav export CSV and create Mutual rows linked to one lead."""
    reader = csv.DictReader(io.StringIO(csv_text))
    created: list[Mutual] = []
    for row in reader:
        first = row.get("First Name") or row.get("first_name") or ""
        last = row.get("Last Name") or row.get("last_name") or ""
        full_name = f"{first} {last}".strip()
        if not full_name:
            continue
        # Avoid duplicate by name
        exists = any(_normalize(m.full_name) == _normalize(full_name) for m in lead.mutuals)
        if exists:
            continue
        m = Mutual(
            lead_id=lead.id,
            full_name=full_name,
            title=row.get("Title") or row.get("title"),
            company=row.get("Company") or row.get("company"),
            location=row.get("Location") or row.get("location"),
            linkedin_url=row.get("LinkedIn URL") or row.get("linkedin_url"),
            intro_strength=_score_intro_strength(
                row.get("Title") or "",
                row.get("Location") or "",
                lead.location or "",
            ),
        )
        db.add(m)
        created.append(m)
    if created:
        lead.mutual_count = len(lead.mutuals) + len(created)
        db.commit()
    return created


def _score_intro_strength(title: str, mutual_loc: str, lead_loc: str) -> str:
    title_lo = title.lower()
    senior = any(k in title_lo for k in ["ceo", "founder", "vp ", "head of", "executive director", "chairman", "partner"])
    co_located = any(
        k in mutual_loc.lower() and k in lead_loc.lower()
        for k in ["dubai", "abu dhabi", "uae", "united arab emirates", "saudi", "qatar"]
    )
    if senior and co_located:
        return "strong"
    if co_located or senior:
        return "moderate"
    return "weak"


def resolve_warm_intro_target(lead: Lead) -> Mutual | None:
    """Pick the best mutual to ask for an intro, given current state."""
    if not lead.mutuals:
        return None
    rank = {"strong": 0, "moderate": 1, "weak": 2, None: 3}
    return min(
        (m for m in lead.mutuals if m.can_intro and m.intro_status not in ("declined",)),
        key=lambda m: rank.get(m.intro_strength, 3),
        default=None,
    )


def export_drafts_for_copy_paste(lead: Lead) -> dict:
    """Render the LinkedIn drafts as plaintext blocks the user copies into LinkedIn."""
    blocks = []
    for d in lead.drafts:
        if d.channel.value not in ("linkedin_warm", "linkedin_direct"):
            continue
        blocks.append({
            "draft_id": d.id,
            "channel": d.channel.value,
            "target_mutual_name": next(
                (m.full_name for m in lead.mutuals if m.id == d.target_mutual_id),
                None,
            ),
            "body": d.body,
            "rationale": d.rationale,
            "lead_linkedin_url": lead.linkedin_url,
        })
    return {"lead_id": lead.id, "blocks": blocks}
