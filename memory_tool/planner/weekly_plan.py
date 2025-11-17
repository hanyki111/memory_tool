"""Weekly Plan management for memory_tool.

Provides weekly goal planning with daily plan integration.
"""

import re
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Tuple


class WeeklyPlan:
    """Manage weekly plans."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize weekly plan manager.

        Args:
            base_path: Base path for .memory/ (auto-detected if None)
        """
        if base_path is None:
            base_path = self._find_memory_root()

        self.base_path = base_path
        self.plans_path = base_path / "plans" / "weekly"
        self.template_path = self.plans_path / "templates" / "weekly.md"

    def _find_memory_root(self) -> Path:
        """Find .memory/ directory in current or parent directories."""
        current = Path.cwd()
        while current != current.parent:
            memory_path = current / ".memory"
            if memory_path.exists() and memory_path.is_dir():
                return memory_path
            current = current.parent

        # Default to current directory
        return Path.cwd() / ".memory"

    def get_week_info(self, target_date: Optional[date] = None) -> Tuple[int, int, date, date]:
        """Get week information for a date.

        Args:
            target_date: Target date (today if None)

        Returns:
            Tuple of (year, week, start_date, end_date)
        """
        if target_date is None:
            target_date = date.today()

        iso_calendar = target_date.isocalendar()
        year = iso_calendar[0]
        week = iso_calendar[1]

        # Calculate week start (Monday) and end (Sunday)
        # Get Monday of the week
        days_since_monday = target_date.weekday()
        week_start = target_date - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)

        return (year, week, week_start, week_end)

    def get_plan_path(self, target_date: Optional[date] = None) -> Path:
        """Get path for weekly plan file.

        Args:
            target_date: Target date (today if None)

        Returns:
            Path to plan file
        """
        year, week, _, _ = self.get_week_info(target_date)

        plan_dir = self.plans_path / str(year)
        plan_dir.mkdir(parents=True, exist_ok=True)

        return plan_dir / f"W{week:02d}.md"

    def create_plan(self, target_date: Optional[date] = None) -> Path:
        """Create weekly plan from template.

        Args:
            target_date: Target date (today if None)

        Returns:
            Path to created plan
        """
        year, week, week_start, week_end = self.get_week_info(target_date)
        plan_path = self.get_plan_path(target_date)

        # Check if already exists
        if plan_path.exists():
            return plan_path

        # Load template
        if self.template_path.exists():
            template = self.template_path.read_text(encoding='utf-8')
        else:
            # Fallback template
            template = """# Weekly Plan: W{week} ({start_date} ~ {end_date})

## Weekly Goals

- [ ]

## Daily Breakdown

{daily_links}

**Progress:** 0/0 (0%)

---

**Created:** {timestamp}
"""

        # Generate daily links
        daily_links = []
        current = week_start
        day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day_name in enumerate(day_names):
            day_date = current + timedelta(days=i)
            link = f"- **{day_name} {day_date.strftime('%m/%d')}:** [Daily Plan](../../daily/{day_date.strftime('%Y-%m')}/{day_date.strftime('%d')}.md)"
            daily_links.append(link)

        daily_links_str = '\n'.join(daily_links)

        # Substitute variables
        content = template.format(
            week=week,
            year=year,
            month=week_start.month,  # First day's month
            start_date=week_start.strftime("%Y-%m-%d"),
            end_date=week_end.strftime("%Y-%m-%d"),
            daily_links=daily_links_str,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # Write to file
        plan_path.write_text(content, encoding='utf-8')

        return plan_path

    def show_plan(self, week_id: Optional[str] = None) -> str:
        """Show weekly plan content.

        Args:
            week_id: Week ID (e.g., "W47") or None for current week

        Returns:
            Plan content
        """
        if week_id:
            # Parse W## format
            match = re.match(r'W(\d+)', week_id, re.IGNORECASE)
            if not match:
                return f"Invalid week ID: {week_id}. Use format: W47"

            week_num = int(match.group(1))
            year = date.today().year

            # Find the date for this week
            # Start from Jan 1 and find the Monday of week N
            jan1 = date(year, 1, 1)
            # ISO week 1 is the week with the first Thursday
            # Find first Monday of year
            days_to_monday = (7 - jan1.weekday()) % 7
            if days_to_monday == 0 and jan1.weekday() > 3:
                days_to_monday = 7
            first_monday = jan1 + timedelta(days=days_to_monday)

            # Calculate target date
            target_date = first_monday + timedelta(weeks=week_num - 1)
            plan_path = self.get_plan_path(target_date)
        else:
            plan_path = self.get_plan_path()

        if not plan_path.exists():
            return f"No weekly plan found\nCreate one with: mplan weekly"

        return plan_path.read_text(encoding='utf-8')

    def add_goal(self, goal: str, target_date: Optional[date] = None) -> bool:
        """Add goal to weekly plan.

        Args:
            goal: Goal description
            target_date: Target date (today if None)

        Returns:
            True if added, False if plan doesn't exist
        """
        plan_path = self.get_plan_path(target_date)

        if not plan_path.exists():
            # Auto-create plan
            self.create_plan(target_date)

        content = plan_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Find "## Weekly Goals" section and add goal
        insert_index = None
        for i, line in enumerate(lines):
            if line.startswith("## Weekly Goals"):
                insert_index = i + 2
                break

        if insert_index is None:
            lines.append("\n## Weekly Goals\n")
            lines.append(f"- [ ] {goal}")
        else:
            lines.insert(insert_index, f"- [ ] {goal}")

        # Update progress
        updated_content = '\n'.join(lines)
        updated_content = self._update_progress(updated_content)

        plan_path.write_text(updated_content, encoding='utf-8')
        return True

    def mark_done(self, goal: str, target_date: Optional[date] = None) -> bool:
        """Mark goal as completed.

        Args:
            goal: Goal description (partial match)
            target_date: Target date (today if None)

        Returns:
            True if marked, False if not found
        """
        plan_path = self.get_plan_path(target_date)

        if not plan_path.exists():
            return False

        content = plan_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Find and mark goal
        marked = False
        for i, line in enumerate(lines):
            if line.strip().startswith('- [ ]') and goal.lower() in line.lower():
                lines[i] = line.replace('- [ ]', '- [x]')
                marked = True
                break

        if not marked:
            return False

        # Update progress
        updated_content = '\n'.join(lines)
        updated_content = self._update_progress(updated_content)

        plan_path.write_text(updated_content, encoding='utf-8')
        return True

    def get_progress(self, target_date: Optional[date] = None) -> Tuple[int, int]:
        """Get progress statistics.

        Args:
            target_date: Target date (today if None)

        Returns:
            Tuple of (completed, total) goals
        """
        plan_path = self.get_plan_path(target_date)

        if not plan_path.exists():
            return (0, 0)

        content = plan_path.read_text(encoding='utf-8')

        # Count goals
        total = len(re.findall(r'- \[[ x]\]', content))
        completed = len(re.findall(r'- \[x\]', content))

        return (completed, total)

    def _update_progress(self, content: str) -> str:
        """Update progress section in content.

        Args:
            content: Plan content

        Returns:
            Updated content
        """
        # Count goals
        total = len(re.findall(r'- \[[ x]\]', content))
        completed = len(re.findall(r'- \[x\]', content))

        # Calculate percentage
        if total > 0:
            percentage = (completed / total) * 100
        else:
            percentage = 0

        # Update progress line
        progress_line = f"**Progress:** {completed}/{total} ({percentage:.0f}%)"
        content = re.sub(
            r'\*\*Progress:\*\* \d+/\d+ \(\d+%\)',
            progress_line,
            content
        )

        return content
