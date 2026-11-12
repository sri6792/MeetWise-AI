from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.routes.meeting import apply_filters
from app.models import Briefing, Meeting, MeetingStatus, Source
from app.schemas.briefing_schema import DashboardStats, HistoryItem, HistoryListResponse
from app.schemas.meeting_schema import MeetingRead

router = APIRouter(prefix="/api/history", tags=["History"])


@router.get("", response_model=HistoryListResponse)
def list_history(
    q: Optional[str] = Query(None, max_length=100),
    status_filter: Optional[MeetingStatus] = Query(None, alias="status"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort: Literal["date_desc", "date_asc", "created_desc"] = "date_desc",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Meeting history with briefing info. Search, filter, sort and paginate."""
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")

    base = apply_filters(select(Meeting), q, status_filter, date_from, date_to)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0

    src_count = select(func.count(Source.id)).where(Source.meeting_id == Meeting.id).correlate(Meeting).scalar_subquery()
    gen_at = select(Briefing.generated_at).where(Briefing.meeting_id == Meeting.id).correlate(Meeting).scalar_subquery()
    stmt = apply_filters(select(Meeting, src_count, gen_at), q, status_filter, date_from, date_to)

    if sort == "date_asc":
        stmt = stmt.order_by(Meeting.meeting_date.asc(), Meeting.meeting_time.asc(), Meeting.id.asc())
    elif sort == "created_desc":
        stmt = stmt.order_by(Meeting.created_at.desc(), Meeting.id.desc())
    else:
        stmt = stmt.order_by(Meeting.meeting_date.desc(), Meeting.meeting_time.desc(), Meeting.id.desc())

    items = []
    for meeting, sc, ga in db.execute(stmt.limit(limit).offset(offset)).all():
        data = MeetingRead.model_validate(meeting).model_dump()
        items.append(HistoryItem(**data, source_count=sc or 0, has_briefing=ga is not None, generated_at=ga))
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/stats", response_model=DashboardStats)
def dashboard_stats(today: Optional[date] = None, db: Session = Depends(get_db)):
    """Numbers for the dashboard cards. Pass the user's local date as ?today=YYYY-MM-DD."""
    today = today or date.today()

    def count(*conds) -> int:
        return db.scalar(select(func.count(Meeting.id)).where(*conds)) or 0

    return {
        "total_meetings": count(),
        "briefings_ready": db.scalar(select(func.count(Briefing.id))) or 0,
        "upcoming_meetings": count(Meeting.meeting_date >= today),
        "researching": count(Meeting.status == MeetingStatus.RESEARCHING.value),
        "failed": count(Meeting.status == MeetingStatus.FAILED.value),
    }
