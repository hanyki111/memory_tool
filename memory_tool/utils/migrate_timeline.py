"""Timeline migration utility.

Migrates timeline files from legacy structure (timeline/YYYY-MM/DD.md)
to new structure (timeline/daily/YYYY-MM/DD.md).
"""

from pathlib import Path
from typing import List, Tuple
import shutil


class TimelineMigrationError(Exception):
    """Base exception for timeline migration."""
    pass


class TimelineMigrator:
    """Migrates timeline files to new structure."""

    def __init__(self, base_path: Path = None):
        """Initialize migrator.

        Args:
            base_path: Base path for .memory/ directory. Defaults to current directory.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"
        self.timeline_path = self.memory_path / "timeline"
        self.daily_path = self.timeline_path / "daily"

    def find_legacy_files(self) -> List[Tuple[Path, Path]]:
        """Find all timeline files in legacy structure.

        Returns:
            List of (source_path, destination_path) tuples
        """
        if not self.timeline_path.exists():
            return []

        migrations = []

        # Find all YYYY-MM directories (legacy structure)
        for year_month_dir in self.timeline_path.iterdir():
            # Skip daily/ directory (new structure)
            if year_month_dir.name == "daily":
                continue

            # Skip non-directories
            if not year_month_dir.is_dir():
                continue

            # Check if directory name matches YYYY-MM pattern
            if not self._is_year_month_dir(year_month_dir.name):
                continue

            # Find all DD.md files in this directory
            for day_file in year_month_dir.glob("*.md"):
                if not self._is_day_file(day_file.name):
                    continue

                # Build destination path
                dest_dir = self.daily_path / year_month_dir.name
                dest_file = dest_dir / day_file.name

                # Skip if destination already exists
                if dest_file.exists():
                    continue

                migrations.append((day_file, dest_file))

        return migrations

    def _is_year_month_dir(self, name: str) -> bool:
        """Check if directory name matches YYYY-MM pattern.

        Args:
            name: Directory name

        Returns:
            True if matches YYYY-MM pattern
        """
        parts = name.split("-")
        if len(parts) != 2:
            return False

        year, month = parts
        if len(year) != 4 or not year.isdigit():
            return False
        if len(month) != 2 or not month.isdigit():
            return False
        if not (1 <= int(month) <= 12):
            return False

        return True

    def _is_day_file(self, name: str) -> bool:
        """Check if file name matches DD.md pattern.

        Args:
            name: File name

        Returns:
            True if matches DD.md pattern
        """
        if not name.endswith(".md"):
            return False

        day = name[:-3]  # Remove .md extension
        if len(day) != 2 or not day.isdigit():
            return False
        if not (1 <= int(day) <= 31):
            return False

        return True

    def migrate(self, dry_run: bool = False) -> Tuple[int, int]:
        """Migrate timeline files to new structure.

        Args:
            dry_run: If True, only show what would be migrated without actually moving files

        Returns:
            Tuple of (success_count, error_count)
        """
        migrations = self.find_legacy_files()

        if not migrations:
            return 0, 0

        success_count = 0
        error_count = 0

        for source, dest in migrations:
            try:
                if not dry_run:
                    # Create destination directory
                    dest.parent.mkdir(parents=True, exist_ok=True)

                    # Move file
                    shutil.move(str(source), str(dest))

                success_count += 1

            except Exception as e:
                error_count += 1
                # Continue with other files even if one fails

        # Clean up empty legacy directories (only if not dry-run)
        if not dry_run and success_count > 0:
            self._cleanup_empty_dirs()

        return success_count, error_count

    def _cleanup_empty_dirs(self):
        """Remove empty legacy YYYY-MM directories."""
        if not self.timeline_path.exists():
            return

        for year_month_dir in self.timeline_path.iterdir():
            # Skip daily/ directory
            if year_month_dir.name == "daily":
                continue

            # Skip non-directories
            if not year_month_dir.is_dir():
                continue

            # Check if directory is empty
            if not any(year_month_dir.iterdir()):
                try:
                    year_month_dir.rmdir()
                except Exception:
                    # Ignore errors during cleanup
                    pass


def migrate_timeline(base_path: Path = None, dry_run: bool = False) -> Tuple[int, int]:
    """Migrate timeline files to new structure.

    Args:
        base_path: Base path for .memory/ directory. Defaults to current directory.
        dry_run: If True, only show what would be migrated

    Returns:
        Tuple of (success_count, error_count)
    """
    migrator = TimelineMigrator(base_path)
    return migrator.migrate(dry_run=dry_run)
