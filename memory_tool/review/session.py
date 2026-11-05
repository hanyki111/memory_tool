"""Start a review, or return to the one in progress."""

from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from memory_tool.review import collector, proposer, store
from memory_tool.review.store import Review, ReviewError
from memory_tool.review.text import say


def reflection_comment() -> str:
    """Return the fixed questions, as comments that stay out of the way."""
    questions: Optional[List[str]] = None

    try:
        from memory_tool.utils.config import Config

        questions = Config().get("review.reflection_questions")
    except Exception:
        pass

    if not questions:
        questions = [
            say(
                "What went well, what could be better, and what did you learn?",
                "잘된 점, 개선할 점, 배운 점은 무엇인가요?",
            )
        ]

    return "\n".join(f"<!-- {question} -->" for question in questions)


def open_review(
    base: Path,
    now: Optional[datetime] = None,
    since: Optional[datetime] = None,
    client: Any = None,
) -> Optional[Review]:
    """Return the review to work on, starting a new one if none is in progress.

    A review in progress comes back as saved, so its proposals do not change and
    no LLM is called. If proposals cannot be obtained, nothing is written and the
    last review's end stays where it was, so no entries are lost.

    Args:
        base: The knowledge base folder
        now: The current time
        since: Start of the period, in place of the last review's end
        client: An LLM client. Defaults to the configured provider.

    Returns:
        The review, or None if there are neither new entries nor open items.

    Raises:
        ReviewError: If the review cannot start.
    """
    now = now or datetime.now()
    previous = store.latest_review(base)

    if previous and not previous.is_done:
        return previous

    start, end = collector.review_window(previous.end if previous else None, now, since)

    if start > end:
        raise ReviewError(
            say("The start of the period is in the future.", "기간의 시작이 미래입니다.")
        )

    entries = collector.collect_entries(base, start, end)
    open_items = previous.open_items() if previous else []

    if not entries and not open_items:
        return None

    proposals, left_out = proposer.propose(base, entries, client) if entries else ([], 0)
    entry_count, active_days = collector.entry_statistics(entries)

    return store.start_review(
        base,
        f"{now:%Y-%m-%d}",
        collector.format_time(start),
        collector.format_time(end),
        proposals,
        dropped=left_out,
        entry_count=entry_count,
        active_days=active_days,
        reflection_comment=reflection_comment(),
    )
