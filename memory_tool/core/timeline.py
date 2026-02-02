"""Timeline recording functionality."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple, List
import re

# Import db for indexing (optional dependency)
try:
    from ..db import IndexManager
    INDEXING_AVAILABLE = True
except Exception:
    INDEXING_AVAILABLE = False


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

    def __init__(self, base_path: Optional[Path] = None, use_daily_structure: bool = True):
        """Initialize timeline manager.

        Args:
            base_path: Base path for .memory/ directory. Defaults to current directory.
            use_daily_structure: Use new daily/ structure (default: True). Set to False for legacy.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"
        self.timeline_path = self.memory_path / "timeline"
        self.use_daily_structure = use_daily_structure

    def get_timeline_file(self, date: datetime, create: bool = True) -> Path:
        """Get timeline file path for a given date.

        Args:
            date: Date for the timeline file
            create: If True, use new daily/ structure. If False, check both locations.

        Returns:
            Path to timeline markdown file (daily/YYYY-MM/DD.md or YYYY-MM/DD.md for legacy)
        """
        year_month = date.strftime("%Y-%m")
        day = date.strftime("%d")

        if create and self.use_daily_structure:
            # New structure: timeline/daily/YYYY-MM/DD.md
            return self.timeline_path / "daily" / year_month / f"{day}.md"
        elif create:
            # Legacy structure: timeline/YYYY-MM/DD.md
            return self.timeline_path / year_month / f"{day}.md"
        else:
            # Reading: Prefer legacy path if it exists (for backward compatibility during migration)
            # This ensures old entries are not hidden when both files exist
            legacy_path = self.timeline_path / year_month / f"{day}.md"
            if legacy_path.exists():
                return legacy_path
            # Try new structure if legacy doesn't exist
            new_path = self.timeline_path / "daily" / year_month / f"{day}.md"
            if new_path.exists():
                return new_path
            # Return new path as default (for existence checks)
            return new_path

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
            # Generate default header
            date_str = file_path.stem  # DD from DD.md
            year_month = file_path.parent.name  # YYYY-MM
            lines.append(f"# {year_month}-{date_str} Timeline")

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
        year_month = dt.strftime("%Y-%m")
        day = dt.strftime("%d")
        legacy_path = self.timeline_path / year_month / f"{day}.md"

        if legacy_path.exists():
            # Use legacy file if it exists (backward compatibility during migration)
            file_path = legacy_path
        else:
            # Use new structure for new files
            file_path = self.get_timeline_file(dt)

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

        # Find Monday of current week
        days_since_monday = today.weekday()  # 0=Monday, 6=Sunday
        monday = today - timedelta(days=days_since_monday)

        # Collect files from Monday to today
        results = []
        current_date = monday
        while current_date <= today:
            file_path = self.get_timeline_file(current_date, create=False)
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                results.append((file_path, content))
            current_date += timedelta(days=1)

        return results

    def get_month(self) -> list[Tuple[Path, str]]:
        """Get this month's timeline files (1st to today).

        Returns:
            List of (file_path, content) tuples, sorted by date
            Empty list if no timeline files exist
        """
        today = datetime.now()

        # First day of current month
        first_day = today.replace(day=1)

        # Collect files from 1st to today
        results = []
        current_date = first_day
        while current_date <= today:
            file_path = self.get_timeline_file(current_date, create=False)
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                results.append((file_path, content))
            current_date += timedelta(days=1)

        return results

    def get_days(self, days: int = 14) -> list[Tuple[Path, str]]:
        """Get timeline files for the last N days (including today).

        Args:
            days: Number of days to retrieve (default: 14)

        Returns:
            List of (file_path, content) tuples, sorted by date
            Empty list if no timeline files exist
        """
        today = datetime.now()

        # Start date is (days-1) days ago
        start_date = today - timedelta(days=days - 1)

        # Collect files from start_date to today
        results = []
        current_date = start_date
        while current_date <= today:
            file_path = self.get_timeline_file(current_date, create=False)
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                results.append((file_path, content))
            current_date += timedelta(days=1)

        return results
