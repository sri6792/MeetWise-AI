"""Clearly-labelled DEMO data for MOCK_MODE=true.

Everything here is fictional and prefixed "[MOCK DATA]". It is used only so the app
can be developed and demonstrated without API keys. Mock briefings are flagged
(is_mock) in the database, the API, the UI and the PDF.
"""
from datetime import timedelta

from app.services.tavily_service import SearchHit
from app.utils.date_utils import today_utc

TAG = "[MOCK DATA]"


def mock_hits(kind: str, org: str, attendee: str | None = None) -> list[SearchHit]:
    t = today_utc()
    if kind == "news":
        return [
            SearchHit(f"{TAG} {org} announces new partnership programme", "https://example.com/mock/news-1",
                      f"{TAG} {org} announced a sample partnership programme in a simulated news item used only for demonstration.",
                      t - timedelta(days=3)),
            SearchHit(f"{TAG} {org} expands engineering team", "https://example.org/mock/news-2",
                      f"{TAG} {org} is described as expanding its engineering team in a simulated article used only for demonstration.",
                      t - timedelta(days=11)),
            SearchHit(f"{TAG} {org} quarterly update (older)", "https://example.net/mock/news-3",
                      f"{TAG} A simulated older update about {org}, included to demonstrate the potentially-outdated label.",
                      t - timedelta(days=45)),
        ]
    if kind == "company":
        return [
            SearchHit(f"{TAG} {org} company overview", "https://example.com/mock/about",
                      f"{TAG} {org} is a fictional technology organisation described here for demonstration purposes only.",
                      t - timedelta(days=60)),
            SearchHit(f"{TAG} About {org}", "https://example.org/mock/profile",
                      f"{TAG} {org} is a fictional technology organisation described here for demonstration purposes only, offering sample platform products.",
                      t - timedelta(days=90)),
            SearchHit(f"{TAG} {org} products", "https://example.net/mock/products",
                      f"{TAG} {org} sells subscription software to business customers in this fictional demonstration profile.",
                      None),
        ]
    if kind == "person" and attendee:
        return [
            SearchHit(f"{TAG} {attendee} profile at {org}", "https://example.com/mock/person",
                      f"{TAG} {attendee} is a fictional professional at {org}, used only to demonstrate the attendee section.",
                      t - timedelta(days=200)),
            SearchHit(f"{TAG} Interview with {attendee}", "https://example.org/mock/interview",
                      f"{TAG} In a simulated interview, {attendee} discusses sample industry topics for demonstration.",
                      t - timedelta(days=20)),
        ]
    return []


def _st(text, ids, inf=False):
    return {"text": text, "source_ids": ids, "is_inference": inf}


def mock_company_findings(org: str, sources: list) -> dict:
    comp = [s for s in sources if s.category == "company"]
    news = [s for s in sources if s.category == "news"]
    return {
        "overview": [_st(comp[0].content, [comp[0].id, comp[1].id])] if len(comp) > 1 else [],
        "business_model": [_st(comp[2].content, [comp[2].id])] if len(comp) > 2 else [],
        "products_services": [_st(comp[1].content, [comp[1].id])] if len(comp) > 1 else [],
        "competitors": [_st(f"{TAG} Competitors are not known in demo mode; run real research.", [], True)],
        "strategic_initiatives": [_st(news[0].content, [news[0].id])] if news else [],
        "challenges": [_st(f"{TAG} Possible integration challenges (illustrative assumption only).", [], True)],
        "recent_developments": [{"source_id": n.id, "summary": n.content} for n in news],
        "limitations": ["Mock mode: this briefing contains demonstration data, not real research."],
    }


def mock_person_findings(attendee: str, sources: list) -> dict:
    ps = [s for s in sources if s.category == "person"]
    return {
        "role": [_st(ps[0].content, [ps[0].id])] if ps else [],
        "experience": [],
        "achievements": [],
        "expertise": [_st(ps[1].content, [ps[1].id])] if len(ps) > 1 else [],
        "public_content": [_st(ps[1].content, [ps[1].id])] if len(ps) > 1 else [],
        "identity_note": f"{TAG} Fictional attendee; no real person was researched.",
        "limitations": [],
    }


def mock_synthesis(org: str, attendee: str | None, purpose: str, sources: list) -> dict:
    ids = [s.id for s in sources[:2]]
    q = lambda text, why: {"question": text, "rationale": why, "reveals": None, "source_ids": ids[:1]}
    return {
        "meeting_overview": [_st(f"{TAG} Meeting with {org} focused on: {purpose}", [], True)],
        "insights": [_st(f"{TAG} {org} appears to be investing in partnerships (simulated).", ids[:1], True)],
        "opportunities": [{
            "title": f"{TAG} Joint pilot programme",
            "type": "collaboration",
            "description": "A small pilot could test fit before a larger commitment.",
            "why_relevant": f"Simulated news mentions a partnership programme at {org}.",
            "source_ids": ids[:1],
        }],
        "risks": [_st(f"{TAG} Unclear decision-maker for partnerships (assumption).", [], True)],
        "discussion_points": [_st(f"{TAG} Clarify success criteria for: {purpose}", [], True)],
        "strategy": [_st(f"{TAG} Open with shared goals, then agree one concrete next step.", [], True)],
        "questions": {
            "strategic": [q(f"{TAG} What outcomes would make a partnership worthwhile this year?", "Aligns on goals.")],
            "technical": [q(f"{TAG} Which systems would any integration need to connect to?", "Surfaces constraints.")],
            "business": [q(f"{TAG} How are partnership decisions budgeted and approved?", "Reveals the buying process.")],
            "collaboration": [q(f"{TAG} Would a time-boxed pilot be acceptable?", "Tests appetite for a small start.")],
            "follow_up": [q(f"{TAG} Who else should join the next conversation?", "Identifies stakeholders.")],
        },
    }
