"""People Intelligence (Feature 4): professional, public information only."""
import logging

from app.config import settings
from app.services import claude_service, mock_data
from app.services.evidence_service import as_list, clean_text, verify_statements

logger = logging.getLogger(__name__)

KEYS = ["role", "experience", "achievements", "expertise", "public_content"]

_TASK = """TASK
Build a professional profile of the attendee using only the sources above. Return JSON with exactly these keys:
{
  "role": [S], "experience": [S], "achievements": [S], "expertise": [S], "public_content": [S],
  "identity_note": "<say plainly if the sources might refer to different people with this name, or if the match to this organisation is uncertain; otherwise null>",
  "limitations": ["<what could not be found>"]
}
where S = {"text": "<one sentence>", "source_ids": [<int>], "is_inference": <bool>}.
"role" = current designation; "experience" = previous roles; "public_content" = interviews, talks or articles by or about them.
Professional information only. Return empty lists rather than guessing."""


def analyze_person(meeting, sources: list, today) -> dict:
    if settings.mock_mode:
        return mock_data.mock_person_findings(meeting.attendee_name, sources)
    user = (
        f"MEETING CONTEXT\nAttendee: {meeting.attendee_name}\nOrganisation: {meeting.organization_or_person}\n"
        f"Meeting purpose: {meeting.purpose}\nToday: {today.isoformat()}\n\n"
        f"SOURCES\n{claude_service.format_sources(sources)}\n\n{_TASK}"
    )
    return claude_service.generate_json(claude_service.GROUNDING_RULES, user, max_tokens=3500)


def verify_person(db, meeting, raw: dict, sources_by_id: dict, ref_map: dict):
    """Returns (attendee_section, limitations)."""
    section = {
        k: verify_statements(db, meeting.id, raw.get(k), f"person_{k}", sources_by_id, ref_map)
        for k in KEYS
    }
    note = clean_text(raw.get("identity_note")) or None
    section["identity_note"] = note
    limitations = [clean_text(x) for x in as_list(raw.get("limitations")) if clean_text(x)]
    return section, limitations
