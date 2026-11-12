"""Claude integration: one function that returns a validated JSON object."""
import logging
import time

import httpx

from app.config import settings
from app.utils.helpers import extract_json

logger = logging.getLogger(__name__)


class ClaudeServiceError(Exception):
    pass


class ProviderBusyError(ClaudeServiceError):
    """The provider kept answering 'overloaded / try later' even after retries."""


GROUNDING_RULES = """You are the research analyst inside MeetWise AI, a pre-meeting briefing tool.

Non-negotiable rules:
1. Use ONLY the numbered sources provided. Never use outside knowledge to state facts about the organisation or person.
2. Every factual statement must list the ids of the sources that support it in "source_ids" (integers taken from the [S<id>] labels). Never invent ids.
3. If the sources do not support something, leave it out. Never guess names, dates, job titles, numbers or quotes.
4. Set "is_inference": true for any interpretation, opinion, prediction or recommendation that is not directly stated in a source. Inferences may still cite the sources that motivated them.
5. Professional, publicly available information only. Never include personal life, family, health, religion, politics, home address or contact details.
6. Keep each statement to one short, specific sentence written for a busy professional.
7. Reply with ONE valid JSON object and nothing else: no markdown fences, no commentary."""


RETRY_NOTE = (
    "\n\nIMPORTANT: your previous reply was not valid JSON or was cut off. "
    "Reply again with ONLY one valid JSON object, more concise this time."
)


def generate_json(system: str, user: str, max_tokens: int = 4000) -> dict:
    """Ask the configured AI model for a JSON object (provider chosen by LLM_PROVIDER)."""
    if settings.llm_provider == "openai_compatible":
        return _generate_openai_compatible(system, user, max_tokens)
    return _generate_anthropic(system, user, max_tokens)


# ------------------------------------------------------------------ Anthropic

def _generate_anthropic(system: str, user: str, max_tokens: int) -> dict:
    if not settings.anthropic_api_key:
        raise ClaudeServiceError("ANTHROPIC_API_KEY is not configured")

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key, max_retries=2, timeout=120.0)

    for attempt in (1, 2):
        prompt = user
        if attempt == 2:
            prompt += RETRY_NOTE
        try:
            resp = client.messages.create(
                model=settings.claude_model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.RateLimitError as exc:
            raise ClaudeServiceError("Claude API rate limit reached. Try again shortly.") from exc
        except anthropic.AuthenticationError as exc:
            raise ClaudeServiceError("Claude rejected the API key. Check ANTHROPIC_API_KEY.") from exc
        except anthropic.APIConnectionError as exc:
            raise ClaudeServiceError("Could not reach the Claude API (network problem).") from exc
        except anthropic.APIStatusError as exc:
            detail = (getattr(exc, "message", "") or "")[:300]
            logger.error("Claude API error %s: %s", exc.status_code, detail)
            raise ClaudeServiceError(f"Claude API error (HTTP {exc.status_code}): {detail}") from exc

        text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        try:
            data = extract_json(text)
            if isinstance(data, dict):
                return data
        except ValueError as exc:
            logger.warning("Claude JSON parse failed (attempt %s): %s", attempt, exc)

    raise ClaudeServiceError("Claude returned an unusable response twice. Please retry.")


# ------------------------------------------------------------------ OpenAI-compatible (Gemini, OpenAI, Groq, OpenRouter...)

def _post(url: str, headers: dict, payload: dict):
    return httpx.post(url, headers=headers, json=payload, timeout=120.0)


_sleep = time.sleep
_now = time.monotonic
TRANSIENT_STATUS = {429, 500, 502, 503, 504}
RETRY_DELAYS = (2, 6, 15)   # waits before each retry when there is no other model to switch to
FAILOVER_DELAYS = (2,)      # when a backup model exists, retry once, then switch quickly
BUSY_COOLDOWN = 120.0       # seconds to avoid a model after it proved overloaded
_BUSY: dict[str, float] = {}  # model -> time (monotonic) until which we skip it


def _error_detail(resp) -> str:
    try:
        body = resp.json()
    except Exception:
        return (getattr(resp, "text", "") or "")[:300]
    if isinstance(body, list) and body:
        body = body[0]
    err = body.get("error", body) if isinstance(body, dict) else body
    if isinstance(err, dict):
        err = err.get("message") or str(err)
    return str(err)[:300]


def _describe(status: int, detail: str) -> str:
    if status in (401, 403):
        return f"The AI provider rejected the API key (HTTP {status}). Check LLM_API_KEY. {detail}"
    if status == 404:
        return f"The AI provider says 'not found'. Check LLM_MODEL and LLM_BASE_URL. {detail}"
    if status == 429:
        return f"AI provider rate limit reached. Wait a minute and retry. {detail}"
    if status in (500, 502, 503, 504):
        return f"The AI provider is overloaded or unavailable (HTTP {status}). Please retry in a minute. {detail}"
    return f"AI provider error (HTTP {status}): {detail}"


def _chat_once(url: str, headers: dict, system: str, prompt: str, max_tokens: int, state: dict, model: str,
               delays: tuple = RETRY_DELAYS) -> str:
    """One chat request. Adapts to provider quirks (token parameter name, JSON mode)
    and waits/retries when the provider reports it is busy."""
    retries = 0
    while True:
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            state["token_key"]: max_tokens,
        }
        if state["json_mode"]:
            payload["response_format"] = {"type": "json_object"}
        try:
            resp = _post(url, headers, payload)
        except httpx.TimeoutException as exc:
            raise ClaudeServiceError("The AI provider timed out. Please retry.") from exc
        except httpx.HTTPError as exc:
            raise ClaudeServiceError("Could not reach the AI provider (network problem).") from exc

        if resp.status_code == 200:
            try:
                return resp.json()["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise ClaudeServiceError("The AI provider returned an unexpected response format.") from exc

        detail = _error_detail(resp)
        logger.warning("LLM HTTP %s (model %s): %s", resp.status_code, model, detail)
        low = detail.lower()

        if resp.status_code == 400:  # each adaptation can happen only once, so this always ends
            if state["token_key"] == "max_tokens" and "max_completion_tokens" in low:
                state["token_key"] = "max_completion_tokens"
                continue
            if state["json_mode"] and ("response_format" in low or "json" in low):
                state["json_mode"] = False
                continue

        if resp.status_code in TRANSIENT_STATUS:
            if retries < len(delays):
                logger.info("Provider busy (HTTP %s); retrying in %ss", resp.status_code, delays[retries])
                _sleep(delays[retries])
                retries += 1
                continue
            raise ProviderBusyError(_describe(resp.status_code, detail))

        raise ClaudeServiceError(_describe(resp.status_code, detail))


def _generate_openai_compatible(system: str, user: str, max_tokens: int) -> dict:
    missing = settings.llm_missing
    if missing:
        raise ClaudeServiceError(f"Missing configuration: {', '.join(missing)}")

    url = settings.llm_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
    state = {"token_key": "max_tokens", "json_mode": True}

    models = [settings.llm_model]
    if settings.llm_fallback_model and settings.llm_fallback_model != settings.llm_model:
        models.append(settings.llm_fallback_model)

    def ask(prompt: str) -> str:
        busy: ProviderBusyError | None = None
        # skip models that were recently found overloaded (unless nothing else is left)
        candidates = [m for m in models if _BUSY.get(m, 0.0) <= _now()] or models
        for i, model in enumerate(candidates):
            last = i == len(candidates) - 1
            try:
                return _chat_once(url, headers, system, prompt, max_tokens, state, model,
                                  RETRY_DELAYS if last else FAILOVER_DELAYS)
            except ProviderBusyError as exc:
                busy = exc
                _BUSY[model] = _now() + BUSY_COOLDOWN
                logger.warning("Model %s is overloaded; %s", model, "no other model left" if last else "switching to the backup model")
        assert busy is not None
        raise busy

    for attempt in (1, 2):
        text = ask(user + (RETRY_NOTE if attempt == 2 else ""))
        try:
            data = extract_json(text)
            if isinstance(data, dict):
                return data
        except ValueError as exc:
            logger.warning("LLM JSON parse failed (attempt %s): %s", attempt, exc)
    raise ClaudeServiceError("The AI model returned an unusable response twice. Please retry.")


def format_sources(sources: list, max_chars: int = 900) -> str:
    """Render sources as the numbered evidence block Claude is allowed to use."""
    blocks = []
    for s in sources:
        published = s.published_date.isoformat() if s.published_date else "unknown"
        text = (s.content or s.snippet or "").strip().replace("\n", " ")
        if len(text) > max_chars:
            text = text[: max_chars - 1] + "…"
        blocks.append(
            f"[S{s.id}] ({s.category}) {s.title}\nURL: {s.url}\nPublished: {published}\nText: {text}"
        )
    return "\n\n".join(blocks) if blocks else "(no sources)"
