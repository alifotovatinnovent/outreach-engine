"""Draft generation + send routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Draft, Lead
from ..services import channels, claude

router = APIRouter(prefix="/leads/{lead_id}/drafts", tags=["drafts"])


@router.post("/generate")
def generate_drafts(lead_id: str, db: Session = Depends(get_db)):
    """Run Claude to generate per-channel drafts for this lead."""
    lead = db.query(Lead).get(lead_id)
    if not lead:
        raise HTTPException(404, "Lead not found")
    drafts = claude.generate_drafts_for_lead(db, lead)
    return {"created": len(drafts)}


class DraftPatch(BaseModel):
    subject: str | None = None
    body: str | None = None
    approved: bool | None = None


@router.patch("/{draft_id}")
def update_draft(lead_id: str, draft_id: str, patch: DraftPatch, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id, Draft.lead_id == lead_id).one_or_none()
    if not draft:
        raise HTTPException(404, "Draft not found")
    if patch.subject is not None:
        draft.subject = patch.subject
        draft.edited_by_user = True
    if patch.body is not None:
        draft.body = patch.body
        draft.edited_by_user = True
    if patch.approved is not None:
        draft.approved = patch.approved
    db.commit()
    db.refresh(draft)
    return {"ok": True, "id": draft.id, "edited_by_user": draft.edited_by_user}


@router.post("/{draft_id}/send")
def send_draft(lead_id: str, draft_id: str, db: Session = Depends(get_db)):
    draft = db.query(Draft).filter(Draft.id == draft_id, Draft.lead_id == lead_id).one_or_none()
    if not draft:
        raise HTTPException(404, "Draft not found")
    if not draft.approved:
        raise HTTPException(400, "Draft must be approved before sending")
    send = channels.send_draft(db, draft)
    return {
        "send_id": send.id,
        "channel": send.channel.value,
        "status": send.status.value,
        "external_id": send.external_id,
        "error": send.error,
    }


class MarkSentPayload(BaseModel):
    send_id: str


@router.post("/linkedin_mark_sent")
def mark_linkedin_sent(lead_id: str, payload: MarkSentPayload, db: Session = Depends(get_db)):
    """Confirm a LinkedIn draft was manually pasted/sent."""
    send = channels.mark_linkedin_sent(db, payload.send_id)
    return {"ok": True, "send_id": send.id, "status": send.status.value}
