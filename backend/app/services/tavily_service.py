"""Thin, defensive wrapper around the Tavily Search / Extract APIs.

Everything returned here is *retrieved evidence*: we pass through what Tavily
gives us and never fill in missing fields (e.g. unknown publication dates stay None).
"""
import logging
import time
from dataclasses import dataclass

from app.config import settings
from app.utils.date_utils import parse_date
from app.utils.helpers import truncate

logger = logging.getLogger(__name__)


@dataclass
class SearchHit:
    title: str
    url: str
    content: str
    published_date: object | None = None  # datetime.date | None
    score: float | None = None


class TavilyServiceError(Exception):
    """kind: config | auth | rate_limit | error"""

    def __init__(self, message: str, kind: str = "error"):
        super().__init__(message)
        self.kind = kind


def _client():
    if not settings.tavily_api_key:
        raise TavilyServiceError("TAVILY_API_KEY is not configured", kind="config")
    from tavily import TavilyClient

    return TavilyClient(api_key=settings.tavily_api_key)


def _translate(exc: Exception) -> TavilyServiceError:
    name, msg = type(exc).__name__, str(exc)
    low = msg.lower()
    if "usagelimit" in name.lower() or "429" in msg or "rate limit" in low or "usage limit" in low:
        return TavilyServiceError("Tavily rate/usage limit reached. Try again later.", kind="rate_limit")
    if "invalidapikey" in name.lower() or "forbidden" in name.lower() or "401" in msg or "unauthorized" in low:
        return TavilyServiceError("Tavily rejected the API key. Check TAVILY_API_KEY.", kind="auth")
    return TavilyServiceError(f"Tavily request failed ({name})", kind="error")


def search(
    query: str,
    *,
    topic: str = "general",
    days: int | None = None,
    max_results: int = 6,
    depth: str = "basic",
) -> list[SearchHit]:
    client = _client()
    kwargs: dict = dict(
        query=query,
        search_depth=depth,
        topic=topic,
        max_results=max_results,
        include_answer=False,
    )
    if topic == "news" and days:
        kwargs["days"] = days

    last: TavilyServiceError | None = None
    for attempt in (1, 2):
        try:
            resp = client.search(**kwargs)
            break
        except Exception as exc:  # the SDK raises several exception types
            last = _translate(exc)
            logger.warning("Tavily search failed (attempt %s): %s", attempt, last)
            if last.kind != "error" or attempt == 2:
                raise last from exc
            time.sleep(1.5)
    else:  # pragma: no cover
        raise last or TavilyServiceError("Tavily request failed")

    hits: list[SearchHit] = []
    seen: set[str] = set()
    for r in (resp or {}).get("results", []) or []:
        url = (r.get("url") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        hits.append(
            SearchHit(
                title=(r.get("title") or url).strip(),
                url=url,
                content=(r.get("content") or "").strip(),
                published_date=parse_date(r.get("published_date")),
                score=r.get("score"),
            )
        )
    logger.info("Tavily %r topic=%s -> %d results", query, topic, len(hits))
    return hits


def extract(urls: list[str]) -> dict[str, str]:
    """Fetch fuller page text for a few URLs. Failures are non-fatal (returns {})."""
    if not urls:
        return {}
    try:
        resp = _client().extract(urls=urls)
    except Exception as exc:
        logger.warning("Tavily extract failed: %s", _translate(exc))
        return {}
    out: dict[str, str] = {}
    for r in (resp or {}).get("results", []) or []:
        url, raw = r.get("url"), r.get("raw_content")
        if url and raw:
            out[url] = truncate(raw, 6000)
    return out
