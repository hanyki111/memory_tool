"""Timeline sorting functionality."""

import re
import shutil
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime, date, time
from memory_tool.utils.paths import base_dir_for_root, get_project_root


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
            base_path = get_project_root()
        self.base_path = Path(base_path)
        self.memory_path = base_dir_for_root(self.base_path)
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

            # Reorder each contiguous run of timed entries in place, leaving
            # every other line exactly where it is.
            #
            # Only "- HH:MM | ..." counts as an entry. Treating any "- " line as
            # one meant a note's own list items -- an Obsidian Daily Note
            # template's "- [ ] task", for instance -- were pulled out of their
            # section, appended after the entries, and had their surrounding
            # headings and blank lines dropped.
            new_lines: List[str] = []
            # Each entry carries its own continuation lines so they move with it.
            run: List[Tuple[time, int, List[str]]] = []
            total = 0
            sorted_count = 0

            def flush_run() -> None:
                """Emit the pending run of entries in time order."""
                if not run:
                    return
                # Sort by time, then original position, so entries sharing a
                # timestamp keep the order they were recorded in.
                run.sort(key=lambda item: (item[0], item[1]))
                for _, _, block in run:
                    new_lines.extend(block)
                run.clear()

            for index, line in enumerate(lines):
                entry_time, _ = self._parse_entry(line.strip())

                if entry_time is not None:
                    total += 1
                    sorted_count += 1
                    run.append((entry_time, index, [line]))
                    continue

                # An indented line belongs to the entry above it (a sub-bullet
                # added while editing the note), so it travels with that entry
                # instead of being stranded when the order changes.
                if run and line[:1] in (" ", "\t"):
                    run[-1][2].append(line)
                    if line.strip().startswith("-"):
                        total += 1
                    continue

                # Untimed top-level "- " lines still count toward the reported
                # total, for continuity with previous output, but never move.
                if line.strip().startswith("-"):
                    total += 1

                flush_run()
                new_lines.append(line)

            flush_run()

            # Write back
            file_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")

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
