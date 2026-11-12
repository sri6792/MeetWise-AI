from datetime import date, datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.meeting_schema import MeetingRead


def _utc(v: datetime) -> datetime:
    return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v


class Statement(BaseModel):
    """One claim in the briefing, with its evidence label and source references."""
    text: str
    source_ids: list[int] = Field(default_factory=list)
    refs: list[int] = Field(default_factory=list, description="Numbered references shown to the user, e.g. [1]")
    evidence_label: str = "needs_verification"
    is_inference: bool = False
    note: Optional[str] = None
    claim_id: Optional[int] = None


class Opportunity(BaseModel):
    title: str
    type: str
    description: str = ""
    why_relevant: str = ""
    source_ids: list[int] = Field(default_factory=list)
    refs: list[int] = Field(default_factory=list)
    evidence_label: str = "needs_verification"
    is_inference: bool = True
    note: Optional[str] = None
    claim_id: Optional[int] = None


class QuestionItem(BaseModel):
    question: str
    rationale: Optional[str] = None
    reveals: Optional[str] = None
    source_ids: list[int] = Field(default_factory=list)
    refs: list[int] = Field(default_factory=list)


class Questions(BaseModel):
    strategic: list[QuestionItem] = Field(default_factory=list)
    technical: list[QuestionItem] = Field(default_factory=list)
    business: list[QuestionItem] = Field(default_factory=list)
    collaboration: list[QuestionItem] = Field(default_factory=list)
    follow_up: list[QuestionItem] = Field(default_factory=list)


class NewsItem(BaseModel):
    source_id: int
    ref: int
    headline: str
    summary: str
    summary_is_ai: bool = False
    published_date: Optional[date] = None
    url: str
    freshness: str = "unknown"


class CompanySection(BaseModel):
    overview: list[Statement] = Field(default_factory=list)
    business_model: list[Statement] = Field(default_factory=list)
    products_services: list[Statement] = Field(default_factory=list)
    competitors: list[Statement] = Field(default_factory=list)
    strategic_initiatives: list[Statement] = Field(default_factory=list)
    challenges: list[Statement] = Field(default_factory=list)


class AttendeeSection(BaseModel):
    role: list[Statement] = Field(default_factory=list)
    experience: list[Statement] = Field(default_factory=list)
    achievements: list[Statement] = Field(default_factory=list)
    expertise: list[Statement] = Field(default_factory=list)
    public_content: list[Statement] = Field(default_factory=list)
    identity_note: Optional[str] = None


class EvidenceSummary(BaseModel):
    total_sources: int = 0
    recent_sources: int = 0
    outdated_sources: int = 0
    undated_sources: int = 0
    total_claims: int = 0
    verified: int = 0
    partially_supported: int = 0
    needs_verification: int = 0
    potentially_outdated: int = 0


class BriefingContent(BaseModel):
    meeting_overview: list[Statement] = Field(default_factory=list)
    company: CompanySection = Field(default_factory=CompanySection)
    attendee: Optional[AttendeeSection] = None
    recent_developments: list[NewsItem] = Field(default_factory=list)
    insights: list[Statement] = Field(default_factory=list)
    opportunities: list[Opportunity] = Field(default_factory=list)
    risks: list[Statement] = Field(default_factory=list)
    discussion_points: list[Statement] = Field(default_factory=list)
    strategy: list[Statement] = Field(default_factory=list)
    questions: Questions = Field(default_factory=Questions)
    evidence_summary: EvidenceSummary = Field(default_factory=EvidenceSummary)
    limitations: list[str] = Field(default_factory=list)


class SourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ref: int = 0
    category: str
    url: str
    title: str
    published_date: Optional[date] = None
    retrieved_at: datetime
    snippet: Optional[str] = None
    freshness: str

    @field_validator("retrieved_at", mode="after")
    @classmethod
    def _as_utc(cls, v):
        return _utc(v)


class BriefingResponse(BaseModel):
    meeting: MeetingRead
    is_mock: bool
    generated_at: datetime
    content: BriefingContent
    sources: list[SourceRead]

    @field_validator("generated_at", mode="after")
    @classmethod
    def _as_utc(cls, v):
        return _utc(v)


class ResearchStatusResponse(BaseModel):
    meeting_id: int
    status: str
    stage: Optional[str] = None
    progress_percent: int = 0
    error_message: Optional[str] = None
    mock_mode: bool = False


class HistoryItem(MeetingRead):
    source_count: int = 0
    has_briefing: bool = False
    generated_at: Optional[datetime] = None


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    limit: int
    offset: int


class DashboardStats(BaseModel):
    total_meetings: int
    briefings_ready: int
    upcoming_meetings: int
    researching: int
    failed: int
