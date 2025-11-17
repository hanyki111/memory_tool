"""Weekly review functionality."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import calendar


class WeeklyReview:
    """Manager for weekly reviews."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize weekly review manager.

        Args:
            base_path: Base path for .memory/ directory. Defaults to current directory.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"
        self.reviews_path = self.memory_path / "reviews" / "weekly"
        self.timeline_path = self.memory_path / "timeline"
        self.template_path = self.memory_path / "reviews" / "templates" / "weekly.md"

    def get_week_info(self, date: Optional[datetime] = None) -> Tuple[int, int, datetime, datetime]:
        """Get week information for a given date.

        Args:
            date: Reference date. Defaults to today.

        Returns:
            Tuple of (year, week_number, week_start, week_end)
        """
        if date is None:
            date = datetime.now()

        # ISO week number
        year, week, _ = date.isocalendar()

        # Calculate week start (Monday) and end (Sunday)
        week_start = date - timedelta(days=date.weekday())
        week_end = week_start + timedelta(days=6)

        return year, week, week_start, week_end

    def get_week_id(self, date: Optional[datetime] = None) -> str:
        """Get week ID in W## format.

        Args:
            date: Reference date. Defaults to today.

        Returns:
            Week ID string (e.g., "W47")
        """
        year, week, _, _ = self.get_week_info(date)
        return f"W{week:02d}"

    def get_review_file(self, date: Optional[datetime] = None) -> Path:
        """Get review file path for a given date.

        Args:
            date: Reference date. Defaults to today.

        Returns:
            Path to weekly review markdown file
        """
        year, week, _, _ = self.get_week_info(date)
        week_id = f"W{week:02d}"
        return self.reviews_path / str(year) / f"{week_id}.md"

    def load_template(self) -> str:
        """Load weekly review template.

        Returns:
            Template content as string
        """
        if not self.template_path.exists():
            # Return default template if file doesn't exist
            return """# Weekly Review: {week_id} ({date_range})

## Summary

[한 줄 요약을 작성하세요]

---

## Daily Timelines

{daily_timeline_links}

---

## Highlights

### What Went Well

- [잘된 점을 기록하세요]

### What Could Be Better

- [개선할 점을 기록하세요]

### Key Learnings

- [배운 점을 기록하세요]

---

## Statistics

- **Total Entries:** {total_entries}
- **Active Days:** {active_days}/7

---

## Next Week Goals

- [ ] [다음 주 목표를 설정하세요]

---

**Created:** {created_date}
"""
        return self.template_path.read_text(encoding="utf-8")

    def get_daily_timeline_links(self, week_start: datetime, week_end: datetime) -> Tuple[str, int, int]:
        """Generate links to daily timeline files for the week.

        Args:
            week_start: Start of the week (Monday)
            week_end: End of the week (Sunday)

        Returns:
            Tuple of (markdown_links, total_entries, active_days)
        """
        links = []
        total_entries = 0
        active_days = 0

        current = week_start
        while current <= week_end:
            day_name = current.strftime("%a")
            date_str = current.strftime("%m/%d")

            # Check both legacy and new timeline structures
            year_month = current.strftime("%Y-%m")
            day = current.strftime("%d")

            # Try legacy path first
            legacy_path = self.timeline_path / year_month / f"{day}.md"
            timeline_file = legacy_path if legacy_path.exists() else self.timeline_path / "daily" / year_month / f"{day}.md"

            if timeline_file.exists():
                # Count entries (lines starting with "- HH:MM")
                content = timeline_file.read_text(encoding="utf-8")
                entry_count = len([line for line in content.split("\n") if line.strip().startswith("- ") and "|" in line])
                total_entries += entry_count
                active_days += 1

                # Generate relative link
                # From: .memory/reviews/weekly/2025/W47.md
                # To: .memory/timeline/daily/2025-11/17.md
                rel_path = f"../../../timeline/daily/{year_month}/{day}.md"
                links.append(f"- **{day_name} {date_str}:** [{timeline_file.name}]({rel_path}) - {entry_count} entries")
            else:
                links.append(f"- **{day_name} {date_str}:** No timeline")

            current += timedelta(days=1)

        return "\n".join(links), total_entries, active_days

    def create_review(self, date: Optional[datetime] = None) -> Path:
        """Create a new weekly review file.

        Args:
            date: Reference date. Defaults to today.

        Returns:
            Path to created review file
        """
        year, week, week_start, week_end = self.get_week_info(date)
        week_id = f"W{week:02d}"
        review_file = self.get_review_file(date)

        # Create directory if it doesn't exist
        review_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if review already exists
        if review_file.exists():
            return review_file

        # Load template
        template = self.load_template()

        # Generate daily timeline links and statistics
        daily_links, total_entries, active_days = self.get_daily_timeline_links(week_start, week_end)

        # Format date range
        date_range = f"{week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}"

        # Fill template
        content = template.format(
            week_id=week_id,
            date_range=date_range,
            daily_timeline_links=daily_links,
            total_entries=total_entries,
            active_days=active_days,
            created_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        # Write file
        review_file.write_text(content, encoding="utf-8")

        return review_file

    def get_review(self, week_id: Optional[str] = None, date: Optional[datetime] = None) -> Optional[Path]:
        """Get existing review file.

        Args:
            week_id: Week ID (e.g., "W47"). Takes precedence over date.
            date: Reference date. Defaults to today.

        Returns:
            Path to review file if exists, None otherwise
        """
        if week_id:
            # Parse week_id (W##)
            if not week_id.startswith("W"):
                return None
            try:
                week_num = int(week_id[1:])
            except ValueError:
                return None

            # Find the file in any year directory
            for year_dir in sorted(self.reviews_path.glob("*"), reverse=True):
                if year_dir.is_dir():
                    review_file = year_dir / f"{week_id}.md"
                    if review_file.exists():
                        return review_file
            return None
        else:
            review_file = self.get_review_file(date)
            return review_file if review_file.exists() else None

    def list_reviews(self, year: Optional[int] = None) -> list[Path]:
        """List all weekly reviews.

        Args:
            year: Filter by year. If None, return all years.

        Returns:
            List of review file paths, sorted by date (newest first)
        """
        reviews = []

        if year:
            year_dir = self.reviews_path / str(year)
            if year_dir.exists():
                reviews = list(year_dir.glob("W*.md"))
        else:
            for year_dir in self.reviews_path.glob("*"):
                if year_dir.is_dir():
                    reviews.extend(year_dir.glob("W*.md"))

        return sorted(reviews, reverse=True)
