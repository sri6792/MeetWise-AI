"""Research pipeline: search -> store evidence -> analyse -> verify -> briefing.

Runs in a background task. Progress is written to the meeting row so the frontend
can show *real* progress instead of a fake timer.
"""
import logging

from sqlalchemy.orm import Session

from app.config import settings
from app.database.connection import SessionLocal
from app.models import Briefing, Claim, Meeting, MeetingStatus, Source
from app.services import (
    briefing_service, claude_service, company_service, mock_data,
    opportunity_service, people_service, tavily_service,
)
from app.services.claude_service import ClaudeServiceError
from app.services.evidence_service import classify_freshness
from app.services.tavily_service import SearchHit, TavilyServiceError
from app.utils.date_utils import today_utc
from app.utils.helpers import normalise_url, truncate

logger = logging.getLogger(__name__)


class ResearchError(Exception):
    """A user-presentable reason why research could not complete."""


# ------------------------------------------------------------------ collection

def collect_news(org: str) -> list[SearchHit]:
    if settings.mock_mode:
        return mock_data.mock_hits("news", org)
    hits = tavily_service.search(f"{org} latest news", topic="news", days=settings.news_window_days, max_results=8)
    if not hits:  # fall back to general web results; freshness labels will reveal their age
        hits = tavily_service.search(f"{org} news announcements", topic="general", max_results=5)
    return hits


def collect_company(org: str) -> list[SearchHit]:
    if settings.mock_mode:
        return mock_data.mock_hits("company", org)
    hits = tavily_service.search(f"{org} company overview products services business model", max_results=6)
    hits += tavily_service.search(f"{org} competitors strategy initiatives challenges", max_results=5)
    # enrich the top pages with fuller extracted text
    top = [h.url for h in sorted(hits, key=lambda h: h.score or 0, reverse=True)[:2]]
    extracted = tavily_service.extract(top)
    for h in hits:
        if h.url in extracted:
            h.content = extracted[h.url]
    return hits


def collect_person(attendee: str, org: str) -> list[SearchHit]:
    if settings.mock_mode:
        return mock_data.mock_hits("person", org, attendee)
    hits = tavily_service.search(f'"{attendee}" {org} professional background current role', max_results=6)
    hits += tavily_service.search(f'"{attendee}" {org} interview OR keynote OR article', max_results=5)

    # Relevance guard: keep only pages that actually mention this person (and ideally the organisation)
    name, org_l = attendee.lower(), org.lower()
    last = name.split()[-1] if name.split() else name
    kept = []
    for h in hits:
        text = f"{h.title} {h.content}".lower()
        if name in text or (len(last) >= 3 and last in text and org_l in text):
            kept.append(h)
    return kept


def _guard(fn, label: str, limitations: list[str]) -> list[SearchHit]:
    """Run one search step. Fatal errors (bad key / rate limit) abort; others become limitations."""
    try:
        return fn()
    except TavilyServiceError as exc:
        if exc.kind in ("config", "auth", "rate_limit"):
            raise
        limitations.append(f"{label} failed and was skipped: {exc}")
        return []


# ------------------------------------------------------------------ pipeline

def _progress(db: Session, meeting: Meeting, stage: str, percent: int) -> None:
    meeting.progress_stage = stage
    meeting.progress_percent = percent
    db.commit()


def _clear_previous(db: Session, meeting_id: int) -> None:
    db.query(Claim).filter(Claim.meeting_id == meeting_id).delete()
    db.query(Source).filter(Source.meeting_id == meeting_id).delete()
    db.query(Briefing).filter(Briefing.meeting_id == meeting_id).delete()
    db.commit()


def _fail(session_factory, meeting_id: int, message: str) -> None:
    db = session_factory()
    try:
        m = db.get(Meeting, meeting_id)
        if m:
            m.status = MeetingStatus.FAILED.value
            m.progress_stage = "failed"
            m.error_message = message
            db.commit()
    finally:
        db.close()


def run_research_pipeline(meeting_id: int, session_factory=SessionLocal) -> None:
    db = session_factory()
    try:
        meeting = db.get(Meeting, meeting_id)
        if meeting is None:
            return
        org, attendee = meeting.organization_or_person, meeting.attendee_name
        today = today_utc()
        limitations: list[str] = []
        logger.info("Research started meeting=%s org=%r mock=%s", meeting_id, org, settings.mock_mode)

        _clear_previous(db, meeting_id)
        meeting.status = MeetingStatus.RESEARCHING.value
        meeting.error_message = None
        _progress(db, meeting, "searching_news", 10)

        news_hits = _guard(lambda: collect_news(org), "News search", limitations)
        if not news_hits:
            limitations.append(f"No recent news was found for {org}.")

        _progress(db, meeting, "researching_company", 25)
        company_hits = _guard(lambda: collect_company(org), "Company research", limitations)

        person_hits: list[SearchHit] = []
        if attendee:
            _progress(db, meeting, "researching_people", 40)
            person_hits = _guard(lambda: collect_person(attendee, org), "Attendee research", limitations)
            if not person_hits:
                limitations.append(
                    f"No reliable public professional information was found for {attendee}; "
                    "the attendee section was skipped rather than guessed."
                )
        else:
            limitations.append("No attendee name was given, so attendee research was skipped.")

        # ---- store retrieved evidence (never modified by AI)
        _progress(db, meeting, "verifying_evidence", 50)
        sources: list[Source] = []
        seen: set[str] = set()
        for category, hits in (("news", news_hits), ("company", company_hits), ("person", person_hits)):
            for h in hits:
                key = normalise_url(h.url)
                if key in seen or len(sources) >= settings.max_sources_total:
                    continue
                seen.add(key)
                src = Source(
                    meeting_id=meeting_id,
                    category=category,
                    url=h.url,
                    title=truncate(h.title, 500),
                    published_date=h.published_date,
                    snippet=truncate(h.content, 500),
                    content=truncate(h.content, 4000),
                    freshness=classify_freshness(h.published_date, category, today),
                )
                db.add(src)
                sources.append(src)
        db.flush()
        if not sources:
            raise ResearchError(
                f"No sources were found for '{org}'. Check the spelling of the name or try again later."
            )
        db.commit()

        sources_by_id = {s.id: s for s in sources}
        ref_map = briefing_service.build_ref_map(sources)

        # ---- company analysis
        _progress(db, meeting, "analysing_company", 60)
        company_sources = [s for s in sources if s.category in ("news", "company")]
        raw_company = company_service.analyze_company(meeting, company_sources, today)
        company, ai_summaries, lim = company_service.verify_company(db, meeting, raw_company, sources_by_id, ref_map)
        limitations += lim
        news_items = briefing_service.build_news_items(sources, ai_summaries, ref_map)

        # ---- attendee analysis
        attendee_section = None
        person_sources = [s for s in sources if s.category == "person"]
        if person_sources:
            _progress(db, meeting, "analysing_person", 72)
            raw_person = people_service.analyze_person(meeting, person_sources, today)
            attendee_section, lim = people_service.verify_person(db, meeting, raw_person, sources_by_id, ref_map)
            limitations += lim
        db.commit()

        # ---- synthesis: insights, opportunities, questions
        _progress(db, meeting, "generating_briefing", 85)
        raw_insights = opportunity_service.generate_insights(
            meeting, company, attendee_section, news_items, sources, today
        )
        insights = opportunity_service.verify_insights(db, meeting, raw_insights, sources_by_id, ref_map)

        briefing_service.save_briefing(db, meeting, sources, company, attendee_section, news_items, insights, limitations)
        meeting.status = MeetingStatus.READY.value
        meeting.progress_stage = "done"
        meeting.progress_percent = 100
        db.commit()
        logger.info("Research finished meeting=%s sources=%d", meeting_id, len(sources))

    except (ResearchError, TavilyServiceError, ClaudeServiceError) as exc:
        db.rollback()
        logger.warning("Research failed meeting=%s: %s", meeting_id, exc)
        _fail(session_factory, meeting_id, str(exc))
    except Exception:
        db.rollback()
        logger.exception("Unexpected research failure meeting=%s", meeting_id)
        _fail(session_factory, meeting_id, "An unexpected error occurred while researching. Please try again.")
    finally:
        db.close()
