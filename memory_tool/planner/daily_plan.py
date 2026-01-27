"""Daily Plan management for memory_tool.

Provides daily task planning with weekly plan integration.
"""

import re
from datetime import datetime, date, timedelta
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

<!-- Add tasks with: mplan daily add "task" -->

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

    def parse_date_keyword(self, keyword: str) -> Optional[date]:
        """Parse date keyword like 'yesterday' or date string.

        Args:
            keyword: Date keyword or YYYY-MM-DD format

        Returns:
            Parsed date or None if invalid
        """
        keyword_lower = keyword.lower()

        if keyword_lower == "yesterday":
            return date.today() - timedelta(days=1)
        elif keyword_lower == "today":
            return date.today()
        else:
            # Try to parse as date
            try:
                return datetime.strptime(keyword, "%Y-%m-%d").date()
            except ValueError:
                return None

    def _format_for_display(self, content: str) -> str:
        """Format content for display with visual check marks.

        Converts '- [x]' to checkmark symbol for better visual feedback.
        File content remains unchanged (uses [x]).

        Args:
            content: Plan content

        Returns:
            Formatted content for display
        """
        # Replace completed tasks with check mark (U+2713)
        return re.sub(r'^- \[x\]', '- \u2713', content, flags=re.MULTILINE)

    def show_plan(self, target_date: Optional[date] = None, auto_update: bool = True) -> str:
        """Show daily plan content.

        Args:
            target_date: Target date (today if None)
            auto_update: If True, automatically update progress before showing

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

        # Auto-update progress if requested
        if auto_update:
            try:
                content = plan_path.read_text(encoding='utf-8')
                updated_content = self._update_progress(content)
                # Save if changed
                if updated_content != content:
                    plan_path.write_text(updated_content, encoding='utf-8')
                return self._format_for_display(updated_content)
            except Exception:
                # If update fails, just return original content
                return self._format_for_display(plan_path.read_text(encoding='utf-8'))

        return self._format_for_display(plan_path.read_text(encoding='utf-8'))

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

    def get_tasks(self, target_date: Optional[date] = None, incomplete_only: bool = False) -> List[dict]:
        """Get list of tasks from plan.

        Args:
            target_date: Target date (today if None)
            incomplete_only: Only return incomplete tasks

        Returns:
            List of task dicts with 'index', 'text', 'completed', 'line_num'
        """
        if target_date is None:
            target_date = date.today()

        plan_path = self.get_plan_path(target_date)

        if not plan_path.exists():
            return []

        content = plan_path.read_text(encoding='utf-8')
        lines = content.split('\n')
        tasks = []
        index = 1

        for line_num, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('- [ ]'):
                # Incomplete task
                text = stripped[5:].strip()
                tasks.append({
                    'index': index,
                    'text': text,
                    'completed': False,
                    'line_num': line_num
                })
                index += 1
            elif stripped.startswith('- [x]'):
                # Completed task
                if not incomplete_only:
                    text = stripped[5:].strip()
                    # Remove timestamp suffix if present
                    text = re.sub(r'\s*\[\d{1,2}:\d{2}\]$', '', text)
                    tasks.append({
                        'index': index,
                        'text': text,
                        'completed': True,
                        'line_num': line_num
                    })
                index += 1

        return tasks

    def _find_matching_task(self, query: str, tasks: List[dict]) -> Optional[dict]:
        """Find a task matching the query (prefix or contains).

        Matching priority:
        1. Exact match (case-insensitive)
        2. Unique prefix match (if query is a unique prefix)
        3. Contains match (if only one task contains the query)

        Args:
            query: Search query
            tasks: List of task dicts (incomplete only)

        Returns:
            Matching task dict, or None if not found or ambiguous
        """
        query_lower = query.lower()
        incomplete_tasks = [t for t in tasks if not t['completed']]

        # 1. Exact match
        for task in incomplete_tasks:
            if task['text'].lower() == query_lower:
                return task

        # 2. Prefix match - find all tasks that start with query
        prefix_matches = [t for t in incomplete_tasks if t['text'].lower().startswith(query_lower)]
        if len(prefix_matches) == 1:
            return prefix_matches[0]

        # 3. Contains match - find all tasks that contain query
        contains_matches = [t for t in incomplete_tasks if query_lower in t['text'].lower()]
        if len(contains_matches) == 1:
            return contains_matches[0]

        return None

    def mark_done(self, task: str, target_date: Optional[date] = None) -> Tuple[bool, Optional[str]]:
        """Mark task as completed.

        Supports:
        - Numeric index: "1", "2", "3" marks 1st, 2nd, 3rd incomplete task
        - Exact match: Full task text
        - Prefix match: Unique prefix of task text
        - Contains match: Unique substring match

        Args:
            task: Task description, index, or partial match
            target_date: Target date (today if None)

        Returns:
            Tuple of (success, matched_task_text)
            - (True, "task text") if marked successfully
            - (False, None) if not found
            - (False, "ambiguous") if multiple matches
        """
        if target_date is None:
            target_date = date.today()

        plan_path = self.get_plan_path(target_date)

        if not plan_path.exists():
            return (False, None)

        # Get all tasks
        all_tasks = self.get_tasks(target_date)
        incomplete_tasks = [t for t in all_tasks if not t['completed']]

        if not incomplete_tasks:
            return (False, None)

        # Check if task is a numeric index
        target_task = None
        if task.isdigit():
            index = int(task)
            if 1 <= index <= len(incomplete_tasks):
                target_task = incomplete_tasks[index - 1]
        else:
            # Try to find matching task
            target_task = self._find_matching_task(task, all_tasks)

        if target_task is None:
            # Check if there are multiple matches (ambiguous)
            query_lower = task.lower()
            matches = [t for t in incomplete_tasks if query_lower in t['text'].lower()]
            if len(matches) > 1:
                return (False, "ambiguous")
            return (False, None)

        # Mark the task as done
        content = plan_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        completion_time = datetime.now()
        timestamp = completion_time.strftime("%H:%M")
        line_num = target_task['line_num']
        matched_text = target_task['text']

        # Mark as completed with timestamp
        lines[line_num] = lines[line_num].replace('- [ ]', '- [x]') + f" [{timestamp}]"

        # Update progress
        updated_content = '\n'.join(lines)
        updated_content = self._update_progress(updated_content)

        plan_path.write_text(updated_content, encoding='utf-8')

        # Record completion in timeline (Plan-Timeline integration)
        try:
            from .integration import PlanTimelineIntegration
            integration = PlanTimelineIntegration(self.base_path)
            integration.record_task_completion(
                task=matched_text,
                plan_type='daily',
                plan_date=target_date,
                completion_time=completion_time
            )
        except Exception:
            # Silent failure - integration is optional
            pass

        return (True, matched_text)

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

        # Count tasks (only those with actual text, exclude empty checkboxes)
        total = len(re.findall(r'- \[[ x]\] \S', content))
        completed = len(re.findall(r'- \[x\] \S', content))

        return (completed, total)

    def _update_progress(self, content: str) -> str:
        """Update progress section in content.

        Args:
            content: Plan content

        Returns:
            Updated content
        """
        # Count tasks (only those with actual text, exclude empty checkboxes)
        total = len(re.findall(r'- \[[ x]\] \S', content))
        completed = len(re.findall(r'- \[x\] \S', content))

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

    def get_incomplete_tasks(self, target_date: Optional[date] = None) -> List[str]:
        """Extract incomplete tasks (- [ ] ...) from plan.

        Args:
            target_date: Target date (yesterday if None)

        Returns:
            List of incomplete task texts
        """
        if target_date is None:
            target_date = date.today() - timedelta(days=1)

        plan_path = self.get_plan_path(target_date)

        if not plan_path.exists():
            return []

        content = plan_path.read_text(encoding='utf-8')

        # Extract incomplete tasks
        tasks = []
        for match in re.finditer(r'^- \[ \] (.+)$', content, re.MULTILINE):
            task_text = match.group(1).strip()
            # Remove any timestamp suffix if present
            task_text = re.sub(r'\s*\[\d{1,2}:\d{2}\]$', '', task_text)
            tasks.append(task_text)

        return tasks

    def carryover_tasks(
        self,
        tasks: List[str],
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> int:
        """Move selected tasks from one plan to another.

        Args:
            tasks: List of task texts to carry over
            from_date: Source date (yesterday if None)
            to_date: Target date (today if None)

        Returns:
            Number of tasks carried over
        """
        if from_date is None:
            from_date = date.today() - timedelta(days=1)
        if to_date is None:
            to_date = date.today()

        if not tasks:
            return 0

        # Add tasks to target plan
        carried = 0
        for task in tasks:
            self.add_task(task, to_date)
            carried += 1

        return carried
