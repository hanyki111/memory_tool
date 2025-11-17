"""Daily Plan management for memory_tool.

Provides daily task planning with weekly plan integration.
"""

import re
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Tuple


class DailyPlan:
    """Manage daily plans."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize daily plan manager.

        Args:
            base_path: Base path for .memory/ (auto-detected if None)
        """
        if base_path is None:
            base_path = self._find_memory_root()

        self.base_path = base_path
        self.plans_path = base_path / "plans" / "daily"
        self.template_path = self.plans_path / "templates" / "daily.md"

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
        """Get path for daily plan file.

        Args:
            target_date: Target date (today if None)

        Returns:
            Path to plan file
        """
        if target_date is None:
            target_date = date.today()

        year_month = target_date.strftime("%Y-%m")
        day = target_date.strftime("%d")

        plan_dir = self.plans_path / year_month
        plan_dir.mkdir(parents=True, exist_ok=True)

        return plan_dir / f"{day}.md"

    def create_plan(self, target_date: Optional[date] = None) -> Path:
        """Create daily plan from template.

        Args:
            target_date: Target date (today if None)

        Returns:
            Path to created plan
        """
        if target_date is None:
            target_date = date.today()

        plan_path = self.get_plan_path(target_date)

        # Check if already exists
        if plan_path.exists():
            return plan_path

        # Load template
        if self.template_path.exists():
            template = self.template_path.read_text(encoding='utf-8')
        else:
            # Fallback template
            template = """# Daily Plan: {date}

## Today's Goals

- [ ]

## Progress

**Progress:** 0/0 (0%)

---

**Created:** {timestamp}
"""

        # Get ISO week number
        iso_calendar = target_date.isocalendar()
        week = iso_calendar[1]

        # Substitute variables
        content = template.format(
            date=target_date.strftime("%Y-%m-%d"),
            year=target_date.year,
            month=target_date.month,
            day=target_date.day,
            week=week,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # Write to file
        plan_path.write_text(content, encoding='utf-8')

        return plan_path

    def show_plan(self, target_date: Optional[date] = None) -> str:
        """Show daily plan content.

        Args:
            target_date: Target date (today if None)

        Returns:
            Plan content
        """
        plan_path = self.get_plan_path(target_date)

        if not plan_path.exists():
            if target_date is None:
                date_str = "today"
            else:
                date_str = target_date.strftime("%Y-%m-%d")
            return f"No plan found for {date_str}\nCreate one with: mplan daily"

        return plan_path.read_text(encoding='utf-8')

    def add_task(self, task: str, target_date: Optional[date] = None) -> bool:
        """Add task to daily plan.

        Args:
            task: Task description
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

        # Find "## Today's Goals" section and add task
        insert_index = None
        for i, line in enumerate(lines):
            if line.startswith("## Today's Goals"):
                # Find next empty line or next section
                insert_index = i + 2  # After heading and empty line
                break

        if insert_index is None:
            # No goals section, append at end
            lines.append("\n## Today's Goals\n")
            lines.append(f"- [ ] {task}")
        else:
            # Insert after goals heading
            lines.insert(insert_index, f"- [ ] {task}")

        # Update progress
        updated_content = '\n'.join(lines)
        updated_content = self._update_progress(updated_content)

        plan_path.write_text(updated_content, encoding='utf-8')
        return True

    def mark_done(self, task: str, target_date: Optional[date] = None) -> bool:
        """Mark task as completed.

        Args:
            task: Task description (partial match)
            target_date: Target date (today if None)

        Returns:
            True if marked, False if not found
        """
        plan_path = self.get_plan_path(target_date)

        if not plan_path.exists():
            return False

        content = plan_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Find and mark task
        marked = False
        for i, line in enumerate(lines):
            if line.strip().startswith('- [ ]') and task.lower() in line.lower():
                # Mark as completed with timestamp
                timestamp = datetime.now().strftime("%H:%M")
                lines[i] = line.replace('- [ ]', f'- [x]') + f" [{timestamp}]"
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
            Tuple of (completed, total) tasks
        """
        plan_path = self.get_plan_path(target_date)

        if not plan_path.exists():
            return (0, 0)

        content = plan_path.read_text(encoding='utf-8')

        # Count tasks
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
        # Count tasks
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
