"""Daily Plan management for memory_tool.

Provides daily task planning with weekly plan integration.
"""

import os
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Optional, List, Tuple
from memory_tool.utils.paths import get_base_path


#: A task line: "- [ ] text" or "- [x] text [14:30]"
_TASK_LINE = re.compile(r'^\s*- \[([ xX])\](.*)$')
#: The completion time ``mark_done`` adds at the end of a task
_COMPLETION_TIME = re.compile(r'\s*\[(\d{1,2}:\d{2})\]\s*$')


def _split_completion_time(text: str) -> Tuple[str, Optional[str]]:
    """A completed task's text and the time it was completed (or None)."""
    match = _COMPLETION_TIME.search(text)
    if not match:
        return text.strip(), None
    hour, minute = match.group(1).split(":")
    return text[:match.start()].strip(), f"{int(hour):02d}:{minute}"


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
        """Find the knowledge base folder.

        Delegates to the central resolver so the configurable base folder
        name (and a base of ".") is honoured.
        """
        return get_base_path()

    def get_plan_path(self, target_date: Optional[date] = None) -> Path:
        """Get path for daily plan file.

        Args:
            target_date: Target date (today if None)

        Returns:
            Path to plan file
        """
        if target_date is None:
            target_date = date.today()

        # Only the path: reading a plan must not create its folder.
        return self.plans_path / target_date.strftime("%Y-%m") / f"{target_date:%d}.md"

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
**Timeline:** [View the day's timeline]({timeline})

---

**Created:** {timestamp}
"""

        # Get ISO week number
        iso_calendar = target_date.isocalendar()
        week = iso_calendar[1]

        # Substitute variables. {timeline} is a link to the day's timeline file
        # as it is named in this knowledge base (21.md or 2026-08-21.md).
        content = template.format(
            date=target_date.strftime("%Y-%m-%d"),
            year=target_date.year,
            month=target_date.month,
            day=target_date.day,
            week=week,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            timeline=self._timeline_link(plan_path, target_date),
        )

        # Write to file
        plan_path.parent.mkdir(parents=True, exist_ok=True)
        plan_path.write_text(content, encoding='utf-8')

        return plan_path

    def _timeline_link(self, plan_path: Path, target_date: date) -> str:
        """A relative link from a plan to its day's timeline file."""
        from .integration import PlanTimelineIntegration

        timeline_file = PlanTimelineIntegration(self.base_path).get_timeline_path(target_date)
        return Path(os.path.relpath(timeline_file, plan_path.parent)).as_posix()

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

    def _get_recurring_content(self) -> Optional[str]:
        """Read recurring.md if it exists.

        Returns:
            File content or None if file doesn't exist
        """
        recurring_path = self.base_path / "plans" / "recurring.md"
        if recurring_path.exists():
            content = recurring_path.read_text(encoding='utf-8').strip()
            if content:
                return content
        return None

    def show_plan(self, target_date: Optional[date] = None, auto_update: bool = True) -> str:
        """Show daily plan content.

        Showing changes nothing on disk. The progress line is shown as the
        tasks stand, even when the file was edited by hand since; the file's
        own line is brought up to date the next time a task changes.

        Args:
            target_date: Target date (today if None)
            auto_update: If True, show the progress as the tasks stand

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

        content = plan_path.read_text(encoding='utf-8')
        if auto_update:
            content = self._update_progress(content)
        result = self._format_for_display(content)

        # Append recurring items if available
        recurring = self._get_recurring_content()
        if recurring:
            result = result.rstrip() + "\n\n---\n\n" + recurring

        return result

    def add_task(self, task: str, target_date: Optional[date] = None) -> bool:
        """Add task to daily plan.

        Args:
            task: Task description
            target_date: Target date (today if None)

        Returns:
            True if added, False if plan doesn't exist
        """
        # A task is one line.
        task = " ".join(task.split())

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

        Tasks are numbered as ``done`` and ``undo`` take them: an incomplete
        task by its place among the incomplete ones, a completed task by its
        place among the completed ones. A checkbox with no text is not a task.

        Args:
            target_date: Target date (today if None)
            incomplete_only: Only return incomplete tasks

        Returns:
            List of task dicts with 'index', 'text', 'completed', 'time' (when
            it was completed, "HH:MM", or None) and 'line_num' (0-based)
        """
        if target_date is None:
            target_date = date.today()

        plan_path = self.get_plan_path(target_date)

        if not plan_path.exists():
            return []

        lines = plan_path.read_text(encoding='utf-8').split('\n')
        tasks = []
        open_count = 0
        done_count = 0

        for line_num, line in enumerate(lines):
            match = _TASK_LINE.match(line)
            if not match:
                continue
            completed = match.group(1).lower() == "x"
            text, time = _split_completion_time(match.group(2)) if completed else (match.group(2).strip(), None)
            if not text:
                continue
            if completed:
                done_count += 1
                if incomplete_only:
                    continue
                index = done_count
            else:
                open_count += 1
                index = open_count
            tasks.append({
                'index': index,
                'text': text,
                'completed': completed,
                'time': time,
                'line_num': line_num,
            })

        return tasks

    def _find_matching_task(self, query: str, tasks: List[dict]) -> Optional[dict]:
        """Find a task matching the query (prefix or contains).

        Matching priority:
        1. Exact match (case-insensitive)
        2. Unique prefix match (if query is a unique prefix)
        3. Contains match (if only one task contains the query)

        Args:
            query: Search query
            tasks: The tasks to choose from

        Returns:
            Matching task dict, or None if not found or ambiguous
        """
        query_lower = query.lower()

        # 1. Exact match
        for task in tasks:
            if task['text'].lower() == query_lower:
                return task

        # 2. Prefix match - find all tasks that start with query
        prefix_matches = [t for t in tasks if t['text'].lower().startswith(query_lower)]
        if len(prefix_matches) == 1:
            return prefix_matches[0]

        # 3. Contains match - find all tasks that contain query
        contains_matches = [t for t in tasks if query_lower in t['text'].lower()]
        if len(contains_matches) == 1:
            return contains_matches[0]

        return None

    def find_task(
        self,
        task: str,
        completed: bool,
        target_date: Optional[date] = None,
        line: Optional[int] = None,
    ) -> Tuple[Optional[dict], Optional[str]]:
        """Find one incomplete (or completed) task.

        Args:
            task: Its number among those tasks, its text, or part of its text.
                With ``line``, its exact text.
            completed: Look among the completed tasks instead of the incomplete
            target_date: Target date (today if None)
            line: The task's line (1-based) as a program saw it. The task is
                found only if that line still holds it, so a file changed since
                is never changed in the wrong place.

        Returns:
            (task, None) when found, (None, "ambiguous") when several match,
            (None, None) when none does
        """
        candidates = [t for t in self.get_tasks(target_date) if t['completed'] == completed]

        if line is not None:
            for candidate in candidates:
                if candidate['line_num'] == line - 1 and candidate['text'] == task.strip():
                    return candidate, None
            return None, None

        if task.isdigit():
            index = int(task)
            for candidate in candidates:
                if candidate['index'] == index:
                    return candidate, None
            return None, None

        found = self._find_matching_task(task, candidates)
        if found is not None:
            return found, None
        query_lower = task.lower()
        if len([t for t in candidates if query_lower in t['text'].lower()]) > 1:
            return None, "ambiguous"
        return None, None

    def mark_done(
        self,
        task: str,
        target_date: Optional[date] = None,
        line: Optional[int] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Mark task as completed.

        Supports:
        - Numeric index: "1", "2", "3" marks 1st, 2nd, 3rd incomplete task
        - Exact match: Full task text
        - Prefix match: Unique prefix of task text
        - Contains match: Unique substring match
        - ``line``: the exact text on that line (see :meth:`find_task`)

        The completion is recorded in the timeline as "✓ task (Daily Plan)".

        Args:
            task: Task description, index, or partial match
            target_date: Target date (today if None)
            line: The task's line (1-based), from ``get_tasks`` or --json

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

        target_task, problem = self.find_task(task, completed=False, target_date=target_date, line=line)
        if target_task is None:
            return (False, problem)

        # Mark the task as done
        content = plan_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        completion_time = datetime.now()
        timestamp = completion_time.strftime("%H:%M")
        line_num = target_task['line_num']
        matched_text = target_task['text']

        # Mark as completed with timestamp
        lines[line_num] = lines[line_num].replace('- [ ]', '- [x]', 1).rstrip() + f" [{timestamp}]"

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

    def mark_undone(
        self,
        task: str,
        target_date: Optional[date] = None,
        line: Optional[int] = None,
    ) -> Tuple[bool, Optional[str], bool]:
        """Mark a completed task as not done, and delete its timeline entry.

        The task is found as :meth:`mark_done` finds one, among the completed
        tasks. Its completion time is removed, and the "✓ task (Daily Plan)"
        entry ``mark_done`` recorded at that time is deleted. If that entry is
        no longer there (edited or deleted by hand), the task is still marked
        as not done.

        Returns:
            (success, matched task text or "ambiguous", whether the timeline
            entry was deleted)
        """
        if target_date is None:
            target_date = date.today()

        plan_path = self.get_plan_path(target_date)

        if not plan_path.exists():
            return (False, None, False)

        target_task, problem = self.find_task(task, completed=True, target_date=target_date, line=line)
        if target_task is None:
            return (False, problem, False)

        lines = plan_path.read_text(encoding='utf-8').split('\n')
        line_num = target_task['line_num']
        reopened = re.sub(r'\[[xX]\]', '[ ]', lines[line_num], count=1)
        lines[line_num] = re.sub(_COMPLETION_TIME, "", reopened).rstrip()

        plan_path.write_text(self._update_progress('\n'.join(lines)), encoding='utf-8')

        removed = False
        if target_task['time']:
            try:
                from .integration import PlanTimelineIntegration
                removed = PlanTimelineIntegration(self.base_path).remove_task_completion(
                    task=target_task['text'],
                    plan_type='daily',
                    plan_date=target_date,
                    completion_time=target_task['time'],
                )
            except Exception:
                removed = False

        return (True, target_task['text'], removed)

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

        return [t['text'] for t in self.get_tasks(target_date, incomplete_only=True)]

    def carryover_tasks(
        self,
        tasks: List[str],
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> int:
        """Copy selected tasks from one plan to another.

        A task the target plan already has (done or not) is not added again,
        so carrying over twice does not double it. The tasks keep their order.

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

        present = {t['text'] for t in self.get_tasks(to_date)}
        new = [task for task in dict.fromkeys(tasks) if task not in present]

        # add_task puts each task on top, so add them last first.
        for task in reversed(new):
            self.add_task(task, to_date)

        return len(new)
