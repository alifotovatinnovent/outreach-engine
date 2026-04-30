"""Claude integration for draft generation and reply classification."""
from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
from sqlalchemy.orm import Session

from ..config import settings
from ..models import Account, ChannelEnum, Draft, Lead
from ..prompts.drafts import (
    SYSTEM_DRAFT_GENERATOR,
    USER_PROMPT_ALL_CHANNELS,
    lead_context_block,
)

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"


def _client() -> anthropic.Anthropic:
    if not settings.anthropic_api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key)


def _lead_to_dict(lead: Lead) -> dict[str, Any]:
    return {
        "full_name": lead.full_name,
        "title": lead.title,
        "seniority": lead.seniority,
        "email": lead.email,
        "linkedin_url": lead.linkedin_url,
        "location": lead.location,
        "bio": lead.bio,
        "tier": lead.tier.value if lead.tier else None,
        "recent_signals": lead.recent_signals or {},
    }


def _account_to_dict(account: Account) -> dict[str, Any]:
    return {
        "name": account.name,
        "industry": account.industry,
        "headcount": account.headcount,
        "summary": account.summary,
    }


def _mutuals_to_list(lead: Lead) -> list[dict[str, Any]]:
    return [
        {
            "id": m.id,
            "full_name": m.full_name,
            "title": m.title,
            "company": m.company,
            "location": m.location,
        }
        for m in lead.mutuals
    ]


def _parse_json_response(text: str) -> dict[str, Any]:
    """Claude sometimes wraps JSON in fences despite instructions; strip them."""
    t = text.strip()
    if t.startswith("```"):
        # Strip ```json ... ```
        lines = t.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        t = "\n".join(lines)
    return json.loads(t)


def generate_drafts_for_lead(db: Session, lead: Lead) -> list[Draft]:
    """Generate per-channel drafts for one lead. Persists Draft rows."""
    account = lead.account
    sys_prompt = SYSTEM_DRAFT_GENERATOR.format(
        sender_name=settings.sender_name,
        sender_role=settings.sender_role,
        sender_company=settings.sender_company,
        product_pitch=settings.product_pitch,
    )
    ctx = lead_context_block(
        lead=_lead_to_dict(lead),
        account=_account_to_dict(account),
        mutuals=_mutuals_to_list(lead),
    )
    user_msg = USER_PROMPT_ALL_CHANNELS.format(context_block=ctx)

    log.info("Generating drafts for lead %s (%s)", lead.full_name, lead.id)
    resp = _client().messages.create(
        model=MODEL,
        max_tokens=2000,
        system=sys_prompt,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = resp.content[0].text if resp.content else ""
    try:
        parsed = _parse_json_response(raw)
    except json.JSONDecodeError as e:
        log.error("Failed to parse Claude response for %s: %s\nRaw: %s", lead.full_name, e, raw[:500])
        raise

    # Wipe previously generated (non-edited) drafts so re-running is idempotent
    for old in list(lead.drafts):
        if not old.edited_by_user:
            db.delete(old)
    db.flush()

    out: list[Draft] = []

    # LinkedIn warm-intro ask
    li_warm = parsed.get("linkedin_warm_intro_ask")
    if li_warm and li_warm.get("body"):
        target_mutual = next(
            (m for m in lead.mutuals if m.full_name == li_warm.get("target_mutual_name")),
            None,
        )
        out.append(Draft(
            lead_id=lead.id,
            channel=ChannelEnum.LINKEDIN_WARM,
            target_mutual_id=target_mutual.id if target_mutual else None,
            body=li_warm["body"].strip(),
            rationale=li_warm.get("rationale"),
        ))

    # LinkedIn direct DM
    li_dm = parsed.get("linkedin_direct_dm")
    if li_dm and li_dm.get("body"):
        out.append(Draft(
            lead_id=lead.id,
            channel=ChannelEnum.LINKEDIN_DIRECT,
            body=li_dm["body"].strip(),
            rationale=li_dm.get("rationale"),
        ))

    # Email sequence
    for step_key, step_num in [("email_opener", 1), ("email_followup_1", 2), ("email_breakup", 3)]:
        em = parsed.get(step_key)
        if em and em.get("body"):
            out.append(Draft(
                lead_id=lead.id,
                channel=ChannelEnum.EMAIL,
                sequence_step=step_num,
                subject=em.get("subject"),
                body=em["body"].strip(),
                rationale=em.get("rationale"),
            ))

    # WhatsApp
    wa = parsed.get("whatsapp_opener")
    if wa and wa.get("body"):
        out.append(Draft(
            lead_id=lead.id,
            channel=ChannelEnum.WHATSAPP,
            body=wa["body"].strip(),
            rationale=wa.get("rationale"),
        ))

    for d in out:
        db.add(d)
    db.commit()
    log.info("Created %d drafts for %s", len(out), lead.full_name)
    return out


CLASSIFY_REPLY_PROMPT = """A sales prospect just replied to outbound from {sender_name}.

Their reply:
\"\"\"
{reply_body}
\"\"\"

Original outreach context:
- Lead: {lead_name}, {lead_title} at {company}
- Channel: {channel}
- Our message: {original}

Classify the reply as exactly one of: interested, not_now, not_interested, book, question.
Then suggest the next step in 1-2 sentences.

Return JSON only: {{"classification": "...", "next_step": "..."}}"""


def classify_reply(
    *,
    sender_name: str,
    reply_body: str,
    lead_name: str,
    lead_title: str | None,
    company: str | None,
    channel: str,
    original: str,
) -> dict[str, str]:
    prompt = CLASSIFY_REPLY_PROMPT.format(
        sender_name=sender_name,
        reply_body=reply_body[:1500],
        lead_name=lead_name,
        lead_title=lead_title or "—",
        company=company or "—",
        channel=channel,
        original=original[:500],
    )
    resp = _client().messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text if resp.content else "{}"
    return _parse_json_response(raw)
