"""Say when a review is due, which supplies the occasion that is otherwise missing.

This only counts entries. It sends nothing anywhere and never calls an LLM.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from memory_tool.review import collector, store
from memory_tool.review.store import ReviewError
from memory_tool.review.text import say

DEFAULT_MIN_DAYS = 7
DEFAULT_MIN_ENTRIES = 10


def _setting(base: Path, key: str, default):
    """Read a notice setting, keeping the default if it is not usable."""
    try:
        from memory_tool.utils.config import Config

        value = Config(Path(base)).get(f"review.notice.{key}", default)
    except Exception:
        return default

    return value if type(value) is type(default) else default


def review_notice(base: Path, now: Optional[datetime] = None) -> Optional[str]:
    """Build the one-line notice, if one is due.

    Args:
        base: The knowledge base folder
        now: The current time

    Returns:
        The notice, or None. A review in progress is always mentioned. Otherwise
        enough days must have passed and enough entries gathered, so that a
        quiet period does not nag.
    """
    if not _setting(base, "enabled", True):
        return None

    now = now or datetime.now()

    try:
        latest = store.latest_review(base)
    except ReviewError:
        return None

    if latest and not latest.is_done:
        return say(
            f"Review {latest.name} is in progress. Run mreview to continue.",
            f"진행 중인 리뷰가 있습니다({latest.name}). mreview로 이어 갈 수 있습니다.",
        )

    start, end = collector.review_window(latest.end if latest else None, now)
    min_entries = _setting(base, "min_entries", DEFAULT_MIN_ENTRIES)

    if latest:
        days = (now - start).days
        if days < _setting(base, "min_days", DEFAULT_MIN_DAYS):
            return None

    count = len(collector.collect_entries(base, start, end))

    if count < min_entries:
        return None

    if latest:
        return say(
            f"{days} days since the last review, with {count} entries. Run mreview to review them.",
            f"지난 리뷰 후 {days}일이 지났고 기록이 {count}건 있습니다. 리뷰하려면 mreview를 실행하세요.",
        )

    return say(
        f"No review yet, and {count} recent entries. Run mreview to review them.",
        f"아직 리뷰가 없고 최근 기록이 {count}건 있습니다. 리뷰하려면 mreview를 실행하세요.",
    )
