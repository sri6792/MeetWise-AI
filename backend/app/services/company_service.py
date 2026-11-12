"""Company Intelligence (Feature 3) + the Claude analysis of news (Feature 2 summaries)."""
import logging

from app.config import settings
from app.services import claude_service, mock_data
from app.services.evidence_service import as_list, clean_text, int_list, verify_statements

logger = logging.getLogger(__name__)

KEYS = ["overview", "business_model", "products_services", "competitors", "strategic_initiatives", "challenges"]

_TASK = """TASK
Analyse the organisation using only the sources above. Return JSON with exactly these keys:
{
  "overview": [S], "business_model": [S], "products_services": [S],
  "competitors": [S], "strategic_initiatives": [S], "challenges": [S],
  "recent_developments": [{"source_id": <id of a NEWS source>, "summary": "<one-sentence summary>"}],
  "limitations": ["<anything important the sources could not tell us>"]
}
where S = {"text": "<one sentence>", "source_ids": [<int>], "is_inference": <bool>}.
Give 1-4 items per list; use an empty list when the sources say nothing. "competitors" and "challenges" are usually
inferences unless a source states them. Summarise every news source in "recent_developments"."""


def analyze_company(meeting, sources: list, today) -> dict:
    if settings.mock_mode:
        return mock_data.mock_company_findings(meeting.organization_or_person, sources)
    user = (
        f"MEETING CONTEXT\nOrganisation: {meeting.organization_or_person}\n"
        f"Meeting purpose: {meeting.purpose}\nToday: {today.isoformat()}\n\n"
        f"SOURCES\n{claude_service.format_sources(sources)}\n\n{_TASK}"
    )
    return claude_service.generate_json(claude_service.GROUNDING_RULES, user, max_tokens=4500)


def verify_company(db, meeting, raw: dict, sources_by_id: dict, ref_map: dict):
    """Returns (company_section, {news_source_id: ai_summary}, limitations)."""
    section = {
        k: verify_statements(
            db, meeting.id, raw.get(k), f"company_{k}", sources_by_id, ref_map,
            default_inference=k in ("competitors", "challenges"),
        )
        for k in KEYS
    }
    summaries: dict[int, str] = {}
    for item in as_list(raw.get("recent_developments")):
        if not isinstance(item, dict):
            continue
        ids = int_list(item.get("source_id"))
        sid = ids[0] if ids else None
        summary = clean_text(item.get("summary"))
        if sid in sources_by_id and sources_by_id[sid].category == "news" and summary:
            summaries[sid] = summary
    limitations = [clean_text(x) for x in as_list(raw.get("limitations")) if clean_text(x)]
    return section, summaries, limitations
