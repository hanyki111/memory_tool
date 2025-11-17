"""Monthly review functionality."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import calendar


class MonthlyReview:
    """Manager for monthly reviews."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize monthly review manager.

        Args:
            base_path: Base path for .memory/ directory. Defaults to current directory.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"
        self.reviews_path = self.memory_path / "reviews" / "monthly"
        self.weekly_reviews_path = self.memory_path / "reviews" / "weekly"
        self.timeline_path = self.memory_path / "timeline"
        self.template_path = self.memory_path / "reviews" / "templates" / "monthly.md"

    def get_month_info(self, date: Optional[datetime] = None) -> Tuple[int, int, str, int]:
        """Get month information for a given date.

        Args:
            date: Reference date. Defaults to today.

        Returns:
            Tuple of (year, month, month_name, total_days)
        """
        if date is None:
            date = datetime.now()

        year = date.year
        month = date.month
        month_name = calendar.month_name[month]
        _, total_days = calendar.monthrange(year, month)

        return year, month, month_name, total_days

    def get_review_file(self, date: Optional[datetime] = None) -> Path:
        """Get review file path for a given date.

        Args:
            date: Reference date. Defaults to today.

        Returns:
            Path to monthly review markdown file
        """
        year, month, _, _ = self.get_month_info(date)
        return self.reviews_path / str(year) / f"{month:02d}.md"

    def load_template(self) -> str:
        """Load monthly review template.

        Returns:
            Template content as string
        """
        if not self.template_path.exists():
            # Return default template if file doesn't exist
            return """# Monthly Review: {month_name} {year}

## Summary

[한 줄 요약을 작성하세요]

---

## Weekly Breakdown

{weekly_links}

---

## Achievements

### Major Milestones

- [주요 성과를 기록하세요]

### Completed Goals

- [완료한 목표를 기록하세요]

---

## Challenges & Learnings

### Challenges

- [어려웠던 점을 기록하세요]

### Learnings

- [배운 점을 기록하세요]

---

## Statistics

- **Total Entries:** {total_entries}
- **Active Days:** {active_days}/{total_days}
- **Weekly Reviews:** {weekly_reviews}/4-5

---

## Next Month Goals

- [ ] [다음 달 목표를 설정하세요]

---

**Created:** {created_date}
"""
        return self.template_path.read_text(encoding="utf-8")

    def get_weekly_links(self, year: int, month: int) -> Tuple[str, int]:
        """Generate links to weekly review files for the month.

        Args:
            year: Year
            month: Month

        Returns:
            Tuple of (markdown_links, weekly_review_count)
        """
        links = []
        weekly_count = 0

        # Get first and last day of month
        first_day = datetime(year, month, 1)
        _, last_day_num = calendar.monthrange(year, month)
        last_day = datetime(year, month, last_day_num)

        # Find all weeks that intersect with this month
        current = first_day
        seen_weeks = set()

        while current <= last_day:
            # Get ISO week number
            iso_year, iso_week, _ = current.isocalendar()
            week_id = f"W{iso_week:02d}"

            if week_id not in seen_weeks:
                seen_weeks.add(week_id)

                # Check if weekly review exists
                weekly_review_file = self.weekly_reviews_path / str(iso_year) / f"{week_id}.md"

                if weekly_review_file.exists():
                    weekly_count += 1
                    # Generate relative link
                    # From: .memory/reviews/monthly/2025/11.md
                    # To: .memory/reviews/weekly/2025/W47.md
                    rel_path = f"../../weekly/{iso_year}/{week_id}.md"
                    links.append(f"- **{week_id}:** [View Review]({rel_path})")
                else:
                    links.append(f"- **{week_id}:** No review")

            # Move to next day
            current += timedelta(days=1)

        return "\n".join(links) if links else "No weekly reviews", weekly_count

    def get_timeline_statistics(self, year: int, month: int) -> Tuple[int, int]:
        """Calculate timeline statistics for the month.

        Args:
            year: Year
            month: Month

        Returns:
            Tuple of (total_entries, active_days)
        """
        total_entries = 0
        active_days = 0

        _, last_day_num = calendar.monthrange(year, month)

        for day in range(1, last_day_num + 1):
            date = datetime(year, month, day)
            year_month = date.strftime("%Y-%m")
            day_str = date.strftime("%d")

            # Check both legacy and new timeline structures
            legacy_path = self.timeline_path / year_month / f"{day_str}.md"
            timeline_file = legacy_path if legacy_path.exists() else self.timeline_path / "daily" / year_month / f"{day_str}.md"

            if timeline_file.exists():
                # Count entries (lines starting with "- HH:MM")
                content = timeline_file.read_text(encoding="utf-8")
                entry_count = len([line for line in content.split("\n") if line.strip().startswith("- ") and "|" in line])
                total_entries += entry_count
                active_days += 1

        return total_entries, active_days

    def create_review(self, date: Optional[datetime] = None) -> Path:
        """Create a new monthly review file.

        Args:
            date: Reference date. Defaults to today.

        Returns:
            Path to created review file
        """
        year, month, month_name, total_days = self.get_month_info(date)
        review_file = self.get_review_file(date)

        # Create directory if it doesn't exist
        review_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if review already exists
        if review_file.exists():
            return review_file

        # Load template
        template = self.load_template()

        # Generate weekly links and statistics
        weekly_links, weekly_reviews = self.get_weekly_links(year, month)
        total_entries, active_days = self.get_timeline_statistics(year, month)

        # Fill template
        content = template.format(
            month_name=month_name,
            year=year,
            weekly_links=weekly_links,
            total_entries=total_entries,
            active_days=active_days,
            total_days=total_days,
            weekly_reviews=weekly_reviews,
            created_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        )

        # Write file
        review_file.write_text(content, encoding="utf-8")

        return review_file

    def get_review(self, month: Optional[int] = None, year: Optional[int] = None, date: Optional[datetime] = None) -> Optional[Path]:
        """Get existing review file.

        Args:
            month: Month (1-12). Takes precedence over date.
            year: Year. Required if month is specified.
            date: Reference date. Defaults to today.

        Returns:
            Path to review file if exists, None otherwise
        """
        if month is not None:
            if year is None:
                year = datetime.now().year
            review_file = self.reviews_path / str(year) / f"{month:02d}.md"
        else:
            review_file = self.get_review_file(date)

        return review_file if review_file.exists() else None

    def list_reviews(self, year: Optional[int] = None) -> list[Path]:
        """List all monthly reviews.

        Args:
            year: Filter by year. If None, return all years.

        Returns:
            List of review file paths, sorted by date (newest first)
        """
        reviews = []

        if year:
            year_dir = self.reviews_path / str(year)
            if year_dir.exists():
                reviews = list(year_dir.glob("*.md"))
        else:
            for year_dir in self.reviews_path.glob("*"):
                if year_dir.is_dir():
                    reviews.extend(year_dir.glob("*.md"))

        return sorted(reviews, reverse=True)
