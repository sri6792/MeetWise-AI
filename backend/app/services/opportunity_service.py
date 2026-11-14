"""Opportunity & Question Intelligence (Features 6 and 9) and the briefing synthesis."""
import logging

from app.config import settings
from app.models import Claim
from app.services import claude_service, mock_data
from app.services.evidence_service import (
    as_list, clean_text, evaluate_claim, int_list, verify_statements,
)

logger = logging.getLogger(__name__)

QUESTION_KEYS = ["strategic", "technical", "business", "collaboration", "follow_up"]
OPP_TYPES = {"collaboration", "business", "partnership"}

_TASK = """TASK
Using the verified findings and sources above, produce a briefing personalised to the meeting purpose.
Return JSON with exactly these keys:
{
  "meeting_overview": [S],
  "insights": [S],
  "opportunities": [{"title": "", "type": "collaboration|business|partnership", "description": "",
                     "why_relevant": "", "source_ids": [<int>]}],
  "risks": [S],
  "discussion_points": [S],
  "strategy": [S],
  "questions": {"strategic": [Q], "technical": [Q], "business": [Q], "collaboration": [Q], "follow_up": [Q]}
}
S = {"text": "<one sentence>", "source_ids": [<int>], "is_inference": <bool>}
Q = {"question": "", "rationale": "<why ask this>", "reveals": "<the opportunity or risk this could uncover, or null>", "source_ids": [<int>]}
Guidance (do NOT put comments in the JSON):
- meeting_overview: 2-3 statements on what this meeting is and what success looks like.
- insights: 3-5 important insights that follow from the evidence.
- opportunities: 2-4; "why_relevant" must explain why it fits THIS meeting purpose.
- risks: 2-4 possible challenges. discussion_points: 4-6. strategy: 2-4 statements.
- questions: 2-3 per category. They must refer to specific researched facts or the meeting purpose;
  generic questions such as "What are your goals?" are not acceptable.
- Mark interpretation and advice as is_inference true.
- Output raw JSON only: no comments, no trailing commas, no markdown."""


def _findings_text(company: dict, attendee: dict | None, news_items: list) -> str:
    lines: list[str] = []

    def add(title: str, items: list):
        for s in items:
            ids = ",".join(f"S{i}" for i in s["source_ids"]) or "no source"
            lines.append(f"- [{title}] ({s['evidence_label']}) {s['text']} [{ids}]")

    for k, items in company.items():
        add(f"company/{k}", items)
    if attendee:
        for k, items in attendee.items():
            if isinstance(items, list):
                add(f"attendee/{k}", items)
        if attendee.get("identity_note"):
            lines.append(f"- [attendee/identity note] {attendee['identity_note']}")
    for n in news_items[:8]:
        d = n["published_date"] or "date unknown"
        lines.append(f"- [news] ({n['freshness']}, {d}) {n['headline']} [S{n['source_id']}]")
    return "\n".join(lines) or "(no findings)"


def generate_insights(meeting, company: dict, attendee: dict | None, news_items: list, sources: list, today) -> dict:
    if settings.mock_mode:
        return mock_data.mock_synthesis(meeting.organization_or_person, meeting.attendee_name, meeting.purpose, sources)
    user = (
        "MEETING CONTEXT\n"
        f"Organisation: {meeting.organization_or_person}\n"
        f"Attendee: {meeting.attendee_name or 'not specified'}\n"
        f"Date: {meeting.meeting_date} {meeting.meeting_time}\n"
        f"Purpose: {meeting.purpose}\nToday: {today.isoformat()}\n\n"
        f"VERIFIED FINDINGS (with evidence labels)\n{_findings_text(company, attendee, news_items)}\n\n"
        f"SOURCES\n{claude_service.format_sources(sources, max_chars=500)}\n\n{_TASK}"
    )
    return claude_service.generate_json(claude_service.GROUNDING_RULES, user, max_tokens=6000)


def _question_items(raw, sources_by_id: dict, ref_map: dict) -> list[dict]:
    out = []
    for item in as_list(raw):
        if isinstance(item, str):
            item = {"question": item}
        if not isinstance(item, dict):
            continue
        q = clean_text(item.get("question"))
        if not q:
            continue
        ids = [i for i in dict.fromkeys(int_list(item.get("source_ids"))) if i in sources_by_id]
        out.append({
            "question": q,
            "rationale": clean_text(item.get("rationale")) or None,
            "reveals": clean_text(item.get("reveals")) or None,
            "source_ids": ids,
            "refs": [ref_map[i] for i in ids],
        })
    return out


def verify_insights(db, meeting, raw: dict, sources_by_id: dict, ref_map: dict) -> dict:
    mid = meeting.id
    result = {
        "meeting_overview": verify_statements(db, mid, raw.get("meeting_overview"), "overview", sources_by_id, ref_map, True),
        "insights": verify_statements(db, mid, raw.get("insights"), "insight", sources_by_id, ref_map, True),
        "risks": verify_statements(db, mid, raw.get("risks"), "risk", sources_by_id, ref_map, True),
        "discussion_points": verify_statements(db, mid, raw.get("discussion_points"), "discussion", sources_by_id, ref_map, True),
        "strategy": verify_statements(db, mid, raw.get("strategy"), "strategy", sources_by_id, ref_map, True),
    }

    opportunities = []
    for item in as_list(raw.get("opportunities")):
        if not isinstance(item, dict):
            continue
        title = clean_text(item.get("title"))
        desc = clean_text(item.get("description"))
        why = clean_text(item.get("why_relevant"))
        if not title:
            continue
        otype = clean_text(item.get("type")).lower()
        otype = otype if otype in OPP_TYPES else "business"
        # Opportunities are always interpretations: they can be supported, never "verified fact"
        verdict = evaluate_claim(f"{title}. {desc} {why}", int_list(item.get("source_ids")), sources_by_id, True)
        claim = Claim(
            meeting_id=mid, section="opportunity", text=f"{title}. {desc}".strip(),
            evidence_label=verdict.label, source_ids=verdict.valid_ids, is_inference=True, note=verdict.note,
        )
        db.add(claim)
        db.flush()
        opportunities.append({
            "title": title, "type": otype, "description": desc, "why_relevant": why,
            "source_ids": verdict.valid_ids, "refs": [ref_map[i] for i in verdict.valid_ids],
            "evidence_label": verdict.label, "is_inference": True, "note": verdict.note, "claim_id": claim.id,
        })
    result["opportunities"] = opportunities

    qraw = raw.get("questions") if isinstance(raw.get("questions"), dict) else {}
    result["questions"] = {k: _question_items(qraw.get(k), sources_by_id, ref_map) for k in QUESTION_KEYS}
    return result
