"""Review manager for unified interface."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from .weekly_review import WeeklyReview
from .monthly_review import MonthlyReview


class ReviewManager:
    """Unified manager for weekly and monthly reviews."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize review manager.

        Args:
            base_path: Base path for .memory/ directory. Defaults to current directory.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.weekly = WeeklyReview(base_path)
        self.monthly = MonthlyReview(base_path)

    def create_weekly_review(self, date: Optional[datetime] = None) -> Path:
        """Create a new weekly review.

        Args:
            date: Reference date. Defaults to today.

        Returns:
            Path to created review file
        """
        return self.weekly.create_review(date)

    def create_monthly_review(self, date: Optional[datetime] = None) -> Path:
        """Create a new monthly review.

        Args:
            date: Reference date. Defaults to today.

        Returns:
            Path to created review file
        """
        return self.monthly.create_review(date)

    def get_weekly_review(self, week_id: Optional[str] = None, date: Optional[datetime] = None) -> Optional[Path]:
        """Get existing weekly review.

        Args:
            week_id: Week ID (e.g., "W47"). Takes precedence over date.
            date: Reference date. Defaults to today.

        Returns:
            Path to review file if exists, None otherwise
        """
        return self.weekly.get_review(week_id, date)

    def get_monthly_review(self, month: Optional[int] = None, year: Optional[int] = None, date: Optional[datetime] = None) -> Optional[Path]:
        """Get existing monthly review.

        Args:
            month: Month (1-12). Takes precedence over date.
            year: Year. Required if month is specified.
            date: Reference date. Defaults to today.

        Returns:
            Path to review file if exists, None otherwise
        """
        return self.monthly.get_review(month, year, date)

    def list_weekly_reviews(self, year: Optional[int] = None) -> list[Path]:
        """List all weekly reviews.

        Args:
            year: Filter by year. If None, return all years.

        Returns:
            List of review file paths, sorted by date (newest first)
        """
        return self.weekly.list_reviews(year)

    def list_monthly_reviews(self, year: Optional[int] = None) -> list[Path]:
        """List all monthly reviews.

        Args:
            year: Filter by year. If None, return all years.

        Returns:
            List of review file paths, sorted by date (newest first)
        """
        return self.monthly.list_reviews(year)
