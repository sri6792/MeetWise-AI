import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.models import Briefing, Meeting, Source
from app.schemas.briefing_schema import BriefingResponse, SourceRead
from app.schemas.meeting_schema import MeetingRead
from app.services import briefing_service, pdf_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/meetings", tags=["Briefing"])


def _load(db: Session, meeting_id: int):
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")
    briefing = db.query(Briefing).filter(Briefing.meeting_id == meeting_id).first()
    if briefing is None:
        raise HTTPException(status_code=404, detail="No briefing has been generated for this meeting yet")
    sources = db.query(Source).filter(Source.meeting_id == meeting_id).order_by(Source.id).all()
    return meeting, briefing, sources


@router.get("/{meeting_id}/briefing", response_model=BriefingResponse)
def get_briefing(meeting_id: int, db: Session = Depends(get_db)):
    meeting, briefing, sources = _load(db, meeting_id)
    ref_map = briefing_service.build_ref_map(sources)
    source_models = []
    for s in sources:
        item = SourceRead.model_validate(s)
        item.ref = ref_map[s.id]
        source_models.append(item)
    return BriefingResponse(
        meeting=MeetingRead.model_validate(meeting),
        is_mock=briefing.is_mock,
        generated_at=briefing.generated_at,
        content=briefing.content,
        sources=source_models,
    )


@router.get("/{meeting_id}/pdf")
def download_pdf(meeting_id: int, db: Session = Depends(get_db)):
    meeting, briefing, sources = _load(db, meeting_id)
    try:
        pdf_bytes = pdf_service.build_pdf(meeting, briefing, sources)
    except Exception:
        logger.exception("PDF generation failed for meeting %s", meeting_id)
        raise HTTPException(status_code=500, detail="Could not generate the PDF")
    slug = re.sub(r"[^A-Za-z0-9]+", "-", meeting.organization_or_person).strip("-")[:40] or "meeting"
    filename = f"MeetWise-Briefing-{slug}-{meeting.meeting_date}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
