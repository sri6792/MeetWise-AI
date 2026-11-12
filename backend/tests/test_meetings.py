from app.models import Meeting, Source


def create(client, **overrides):
    payload = {
        "organization_or_person": "Stripe",
        "attendee_name": "Jane Doe",
        "meeting_date": "2026-11-20",
        "meeting_time": "10:30:00",
        "purpose": "Discuss a payments partnership",
    }
    payload.update(overrides)
    return client.post("/api/meetings", json=payload)


# ---------- health / preview (existing behaviour must not break) ----------

def test_health_reports_status_and_never_exposes_keys(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["application"] == "MeetWise AI"
    assert isinstance(body["tavily_configured"], bool)
    assert isinstance(body["anthropic_configured"], bool)
    assert "key" not in str(body).lower().replace("configured", "")


def test_preview_still_validates_and_returns_meeting(client, valid_payload):
    r = client.post("/api/meetings/preview", json=valid_payload)
    assert r.status_code == 200
    assert r.json()["status"] == "success"
    assert r.json()["meeting"]["organization_or_person"] == "Stripe"


def test_preview_does_not_save(client, db_session, valid_payload):
    client.post("/api/meetings/preview", json=valid_payload)
    assert db_session.query(Meeting).count() == 0


# ---------- create ----------

def test_create_success_returns_201_and_persists(client, db_session):
    r = create(client)
    assert r.status_code == 201
    body = r.json()
    assert body["id"] >= 1
    assert body["status"] == "created"
    assert body["created_at"].endswith("Z") or "+00:00" in body["created_at"]

    row = db_session.get(Meeting, body["id"])
    assert row.organization_or_person == "Stripe"
    assert row.attendee_name == "Jane Doe"
    assert str(row.meeting_date) == "2026-11-20"


def test_create_without_attendee_is_allowed(client):
    r = client.post("/api/meetings", json={
        "organization_or_person": "Stripe",
        "meeting_date": "2026-11-20",
        "meeting_time": "10:30",
        "purpose": "Discovery call",
    })
    assert r.status_code == 201
    assert r.json()["attendee_name"] is None


def test_create_trims_whitespace_and_blank_attendee_becomes_null(client):
    r = create(client, organization_or_person="  Stripe  ", attendee_name="   ")
    assert r.status_code == 201
    assert r.json()["organization_or_person"] == "Stripe"
    assert r.json()["attendee_name"] is None


def test_create_missing_required_fields_returns_422(client):
    for missing in ("organization_or_person", "meeting_date", "meeting_time", "purpose"):
        payload = {
            "organization_or_person": "Stripe",
            "meeting_date": "2026-11-20",
            "meeting_time": "10:30:00",
            "purpose": "Discuss a payments partnership",
        }
        payload.pop(missing)
        r = client.post("/api/meetings", json=payload)
        assert r.status_code == 422, f"{missing} should be required"


def test_create_invalid_values_return_422_and_save_nothing(client, db_session):
    assert create(client, organization_or_person="A").status_code == 422      # too short
    assert create(client, organization_or_person="   ").status_code == 422    # blank
    assert create(client, purpose="hey").status_code == 422                   # too short
    assert create(client, meeting_date="not-a-date").status_code == 422
    assert create(client, meeting_date="2026-13-45").status_code == 422
    assert create(client, meeting_time="25:99").status_code == 422
    assert create(client, purpose="x" * 2001).status_code == 422              # too long
    assert db_session.query(Meeting).count() == 0


def test_create_with_empty_body_returns_422(client):
    assert client.post("/api/meetings", json={}).status_code == 422


# ---------- get ----------

def test_get_existing_and_missing(client):
    mid = create(client).json()["id"]
    assert client.get(f"/api/meetings/{mid}").status_code == 200
    assert client.get("/api/meetings/9999").status_code == 404
    assert client.get("/api/meetings/abc").status_code == 422


# ---------- list / search / filter ----------

def test_list_empty_returns_empty_state(client):
    r = client.get("/api/meetings")
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


def test_list_search_filter_sort_and_pagination(client):
    create(client, organization_or_person="Microsoft", meeting_date="2026-11-08", purpose="Partnership discussion")
    create(client, organization_or_person="Google", attendee_name="Priya Shah", meeting_date="2026-11-09", purpose="Product discussion")
    create(client, organization_or_person="Amazon", meeting_date="2026-11-11", purpose="Business meeting")

    r = client.get("/api/meetings")
    assert r.json()["total"] == 3
    assert [m["organization_or_person"] for m in r.json()["items"]] == ["Amazon", "Google", "Microsoft"]  # newest first

    r = client.get("/api/meetings", params={"sort": "date_asc"})
    assert r.json()["items"][0]["organization_or_person"] == "Microsoft"

    assert client.get("/api/meetings", params={"q": "goog"}).json()["total"] == 1       # company, case-insensitive
    assert client.get("/api/meetings", params={"q": "priya"}).json()["total"] == 1      # attendee
    assert client.get("/api/meetings", params={"q": "partnership"}).json()["total"] == 1  # purpose
    assert client.get("/api/meetings", params={"q": "%"}).json()["total"] == 0          # wildcard is escaped
    assert client.get("/api/meetings", params={"q": "nomatch"}).json()["items"] == []

    r = client.get("/api/meetings", params={"date_from": "2026-11-09", "date_to": "2026-11-09"})
    assert r.json()["total"] == 1
    assert client.get("/api/meetings", params={"status": "created"}).json()["total"] == 3
    assert client.get("/api/meetings", params={"status": "ready"}).json()["total"] == 0

    r = client.get("/api/meetings", params={"limit": 2, "offset": 2})
    assert len(r.json()["items"]) == 1 and r.json()["total"] == 3


def test_list_invalid_params_return_422(client):
    assert client.get("/api/meetings", params={"limit": 0}).status_code == 422
    assert client.get("/api/meetings", params={"limit": 101}).status_code == 422
    assert client.get("/api/meetings", params={"status": "bogus"}).status_code == 422
    assert client.get("/api/meetings", params={"sort": "bogus"}).status_code == 422
    r = client.get("/api/meetings", params={"date_from": "2026-12-01", "date_to": "2026-11-01"})
    assert r.status_code == 422


# ---------- update ----------

def test_patch_updates_only_sent_fields_and_persists(client, db_session):
    mid = create(client).json()["id"]
    r = client.patch(f"/api/meetings/{mid}", json={"purpose": "Renewal negotiation"})
    assert r.status_code == 200
    assert r.json()["purpose"] == "Renewal negotiation"
    assert r.json()["organization_or_person"] == "Stripe"  # untouched

    db_session.expire_all()
    assert db_session.get(Meeting, mid).purpose == "Renewal negotiation"


def test_patch_can_clear_attendee(client):
    mid = create(client).json()["id"]
    r = client.patch(f"/api/meetings/{mid}", json={"attendee_name": None})
    assert r.status_code == 200 and r.json()["attendee_name"] is None


def test_patch_rejects_bad_input(client):
    mid = create(client).json()["id"]
    assert client.patch(f"/api/meetings/{mid}", json={}).status_code == 422
    assert client.patch(f"/api/meetings/{mid}", json={"organization_or_person": None}).status_code == 422
    assert client.patch(f"/api/meetings/{mid}", json={"purpose": "no"}).status_code == 422
    assert client.patch(f"/api/meetings/{mid}", json={"meeting_date": "garbage"}).status_code == 422
    assert client.get(f"/api/meetings/{mid}").json()["purpose"] == "Discuss a payments partnership"


def test_patch_missing_meeting_returns_404(client):
    assert client.patch("/api/meetings/9999", json={"purpose": "Valid purpose"}).status_code == 404


# ---------- delete ----------

def test_delete_removes_row_then_404(client, db_session):
    mid = create(client).json()["id"]
    assert client.delete(f"/api/meetings/{mid}").status_code == 204
    assert db_session.query(Meeting).count() == 0
    assert client.get(f"/api/meetings/{mid}").status_code == 404
    assert client.delete(f"/api/meetings/{mid}").status_code == 404


def test_delete_cascades_to_sources(client, db_session):
    mid = create(client).json()["id"]
    db_session.add(Source(meeting_id=mid, url="https://example.com/a", title="Example"))
    db_session.commit()
    assert db_session.query(Source).count() == 1

    client.delete(f"/api/meetings/{mid}")
    assert db_session.query(Source).count() == 0


def test_source_without_publication_date_is_stored_as_null_not_guessed(client, db_session):
    mid = create(client).json()["id"]
    db_session.add(Source(meeting_id=mid, url="https://example.com/a", title="Undated"))
    db_session.commit()
    src = db_session.query(Source).one()
    assert src.published_date is None
    assert src.freshness == "unknown"
