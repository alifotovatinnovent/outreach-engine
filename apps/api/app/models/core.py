"""Core data model.

The graph:
  Account 1—* Lead 1—* Mutual
                 1—* Draft 1—* Send 1—* Reply
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    String, Integer, Text, DateTime, Boolean, ForeignKey, Enum, JSON, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db import Base


class ChannelEnum(str, enum.Enum):
    LINKEDIN_WARM = "linkedin_warm"      # Warm-intro ask sent to a mutual
    LINKEDIN_DIRECT = "linkedin_direct"  # Direct DM/InMail to the lead
    EMAIL = "email"
    WHATSAPP = "whatsapp"


class TierEnum(str, enum.Enum):
    TIER_1 = "tier_1"  # Deep dive — strong warm path + senior
    TIER_2 = "tier_2"  # Light pass — moderate warm path or senior
    TIER_3 = "tier_3"  # Cold outreach — senior but no warm path
    PARKED = "parked"


class SendStatusEnum(str, enum.Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    REPLIED = "replied"
    BOUNCED = "bounced"
    FAILED = "failed"
    SKIPPED = "skipped"


def _uuid() -> str:
    return str(uuid.uuid4())


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    apollo_org_id: Mapped[str | None] = mapped_column(String(64))
    domain: Mapped[str | None] = mapped_column(String(255))
    industry: Mapped[str | None] = mapped_column(String(255))
    headcount: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str | None] = mapped_column(Text)
    research_blob: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    leads: Mapped[list["Lead"]] = relationship(back_populates="account", cascade="all, delete-orphan")


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"))
    apollo_person_id: Mapped[str | None] = mapped_column(String(64), index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    seniority: Mapped[str | None] = mapped_column(String(50))
    department: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    email_status: Mapped[str | None] = mapped_column(String(40))  # verified / guess / unavailable
    phone: Mapped[str | None] = mapped_column(String(50))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(255))
    bio: Mapped[str | None] = mapped_column(Text)
    recent_signals: Mapped[dict | None] = mapped_column(JSON)  # posts, news, talks
    mutual_count: Mapped[int] = mapped_column(Integer, default=0)
    tier: Mapped[TierEnum] = mapped_column(Enum(TierEnum), default=TierEnum.PARKED)
    score: Mapped[float] = mapped_column(Integer, default=0)  # composite priority
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    account: Mapped[Account] = relationship(back_populates="leads")
    mutuals: Mapped[list["Mutual"]] = relationship(back_populates="lead", cascade="all, delete-orphan")
    drafts: Mapped[list["Draft"]] = relationship(back_populates="lead", cascade="all, delete-orphan")


class Mutual(Base):
    """A 1st-degree connection of the user (Ali) who is also connected to the lead."""

    __tablename__ = "mutuals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"))
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str | None] = mapped_column(String(500))
    company: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    intro_strength: Mapped[str | None] = mapped_column(String(20))  # strong / moderate / weak
    can_intro: Mapped[bool] = mapped_column(Boolean, default=True)
    asked_at: Mapped[datetime | None] = mapped_column(DateTime)
    intro_status: Mapped[str | None] = mapped_column(String(30))  # asked / agreed / declined / sent

    lead: Mapped[Lead] = relationship(back_populates="mutuals")


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    lead_id: Mapped[str] = mapped_column(ForeignKey("leads.id", ondelete="CASCADE"))
    channel: Mapped[ChannelEnum] = mapped_column(Enum(ChannelEnum), nullable=False)
    sequence_step: Mapped[int] = mapped_column(Integer, default=1)  # 1 for openers, 2/3 for follow-ups
    target_mutual_id: Mapped[str | None] = mapped_column(ForeignKey("mutuals.id", ondelete="SET NULL"))
    subject: Mapped[str | None] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text)  # why this angle, for the user
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    edited_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    lead: Mapped[Lead] = relationship(back_populates="drafts")
    sends: Mapped[list["Send"]] = relationship(back_populates="draft", cascade="all, delete-orphan")


class Send(Base):
    __tablename__ = "sends"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    draft_id: Mapped[str] = mapped_column(ForeignKey("drafts.id", ondelete="CASCADE"))
    channel: Mapped[ChannelEnum] = mapped_column(Enum(ChannelEnum), nullable=False)
    status: Mapped[SendStatusEnum] = mapped_column(Enum(SendStatusEnum), default=SendStatusEnum.QUEUED)
    external_id: Mapped[str | None] = mapped_column(String(255))  # provider-side ID (smartlead/twilio)
    queued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text)

    draft: Mapped[Draft] = relationship(back_populates="sends")
    replies: Mapped[list["Reply"]] = relationship(back_populates="send", cascade="all, delete-orphan")


class Reply(Base):
    __tablename__ = "replies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    send_id: Mapped[str] = mapped_column(ForeignKey("sends.id", ondelete="CASCADE"))
    body: Mapped[str] = mapped_column(Text, nullable=False)
    classification: Mapped[str | None] = mapped_column(String(40))  # interested / not_now / not_interested / book / question
    next_step: Mapped[str | None] = mapped_column(Text)  # claude-suggested next move
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    send: Mapped[Send] = relationship(back_populates="replies")


# Useful indexes
Index("ix_leads_account_tier", Lead.account_id, Lead.tier)
Index("ix_drafts_lead_channel", Draft.lead_id, Draft.channel)
Index("ix_sends_status", Send.status)
