"""Monthly Plan management for memory_tool.

Provides monthly milestone planning with weekly plan integration.
"""

import re
import calendar
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, Tuple, List


class MonthlyPlan:
    """Manage monthly plans."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize monthly plan manager.

        Args:
            base_path: Base path for .memory/ (auto-detected if None)
        """
        if base_path is None:
            base_path = self._find_memory_root()

        self.base_path = base_path
        self.plans_path = base_path / "plans" / "monthly"
        self.template_path = self.plans_path / "templates" / "monthly.md"

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

    def get_plan_path(self, target_date: Optional[date] = None) -> Path:
        """Get path for monthly plan file.

        Args:
            target_date: Target date (today if None)

        Returns:
            Path to plan file
        """
        if target_date is None:
            target_date = date.today()

        year = target_date.year
        month = target_date.month

        plan_dir = self.plans_path / str(year)
        plan_dir.mkdir(parents=True, exist_ok=True)

        return plan_dir / f"{month:02d}.md"

    def get_weeks_in_month(self, year: int, month: int) -> List[Tuple[int, str]]:
        """Get ISO week numbers for a month.

        Args:
            year: Year
            month: Month (1-12)

        Returns:
            List of (week_number, date_range_str) tuples
        """
        # Get first and last day of month
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        weeks = []
        current = first_day

        while current <= last_day:
            week_num = current.isocalendar()[1]

            # Find Monday of this week
            days_since_monday = current.weekday()
            week_start = current - timedelta(days=days_since_monday)

            # Find Sunday of this week
            week_end = week_start + timedelta(days=6)

            # Only include dates within the month
            display_start = max(week_start, first_day)
            display_end = min(week_end, last_day)

            date_range = f"{display_start.strftime('%m/%d')}-{display_end.strftime('%m/%d')}"

            if week_num not in [w[0] for w in weeks]:
                weeks.append((week_num, date_range))

            # Move to next week
            current = week_end + timedelta(days=1)

        return weeks

    def create_plan(self, target_date: Optional[date] = None) -> Path:
        """Create monthly plan from template.

        Args:
            target_date: Target date (today if None)

        Returns:
            Path to created plan
        """
        if target_date is None:
            target_date = date.today()

        year = target_date.year
        month = target_date.month
        plan_path = self.get_plan_path(target_date)

        # Check if already exists
        if plan_path.exists():
            return plan_path

        # Load template
        if self.template_path.exists():
            template = self.template_path.read_text(encoding='utf-8')
        else:
            # Fallback template
            template = """# Monthly Plan: {month_name} {year}

## Monthly Goals

- [ ]

## Milestones

{milestones}

## Weekly Plans

{weekly_links}

**Progress:** 0/0 (0%)

---

**Created:** {timestamp}
"""

        # Get weeks in month
        weeks = self.get_weeks_in_month(year, month)

        # Generate milestones
        milestones = []
        for i, (week_num, date_range) in enumerate(weeks, 1):
            milestones.append(f"- Week {i} ({date_range}):")

        milestones_str = '\n'.join(milestones)

        # Generate weekly links
        weekly_links = []
        for week_num, _ in weeks:
            link = f"- [W{week_num:02d}](../../weekly/{year}/W{week_num:02d}.md)"
            weekly_links.append(link)

        weekly_links_str = '\n'.join(weekly_links)

        # Get month name
        month_name = calendar.month_name[month]

        # Substitute variables
        content = template.format(
            year=year,
            month=month,
            month_name=month_name,
            milestones=milestones_str,
            weekly_links=weekly_links_str,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # Write to file
        plan_path.write_text(content, encoding='utf-8')

        return plan_path

    def show_plan(self, month_id: Optional[str] = None) -> str:
        """Show monthly plan content.

        Args:
            month_id: Month ID (e.g., "11") or None for current month

        Returns:
            Plan content
        """
        if month_id:
            try:
                month_num = int(month_id)
                if not 1 <= month_num <= 12:
                    return f"Invalid month: {month_id}. Use 01-12"

                year = date.today().year
                target_date = date(year, month_num, 1)
                plan_path = self.get_plan_path(target_date)
            except ValueError:
                return f"Invalid month ID: {month_id}. Use format: 11"
        else:
            plan_path = self.get_plan_path()

        if not plan_path.exists():
            return f"No monthly plan found\nCreate one with: mplan monthly"

        return plan_path.read_text(encoding='utf-8')

    def add_goal(self, goal: str, target_date: Optional[date] = None) -> bool:
        """Add goal to monthly plan.

        Args:
            goal: Goal description
            target_date: Target date (today if None)

        Returns:
            True if added
        """
        plan_path = self.get_plan_path(target_date)

        if not plan_path.exists():
            # Auto-create plan
            self.create_plan(target_date)

        content = plan_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Find "## Monthly Goals" section and add goal
        insert_index = None
        for i, line in enumerate(lines):
            if line.startswith("## Monthly Goals"):
                insert_index = i + 2
                break

        if insert_index is None:
            lines.append("\n## Monthly Goals\n")
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
        if target_date is None:
            target_date = date.today()

        plan_path = self.get_plan_path(target_date)

        if not plan_path.exists():
            return False

        content = plan_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Find and mark goal
        marked = False
        completion_time = datetime.now()

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

        # Record completion in timeline (Plan-Timeline integration)
        try:
            from .integration import PlanTimelineIntegration
            integration = PlanTimelineIntegration(self.base_path)
            integration.record_task_completion(
                task=goal,
                plan_type='monthly',
                plan_date=target_date,
                completion_time=completion_time
            )
        except Exception:
            # Silent failure - integration is optional
            pass

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
