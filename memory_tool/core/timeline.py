"""Timeline recording functionality."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import re


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

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize timeline manager.

        Args:
            base_path: Base path for .memory/ directory. Defaults to current directory.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"
        self.timeline_path = self.memory_path / "timeline"

    def get_timeline_file(self, date: datetime) -> Path:
        """Get timeline file path for a given date.

        Args:
            date: Date for the timeline file

        Returns:
            Path to timeline markdown file (YYYY-MM/DD.md)
        """
        year_month = date.strftime("%Y-%m")
        day = date.strftime("%d")
        return self.timeline_path / year_month / f"{day}.md"

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

    def format_entry(self, dt: datetime, message: str) -> str:
        """Format a timeline entry.

        Args:
            dt: Datetime for the entry
            message: Message to record

        Returns:
            Formatted entry string (e.g., "- 14:30 | Message here")
        """
        time_str = dt.strftime("%H:%M")
        return f"- {time_str} | {message}"

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
    ) -> Tuple[datetime, Path]:
        """Record a message to timeline.

        Args:
            message: Message to record
            date_str: Optional date (YYYY-MM-DD)
            time_str: Optional time (HH:MM)
            force: If True, skip distant past warning

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
        file_path = self.get_timeline_file(dt)

        # Read existing content
        header, entries = self.read_timeline(file_path)

        # Format new entry
        new_entry = self.format_entry(dt, message)

        # Add to entries
        entries.append(new_entry)

        # Write back
        self.write_timeline(file_path, header, entries)

        return dt, file_path

    def get_today(self) -> Tuple[Optional[Path], Optional[str]]:
        """Get today's timeline content.

        Returns:
            Tuple of (file_path, content)
            Returns (None, None) if today's timeline doesn't exist
        """
        today = datetime.now()
        file_path = self.get_timeline_file(today)

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
            file_path = self.get_timeline_file(current_date)
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                results.append((file_path, content))
            current_date += timedelta(days=1)

        return results
