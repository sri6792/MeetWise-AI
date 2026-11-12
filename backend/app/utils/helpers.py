import json
import re
from urllib.parse import urlparse


def truncate(text: str | None, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def domain_of(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def normalise_url(url: str) -> str:
    """Used only to detect duplicate results (ignores fragment, trailing slash, case of host)."""
    p = urlparse(url.strip())
    return f"{p.scheme.lower()}://{p.netloc.lower()}{p.path.rstrip('/')}" + (f"?{p.query}" if p.query else "")


def is_http_url(url: str) -> bool:
    return urlparse(url).scheme in ("http", "https")


def extract_json(text: str) -> dict:
    """Parse a JSON object from an LLM reply, tolerating ``` fences and stray prose."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start == -1 or end <= start:
            raise ValueError("No JSON object found in model reply")
        try:
            return json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON in model reply: {exc}") from exc
