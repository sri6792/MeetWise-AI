"""Assembles the final briefing from verified pieces and stores it."""
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.models import Briefing, Claim, Meeting
from app.schemas.briefing_schema import BriefingContent
from app.services.evidence_service import summarize_evidence
from app.utils.helpers import truncate

logger = logging.getLogger(__name__)


def build_ref_map(sources: list) -> dict[int, int]:
    """Stable human-friendly numbering [1], [2]... in source-id order."""
    return {s.id: i for i, s in enumerate(sorted(sources, key=lambda s: s.id), start=1)}


def build_news_items(sources: list, ai_summaries: dict[int, str], ref_map: dict[int, int]) -> list[dict]:
    news = [s for s in sources if s.category == "news"]
    # newest first; undated last
    news.sort(key=lambda s: (s.published_date is not None, s.published_date or 0), reverse=True)
    items = []
    for s in news:
        ai = ai_summaries.get(s.id)
        items.append({
            "source_id": s.id,
            "ref": ref_map[s.id],
            "headline": s.title,
            "summary": ai or truncate(s.snippet or s.content, 280),
            "summary_is_ai": bool(ai),
            "published_date": s.published_date.isoformat() if s.published_date else None,
            "url": s.url,
            "freshness": s.freshness,
        })
    return items


def save_briefing(
    db: Session,
    meeting: Meeting,
    sources: list,
    company: dict,
    attendee: dict | None,
    news_items: list[dict],
    insights: dict,
    limitations: list[str],
) -> Briefing:
    claims = db.query(Claim).filter(Claim.meeting_id == meeting.id).all()
    content = BriefingContent.model_validate(
        {
            "meeting_overview": insights["meeting_overview"],
            "company": company,
            "attendee": attendee,
            "recent_developments": news_items,
            "insights": insights["insights"],
            "opportunities": insights["opportunities"],
            "risks": insights["risks"],
            "discussion_points": insights["discussion_points"],
            "strategy": insights["strategy"],
            "questions": insights["questions"],
            "evidence_summary": summarize_evidence(sources, claims),
            "limitations": list(dict.fromkeys(limitations)),
        }
    ).model_dump(mode="json")

    briefing = Briefing(meeting_id=meeting.id, content=content, is_mock=settings.mock_mode)
    db.add(briefing)
    db.flush()
    return briefing
