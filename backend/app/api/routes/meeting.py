import logging
from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models import Meeting, MeetingStatus
from app.schemas.meeting_schema import (
    MeetingCreateRequest,
    MeetingListResponse,
    MeetingPreviewResponse,
    MeetingRead,
    MeetingUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/meetings",
    tags=["Meetings"]
)


def _get_or_404(db: Session, meeting_id: int) -> Meeting:
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")
    return meeting


def apply_filters(stmt, q, status_filter, date_from, date_to):
    """Shared by the meeting list and the history list."""
    if q and q.strip():
        term = q.strip()
        stmt = stmt.where(
            or_(
                Meeting.organization_or_person.icontains(term, autoescape=True),
                Meeting.attendee_name.icontains(term, autoescape=True),
                Meeting.purpose.icontains(term, autoescape=True),
            )
        )
    if status_filter:
        stmt = stmt.where(Meeting.status == status_filter.value)
    if date_from:
        stmt = stmt.where(Meeting.meeting_date >= date_from)
    if date_to:
        stmt = stmt.where(Meeting.meeting_date <= date_to)
    return stmt


# Existing endpoint - behaviour unchanged (validate only, no saving)
@router.post("/preview", response_model=MeetingPreviewResponse)
def preview_meeting(meeting: MeetingCreateRequest):

    return {
        "status": "success",
        "message": "Meeting details validated successfully!",
        "meeting": meeting
    }


@router.post("", response_model=MeetingRead, status_code=status.HTTP_201_CREATED)
def create_meeting(payload: MeetingCreateRequest, db: Session = Depends(get_db)):
    meeting = Meeting(**payload.model_dump())
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    logger.info("Created meeting id=%s org=%r", meeting.id, meeting.organization_or_person)
    return meeting


@router.get("", response_model=MeetingListResponse)
def list_meetings(
    q: Optional[str] = Query(None, max_length=100, description="Search company, attendee or purpose"),
    status_filter: Optional[MeetingStatus] = Query(None, alias="status"),
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    sort: Literal["date_desc", "date_asc", "created_desc"] = "date_desc",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="date_from must not be after date_to")

    stmt = apply_filters(select(Meeting), q, status_filter, date_from, date_to)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    if sort == "date_asc":
        stmt = stmt.order_by(Meeting.meeting_date.asc(), Meeting.meeting_time.asc(), Meeting.id.asc())
    elif sort == "created_desc":
        stmt = stmt.order_by(Meeting.created_at.desc(), Meeting.id.desc())
    else:
        stmt = stmt.order_by(Meeting.meeting_date.desc(), Meeting.meeting_time.desc(), Meeting.id.desc())

    items = db.scalars(stmt.limit(limit).offset(offset)).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{meeting_id}", response_model=MeetingRead)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    return _get_or_404(db, meeting_id)


@router.patch("/{meeting_id}", response_model=MeetingRead)
def update_meeting(meeting_id: int, payload: MeetingUpdateRequest, db: Session = Depends(get_db)):
    meeting = _get_or_404(db, meeting_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(meeting, field, value)
    db.commit()
    db.refresh(meeting)
    logger.info("Updated meeting id=%s fields=%s", meeting_id, sorted(payload.model_fields_set))
    return meeting


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = _get_or_404(db, meeting_id)
    db.delete(meeting)  # cascades to sources, claims and briefing
    db.commit()
    logger.info("Deleted meeting id=%s", meeting_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
