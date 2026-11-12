import re
from datetime import date, timedelta

from app.models import Briefing, Claim, Meeting, Source
from app.services import claude_service, research_service, tavily_service
from app.services.tavily_service import SearchHit, TavilyServiceError


def make_meeting(client, **over):
    payload = {"organization_or_person": "Acme", "attendee_name": "Jane Doe", "meeting_date": "2026-11-20",
               "meeting_time": "10:30:00", "purpose": "Explore a payments partnership"}
    payload.update(over)
    r = client.post("/api/meetings", json=payload)
    assert r.status_code == 201
    return r.json()["id"]


# ----------------------------------------------------------------- guard rails

def test_research_requires_keys_unless_mock(client, monkeypatch):
    monkeypatch.setattr("app.config.settings.mock_mode", False)
    monkeypatch.setattr("app.config.settings.tavily_api_key", "")
    monkeypatch.setattr("app.config.settings.anthropic_api_key", "")
    mid = make_meeting(client)
    r = client.post(f"/api/meetings/{mid}/research")
    assert r.status_code == 503
    assert "TAVILY_API_KEY" in r.json()["detail"]
    assert client.get(f"/api/meetings/{mid}/status").json()["status"] == "created"


def test_unknown_meeting_returns_404_everywhere(client, mock_mode):
    for method, path in [("post", "research"), ("get", "status"), ("get", "sources"),
                         ("get", "news"), ("get", "briefing"), ("get", "pdf")]:
        assert getattr(client, method)(f"/api/meetings/9999/{path}").status_code == 404


def test_briefing_before_research_is_404(client):
    mid = make_meeting(client)
    r = client.get(f"/api/meetings/{mid}/briefing")
    assert r.status_code == 404 and "yet" in r.json()["detail"]
    assert client.get(f"/api/meetings/{mid}/pdf").status_code == 404


def test_cannot_start_research_twice_concurrently(client, mock_mode, db_session):
    mid = make_meeting(client)
    m = db_session.get(Meeting, mid)
    m.status = "researching"
    db_session.commit()
    assert client.post(f"/api/meetings/{mid}/research").status_code == 409


# ----------------------------------------------------------------- full mock pipeline

def test_mock_pipeline_end_to_end(client, mock_mode, db_session):
    mid = make_meeting(client)
    r = client.post(f"/api/meetings/{mid}/research")
    assert r.status_code == 202

    status = client.get(f"/api/meetings/{mid}/status").json()
    assert status["status"] == "ready" and status["progress_percent"] == 100 and status["mock_mode"] is True

    b = client.get(f"/api/meetings/{mid}/briefing")
    assert b.status_code == 200
    body = b.json()
    assert body["is_mock"] is True
    c = body["content"]
    assert len(body["sources"]) == 8                                   # 3 news + 3 company + 2 person
    assert all(s["title"].startswith("[MOCK DATA]") for s in body["sources"])
    assert c["company"]["overview"][0]["evidence_label"] == "verified"  # 2 domains + recent
    assert any(x["evidence_label"] == "needs_verification" for x in c["company"]["competitors"])
    assert c["attendee"]["role"], "attendee section should exist when an attendee is given"
    assert len(c["recent_developments"]) == 3
    assert c["opportunities"] and c["questions"]["strategic"] and c["strategy"]
    assert c["evidence_summary"]["total_sources"] == 8

    # every reference points at a real source
    valid_refs = {s["ref"] for s in body["sources"]}
    for item in c["company"]["overview"] + c["insights"]:
        assert set(item["refs"]) <= valid_refs

    # old-news item is flagged, not hidden
    assert "potentially_outdated" in {n["freshness"] for n in c["recent_developments"]}

    # news endpoint, sources endpoint with filter
    assert len(client.get(f"/api/meetings/{mid}/news").json()) == 3
    assert len(client.get(f"/api/meetings/{mid}/sources", params={"category": "person"}).json()) == 2
    assert client.get(f"/api/meetings/{mid}/sources", params={"category": "bogus"}).status_code == 422

    # PDF
    pdf = client.get(f"/api/meetings/{mid}/pdf")
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert pdf.headers["content-type"] == "application/pdf"
    assert "attachment" in pdf.headers["content-disposition"]

    # history + stats
    h = client.get("/api/history").json()
    assert h["total"] == 1 and h["items"][0]["has_briefing"] is True and h["items"][0]["source_count"] == 8
    stats = client.get("/api/history/stats", params={"today": "2026-11-01"}).json()
    assert stats == {"total_meetings": 1, "briefings_ready": 1, "upcoming_meetings": 1, "researching": 0, "failed": 0}

    # DB state
    db_session.expire_all()
    assert db_session.query(Source).count() == 8
    assert db_session.query(Claim).count() > 5
    assert db_session.query(Briefing).one().is_mock is True


def test_rerun_replaces_old_research(client, mock_mode, db_session):
    mid = make_meeting(client)
    client.post(f"/api/meetings/{mid}/research")
    client.post(f"/api/meetings/{mid}/research")
    db_session.expire_all()
    assert db_session.query(Source).count() == 8
    assert db_session.query(Briefing).count() == 1


def test_meeting_without_attendee_skips_people_research(client, mock_mode):
    mid = make_meeting(client, attendee_name=None)
    client.post(f"/api/meetings/{mid}/research")
    body = client.get(f"/api/meetings/{mid}/briefing").json()
    assert body["content"]["attendee"] is None
    assert any("No attendee" in x for x in body["content"]["limitations"])


def test_deleting_meeting_removes_all_research(client, mock_mode, db_session):
    mid = make_meeting(client)
    client.post(f"/api/meetings/{mid}/research")
    assert client.delete(f"/api/meetings/{mid}").status_code == 204
    db_session.expire_all()
    assert db_session.query(Source).count() == 0
    assert db_session.query(Claim).count() == 0
    assert db_session.query(Briefing).count() == 0


# ----------------------------------------------------------------- failure handling

def test_tavily_rate_limit_marks_meeting_failed_with_message(client, fake_keys, monkeypatch):
    def boom(*a, **k):
        raise TavilyServiceError("Tavily rate/usage limit reached. Try again later.", kind="rate_limit")
    monkeypatch.setattr(tavily_service, "search", boom)
    mid = make_meeting(client)
    client.post(f"/api/meetings/{mid}/research")
    s = client.get(f"/api/meetings/{mid}/status").json()
    assert s["status"] == "failed" and "rate" in s["error_message"].lower()
    assert client.get(f"/api/meetings/{mid}/briefing").status_code == 404


def test_no_sources_found_fails_cleanly(client, mock_mode, monkeypatch):
    monkeypatch.setattr(research_service, "collect_news", lambda org: [])
    monkeypatch.setattr(research_service, "collect_company", lambda org: [])
    monkeypatch.setattr(research_service, "collect_person", lambda a, o: [])
    mid = make_meeting(client)
    client.post(f"/api/meetings/{mid}/research")
    s = client.get(f"/api/meetings/{mid}/status").json()
    assert s["status"] == "failed" and "No sources were found" in s["error_message"]


# ----------------------------------------------------------------- real-mode path with fakes

def _fake_search(person_fails=False):
    today = date.today()

    def search(query, *, topic="general", days=None, max_results=6, depth="basic"):
        if topic == "news":
            return [SearchHit("Acme opens office", "https://news.example/a", "Acme opened a new office in Berlin.", today - timedelta(days=2))]
        if "competitors" in query:
            return [SearchHit("Acme rivals", "https://rivals.example/r", "Acme competes with several payment providers.", None)]
        if "professional background" in query or "interview" in query:
            if person_fails:
                raise TavilyServiceError("Tavily request failed (Timeout)", kind="error")
            return [SearchHit("Jane Doe profile", "https://people.example/jd", "Jane Doe is VP Engineering at Acme, leading platform teams.", today - timedelta(days=30))]
        return [SearchHit("About Acme", "https://acme.example/about", "Acme builds payment software for small businesses across Europe.", today - timedelta(days=40))]
    return search


def _fake_claude(system, user, max_tokens=4000):
    ids = {cat: int(i) for i, cat in re.findall(r"\[S(\d+)\] \((\w+)\)", user)}
    if "Analyse the organisation" in user:
        return {
            "overview": [{"text": "Acme builds payment software for small businesses.", "source_ids": [ids["company"], 99999]}],
            "business_model": [{"text": "Acme monetises an analytics add-on.", "source_ids": [99999]}],
            "products_services": [], "competitors": [], "strategic_initiatives": [], "challenges": [],
            "recent_developments": [{"source_id": ids["news"], "summary": "Acme opened a Berlin office."}],
            "limitations": [],
        }
    if "professional profile" in user:
        return {"role": [{"text": "Jane Doe is VP Engineering at Acme.", "source_ids": [ids["person"]]}],
                "experience": [], "achievements": [], "expertise": [], "public_content": [],
                "identity_note": None, "limitations": []}
    return {
        "meeting_overview": [{"text": "Explore a partnership.", "source_ids": [], "is_inference": True}],
        "insights": [{"text": "Berlin expansion suggests EU focus.", "source_ids": [ids["news"]], "is_inference": True}],
        "opportunities": [{"title": "EU pilot", "type": "nonsense-type", "description": "Pilot in Berlin.",
                           "why_relevant": "Matches the new office.", "source_ids": [ids["news"], 424242]}],
        "risks": [], "discussion_points": [], "strategy": [],
        "questions": {"strategic": [{"question": "How will Berlin change partner priorities?", "rationale": "New office.",
                                     "reveals": None, "source_ids": [ids["news"], 424242]}]},
    }


def test_real_mode_pipeline_discards_invented_sources(client, fake_keys, monkeypatch, db_session):
    monkeypatch.setattr(tavily_service, "search", _fake_search())
    monkeypatch.setattr(tavily_service, "extract", lambda urls: {})
    monkeypatch.setattr(claude_service, "generate_json", _fake_claude)

    mid = make_meeting(client)
    assert client.post(f"/api/meetings/{mid}/research").status_code == 202
    assert client.get(f"/api/meetings/{mid}/status").json()["status"] == "ready"

    body = client.get(f"/api/meetings/{mid}/briefing").json()
    c = body["content"]
    assert body["is_mock"] is False
    real_ids = {s["id"] for s in body["sources"]}
    assert len(real_ids) == 4

    overview = c["company"]["overview"][0]
    assert set(overview["source_ids"]) <= real_ids and 99999 not in overview["source_ids"]
    assert overview["evidence_label"] == "partially_supported"          # one domain only

    fabricated = c["company"]["business_model"][0]
    assert fabricated["evidence_label"] == "needs_verification" and fabricated["source_ids"] == []

    news = c["recent_developments"][0]
    assert news["summary_is_ai"] is True and news["freshness"] == "recent"

    opp = c["opportunities"][0]
    assert opp["type"] == "business"                                    # invalid type normalised
    assert 424242 not in opp["source_ids"] and opp["is_inference"] is True
    assert opp["evidence_label"] != "verified"

    q = c["questions"]["strategic"][0]
    assert 424242 not in q["source_ids"]

    assert c["attendee"]["role"][0]["evidence_label"] == "partially_supported"
    assert c["evidence_summary"]["needs_verification"] >= 1


def test_partial_search_failure_is_reported_not_fatal(client, fake_keys, monkeypatch):
    monkeypatch.setattr(tavily_service, "search", _fake_search(person_fails=True))
    monkeypatch.setattr(tavily_service, "extract", lambda urls: {})
    monkeypatch.setattr(claude_service, "generate_json", _fake_claude)
    mid = make_meeting(client)
    client.post(f"/api/meetings/{mid}/research")
    assert client.get(f"/api/meetings/{mid}/status").json()["status"] == "ready"
    c = client.get(f"/api/meetings/{mid}/briefing").json()["content"]
    assert c["attendee"] is None
    assert any("Attendee research failed" in x for x in c["limitations"])


def test_claude_failure_marks_meeting_failed(client, fake_keys, monkeypatch):
    from app.services.claude_service import ClaudeServiceError
    monkeypatch.setattr(tavily_service, "search", _fake_search())
    monkeypatch.setattr(tavily_service, "extract", lambda urls: {})

    def boom(*a, **k):
        raise ClaudeServiceError("Claude API rate limit reached. Try again shortly.")
    monkeypatch.setattr(claude_service, "generate_json", boom)
    mid = make_meeting(client)
    client.post(f"/api/meetings/{mid}/research")
    s = client.get(f"/api/meetings/{mid}/status").json()
    assert s["status"] == "failed" and "rate limit" in s["error_message"]


# ----------------------------------------------------------------- history

def test_history_search_filter_and_delete(client, mock_mode):
    a = make_meeting(client, organization_or_person="Microsoft", purpose="Partnership talk")
    make_meeting(client, organization_or_person="Google", purpose="Product review")
    client.post(f"/api/meetings/{a}/research")

    assert client.get("/api/history").json()["total"] == 2
    assert client.get("/api/history", params={"q": "micro"}).json()["total"] == 1
    assert client.get("/api/history", params={"status": "ready"}).json()["total"] == 1
    assert client.get("/api/history", params={"q": "zzz"}).json()["items"] == []
    assert client.get("/api/history", params={"limit": 0}).status_code == 422
    assert client.get("/api/history", params={"date_from": "2026-12-01", "date_to": "2026-01-01"}).status_code == 422
    assert client.delete(f"/api/meetings/{a}").status_code == 204
    assert client.get("/api/history").json()["total"] == 1
