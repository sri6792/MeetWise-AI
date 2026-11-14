import json
from types import SimpleNamespace as NS

import pytest

from app.config import Settings, settings
from app.services import claude_service as cs


def resp(status, body):
    return NS(status_code=status, json=lambda: body, text=json.dumps(body))


def good(text):
    return resp(200, {"choices": [{"message": {"content": text}}]})


@pytest.fixture(autouse=True)
def _reset_busy_models():
    cs._BUSY.clear()
    yield
    cs._BUSY.clear()


@pytest.fixture()
def compat(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai_compatible")
    monkeypatch.setattr(settings, "llm_api_key", "k")
    monkeypatch.setattr(settings, "llm_base_url", "https://x.test/v1/")
    monkeypatch.setattr(settings, "llm_model", "m1")


def script(monkeypatch, *responses):
    sent, it = [], iter(responses)

    def fake_post(url, headers, payload):
        sent.append((url, headers, payload))
        return next(it, responses[-1])

    monkeypatch.setattr(cs, "_post", fake_post)
    return sent


def test_provider_aliases_and_missing_settings():
    s = Settings(_env_file=None, llm_provider="Gemini", anthropic_api_key="")
    assert s.llm_provider == "openai_compatible"
    assert s.llm_missing == ["LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"]
    assert Settings(_env_file=None, llm_provider="anthropic").llm_missing == ["ANTHROPIC_API_KEY"]
    ok = Settings(_env_file=None, llm_provider="groq", llm_api_key="k", llm_base_url="u", llm_model="m")
    assert ok.llm_configured and ok.llm_model_name == "m"


def test_success_builds_correct_request(compat, monkeypatch):
    sent = script(monkeypatch, good('```json\n{"a": 1}\n```'))
    assert cs.generate_json("sys", "user", 100) == {"a": 1}
    url, headers, payload = sent[0]
    assert url == "https://x.test/v1/chat/completions"
    assert headers["Authorization"] == "Bearer k"
    assert payload["response_format"] == {"type": "json_object"}


def test_adapts_to_provider_parameter_quirks(compat, monkeypatch):
    sent = script(monkeypatch,
                  resp(400, {"error": {"message": "Use 'max_completion_tokens' instead."}}),
                  resp(400, {"error": {"message": "response_format is not supported"}}),
                  good('{"b": 2}'))
    assert cs.generate_json("s", "u", 100) == {"b": 2}
    assert "max_completion_tokens" in sent[-1][2] and "response_format" not in sent[-1][2]


@pytest.mark.parametrize("status,needle", [(401, "LLM_API_KEY"), (404, "LLM_MODEL"), (429, "rate limit"), (500, "HTTP 500")])
def test_error_messages_are_actionable(compat, monkeypatch, status, needle):
    script(monkeypatch, resp(status, {"error": {"message": "x"}}))
    with pytest.raises(cs.ClaudeServiceError) as e:
        cs.generate_json("s", "u", 100)
    assert needle.lower() in str(e.value).lower()


def test_retries_once_on_invalid_json(compat, monkeypatch):
    sent = script(monkeypatch, good("not json"), good('{"d": 4}'))
    assert cs.generate_json("s", "u", 100) == {"d": 4}
    assert "more concise" in sent[1][2]["messages"][1]["content"]


def test_research_requires_ai_settings_for_compatible_provider(client, monkeypatch):
    monkeypatch.setattr(settings, "mock_mode", False)
    monkeypatch.setattr(settings, "tavily_api_key", "t")
    monkeypatch.setattr(settings, "llm_provider", "openai_compatible")
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "llm_base_url", "")
    monkeypatch.setattr(settings, "llm_model", "")
    mid = client.post("/api/meetings", json={"organization_or_person": "Acme", "meeting_date": "2026-11-20",
                                              "meeting_time": "10:00", "purpose": "Intro call"}).json()["id"]
    r = client.post(f"/api/meetings/{mid}/research")
    assert r.status_code == 503 and "LLM_API_KEY" in r.json()["detail"]


def test_overloaded_provider_is_retried_then_succeeds(compat, monkeypatch):
    monkeypatch.setattr(cs, "_sleep", lambda s: None)
    sent = script(monkeypatch,
                  resp(503, {"error": {"message": "high demand"}}),
                  resp(503, {"error": {"message": "high demand"}}),
                  good('{"ok": true}'))
    assert cs.generate_json("s", "u", 100) == {"ok": True}
    assert len(sent) == 3


def test_overload_that_never_clears_gives_clear_message(compat, monkeypatch):
    monkeypatch.setattr(cs, "_sleep", lambda s: None)
    script(monkeypatch, *[resp(503, {"error": {"message": "high demand"}})] * 4)
    with pytest.raises(cs.ProviderBusyError) as e:
        cs.generate_json("s", "u", 100)
    assert "overloaded" in str(e.value).lower()


def test_fallback_model_used_when_main_model_stays_busy(compat, monkeypatch):
    monkeypatch.setattr(cs, "_sleep", lambda s: None)
    monkeypatch.setattr(settings, "llm_fallback_model", "backup-model")
    sent = script(monkeypatch, *[resp(503, {"error": {"message": "busy"}})] * 2, good('{"z": 1}'))
    assert cs.generate_json("s", "u", 100) == {"z": 1}
    assert len(sent) == 3                                   # main model: 1 try + 1 quick retry, then the backup
    assert sent[0][2]["model"] == "m1" and sent[-1][2]["model"] == "backup-model"


def test_overloaded_model_is_skipped_on_the_next_call(compat, monkeypatch):
    monkeypatch.setattr(cs, "_sleep", lambda s: None)
    monkeypatch.setattr(settings, "llm_fallback_model", "backup-model")
    script(monkeypatch, *[resp(503, {"error": {"message": "busy"}})] * 2, good('{"a": 1}'))
    cs.generate_json("s", "u", 100)
    sent = script(monkeypatch, good('{"b": 2}'))
    assert cs.generate_json("s", "u", 100) == {"b": 2}
    assert [c[2]["model"] for c in sent] == ["backup-model"]   # did not waste time on the busy model again


def test_truncated_reply_is_retried_with_a_bigger_budget(compat, monkeypatch):
    cut = resp(200, {"choices": [{"message": {"content": '{"a": "cut off'}, "finish_reason": "length"}]})
    sent = script(monkeypatch, cut, good('{"ok": 1}'))
    assert cs.generate_json("s", "u", 100) == {"ok": 1}
    assert sent[0][2]["max_tokens"] == 200 and sent[1][2]["max_tokens"] == 400


def test_comments_and_trailing_commas_are_tolerated(compat, monkeypatch):
    sent = script(monkeypatch, good('{\n "a": [1,], // a note\n}'))
    assert cs.generate_json("s", "u", 100) == {"a": [1]}
    assert len(sent) == 1


def test_gives_up_after_three_unusable_replies(compat, monkeypatch):
    script(monkeypatch, good("nope"), good("nope"), good("nope"))
    with pytest.raises(cs.ClaudeServiceError) as e:
        cs.generate_json("s", "u", 100)
    assert "unusable" in str(e.value)
