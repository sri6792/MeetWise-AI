import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db, get_session_factory
from app.config import settings
from app.models import Briefing, Meeting, MeetingStatus, Source
from app.schemas.briefing_schema import ResearchStatusResponse, SourceRead
from app.services import briefing_service
from app.services.research_service import run_research_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/meetings", tags=["Research"])


def _meeting_or_404(db: Session, meeting_id: int) -> Meeting:
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")
    return meeting


def _status_payload(m: Meeting) -> dict:
    return {
        "meeting_id": m.id,
        "status": m.status,
        "stage": m.progress_stage,
        "progress_percent": m.progress_percent or 0,
        "error_message": m.error_message,
        "mock_mode": settings.mock_mode,
    }


@router.post("/{meeting_id}/research", response_model=ResearchStatusResponse, status_code=status.HTTP_202_ACCEPTED)
def start_research(
    meeting_id: int,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
    session_factory=Depends(get_session_factory),
):
    """Starts research + briefing generation in the background. Poll GET /{id}/status."""
    meeting = _meeting_or_404(db, meeting_id)
    if meeting.status == MeetingStatus.RESEARCHING.value:
        raise HTTPException(status_code=409, detail="Research is already running for this meeting")

    if not settings.mock_mode:
        missing = (["TAVILY_API_KEY"] if not settings.tavily_api_key else []) + settings.llm_missing
        if missing:
            raise HTTPException(
                status_code=503,
                detail=f"Missing configuration: {', '.join(missing)}. Add it to backend/.env, or set MOCK_MODE=true for demo data.",
            )

    meeting.status = MeetingStatus.RESEARCHING.value
    meeting.progress_stage = "queued"
    meeting.progress_percent = 0
    meeting.error_message = None
    db.commit()
    db.refresh(meeting)

    background.add_task(run_research_pipeline, meeting_id, session_factory)
    return _status_payload(meeting)


@router.get("/{meeting_id}/status", response_model=ResearchStatusResponse)
def research_status(meeting_id: int, db: Session = Depends(get_db)):
    return _status_payload(_meeting_or_404(db, meeting_id))


@router.get("/{meeting_id}/sources", response_model=list[SourceRead])
def list_sources(
    meeting_id: int,
    category: str | None = Query(None, pattern="^(news|company|person|other)$"),
    db: Session = Depends(get_db),
):
    """The raw evidence: every source with URL, title, publication date, retrieval date and freshness."""
    _meeting_or_404(db, meeting_id)
    all_sources = db.query(Source).filter(Source.meeting_id == meeting_id).order_by(Source.id).all()
    ref_map = briefing_service.build_ref_map(all_sources)
    out = []
    for s in all_sources:
        if category and s.category != category:
            continue
        item = SourceRead.model_validate(s)
        item.ref = ref_map[s.id]
        out.append(item)
    return out


@router.get("/{meeting_id}/news")
def list_news(meeting_id: int, db: Session = Depends(get_db)):
    """Feature 2: news items (headline, summary, date, link). Empty list = no recent news found."""
    _meeting_or_404(db, meeting_id)
    briefing = db.query(Briefing).filter(Briefing.meeting_id == meeting_id).first()
    return briefing.content.get("recent_developments", []) if briefing else []
