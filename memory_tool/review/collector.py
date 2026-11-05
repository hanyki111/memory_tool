"""Gather the timeline entries a review covers."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from memory_tool.core.timeline import ENTRY_PATTERN, Timeline

#: How far back the first review looks. Older entries stay in the timeline, and
#: --since reaches them.
FIRST_REVIEW_DAYS = 14

TIME_FORMAT = "%Y-%m-%dT%H:%M"


@dataclass
class Entry:
    """One timeline entry."""

    when: datetime
    text: str


def format_time(moment: datetime) -> str:
    """Write a moment the way review files store it."""
    return moment.strftime(TIME_FORMAT)


def parse_time(value: str) -> datetime:
    """Read a moment stored in a review file."""
    return datetime.strptime(value, TIME_FORMAT)


def first_review_start(now: datetime) -> datetime:
    """Return where a first review starts, at the start of that day."""
    day = now - timedelta(days=FIRST_REVIEW_DAYS - 1)
    return day.replace(hour=0, minute=0, second=0, microsecond=0)


def review_window(
    last_end: Optional[str],
    now: datetime,
    since: Optional[datetime] = None,
) -> Tuple[datetime, datetime]:
    """Decide the period of a new review.

    The boundary is a time rather than a date so that entries recorded later on
    the day of a review belong to the next one.

    Args:
        last_end: Where the last review ended, if there was one
        now: The current time
        since: A start chosen by the user, which takes precedence

    Returns:
        (start, end), both to the minute.
    """
    end = now.replace(second=0, microsecond=0)

    if since is not None:
        return since, end
    if last_end:
        return parse_time(last_end), end
    return first_review_start(now), end


def collect_entries(base: Path, start: datetime, end: datetime) -> List[Entry]:
    """Read the entries in a period, oldest first.

    Both ends are included. Times have only minutes, so an entry made in the
    minute a review started may appear in two reviews, rather than in neither.

    Args:
        base: The knowledge base folder
        start: First moment included
        end: Last moment included

    Returns:
        The entries, from files of either naming layout.
    """
    timeline_path = Path(base) / "timeline"
    entries: List[Entry] = []
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)

    while day <= end:
        path = Timeline.resolve_existing_file(timeline_path, day)
        if path is not None:
            entries.extend(_read_day(path, day, start, end))
        day += timedelta(days=1)

    return sorted(entries, key=lambda entry: entry.when)


def _read_day(path: Path, day: datetime, start: datetime, end: datetime) -> List[Entry]:
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []

    entries = []
    for match in ENTRY_PATTERN.finditer(content):
        hour, minute = (int(part) for part in match.group(1).split(":"))
        if hour > 23 or minute > 59:
            continue

        when = day.replace(hour=hour, minute=minute)
        if start <= when <= end:
            entries.append(Entry(when=when, text=match.group(2).strip()))

    return entries


def entry_statistics(entries: List[Entry]) -> Tuple[int, int]:
    """Return (entry count, active days)."""
    return len(entries), len({entry.when.date() for entry in entries})
