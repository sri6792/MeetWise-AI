from datetime import date, datetime, time, timezone
from types import SimpleNamespace as NS

import pytest

from app.services import pdf_service, tavily_service
from app.services.tavily_service import TavilyServiceError


class FakeClient:
    def __init__(self, response=None, error=None):
        self.response, self.error = response, error

    def search(self, **kwargs):
        if self.error:
            raise self.error
        return self.response


def test_search_parses_results_without_inventing_dates(monkeypatch):
    resp = {"results": [
        {"title": "A", "url": "https://a.com/1", "content": "c", "published_date": "2026-11-03", "score": 0.9},
        {"title": "B", "url": "https://b.com/2", "content": "c", "published_date": "not a date"},
        {"title": "dup", "url": "https://a.com/1", "content": "x"},
        {"title": "no url", "content": "x"},
    ]}
    monkeypatch.setattr(tavily_service, "_client", lambda: FakeClient(resp))
    hits = tavily_service.search("q")
    assert [h.url for h in hits] == ["https://a.com/1", "https://b.com/2"]
    assert hits[0].published_date == date(2026, 11, 3)
    assert hits[1].published_date is None


def test_search_translates_rate_limit(monkeypatch):
    monkeypatch.setattr(tavily_service, "_client", lambda: FakeClient(error=Exception("429 usage limit exceeded")))
    with pytest.raises(TavilyServiceError) as e:
        tavily_service.search("q")
    assert e.value.kind == "rate_limit"


def test_search_without_key_is_a_config_error(monkeypatch):
    monkeypatch.setattr(tavily_service.settings, "tavily_api_key", "")
    with pytest.raises(TavilyServiceError) as e:
        tavily_service.search("q")
    assert e.value.kind == "config"


def test_pdf_builds_and_survives_hostile_text():
    st = lambda t, l="verified": {"text": t, "refs": [1], "evidence_label": l, "is_inference": False}
    content = {
        "meeting_overview": [st("R&D <Lead> says “hi” 日本語 🚀")],
        "company": {"overview": [st("Acme builds software.")]},
        "attendee": None, "recent_developments": [], "insights": [], "opportunities": [], "risks": [],
        "discussion_points": [], "strategy": [], "questions": {}, "evidence_summary": {}, "limitations": ["gap"],
    }
    meeting = NS(organization_or_person="Acme & Sons", attendee_name=None, meeting_date=date(2026, 11, 20),
                 meeting_time=time(10, 30), purpose="Talk <now>")
    briefing = NS(content=content, is_mock=True, generated_at=datetime(2026, 11, 10, tzinfo=timezone.utc))
    sources = [NS(id=1, category="news", title="S & T", url="https://x.com/?a=1&b=2", published_date=None,
                  retrieved_at=datetime(2026, 11, 10, tzinfo=timezone.utc), freshness="unknown")]
    data = pdf_service.build_pdf(meeting, briefing, sources)
    assert data.startswith(b"%PDF")
