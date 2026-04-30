"""Lead-level routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Account, Lead, Mutual

router = APIRouter(prefix="/accounts/{account_id}/leads", tags=["leads"])


class MutualOut(BaseModel):
    id: str
    full_name: str
    title: str | None
    company: str | None
    location: str | None
    intro_strength: str | None
    intro_status: str | None


class DraftOut(BaseModel):
    id: str
    channel: str
    sequence_step: int
    target_mutual_id: str | None
    subject: str | None
    body: str
    rationale: str | None
    approved: bool
    edited_by_user: bool


class LeadOut(BaseModel):
    id: str
    full_name: str
    title: str | None
    seniority: str | None
    department: str | None
    email: str | None
    email_status: str | None
    phone: str | None
    linkedin_url: str | None
    location: str | None
    bio: str | None
    tier: str
    score: float
    mutual_count: int
    mutuals: list[MutualOut]
    drafts: list[DraftOut]


def _lead_out(lead: Lead) -> LeadOut:
    return LeadOut(
        id=lead.id,
        full_name=lead.full_name,
        title=lead.title,
        seniority=lead.seniority,
        department=lead.department,
        email=lead.email,
        email_status=lead.email_status,
        phone=lead.phone,
        linkedin_url=lead.linkedin_url,
        location=lead.location,
        bio=lead.bio,
        tier=lead.tier.value if lead.tier else "parked",
        score=lead.score,
        mutual_count=lead.mutual_count,
        mutuals=[
            MutualOut(
                id=m.id, full_name=m.full_name, title=m.title, company=m.company,
                location=m.location, intro_strength=m.intro_strength,
                intro_status=m.intro_status,
            ) for m in lead.mutuals
        ],
        drafts=[
            DraftOut(
                id=d.id, channel=d.channel.value, sequence_step=d.sequence_step,
                target_mutual_id=d.target_mutual_id, subject=d.subject,
                body=d.body, rationale=d.rationale, approved=d.approved,
                edited_by_user=d.edited_by_user,
            ) for d in sorted(lead.drafts, key=lambda x: (x.channel.value, x.sequence_step))
        ],
    )


@router.get("", response_model=list[LeadOut])
def list_leads(account_id: str, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    leads = sorted(account.leads, key=lambda l: (-l.score, l.full_name))
    return [_lead_out(l) for l in leads]


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(account_id: str, lead_id: str, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.account_id == account_id).one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    return _lead_out(lead)


class LeadPatch(BaseModel):
    tier: str | None = None
    notes: str | None = None


@router.patch("/{lead_id}", response_model=LeadOut)
def update_lead(account_id: str, lead_id: str, patch: LeadPatch, db: Session = Depends(get_db)):
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.account_id == account_id).one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found")
    if patch.tier:
        from ..models import TierEnum
        lead.tier = TierEnum(patch.tier)
    if patch.notes is not None:
        lead.notes = patch.notes
    db.commit()
    db.refresh(lead)
    return _lead_out(lead)
