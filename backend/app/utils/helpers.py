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


def _scan_once(s: str) -> str:
    """One string-aware pass that removes // and /* */ comments and commas before } or ].
    A URL like "https://x.com" inside a string is left alone."""
    out: list[str] = []
    i, n = 0, len(s)
    in_str = esc = False
    while i < n:
        c = s[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            out.append(c)
            i += 1
        elif c == "/" and s[i + 1 : i + 2] == "/":
            while i < n and s[i] not in "\r\n":
                i += 1
        elif c == "/" and s[i + 1 : i + 2] == "*":
            j = s.find("*/", i + 2)
            i = n if j == -1 else j + 2
        elif c == ",":
            k = i + 1
            while k < n and s[k] in " \t\r\n":
                k += 1
            if k < n and s[k] in "}]":
                i += 1  # drop trailing comma
            else:
                out.append(c)
                i += 1
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _repair_json(s: str) -> str:
    """Fix the small slips LLMs make. Two passes: the first removes comments, the second then
    sees which commas are really trailing (e.g. '1], // note' followed by '}')."""
    return _scan_once(_scan_once(s))


def extract_json(text: str) -> dict:
    """Parse a JSON object from an LLM reply, tolerating ``` fences, stray prose,
    // comments, trailing commas and raw newlines inside strings."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.IGNORECASE)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    candidates = [cleaned]
    if start != -1 and end > start:
        candidates.append(cleaned[start : end + 1])
    last_error: Exception | None = None
    for cand in candidates:
        for attempt in (cand, _repair_json(cand)):
            try:
                return json.loads(attempt, strict=False)
            except json.JSONDecodeError as exc:
                last_error = exc
    if start == -1 or end <= start:
        raise ValueError("No JSON object found in model reply")
    raise ValueError(f"Invalid JSON in model reply: {last_error}")
