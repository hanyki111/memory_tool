"""Plan-Timeline integration for memory_tool.

Provides bidirectional linking between plans and timeline:
- When a plan task is completed, automatically record it in timeline
- Add bidirectional references between plan and timeline entries
"""

from datetime import datetime, date
from pathlib import Path
from typing import Optional
import re
from memory_tool.utils.paths import get_base_path


class PlanTimelineIntegration:
    """Manage integration between Plan and Timeline systems."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize Plan-Timeline integration.

        Args:
            base_path: Base path for .memory/ (auto-detected if None)
        """
        if base_path is None:
            base_path = self._find_memory_root()

        self.base_path = base_path
        self.timeline_path = base_path / "timeline"
        self.plans_path = base_path / "plans"

    def _find_memory_root(self) -> Path:
        """Find the knowledge base folder.

        Delegates to the central resolver so the configurable base folder
        name (and a base of ".") is honoured.
        """
        return get_base_path()

    def record_task_completion(
        self,
        task: str,
        plan_type: str,
        plan_date: date,
        completion_time: Optional[datetime] = None
    ) -> Optional[Path]:
        """Record task completion in timeline.

        Args:
            task: Task description
            plan_type: Type of plan ('daily', 'weekly', 'monthly')
            plan_date: Date of the plan
            completion_time: Completion time (now if None)

        Returns:
            Path to timeline file, or None if failed
        """
        if completion_time is None:
            completion_time = datetime.now()

        # Import Timeline here to avoid circular imports
        from ..core.timeline import Timeline

        # Timeline expects base_path to be the project root (parent of .memory)
        # But self.base_path is already .memory/ directory
        project_root = self.base_path.parent
        timeline = Timeline(project_root)

        # Format message with plan context
        plan_label = self._format_plan_label(plan_type, plan_date)
        message = f"\u2713 {task} ({plan_label})"

        # Record to timeline
        try:
            dt, timeline_path = timeline.record(
                message=message,
                date_str=completion_time.strftime("%Y-%m-%d"),
                time_str=completion_time.strftime("%H:%M")
            )
            return timeline_path
        except Exception:
            # Silent failure - timeline recording is optional
            return None

    def add_timeline_reference_to_plan(
        self,
        plan_path: Path,
        task: str,
        timeline_time: str
    ) -> bool:
        """Add timeline reference to completed task in plan.

        Args:
            plan_path: Path to plan file
            task: Task description (for finding the line)
            timeline_time: Time string (HH:MM)

        Returns:
            True if added, False otherwise
        """
        if not plan_path.exists():
            return False

        content = plan_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Find the task line that was just marked as completed
        updated = False
        for i, line in enumerate(lines):
            if line.strip().startswith('- [x]') and task.lower() in line.lower():
                # Check if timeline reference already exists
                if not re.search(r'\[Timeline: \d{2}:\d{2}\]', line):
                    # Add timeline reference
                    lines[i] = line.rstrip() + f" [Timeline: {timeline_time}]"
                    updated = True
                    break

        if updated:
            plan_path.write_text('\n'.join(lines), encoding='utf-8')

        return updated

    def _format_plan_label(self, plan_type: str, plan_date: date) -> str:
        """Format plan label for timeline entry.

        Args:
            plan_type: Type of plan ('daily', 'weekly', 'monthly')
            plan_date: Date of the plan

        Returns:
            Formatted label string
        """
        if plan_type == 'daily':
            return "Daily Plan"
        elif plan_type == 'weekly':
            week = plan_date.isocalendar()[1]
            return f"Weekly Plan W{week:02d}"
        elif plan_type == 'monthly':
            month_name = plan_date.strftime("%B")
            return f"Monthly Plan {month_name}"
        else:
            return "Plan"

    def get_timeline_path(self, target_date: date) -> Path:
        """Get timeline file path for a date.

        Args:
            target_date: Target date

        Returns:
            Path to timeline file
        """
        year_month = target_date.strftime("%Y-%m")
        day = target_date.strftime("%d")

        # Try new structure first
        new_path = self.timeline_path / "daily" / year_month / f"{day}.md"
        if new_path.exists():
            return new_path

        # Fall back to legacy structure
        legacy_path = self.timeline_path / year_month / f"{day}.md"
        return legacy_path

    def get_relative_path(self, from_path: Path, to_path: Path) -> str:
        """Get relative path from one file to another.

        Args:
            from_path: Source file path
            to_path: Target file path

        Returns:
            Relative path string
        """
        try:
            rel_path = Path(to_path).relative_to(from_path.parent)
            return str(rel_path).replace('\\', '/')
        except ValueError:
            # If relative_to fails, use absolute path
            return str(to_path)
