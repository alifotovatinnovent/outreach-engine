"""Channel send adapters. Each adapter implements a single send() method.

The router picks the right adapter based on draft.channel.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Protocol

import httpx
from sqlalchemy.orm import Session

from ..config import settings
from ..models import ChannelEnum, Draft, Send, SendStatusEnum

log = logging.getLogger(__name__)


class SendResult:
    def __init__(
        self,
        *,
        ok: bool,
        external_id: str | None = None,
        status: SendStatusEnum = SendStatusEnum.SENT,
        error: str | None = None,
    ):
        self.ok = ok
        self.external_id = external_id
        self.status = status
        self.error = error


class ChannelAdapter(Protocol):
    """Interface every send adapter implements."""

    name: str
    enabled: bool

    def send(self, draft: Draft, *, recipient_email: str | None, recipient_phone: str | None) -> SendResult: ...


# =========== Smartlead (email) ===========

class SmartleadAdapter:
    name = "smartlead"

    def __init__(self):
        self.api_key = settings.smartlead_api_key
        self.from_email = settings.smartlead_from_email
        self.campaign_id = settings.smartlead_default_campaign_id

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.from_email)

    def send(self, draft: Draft, *, recipient_email, recipient_phone=None) -> SendResult:
        if not self.enabled:
            return SendResult(ok=False, status=SendStatusEnum.SKIPPED, error="Smartlead not configured")
        if not recipient_email:
            return SendResult(ok=False, status=SendStatusEnum.SKIPPED, error="No recipient email")

        # Smartlead API: https://api.smartlead.ai/api/v1/campaigns/{id}/leads
        # We add the lead to a campaign and let Smartlead handle sequence delivery.
        url = f"https://server.smartlead.ai/api/v1/campaigns/{self.campaign_id}/leads"
        params = {"api_key": self.api_key}
        payload = {
            "lead_list": [{
                "first_name": (draft.lead.full_name or "").split()[0],
                "last_name": " ".join((draft.lead.full_name or "").split()[1:]),
                "email": recipient_email,
                "company_name": draft.lead.account.name if draft.lead.account else "",
                "linkedin_profile": draft.lead.linkedin_url,
                "custom_fields": {
                    "subject": draft.subject or "",
                    "body": draft.body,
                },
            }],
        }
        try:
            r = httpx.post(url, params=params, json=payload, timeout=30.0)
            if r.status_code >= 400:
                return SendResult(ok=False, status=SendStatusEnum.FAILED, error=f"Smartlead {r.status_code}: {r.text[:200]}")
            data = r.json()
            return SendResult(ok=True, external_id=str(data.get("id") or data.get("lead_id") or ""))
        except Exception as e:
            return SendResult(ok=False, status=SendStatusEnum.FAILED, error=str(e))


# =========== Twilio (WhatsApp Business) ===========

class TwilioWhatsAppAdapter:
    name = "twilio_whatsapp"

    def __init__(self):
        self.sid = settings.twilio_account_sid
        self.token = settings.twilio_auth_token
        self.from_ = settings.twilio_whatsapp_from

    @property
    def enabled(self) -> bool:
        return bool(self.sid and self.token and self.from_)

    def send(self, draft: Draft, *, recipient_email=None, recipient_phone=None) -> SendResult:
        if not self.enabled:
            return SendResult(ok=False, status=SendStatusEnum.SKIPPED, error="Twilio not configured")
        if not recipient_phone:
            return SendResult(ok=False, status=SendStatusEnum.SKIPPED, error="No recipient phone")

        try:
            from twilio.rest import Client  # noqa: WPS433

            client = Client(self.sid, self.token)
            to = recipient_phone if recipient_phone.startswith("whatsapp:") else f"whatsapp:{recipient_phone}"
            msg = client.messages.create(from_=self.from_, to=to, body=draft.body)
            return SendResult(ok=True, external_id=msg.sid)
        except Exception as e:
            return SendResult(ok=False, status=SendStatusEnum.FAILED, error=str(e))


# =========== LinkedIn (manual-with-tracking) ===========

class LinkedInManualAdapter:
    """LinkedIn auto-send is against ToS. This adapter does NOT send.

    Instead, it queues the draft for manual copy-paste and tracks the user's
    "Mark as sent" click. The dashboard provides a copy-to-clipboard button.
    """

    name = "linkedin_manual"
    enabled = True  # always available

    def send(self, draft: Draft, *, recipient_email=None, recipient_phone=None) -> SendResult:
        # We don't actually send. We mark as queued; user must click "Mark as sent"
        # in the dashboard once they've pasted the message into LinkedIn.
        return SendResult(ok=True, status=SendStatusEnum.QUEUED, external_id="manual")


# =========== Router ===========

ADAPTERS: dict[ChannelEnum, ChannelAdapter] = {
    ChannelEnum.EMAIL: SmartleadAdapter(),
    ChannelEnum.WHATSAPP: TwilioWhatsAppAdapter(),
    ChannelEnum.LINKEDIN_WARM: LinkedInManualAdapter(),
    ChannelEnum.LINKEDIN_DIRECT: LinkedInManualAdapter(),
}


def send_draft(db: Session, draft: Draft) -> Send:
    """Route a draft to the right adapter and persist a Send row."""
    adapter = ADAPTERS.get(draft.channel)
    recipient_email = draft.lead.email
    recipient_phone = draft.lead.phone

    send = Send(
        draft_id=draft.id,
        channel=draft.channel,
        status=SendStatusEnum.QUEUED,
    )
    db.add(send)
    db.flush()

    if adapter is None:
        send.status = SendStatusEnum.FAILED
        send.error = f"No adapter for channel {draft.channel}"
        db.commit()
        return send

    log.info("Sending draft %s via %s", draft.id, adapter.name)
    result = adapter.send(draft, recipient_email=recipient_email, recipient_phone=recipient_phone)

    send.external_id = result.external_id
    send.status = result.status
    send.error = result.error
    if result.status in (SendStatusEnum.SENT, SendStatusEnum.DELIVERED):
        send.sent_at = datetime.utcnow()
    db.commit()
    return send


def mark_linkedin_sent(db: Session, send_id: str) -> Send:
    """User pasted the LinkedIn draft into their browser and confirms it sent.

    For LinkedIn channels only — this is the human-in-the-loop confirmation.
    """
    send = db.query(Send).get(send_id)
    if not send:
        raise ValueError(f"Send {send_id} not found")
    if send.channel not in (ChannelEnum.LINKEDIN_WARM, ChannelEnum.LINKEDIN_DIRECT):
        raise ValueError(f"mark_linkedin_sent only valid for LinkedIn channels, got {send.channel}")
    send.status = SendStatusEnum.SENT
    send.sent_at = datetime.utcnow()
    db.commit()
    return send
