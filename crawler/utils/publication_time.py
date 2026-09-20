"""Publication timestamps: preserve precision and normalise to Beijing time."""
import re
from datetime import datetime, timedelta, timezone

# The supported publication range starts in 2026; Beijing uses UTC+08:00.
BEIJING = timezone(timedelta(hours=8), "Asia/Shanghai")
# A date alone must never be interpreted as midnight.
_TIMESTAMP = re.compile(
    r"(?<!\d)(20\d{2})[-./年](\d{1,2})[-./月](\d{1,2})日?"
    r"[T\s]+(\d{1,2}):(\d{2})(?::(\d{2})(\.\d+)?)?"
    r"(Z|[+-]\d{2}:?\d{2})?(?![\d:])"
)


def parse_publication_time(value):
    """Return an aware datetime, or None for missing/invalid/date-only input."""
    if isinstance(value, datetime):
        parsed = value
    else:
        match = _TIMESTAMP.search(str(value or "").strip().replace("∶", ":").replace("：", ":"))
        if not match:
            return None
        year, month, day, hour, minute, second, fraction, offset = match.groups()
        stamp = (f"{year}-{int(month):02d}-{int(day):02d}T"
                 f"{int(hour):02d}:{minute}:{second or '00'}{fraction or ''}{offset or ''}")
        try:
            parsed = datetime.fromisoformat(stamp)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BEIJING)
    return parsed.astimezone(BEIJING)
