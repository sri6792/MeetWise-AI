from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any


def today_utc() -> date:
    return datetime.now(timezone.utc).date()


def parse_date(value: Any) -> date | None:
    """Parse a publication date from whatever a search API returns.
    Returns None when the value is missing or unparseable - we never guess a date."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    s = str(value).strip()
    parsed: date | None = None
    try:
        parsed = datetime.fromisoformat(s.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    if parsed is None:
        try:
            parsed = parsedate_to_datetime(s).date()
        except (TypeError, ValueError, IndexError):
            pass
    if parsed is None:
        for fmt in ("%Y-%m-%d", "%d %b %Y", "%b %d, %Y", "%B %d, %Y", "%Y/%m/%d"):
            try:
                parsed = datetime.strptime(s, fmt).date()
                break
            except ValueError:
                continue

    # Reject obvious garbage (far past, or more than a day in the future)
    if parsed is None or parsed.year < 1990 or (parsed - today_utc()).days > 1:
        return None
    return parsed


def age_in_days(published: date | None, today: date | None = None) -> int | None:
    if published is None:
        return None
    return ((today or today_utc()) - published).days
