import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Tuple

TME_RE = re.compile(r"(https?://t\.me/[^\s]+|t\.me/[^\s]+)")

# https://t.me/channel/9311
CHAN_RE = re.compile(r"t\.me/(?P<uname>[A-Za-z0-9_]{5,})/(?P<msgid>\d+)")
# https://t.me/c/1234567890/9311
PRIV_RE = re.compile(r"t\.me/c/(?P<cid>\d+)/(?P<msgid>\d+)")


def extract_first_tme_url(text: str) -> Optional[str]:
    if not text:
        return None
    m = TME_RE.search(text)
    if not m:
        return None
    url = m.group(1)
    if url.startswith("t.me/"):
        url = "https://" + url
    return url


def parse_post_key(url: str) -> Optional[str]:
    url = url.replace("https://", "").replace("http://", "")
    m1 = CHAN_RE.search(url)
    if m1:
        return f"u:{m1.group('uname')}:{m1.group('msgid')}"
    m2 = PRIV_RE.search(url)
    if m2:
        return f"c:{m2.group('cid')}:{m2.group('msgid')}"
    return None


def week_range_msk(now_ts: int, tz_name: str = "Europe/Moscow") -> Tuple[int, int]:
    tz = ZoneInfo(tz_name)
    now = datetime.fromtimestamp(now_ts, tz=tz)
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end = (start + timedelta(days=7)) - timedelta(seconds=1)
    return int(start.timestamp()), int(end.timestamp())


def month_range_msk(now_ts: int, tz_name: str = "Europe/Moscow") -> Tuple[int, int]:
    tz = ZoneInfo(tz_name)
    now = datetime.fromtimestamp(now_ts, tz=tz)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1)
    else:
        next_month = start.replace(month=start.month + 1)

    end = next_month - timedelta(seconds=1)
    return int(start.timestamp()), int(end.timestamp())


def is_same_week_msk(task_created_ts: int, now_ts: int, tz_name: str = "Europe/Moscow") -> bool:
    week_start, week_end = week_range_msk(now_ts, tz_name)
    return week_start <= task_created_ts <= week_end


def display_name(user) -> str:
    if getattr(user, "username", None):
        return f"@{user.username}"
    name = (getattr(user, "full_name", "") or "").strip()
    return name if name else str(user.id)