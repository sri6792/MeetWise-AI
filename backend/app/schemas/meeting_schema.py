from datetime import date, datetime, time, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _clean_text(v):
    """Trim surrounding whitespace so '   ' cannot pass as a real value."""
    return v.strip() if isinstance(v, str) else v


def _clean_optional(v):
    """Trim; an empty string becomes None."""
    if isinstance(v, str):
        v = v.strip()
    return v or None


class MeetingCreateRequest(BaseModel):
    organization_or_person: str = Field(
        min_length=2,
        max_length=200,
        description="Company or person you are meeting",
    )

    attendee_name: Optional[str] = Field(default=None, max_length=200)

    meeting_date: date
    meeting_time: time

    purpose: str = Field(
        min_length=5,
        max_length=2000,
        description="Purpose of the meeting",
    )

    @field_validator("organization_or_person", "purpose", mode="before")
    @classmethod
    def _strip_required(cls, v):
        return _clean_text(v)

    @field_validator("attendee_name", mode="before")
    @classmethod
    def _strip_optional(cls, v):
        return _clean_optional(v)


class MeetingPreviewResponse(BaseModel):
    status: str
    message: str
    meeting: MeetingCreateRequest


class MeetingUpdateRequest(BaseModel):
    """Partial update (PATCH): send only the fields you want to change."""

    organization_or_person: Optional[str] = Field(default=None, min_length=2, max_length=200)
    attendee_name: Optional[str] = Field(default=None, max_length=200)
    meeting_date: Optional[date] = None
    meeting_time: Optional[time] = None
    purpose: Optional[str] = Field(default=None, min_length=5, max_length=2000)

    @field_validator("organization_or_person", "purpose", mode="before")
    @classmethod
    def _strip_required(cls, v):
        return _clean_text(v)

    @field_validator("attendee_name", mode="before")
    @classmethod
    def _strip_optional(cls, v):
        return _clean_optional(v)

    @model_validator(mode="after")
    def _check_fields(self):
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update")
        # attendee_name may be cleared with null; the others may not
        for name in ("organization_or_person", "meeting_date", "meeting_time", "purpose"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} cannot be null")
        return self


class MeetingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_or_person: str
    attendee_name: Optional[str]
    meeting_date: date
    meeting_time: time
    purpose: str
    status: str
    progress_stage: Optional[str] = None
    progress_percent: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def _as_utc(cls, v: datetime) -> datetime:
        # SQLite returns naive datetimes; we always store UTC, so label them as such
        return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v


class MeetingListResponse(BaseModel):
    items: list[MeetingRead]
    total: int
    limit: int
    offset: int
