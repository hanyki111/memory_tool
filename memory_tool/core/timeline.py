"""Timeline recording functionality."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, List
import re
from memory_tool.utils.paths import base_dir_for_root, get_project_root

# Import db for indexing (optional dependency)
try:
    from ..db import IndexManager
    INDEXING_AVAILABLE = True
except Exception:
    INDEXING_AVAILABLE = False


#: How a timeline file is named within its YYYY-MM folder.
#:
#: ``day``  -- "21.md". The original layout: compact, but the month lives only
#:             in the folder name.
#: ``date`` -- "2026-08-21.md". Needed by Obsidian's Calendar and Periodic Notes
#:             plugins, which identify a daily note by parsing its *basename*
#:             alone (they take the date format's last "/" segment). With
#:             "day" naming every month's 21.md collides and the first one found
#:             wins, so clicking a date opens the wrong month.
FILENAME_LAYOUTS = ("day", "date")
DEFAULT_FILENAME_LAYOUT = "day"

#: "2026-08-21.md"
_DATE_STEM = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
#: "21.md", which only yields a date together with its "YYYY-MM" parent folder.
_DAY_STEM = re.compile(r"^(\d{1,2})$")
_MONTH_DIR = re.compile(r"^(\d{4})-(\d{2})$")

#: "- 14:30 | message"
ENTRY_PATTERN = re.compile(r"^- (\d{1,2}:\d{2})\s*\|\s*(.+)$", re.MULTILINE)

#: Tags written before a message: "[bug][urgent] message" or "[bug] [urgent] message"
LEADING_TAGS = re.compile(r"^(\[[\w가-힣-]+\]\s*)+")
#: Tags written after a message: "message #bug #auth"
TRAILING_TAGS = re.compile(r"(\s+#[\w가-힣-]+)+$")
_BRACKET_TAG = re.compile(r"\[([\w가-힣-]+)\]")
_HASH_TAG = re.compile(r"#([\w가-힣-]+)")


def split_tags(message: str) -> Tuple[str, List[str], List[str]]:
    """Separate the tags written around a message.

    Only tags at the start (in brackets) or at the end (as hashtags) count, so a
    "#" or "[...]" in the middle of a sentence stays part of it.

    Args:
        message: An entry's text, or a message about to be recorded

    Returns:
        (message without those tags, leading tags, trailing tags)
    """
    leading: List[str] = []
    trailing: List[str] = []

    match = LEADING_TAGS.match(message)
    if match:
        leading = _BRACKET_TAG.findall(match.group(0))
        message = message[match.end():].strip()

    match = TRAILING_TAGS.search(message)
    if match:
        trailing = _HASH_TAG.findall(match.group(0))
        message = message[:match.start()].strip()

    return message, leading, trailing


def entry_tags(text: str) -> List[str]:
    """Return an entry's tags in order, without duplicates."""
    _, leading, trailing = split_tags(text)
    return list(dict.fromkeys(leading + trailing))


def parse_entry_lines(content: str) -> List[dict]:
    """Read the entries in a timeline file's content.

    Lines that are not "- HH:MM | text" are not entries and are left out; callers
    that must not lose them keep the content as well.

    Returns:
        Dicts with ``time``, ``text`` (as written) and ``tags``, in file order.
    """
    entries = []
    for match in ENTRY_PATTERN.finditer(content):
        text = match.group(2).strip()
        entries.append({"time": match.group(1), "text": text, "tags": entry_tags(text)})
    return entries


def timeline_filename(target_date, layout: str = DEFAULT_FILENAME_LAYOUT) -> str:
    """Build the filename for a timeline date.

    Args:
        target_date: date or datetime
        layout: "day" or "date"

    Returns:
        Filename including the .md suffix.
    """
    if layout == "date":
        return f"{target_date.strftime('%Y-%m-%d')}.md"
    return f"{target_date.strftime('%d')}.md"


def date_from_timeline_path(path: Path):
    """Derive the date a timeline file represents, for either naming layout.

    Callers used to join the parent folder with the file stem, which silently
    produced nonsense such as "2026-08-2026-08-21" once filenames carried the
    full date.

    Args:
        path: Path to a timeline markdown file

    Returns:
        datetime.date, or None if the path is not a dated timeline file.
    """
    from datetime import date as _date

    stem = path.stem

    match = _DATE_STEM.match(stem)
    if match:
        try:
            return _date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            return None

    match = _DAY_STEM.match(stem)
    if match:
        parent = _MONTH_DIR.match(path.parent.name)
        if not parent:
            return None
        try:
            return _date(int(parent.group(1)), int(parent.group(2)), int(match.group(1)))
        except ValueError:
            return None

    return None


def plan_filename_migration(timeline_path: Path, layout: str) -> Tuple[list, list]:
    """Plan renaming every timeline file into the requested naming layout.

    Args:
        timeline_path: The ``timeline`` directory
        layout: Target layout, "day" or "date"

    Returns:
        (moves, conflicts) where moves is a list of (source, target) pairs and
        conflicts is a list of (source, target, reason) that cannot be applied.
    """
    if layout not in FILENAME_LAYOUTS:
        raise TimelineError(
            f"Unknown filename layout: '{layout}'. "
            f"Choose one of: {', '.join(FILENAME_LAYOUTS)}"
        )

    moves = []
    conflicts = []
    claimed = {}

    if not timeline_path.is_dir():
        return moves, conflicts

    for path in sorted(timeline_path.rglob("*.md")):
        file_date = date_from_timeline_path(path)
        if file_date is None:
            continue  # not a dated timeline file; leave it alone

        target = path.parent / timeline_filename(file_date, layout)
        if target == path:
            continue

        if target.exists():
            conflicts.append((path, target, "target already exists"))
            continue

        # Two sources cannot both claim one target (a folder holding both
        # 21.md and 2026-08-21.md for the same day).
        if target in claimed:
            conflicts.append((path, target, f"also claimed by {claimed[target].name}"))
            continue

        claimed[target] = path
        moves.append((path, target))

    return moves, conflicts


def find_basename_clashes(timeline_path: Path, moves: Optional[list] = None) -> dict:
    """Find dates whose file would share a basename with another file.

    Obsidian identifies a daily note by its filename alone, ignoring the folder,
    so two files named 2026-01-08.md in different folders are as ambiguous as
    the "21.md" naming this migration exists to fix. Path-level collision checks
    do not catch this, because the two paths genuinely differ.

    Args:
        timeline_path: The ``timeline`` directory
        moves: Optional pending (source, target) pairs, so a plan can be
            checked before it is applied

    Returns:
        {basename: [paths]} for each basename claimed more than once.
    """
    renamed = {source: target for source, target in (moves or [])}
    by_name = {}

    if not timeline_path.is_dir():
        return {}

    for path in sorted(timeline_path.rglob("*.md")):
        if date_from_timeline_path(path) is None:
            continue
        final = renamed.get(path, path)
        by_name.setdefault(final.name, []).append(final)

    return {name: paths for name, paths in by_name.items() if len(paths) > 1}


def apply_filename_migration(moves: list) -> list:
    """Execute a rename plan, rolling back if any step fails.

    Args:
        moves: (source, target) pairs from plan_filename_migration()

    Returns:
        The moves that were applied.

    Raises:
        TimelineError: If a rename fails; completed renames are undone first.
    """
    import shutil

    done = []
    try:
        for source, target in moves:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(target))
            done.append((source, target))
    except Exception as e:
        for source, target in reversed(done):
            try:
                shutil.move(str(target), str(source))
            except Exception:
                raise TimelineError(
                    f"Rename failed ({e}) and rollback also failed. Timeline files "
                    f"are split between two naming layouts -- both are still "
                    f"readable, but re-run the migration to finish."
                ) from e
        raise TimelineError(f"Rename failed, rolled back cleanly: {e}") from e

    return done


class TimelineError(Exception):
    """Base exception for timeline operations."""
    pass


class FutureTimeError(TimelineError):
    """Raised when trying to record future time."""
    pass


class DistantPastWarning(TimelineError):
    """Warning for recording distant past (1+ year ago)."""
    pass


class Timeline:
    """Timeline manager for recording messages."""

    def __init__(
        self,
        base_path: Optional[Path] = None,
        use_daily_structure: bool = True,
        filename_layout: Optional[str] = None,
    ):
        """Initialize timeline manager.

        Args:
            base_path: Base path for the knowledge base. Defaults to the project root.
            use_daily_structure: Use new daily/ structure (default: True). Set to False for legacy.
            filename_layout: "day" (21.md) or "date" (2026-08-21.md). Defaults to
                the ``timeline.filename`` config value.
        """
        if base_path is None:
            base_path = get_project_root()
        self.base_path = Path(base_path)
        self.memory_path = base_dir_for_root(self.base_path)
        self.timeline_path = self.memory_path / "timeline"
        self.use_daily_structure = use_daily_structure
        self.filename_layout = filename_layout or self._configured_layout()

    def _configured_layout(self) -> str:
        """Read the filename layout from config, falling back to the default."""
        try:
            from memory_tool.utils.config import Config

            configured = Config(self.memory_path).get("timeline.filename")
        except Exception:
            return DEFAULT_FILENAME_LAYOUT

        if configured in FILENAME_LAYOUTS:
            return configured
        return DEFAULT_FILENAME_LAYOUT

    @staticmethod
    def candidate_paths(timeline_path: Path, target_date) -> List[Path]:
        """Every location a timeline file for a date could occupy.

        Covers both directory structures (daily/ and the pre-migration layout)
        and both filename layouts, so a knowledge base part-way through a
        migration stays fully readable.

        Args:
            timeline_path: The ``timeline`` directory
            target_date: date or datetime to look up

        Returns:
            Candidate paths, most current layout first.
        """
        year_month = target_date.strftime("%Y-%m")
        candidates = []

        for directory in (timeline_path / "daily" / year_month, timeline_path / year_month):
            for layout in ("date", "day"):
                candidates.append(directory / timeline_filename(target_date, layout))

        return candidates

    @staticmethod
    def resolve_existing_file(timeline_path: Path, target_date) -> Optional[Path]:
        """Find an existing timeline file for a date, whichever layout it uses.

        Entries are written to ``timeline/daily/YYYY-MM/DD.md``; the unprefixed
        path is the pre-migration location. Callers that check only one of the
        two silently report "no timeline file" for days that do exist.

        Args:
            timeline_path: The ``timeline`` directory
            target_date: date or datetime to look up

        Returns:
            The existing path, or None if neither location has the file.
        """
        for candidate in Timeline.candidate_paths(timeline_path, target_date):
            if candidate.exists():
                return candidate

        return None

    def get_timeline_file(self, date: datetime, create: bool = True) -> Path:
        """Get timeline file path for a given date.

        Args:
            date: Date for the timeline file
            create: If True, use new daily/ structure. If False, check both locations.

        Returns:
            Path to the timeline markdown file, named per the configured layout.
        """
        year_month = date.strftime("%Y-%m")
        filename = timeline_filename(date, self.filename_layout)

        if create:
            directory = (
                self.timeline_path / "daily" / year_month
                if self.use_daily_structure
                else self.timeline_path / year_month
            )
            return directory / filename

        # Reading: return whichever layout actually exists, so a knowledge base
        # part-way through a migration is still fully readable.
        existing = self.resolve_existing_file(self.timeline_path, date)
        if existing is not None:
            return existing

        # Nothing on disk -- return where a new file would go, for existence checks.
        return self.timeline_path / "daily" / year_month / filename

    def parse_time(
        self,
        date_str: Optional[str] = None,
        time_str: Optional[str] = None,
    ) -> datetime:
        """Parse date and time strings into datetime.

        Args:
            date_str: Date string in YYYY-MM-DD format (default: today)
            time_str: Time string in HH:MM format (default: now)

        Returns:
            Parsed datetime

        Raises:
            ValueError: If date/time format is invalid
            FutureTimeError: If the datetime is in the future
            DistantPastWarning: If the datetime is more than 1 year ago
        """
        now = datetime.now()

        # Parse date
        if date_str is None:
            target_date = now.date()
        else:
            # Validate format
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                raise ValueError(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError as e:
                raise ValueError(f"Invalid date: {date_str}") from e

        # Parse time
        if time_str is None:
            target_time = now.time()
        else:
            # Validate format
            if not re.match(r'^\d{1,2}:\d{2}$', time_str):
                raise ValueError(f"Invalid time format: {time_str}. Expected HH:MM")
            try:
                target_time = datetime.strptime(time_str, "%H:%M").time()
            except ValueError as e:
                raise ValueError(f"Invalid time: {time_str}") from e

        # Combine date and time
        target_dt = datetime.combine(target_date, target_time)

        # Validate: no future
        if target_dt > now:
            raise FutureTimeError(
                f"Cannot record future time: {target_dt.strftime('%Y-%m-%d %H:%M')}. "
                f"Current time: {now.strftime('%Y-%m-%d %H:%M')}"
            )

        # Warn: distant past (1+ year ago)
        one_year_ago = now - timedelta(days=365)
        if target_dt < one_year_ago:
            raise DistantPastWarning(
                f"Recording time is more than 1 year ago: {target_dt.strftime('%Y-%m-%d %H:%M')}. "
                f"This might be a mistake."
            )

        return target_dt

    def format_entry(
        self, dt: datetime, message: str, tags: Optional[List[str]] = None
    ) -> str:
        """Format a timeline entry.

        Args:
            dt: Datetime for the entry
            message: Message to record
            tags: Optional list of tags to add

        Returns:
            Formatted entry string based on config:
            - bracket format: "- 14:30 | [tag1] [tag2] Message here"
            - hashtag format: "- 14:30 | Message here #tag1 #tag2"
        """
        time_str = dt.strftime("%H:%M")

        if tags:
            # Get storage format from config
            try:
                from ..utils.config import Config
                config = Config()
                storage_format = config.get("tag.storage_format", "bracket")
            except Exception:
                storage_format = "bracket"

            if storage_format == "bracket":
                # [tag1] [tag2] format (prepended to message)
                tag_str = " ".join(f"[{t.strip().replace(' ', '-')}]" for t in tags if t.strip())
                if tag_str:
                    entry = f"- {time_str} | {tag_str} {message}"
                else:
                    entry = f"- {time_str} | {message}"
            else:
                # #tag1 #tag2 format (appended to message)
                tag_str = " ".join(f"#{t.strip().replace(' ', '-')}" for t in tags if t.strip())
                if tag_str:
                    entry = f"- {time_str} | {message} {tag_str}"
                else:
                    entry = f"- {time_str} | {message}"
        else:
            entry = f"- {time_str} | {message}"

        return entry

    def read_timeline(self, file_path: Path) -> Tuple[str, list[str]]:
        """Read existing timeline file.

        Args:
            file_path: Path to timeline file

        Returns:
            Tuple of (header, entries)
            Header is the first line (# YYYY-MM-DD Timeline)
            Entries are the remaining lines
        """
        if not file_path.exists():
            return "", []

        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines()

        if not lines:
            return "", []

        # First line should be header
        header = lines[0] if lines[0].startswith("#") else ""
        entries = lines[1:] if header else lines

        return header, entries

    def write_timeline(
        self,
        file_path: Path,
        header: str,
        entries: list[str],
    ) -> None:
        """Write timeline file.

        Args:
            file_path: Path to timeline file
            header: Header line
            entries: Entry lines
        """
        # Ensure directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Build content
        lines = []
        if header:
            lines.append(header)
        else:
            # Generate default header. Derived from the path rather than the
            # stem alone, since the stem may be "21" or "2026-08-21".
            file_date = date_from_timeline_path(file_path)
            if file_date is not None:
                lines.append(f"# {file_date.strftime('%Y-%m-%d')} Timeline")
            else:
                lines.append(f"# {file_path.stem} Timeline")

        lines.extend(entries)

        # Ensure newline at end
        content = "\n".join(lines)
        if not content.endswith("\n"):
            content += "\n"

        file_path.write_text(content, encoding="utf-8")

    def record(
        self,
        message: str,
        date_str: Optional[str] = None,
        time_str: Optional[str] = None,
        force: bool = False,
        tags: Optional[List[str]] = None,
    ) -> Tuple[datetime, Path]:
        """Record a message to timeline.

        Args:
            message: Message to record
            date_str: Optional date (YYYY-MM-DD)
            time_str: Optional time (HH:MM)
            force: If True, skip distant past warning
            tags: Optional list of tags for categorization

        Returns:
            Tuple of (datetime, file_path)

        Raises:
            TimelineError: If recording fails
        """
        # Parse and validate time
        try:
            dt = self.parse_time(date_str, time_str)
        except DistantPastWarning:
            if not force:
                raise
            # If force=True, parse again without validation
            # (We need to re-parse because the exception was raised)
            now = datetime.now()
            if date_str is None:
                target_date = now.date()
            else:
                target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if time_str is None:
                target_time = now.time()
            else:
                target_time = datetime.strptime(time_str, "%H:%M").time()
            dt = datetime.combine(target_date, target_time)

        # Get timeline file
        # During migration transition: if legacy file exists for this date, append to it
        # This prevents splitting entries across old and new structures
        # Append to whatever file already holds this date, in any layout, so a
        # day's entries are never split across two differently-named files.
        existing = self.resolve_existing_file(self.timeline_path, dt)
        file_path = existing if existing is not None else self.get_timeline_file(dt)

        # Read existing content
        header, entries = self.read_timeline(file_path)

        # Format new entry
        new_entry = self.format_entry(dt, message, tags)

        # Add to entries
        entries.append(new_entry)

        # Write back
        self.write_timeline(file_path, header, entries)

        # Index the new entry (if indexing is available)
        if INDEXING_AVAILABLE and IndexManager.available():
            try:
                indexer = IndexManager(self.memory_path)
                indexer.index_file(file_path)
            except Exception:
                # Silent failure - indexing is optional
                pass

        return dt, file_path

    def get_today(self) -> Tuple[Optional[Path], Optional[str]]:
        """Get today's timeline content.

        Returns:
            Tuple of (file_path, content)
            Returns (None, None) if today's timeline doesn't exist
        """
        today = datetime.now()
        file_path = self.get_timeline_file(today, create=False)

        if not file_path.exists():
            return None, None

        content = file_path.read_text(encoding="utf-8")
        return file_path, content

    def get_week(self) -> list[Tuple[Path, str]]:
        """Get this week's timeline files (Monday to today).

        Returns:
            List of (file_path, content) tuples, sorted by date
            Empty list if no timeline files exist
        """
        today = datetime.now()
        monday = today - timedelta(days=today.weekday())
        return [(path, content) for _, path, content in self.get_range(monday, today)]

    def get_range(self, start, end) -> List[Tuple[datetime, Path, str]]:
        """Get the timeline files from one date to another, both included.

        Args:
            start: First date (date or datetime; the time is ignored)
            end: Last date

        Returns:
            (date, file_path, content) for each day that has a file, oldest first.
        """
        current = datetime(start.year, start.month, start.day)
        last = datetime(end.year, end.month, end.day)

        results = []
        while current <= last:
            file_path = self.resolve_existing_file(self.timeline_path, current)
            if file_path is not None:
                results.append((current, file_path, file_path.read_text(encoding="utf-8")))
            current += timedelta(days=1)

        return results

    def get_month(self) -> list[Tuple[Path, str]]:
        """Get this month's timeline files (1st to today).

        Returns:
            List of (file_path, content) tuples, sorted by date
            Empty list if no timeline files exist
        """
        today = datetime.now()
        return [(path, content) for _, path, content in self.get_range(today.replace(day=1), today)]

    def get_days(self, days: int = 14) -> list[Tuple[Path, str]]:
        """Get timeline files for the last N days (including today).

        Args:
            days: Number of days to retrieve (default: 14)

        Returns:
            List of (file_path, content) tuples, sorted by date
            Empty list if no timeline files exist
        """
        today = datetime.now()
        start_date = today - timedelta(days=days - 1)
        return [(path, content) for _, path, content in self.get_range(start_date, today)]

    def get_date(self, date_str: str) -> Tuple[Optional[Path], Optional[str], Optional[datetime]]:
        """Get timeline content for a specific date.

        Args:
            date_str: Date string in various formats:
                - "2026-01-15" (full date)
                - "01-15" or "1-15" (month-day, current year)
                - "15" (day only, current month/year)

        Returns:
            Tuple of (file_path, content, parsed_date)
            Returns (None, None, None) if parsing fails or file doesn't exist
        """
        today = datetime.now()
        target_date = None

        # Try parsing different formats
        date_str = date_str.strip()

        # Format: YYYY-MM-DD
        if len(date_str) >= 8 and date_str.count("-") == 2:
            try:
                target_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                pass

        # Format: MM-DD or M-D
        if target_date is None and "-" in date_str:
            try:
                parts = date_str.split("-")
                if len(parts) == 2:
                    month = int(parts[0])
                    day = int(parts[1])
                    target_date = today.replace(month=month, day=day)
            except (ValueError, IndexError):
                pass

        # Format: DD (day only)
        if target_date is None and date_str.isdigit():
            try:
                day = int(date_str)
                target_date = today.replace(day=day)
            except ValueError:
                pass

        if target_date is None:
            return None, None, None

        file_path = self.get_timeline_file(target_date, create=False)

        if not file_path.exists():
            return file_path, None, target_date

        content = file_path.read_text(encoding="utf-8")
        return file_path, content, target_date

    def parse_entries(self, date_str: str) -> Tuple[Optional[Path], List[dict], Optional[datetime]]:
        """Parse timeline entries for a specific date.

        Args:
            date_str: Date string (YYYY-MM-DD, MM-DD, or DD)

        Returns:
            Tuple of (file_path, entries_list, parsed_date)
            entries_list contains dicts with 'time', 'message', 'line_number'
        """
        file_path, content, parsed_date = self.get_date(date_str)

        if content is None:
            return file_path, [], parsed_date

        entries = []

        for i, match in enumerate(ENTRY_PATTERN.finditer(content)):
            entries.append({
                'index': i,
                'time': match.group(1),
                'message': match.group(2).strip(),
                'start': match.start(),
                'end': match.end(),
                'raw': match.group(0)
            })

        return file_path, entries, parsed_date

    def save_entries(self, file_path: Path, entries: List[dict], date: datetime) -> None:
        """Save edited entries back to their file, changing nothing else.

        The heading, lines before the first entry and lines written by hand stay
        as they are. A hand-written line belongs to the entry above it and moves
        with it when the entries are put in time order; when that entry is
        deleted, the line goes to the entry before, so nothing written by hand
        is lost. An entry whose time and message did not change keeps its line
        exactly as written.

        Args:
            file_path: Path to timeline file
            entries: The entries to keep, as ``parse_entries`` gave them, with
                'time' and 'message' possibly changed. 'index' says which entry
                of the file each one is.
            date: Date for the timeline
        """
        original = file_path.read_text(encoding="utf-8") if file_path.exists() else ""

        head: List[str] = []
        lines_of: dict = {}    # entry index -> its line as written
        notes_of: dict = {}    # entry index -> hand-written lines under it
        current = None
        count = 0
        for line in original.splitlines():
            match = ENTRY_PATTERN.match(line)
            if match:
                current = count
                lines_of[current] = (match.group(1), match.group(2).strip(), line)
                notes_of[current] = []
                count += 1
            elif current is None:
                head.append(line)
            else:
                notes_of[current].append(line)

        if not original:
            head = [f"# {date.strftime('%Y-%m-%d')} Timeline"]

        kept = {entry["index"] for entry in entries if "index" in entry}

        # Hand-written lines of deleted entries go to the entry before them.
        carry_to = None
        for index in range(count):
            if index in kept:
                carry_to = index
            elif notes_of.get(index):
                (notes_of[carry_to] if carry_to is not None else head).extend(notes_of[index])

        def normal(time_str: str) -> str:
            hour, _, minute = time_str.partition(":")
            return f"{int(hour):02d}:{minute}"

        ordered = sorted(enumerate(entries), key=lambda item: (normal(item[1]["time"]), item[0]))

        lines = list(head)
        for _, entry in ordered:
            index = entry.get("index")
            written = lines_of.get(index)
            if written and written[0] == entry["time"] and written[1] == entry["message"]:
                lines.append(written[2])
            else:
                lines.append(f"- {normal(entry['time'])} | {entry['message']}")
            lines.extend(notes_of.get(index, []))

        content = "\n".join(lines)
        if not content.endswith("\n"):
            content += "\n"

        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
