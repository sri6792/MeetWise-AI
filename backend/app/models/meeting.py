from datetime import date, datetime, time, timezone

from sqlalchemy import Date, DateTime, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.connection import Base
from app.models.enums import MeetingStatus


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_or_person: Mapped[str] = mapped_column(String(200), index=True)
    attendee_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    meeting_date: Mapped[date] = mapped_column(Date, index=True)
    meeting_time: Mapped[time] = mapped_column(Time)
    purpose: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), default=MeetingStatus.CREATED.value, index=True
    )
    progress_stage: Mapped[str | None] = mapped_column(String(40), nullable=True)
    progress_percent: Mapped[int | None] = mapped_column(Integer, nullable=True, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    # Deleting a meeting deletes everything researched for it
    sources = relationship(
        "Source", back_populates="meeting", cascade="all, delete-orphan"
    )
    claims = relationship(
        "Claim", back_populates="meeting", cascade="all, delete-orphan"
    )
    briefing = relationship(
        "Briefing", back_populates="meeting", uselist=False, cascade="all, delete-orphan"
    )
