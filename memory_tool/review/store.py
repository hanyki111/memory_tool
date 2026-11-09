"""Review files and the rules for what may happen to their items.

Each review is one Markdown file, ``reviews/YYYY-MM-DD.md``. The frontmatter is
the record and the "moves" section of the body is rewritten from it on every
save, so the file stays readable. The reflection section belongs to the user and
is never rewritten. Nothing else holds review state: the time of the last review
comes from these files, which also keeps two synced machines from fighting over
a shared state file.

Only the latest file has open items. Starting a review carries them forward.
"""

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from memory_tool.review.text import say
from memory_tool.utils.frontmatter import Frontmatter

#: How many new proposals one review offers, and how many open items may remain
#: when an item is put off.
MAX_PROPOSALS = 5
MAX_OPEN_ITEMS = 5

KIND_NEW = "new"
KIND_UPDATE = "update"

STATE_PROPOSED = "proposed"
STATE_WRITING = "writing"
STATE_DEFERRED = "deferred"
STATE_WRITTEN = "written"
STATE_REJECTED = "rejected"
#: Handed on to a later review, which now holds the item.
STATE_CARRIED = "carried"

OPEN_STATES = (STATE_PROPOSED, STATE_WRITING, STATE_DEFERRED)

STATUS_IN_PROGRESS = "in_progress"
STATUS_DONE = "done"

REFLECTION_OPEN = "open"
REFLECTION_WRITTEN = "written"
REFLECTION_SKIPPED = "skipped"

#: Either may head the section, whichever language wrote the file.
REFLECTION_HEADINGS = ("## 회고", "## 돌아보기", "## Reflection")

_REVIEW_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:-(\d+))?\.md$")
_REFLECTION_START = re.compile(
    r"^(?:" + "|".join(re.escape(h) for h in REFLECTION_HEADINGS) + r")\s*$",
    re.MULTILINE,
)


def reflection_text(path: Path) -> str:
    """Read what has been written in a review file's reflection section.

    Comments are left out: the prepared questions are not an answer.

    Args:
        path: The review file

    Returns:
        The text, or an empty string if there is none.
    """
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""

    start = _REFLECTION_START.search(content)
    if not start:
        return ""

    return re.sub(r"<!--.*?-->", "", content[start.end():], flags=re.DOTALL).strip()


#: Encloses the period's entries while someone writes alone. It is a comment, so
#: it does not count as an answer, and it is removed when they finish.
_ENTRIES_START = "<!-- memory-tool:entries"
_ENTRIES_BLOCK = re.compile(r"\n\n" + re.escape(_ENTRIES_START) + r".*?-->", re.DOTALL)


def insert_entries(path: Path, lines: List[str]) -> None:
    """Show the period's entries in a review file, under the reflection heading.

    Args:
        path: The review file
        lines: The entries, one per line
    """
    content = path.read_text(encoding="utf-8")
    start = _REFLECTION_START.search(content)
    if not start:
        return

    # An entry that holds a comment's end must not close the block early.
    body = "\n".join(line.replace("-->", "-- >") for line in lines)
    block = f"\n\n{_ENTRIES_START}\n{body}\n-->"
    path.write_text(content[: start.end()] + block + content[start.end():], encoding="utf-8")


def remove_entries(path: Path) -> None:
    """Take the entries back out of a review file, leaving what was written."""
    content = path.read_text(encoding="utf-8")
    path.write_text(_ENTRIES_BLOCK.sub("", content, count=1), encoding="utf-8")


class ReviewError(Exception):
    """Raised when a review cannot go on, with a message for the user.

    ``code`` is the failure code that ``--json`` reports.
    """

    def __init__(self, message: str, code: str = "failed"):
        super().__init__(message)
        self.code = code


@dataclass
class Item:
    """One thing to move into a document."""

    number: int
    kind: str
    title: str
    doc_type: Optional[str] = None
    target: Optional[str] = None
    why: str = ""
    evidence: List[str] = field(default_factory=list)
    #: Line and section counts when the target document could use splitting.
    split_note: Optional[dict] = None
    state: str = STATE_PROPOSED
    #: Whether the user has chosen for this item during the current review.
    decided: bool = False
    #: Whether the item came from an earlier review.
    carried: bool = False
    #: The heading to write under in the target document, as for an open question.
    heading: Optional[str] = None

    @property
    def is_open(self) -> bool:
        return self.state in OPEN_STATES


@dataclass
class Review:
    """A review: a period, its items and how far the user has got."""

    path: Path
    start: str
    end: str
    status: str = STATUS_IN_PROGRESS
    items: List[Item] = field(default_factory=list)
    #: Candidates beyond the limit, which were not kept.
    dropped: int = 0
    entry_count: int = 0
    active_days: int = 0
    reflection: str = REFLECTION_OPEN
    #: Candidates are still to be asked for, once the reflection is settled.
    proposals_pending: bool = False

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def is_done(self) -> bool:
        return self.status == STATUS_DONE

    def item(self, number: int) -> Item:
        """Find an item by its number.

        Raises:
            ReviewError: If there is no such item.
        """
        for candidate in self.items:
            if candidate.number == number:
                return candidate
        raise ReviewError(say(f"No item {number} in this review.", f"이 리뷰에 {number}번 항목이 없습니다."))

    def open_items(self) -> List[Item]:
        return [item for item in self.items if item.is_open]

    def undecided_items(self) -> List[Item]:
        """Items still waiting for a choice, those being written first."""
        waiting = [item for item in self.items if item.is_open and not item.decided]
        return sorted(waiting, key=lambda item: (item.state != STATE_WRITING, item.number))

    def can_defer(self) -> bool:
        """Tell whether an item may be put off right now."""
        return len(self.open_items()) <= MAX_OPEN_ITEMS

    def choices_settled(self) -> bool:
        """Tell whether every item has a choice and none is being written."""
        return not self.undecided_items() and not any(
            item.state == STATE_WRITING for item in self.items
        )


def add_item(
    review: Review,
    title: str,
    target: Optional[str] = None,
    doc_type: Optional[str] = None,
    why: str = "",
    evidence: Optional[List[str]] = None,
    heading: Optional[str] = None,
) -> Item:
    """Add something to keep.

    Args:
        review: The review
        title: What to keep
        target: The document to update. Without one, a new document.
        doc_type: Suggested document type
        why: Why it is worth keeping
        evidence: Days whose entries it rests on
        heading: The heading to write under in the target document

    Returns:
        The new item, not yet saved.
    """
    number = max((item.number for item in review.items), default=0) + 1
    item = Item(
        number=number,
        kind=KIND_UPDATE if target else KIND_NEW,
        title=title,
        doc_type=doc_type,
        target=target,
        why=why,
        evidence=evidence or [],
        heading=heading,
    )
    review.items.append(item)
    return item


def start_writing(review: Review, number: int) -> Item:
    """Mark an item as being written. It stays open until marked written."""
    item = _open_item(review, number)
    item.state = STATE_WRITING
    item.decided = False
    return item


def defer(review: Review, number: int) -> Item:
    """Put an item off to a later review.

    Raises:
        ReviewError: While more than ``MAX_OPEN_ITEMS`` items remain open.
    """
    item = _open_item(review, number)

    if not review.can_defer():
        raise ReviewError(
            say(
                f"Cannot put this off while more than {MAX_OPEN_ITEMS} items remain open.",
                f"남은 항목이 {MAX_OPEN_ITEMS}건을 넘는 동안에는 미룰 수 없습니다.",
            )
        )

    item.state = STATE_DEFERRED
    item.decided = True
    return item


def reject(review: Review, number: int) -> Item:
    """Decide not to write an item. Later reviews avoid proposing it again."""
    item = _open_item(review, number)
    item.state = STATE_REJECTED
    item.decided = True
    return item


def mark_written(review: Review, number: int) -> Item:
    """Mark an item as written."""
    item = _open_item(review, number)
    item.state = STATE_WRITTEN
    item.decided = True
    return item


def finish_if_ready(review: Review) -> bool:
    """Finish a review once its items and reflection are settled.

    Returns:
        True if the review is now done.
    """
    if review.is_done:
        return True

    if review.reflection == REFLECTION_OPEN and not review.entry_count:
        review.reflection = REFLECTION_SKIPPED

    if review.choices_settled() and review.reflection != REFLECTION_OPEN:
        review.status = STATUS_DONE
        return True

    return False


def review_to_dict(review: Review) -> dict:
    """Describe a review for programs that read ``--json`` output."""
    return {
        "name": review.name,
        "path": str(review.path),
        "status": review.status,
        "start": review.start,
        "end": review.end,
        "entry_count": review.entry_count,
        "active_days": review.active_days,
        "dropped": review.dropped,
        "reflection": review.reflection,
        "can_defer": review.can_defer(),
        "items": [asdict(item) for item in review.items],
    }


def _open_item(review: Review, number: int) -> Item:
    item = review.item(number)
    if not item.is_open:
        raise ReviewError(
            say(
                f"Item {number} is already settled: {item.state}.",
                f"{number}번 항목은 이미 처리되었습니다: {item.state}",
            )
        )
    return item


def reviews_folder(base: Path) -> Path:
    """Return the folder holding review files."""
    return Path(base) / "reviews"


def review_files(base: Path) -> List[Path]:
    """List review files, oldest first.

    Only files directly in the folder with a date for a name count, so the
    weekly and monthly files of the removed retrospective are not reviews.
    """
    folder = reviews_folder(base)
    if not folder.is_dir():
        return []

    found = []
    for path in folder.iterdir():
        match = _REVIEW_FILE.match(path.name)
        if match and path.is_file():
            found.append((match.group(1), int(match.group(2) or 1), path))

    return [path for _, _, path in sorted(found, key=lambda entry: entry[:2])]


def latest_review(base: Path) -> Optional[Review]:
    """Load the most recent review, if there is one."""
    files = review_files(base)
    return load_review(files[-1]) if files else None


def new_review_path(base: Path, day: str) -> Path:
    """Choose a file for a new review: ``2026-11-05.md``, then ``2026-11-05-2.md``."""
    folder = reviews_folder(base)
    candidate = folder / f"{day}.md"
    number = 2

    while candidate.exists():
        candidate = folder / f"{day}-{number}.md"
        number += 1

    return candidate


def load_review(path: Path) -> Review:
    """Read a review file.

    Raises:
        ReviewError: If the file's record cannot be read, which most likely
            means its frontmatter was edited by hand.
    """
    try:
        metadata, _ = Frontmatter.parse(Path(path).read_text(encoding="utf-8"))
        items = [_item_from_record(record) for record in metadata.get("items") or []]
        return Review(
            path=Path(path),
            start=str(metadata["period_start"]),
            end=str(metadata["period_end"]),
            status=metadata.get("status", STATUS_IN_PROGRESS),
            items=items,
            dropped=int(metadata.get("dropped", 0)),
            entry_count=int(metadata.get("entry_count", 0)),
            active_days=int(metadata.get("active_days", 0)),
            reflection=metadata.get("reflection", REFLECTION_OPEN),
            proposals_pending=bool(metadata.get("proposals_pending", False)),
        )
    except (OSError, UnicodeDecodeError, KeyError, TypeError, ValueError, AttributeError) as e:
        raise ReviewError(
            say(f"Cannot read review file {path}: {e}", f"리뷰 파일을 읽을 수 없습니다: {path}: {e}")
        )


def _item_from_record(record: dict) -> Item:
    known = {name: record[name] for name in Item.__dataclass_fields__ if name in record}
    item = Item(**known)
    item.evidence = [str(day) for day in item.evidence or []]
    return item


def save_review(review: Review, reflection_comment: str = "") -> None:
    """Write a review file, keeping the reflection section as it is.

    Args:
        review: The review
        reflection_comment: Text for a reflection section that does not exist yet
    """
    path = review.path
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    _, old_body = Frontmatter.parse(existing)
    start = _REFLECTION_START.search(old_body)
    heading = say("## Reflection", "## 회고")

    if start:
        reflection = old_body[start.start():]
    elif old_body.strip():
        # The heading was removed by hand. Keep the text, even if the summary
        # then appears twice, because it cannot be told apart from what was added.
        reflection = f"{heading}\n\n{old_body.strip()}\n"
    else:
        reflection = f"{heading}\n\n{reflection_comment}".rstrip() + "\n"

    metadata = {
        "type": "review",
        "period_start": review.start,
        "period_end": review.end,
        "status": review.status,
        "entry_count": review.entry_count,
        "active_days": review.active_days,
        "dropped": review.dropped,
        "reflection": review.reflection,
        "items": [asdict(item) for item in review.items],
    }
    if review.proposals_pending:
        metadata["proposals_pending"] = True
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        Frontmatter.inject(f"{_render_summary(review)}\n{reflection}", metadata),
        encoding="utf-8",
    )


def _render_summary(review: Review) -> str:
    lines = [
        say(f"# Review {review.name}", f"# 리뷰 {review.name}"),
        "",
        say(
            f"Period: {review.start} to {review.end}. "
            f"{review.entry_count} entries on {review.active_days} days.",
            f"기간: {review.start} ~ {review.end}. 활동 {review.active_days}일, 기록 {review.entry_count}건.",
        ),
        "",
        say("## To keep", "## 남길 것"),
        "",
    ]

    if not review.items:
        if review.is_done:
            lines.append(say("Nothing to keep.", "남길 것이 없습니다."))
        else:
            lines.append(say("Not settled yet.", "아직 정하지 않았습니다."))

    for item in review.items:
        evidence = ", ".join(item.evidence)
        suffix = f" ({evidence})" if evidence else ""
        lines.append(f"- {state_label(item)}: {item_label(item)}{suffix}")

    if review.dropped:
        lines.extend(
            [
                "",
                say(
                    f"{review.dropped} more candidates were not kept.",
                    f"이 밖의 후보 {review.dropped}건은 남기지 않았습니다.",
                ),
            ]
        )

    lines.append("")
    return "\n".join(lines)


def item_label(item: Item) -> str:
    """Describe what an item asks for."""
    if item.kind == KIND_UPDATE:
        where = f"{item.target} > {item.heading}" if item.heading else item.target
        return say(f'Update "{where}": {item.title}', f'기존 문서 갱신 "{where}": {item.title}')
    return say(f'New document: "{item.title}"', f'새 문서: "{item.title}"')


def state_label(item: Item) -> str:
    """Name an item's state."""
    labels = {
        STATE_PROPOSED: say("proposed", "제안"),
        STATE_WRITING: say("writing", "작성 중"),
        STATE_DEFERRED: say("later", "대기"),
        STATE_WRITTEN: say("written", "썼음"),
        STATE_REJECTED: say("rejected", "남기지 않음"),
        STATE_CARRIED: say("carried over", "다음 리뷰로 이월"),
    }
    return labels.get(item.state, item.state)


def start_review(
    base: Path,
    day: str,
    start: str,
    end: str,
    proposals: List[Item],
    dropped: int = 0,
    entry_count: int = 0,
    active_days: int = 0,
    reflection_comment: str = "",
    proposals_pending: bool = False,
) -> Review:
    """Create a review, carrying open items forward from the previous one.

    Carried items come first and every item is numbered within the new review.
    The new file is written before the old one is changed, so a failure between
    the two can repeat an item but cannot lose one.

    Raises:
        ReviewError: If a review is still in progress.
    """
    previous = latest_review(base)

    if previous and not previous.is_done:
        raise ReviewError(
            say(
                f"Review {previous.name} is still in progress. Finish it first.",
                f"리뷰 {previous.name}이(가) 아직 진행 중입니다. 먼저 끝내 주세요.",
            )
        )

    items: List[Item] = []

    for old in previous.open_items() if previous else []:
        items.append(Item(**{**asdict(old), "number": len(items) + 1, "decided": False, "carried": True}))

    for proposal in proposals:
        items.append(Item(**{**asdict(proposal), "number": len(items) + 1}))

    review = Review(
        path=new_review_path(base, day),
        start=start,
        end=end,
        items=items,
        dropped=dropped,
        entry_count=entry_count,
        active_days=active_days,
        proposals_pending=proposals_pending,
    )
    save_review(review, reflection_comment)

    if previous:
        for old in previous.open_items():
            old.state = STATE_CARRIED
        save_review(previous)

    return review


def rejected_titles(base: Path, reviews: int = 10) -> List[str]:
    """List what recent reviews rejected, so that it is not proposed again."""
    titles: List[str] = []

    for path in review_files(base)[-reviews:]:
        try:
            review = load_review(path)
        except ReviewError:
            continue
        titles.extend(item.title for item in review.items if item.state == STATE_REJECTED)

    return list(dict.fromkeys(titles))
