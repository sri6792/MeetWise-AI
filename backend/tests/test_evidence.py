from datetime import timedelta
from types import SimpleNamespace as NS

from app.services import evidence_service as ev
from app.utils.date_utils import parse_date, today_utc
from app.utils.helpers import extract_json

T = today_utc()
TXT = "Acme builds payment software for small businesses across Europe"


def src(i, url, content, days, cat="company"):
    pub = T - timedelta(days=days) if days is not None else None
    return NS(id=i, url=url, title=f"t{i}", content=content, snippet=content, published_date=pub,
              freshness=ev.classify_freshness(pub, cat, T), category=cat)


SOURCES = {s.id: s for s in (
    src(1, "https://a.com/x", TXT + " and was founded in 2015.", 5),
    src(2, "https://b.org/y", "Acme builds payment software for small businesses.", 20),
    src(3, "https://c.com/z", "Unrelated cooking recipe about pasta and tomatoes.", 5),
    src(4, "https://old.com/o", TXT, 500),
    src(5, "https://u.com/u", TXT, None),
    src(6, "https://a.com/other", TXT, 3),
)}


def label(ids, text=TXT, inf=False):
    return ev.evaluate_claim(text, ids, SOURCES, inf).label


def test_freshness_windows():
    assert ev.classify_freshness(T - timedelta(days=10), "news", T) == "recent"
    assert ev.classify_freshness(T - timedelta(days=45), "news", T) == "potentially_outdated"
    assert ev.classify_freshness(T - timedelta(days=200), "company", T) == "recent"
    assert ev.classify_freshness(T - timedelta(days=400), "company", T) == "potentially_outdated"
    assert ev.classify_freshness(None, "news", T) == "unknown"          # never guessed
    assert ev.classify_freshness(T + timedelta(days=5), "news", T) == "unknown"


def test_verified_needs_two_domains_and_a_recent_source():
    assert label([1, 2]) == "verified"
    assert label([1]) == "partially_supported"
    assert label([1, 6]) == "partially_supported"      # same domain twice is not independent
    assert label([5]) == "partially_supported"         # undated can never be verified


def test_unsupported_claims_are_flagged():
    assert label([]) == "needs_verification"
    assert label([999]) == "needs_verification"        # invented id
    assert label([3]) == "needs_verification"          # source doesn't support the text
    assert label([4]) == "potentially_outdated"


def test_ai_inference_is_never_verified():
    assert label([1, 2], inf=True) == "partially_supported"


def test_unsupported_number_blocks_verification():
    assert label([1, 2], text=TXT + " with 4,200 employees") == "partially_supported"


def test_invalid_ids_are_dropped_and_deduplicated():
    assert ev.evaluate_claim(TXT, [1, 999, 1], SOURCES).valid_ids == [1]


def test_tolerant_parsing_helpers():
    assert ev.int_list(["S12", 7, "x", None, "3"]) == [12, 7, 3]
    assert parse_date("2026-11-05T10:00:00Z").isoformat() == "2026-11-05"
    assert parse_date("Mon, 02 Nov 2026 08:00:00 GMT").isoformat() == "2026-11-02"
    assert parse_date("garbage") is None and parse_date(None) is None and parse_date("2099-01-01") is None
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert extract_json('Sure! {"a": [1]} done') == {"a": [1]}


def test_extract_json_repairs_common_llm_slips():
    assert extract_json('{"a": [1, 2,], // note\n "b": 3,}') == {"a": [1, 2], "b": 3}
    assert extract_json('{"u": "https://example.com/a//b", // c\n "n": 1}') == {"u": "https://example.com/a//b", "n": 1}
    assert extract_json('{"t": "line1\nline2"}') == {"t": "line1\nline2"}
