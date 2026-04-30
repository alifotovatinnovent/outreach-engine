"""Account-level routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Account, Lead
from ..services import intelligence, salesnav

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountIn(BaseModel):
    company_name: str


class AccountOut(BaseModel):
    id: str
    name: str
    domain: str | None
    industry: str | None
    headcount: int | None
    summary: str | None
    lead_count: int


def _account_out(a: Account) -> AccountOut:
    return AccountOut(
        id=a.id,
        name=a.name,
        domain=a.domain,
        industry=a.industry,
        headcount=a.headcount,
        summary=a.summary,
        lead_count=len(a.leads),
    )


@router.get("", response_model=list[AccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return [_account_out(a) for a in db.query(Account).order_by(Account.created_at.desc()).all()]


@router.post("", response_model=AccountOut)
async def create_account(payload: AccountIn, db: Session = Depends(get_db)):
    """Trigger the full intelligence pipeline for a company."""
    account = await intelligence.research_account(db, payload.company_name)
    return _account_out(account)


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: str, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    return _account_out(account)


@router.delete("/{account_id}")
def delete_account(account_id: str, db: Session = Depends(get_db)):
    account = db.query(Account).get(account_id)
    if not account:
        raise HTTPException(404, "Account not found")
    db.delete(account)
    db.commit()
    return {"ok": True}


@router.post("/{account_id}/import_mutuals")
async def import_mutuals(
    account_id: str,
    lead_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a Sales Nav CSV export of mutual connections for one lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.account_id == account_id).one_or_none()
    if not lead:
        raise HTTPException(404, "Lead not found in this account")
    text = (await file.read()).decode("utf-8")
    created = salesnav.import_mutuals_csv(db, lead, text)
    return {"imported": len(created)}
