"""Runtime-local date/time helpers for prompt context."""

import logging
import os
from datetime import datetime
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


logger = logging.getLogger(__name__)

DEFAULT_APP_TIMEZONE = "UTC"


@lru_cache(maxsize=8)
def runtime_timezone() -> ZoneInfo:
    tz_name = (os.getenv("APP_TIMEZONE") or os.getenv("TZ") or DEFAULT_APP_TIMEZONE).strip()
    if not tz_name:
        tz_name = DEFAULT_APP_TIMEZONE
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        logger.warning("Invalid APP_TIMEZONE/TZ %r; falling back to UTC", tz_name)
        return ZoneInfo(DEFAULT_APP_TIMEZONE)


def runtime_now() -> datetime:
    return datetime.now(runtime_timezone())
