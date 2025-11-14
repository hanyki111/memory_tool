"""Timeline sorting functionality."""

import re
import shutil
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime, date, time


class SortError(Exception):
    """Base exception for sort operations."""
    pass


class TimelineSorter:
    """Sorter for timeline files."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize timeline sorter.

        Args:
            base_path: Base path for project. Defaults to current directory.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"
        self.timeline_path = self.memory_path / "timeline"

    def is_initialized(self) -> bool:
        """Check if .memory/timeline/ exists.

        Returns:
            True if timeline directory exists
        """
        return self.timeline_path.exists()

    def _parse_entry(self, line: str) -> Tuple[Optional[time], str]:
        """Parse timeline entry and extract time.

        Args:
            line: Timeline entry line

        Returns:
            Tuple of (time, original_line). Time is None if not found.
        """
        # Pattern: - HH:MM | message or - H:MM | message or - HH:M | message
        # Try to extract time
        match = re.match(r'^-\s*(\d{1,2}):(\d{1,2})\s*\|', line)

        if match:
            try:
                hour = int(match.group(1))
                minute = int(match.group(2))

                # Validate time
                if 0 <= hour <= 23 and 0 <= minute <= 59:
                    return (time(hour, minute), line)
            except (ValueError, IndexError):
                pass

        # No valid time found
        return (None, line)

    def _backup_file(self, file_path: Path) -> Path:
        """Create backup of file.

        Args:
            file_path: Path to file to backup

        Returns:
            Path to backup file

        Raises:
            SortError: If backup creation fails
        """
        backup_path = file_path.with_suffix(file_path.suffix + ".bak")

        try:
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception as e:
            raise SortError(f"Failed to create backup: {e}")

    def sort_file(
        self,
        file_path: Path,
        create_backup: bool = True,
    ) -> Tuple[int, int]:
        """Sort timeline file by time.

        Args:
            file_path: Path to timeline file
            create_backup: Whether to create backup before sorting

        Returns:
            Tuple of (total_entries, sorted_entries)

        Raises:
            SortError: If sorting fails
        """
        if not file_path.exists():
            raise SortError(f"File not found: {file_path}")

        # Create backup
        if create_backup:
            self._backup_file(file_path)

        try:
            # Read file
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()

            if not lines:
                return (0, 0)

            # Separate header, entries, and footer
            header_lines = []
            entry_lines = []
            footer_lines = []

            in_entries = False

            for line in lines:
                # Check if it's an entry (starts with -)
                if line.strip().startswith("-"):
                    in_entries = True
                    entry_lines.append(line)
                elif not in_entries:
                    # Before entries (header)
                    header_lines.append(line)
                else:
                    # After entries start (footer - shouldn't normally happen)
                    # But keep them just in case
                    if line.strip():  # Non-empty line after entries
                        footer_lines.append(line)

            # Parse entries
            timed_entries = []
            untimed_entries = []

            for line in entry_lines:
                entry_time, original_line = self._parse_entry(line)

                if entry_time is not None:
                    timed_entries.append((entry_time, original_line))
                else:
                    untimed_entries.append(original_line)

            # Sort timed entries
            timed_entries.sort(key=lambda x: x[0])

            # Reconstruct file
            new_lines = []

            # Add header
            new_lines.extend(header_lines)

            # Add sorted timed entries
            for _, line in timed_entries:
                new_lines.append(line)

            # Add untimed entries at the end
            new_lines.extend(untimed_entries)

            # Add footer
            new_lines.extend(footer_lines)

            # Write back
            file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

            total = len(entry_lines)
            sorted_count = len(timed_entries)

            return (total, sorted_count)

        except Exception as e:
            raise SortError(f"Failed to sort file: {e}")

    def get_timeline_files(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[Path]:
        """Get all timeline files in date range.

        Args:
            from_date: Start date (inclusive)
            to_date: End date (inclusive)

        Returns:
            List of timeline file paths
        """
        if not self.timeline_path.exists():
            return []

        files = []

        # Find all .md files in timeline directory
        for md_file in self.timeline_path.rglob("*.md"):
            # Skip hidden files
            if md_file.name.startswith("."):
                continue

            # Check date range if specified
            if from_date or to_date:
                # Extract date from path: timeline/YYYY-MM/DD.md
                try:
                    parts = md_file.parts
                    timeline_idx = parts.index("timeline")

                    if timeline_idx + 2 >= len(parts):
                        continue

                    year_month = parts[timeline_idx + 1]
                    day_file = parts[timeline_idx + 2]

                    year, month = year_month.split("-")
                    day = day_file.replace(".md", "")

                    file_date = date(int(year), int(month), int(day))

                    # Check range
                    if from_date and file_date < from_date:
                        continue
                    if to_date and file_date > to_date:
                        continue

                except (ValueError, IndexError):
                    # If can't parse date, skip
                    continue

            files.append(md_file)

        # Sort by path (which sorts by date)
        files.sort()

        return files

    def sort_all(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        create_backup: bool = True,
    ) -> List[Tuple[Path, int, int]]:
        """Sort all timeline files in date range.

        Args:
            from_date: Start date (inclusive)
            to_date: End date (inclusive)
            create_backup: Whether to create backups

        Returns:
            List of tuples: (file_path, total_entries, sorted_entries)

        Raises:
            SortError: If sorting fails
        """
        if not self.is_initialized():
            raise SortError(
                f"Timeline not found at {self.timeline_path}. "
                f"Run 'minit' to initialize."
            )

        files = self.get_timeline_files(from_date, to_date)

        if not files:
            return []

        results = []

        for file_path in files:
            total, sorted_count = self.sort_file(file_path, create_backup)
            results.append((file_path, total, sorted_count))

        return results
