"""Evidence-layer tables.

Design rule (Feature 10): retrieved evidence (Source) is stored separately from
interpretation (Claim). A Claim points at Source ids and carries an evidence
label; claims with no supporting source can never be labelled "verified".
"""
from datetime import date, datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.enums import EvidenceLabel, Freshness, SourceCategory
from app.models.meeting import utcnow


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(20), default=SourceCategory.OTHER.value)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    # NULL means "the source did not give a date". We never guess one.
    published_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Retrieved text used for claim verification. Never shown as AI output.
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    freshness: Mapped[str] = mapped_column(String(25), default=Freshness.UNKNOWN.value)

    meeting = relationship("Meeting", back_populates="sources")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    section: Mapped[str] = mapped_column(String(50))  # e.g. "company", "person"
    text: Mapped[str] = mapped_column(Text)
    evidence_label: Mapped[str] = mapped_column(
        String(25), default=EvidenceLabel.NEEDS_VERIFICATION.value
    )
    source_ids: Mapped[list[int]] = mapped_column(JSON, default=list)
    is_inference: Mapped[bool] = mapped_column(Boolean, default=False)  # AI interpretation
    note: Mapped[str | None] = mapped_column(Text, nullable=True)  # why this label was given

    meeting = relationship("Meeting", back_populates="claims")


class Briefing(Base):
    __tablename__ = "briefings"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), unique=True, index=True
    )
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    meeting = relationship("Meeting", back_populates="briefing")
