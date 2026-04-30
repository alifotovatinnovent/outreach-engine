"""Quick CLI for running the pipeline without the web UI.

Usage:
  python cli.py research "Pure Health"
  python cli.py drafts <lead_id>
  python cli.py list
"""
import argparse
import asyncio
import sys

from app.db import Base, SessionLocal, engine
from app.models import Account, Lead
from app.services import claude, intelligence


def cmd_research(name: str):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        account = asyncio.run(intelligence.research_account(db, name))
        print(f"\n✅ {account.name}")
        print(f"   {account.industry} · {account.headcount} ppl · {account.domain}")
        print(f"   {len(account.leads)} senior leaders found")
        for l in sorted(account.leads, key=lambda x: -x.score)[:15]:
            email = f"<{l.email}>" if l.email else ""
            print(f"   [{l.tier.value:7}] score={l.score:>3.0f} {l.full_name:30} {l.title or '—':50} {email}")
    finally:
        db.close()


def cmd_drafts(lead_id: str):
    db = SessionLocal()
    try:
        lead = db.query(Lead).get(lead_id)
        if not lead:
            print(f"Lead {lead_id} not found")
            return
        drafts = claude.generate_drafts_for_lead(db, lead)
        print(f"✅ Generated {len(drafts)} drafts for {lead.full_name}")
        for d in drafts:
            print(f"\n--- {d.channel.value} (step {d.sequence_step}) ---")
            if d.subject: print(f"Subject: {d.subject}")
            print(d.body)
            if d.rationale: print(f"💡 {d.rationale}")
    finally:
        db.close()


def cmd_list():
    db = SessionLocal()
    try:
        for a in db.query(Account).all():
            print(f"{a.id}  {a.name:30} {len(a.leads):>3} leads")
    finally:
        db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("research")
    r.add_argument("company")

    d = sub.add_parser("drafts")
    d.add_argument("lead_id")

    sub.add_parser("list")

    args = p.parse_args()
    if args.cmd == "research":
        cmd_research(args.company)
    elif args.cmd == "drafts":
        cmd_drafts(args.lead_id)
    elif args.cmd == "list":
        cmd_list()
    else:
        sys.exit(1)
