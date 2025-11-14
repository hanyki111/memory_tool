"""Plan management for memory_tool.

Provides task planning, tracking, and progress visualization.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict


class TaskStatus(Enum):
    """Task status enum."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"


@dataclass
class Task:
    """A single task in a plan."""
    title: str
    status: TaskStatus = TaskStatus.PENDING
    description: Optional[str] = None
    subtasks: List['Task'] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)

    def mark_completed(self):
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = datetime.now()

    def mark_in_progress(self):
        """Mark task as in progress."""
        self.status = TaskStatus.IN_PROGRESS

    def mark_blocked(self):
        """Mark task as blocked."""
        self.status = TaskStatus.BLOCKED

    def to_markdown(self, indent: int = 0) -> str:
        """Convert task to markdown format.

        Args:
            indent: Indentation level

        Returns:
            Markdown string
        """
        prefix = "  " * indent
        status_char = {
            TaskStatus.PENDING: " ",
            TaskStatus.IN_PROGRESS: "~",
            TaskStatus.COMPLETED: "x",
            TaskStatus.BLOCKED: "!",
        }[self.status]

        lines = [f"{prefix}- [{status_char}] {self.title}"]

        if self.description:
            lines.append(f"{prefix}  {self.description}")

        if self.tags:
            tags_str = " ".join(f"#{tag}" for tag in self.tags)
            lines.append(f"{prefix}  {tags_str}")

        for subtask in self.subtasks:
            lines.append(subtask.to_markdown(indent + 1))

        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, line: str) -> Optional['Task']:
        """Parse task from markdown line.

        Args:
            line: Markdown line (e.g., "- [x] Task title #tag")

        Returns:
            Task instance or None if not a valid task line
        """
        # Match: - [ ] Task title or - [x] Task title
        match = re.match(r'^(\s*)- \[(.)\] (.+)$', line)
        if not match:
            return None

        indent, status_char, title = match.groups()
        indent_level = len(indent) // 2

        # Parse status
        status_map = {
            ' ': TaskStatus.PENDING,
            '~': TaskStatus.IN_PROGRESS,
            'x': TaskStatus.COMPLETED,
            '!': TaskStatus.BLOCKED,
        }
        status = status_map.get(status_char, TaskStatus.PENDING)

        # Extract tags from title
        tags = re.findall(r'#(\w+)', title)
        title_without_tags = re.sub(r'\s*#\w+', '', title).strip()

        task = cls(
            title=title_without_tags,
            status=status,
            tags=tags
        )

        if status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now()

        return task


@dataclass
class Plan:
    """A plan containing multiple tasks."""
    name: str
    description: str = ""
    tasks: List[Task] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    due_date: Optional[date] = None
    tags: List[str] = field(default_factory=list)

    def add_task(self, task: Task):
        """Add a task to the plan."""
        self.tasks.append(task)

    def get_progress(self) -> Dict[str, int]:
        """Get progress statistics.

        Returns:
            Dict with counts: total, completed, in_progress, pending, blocked
        """
        stats = {
            'total': len(self.tasks),
            'completed': 0,
            'in_progress': 0,
            'pending': 0,
            'blocked': 0,
        }

        for task in self.tasks:
            if task.status == TaskStatus.COMPLETED:
                stats['completed'] += 1
            elif task.status == TaskStatus.IN_PROGRESS:
                stats['in_progress'] += 1
            elif task.status == TaskStatus.BLOCKED:
                stats['blocked'] += 1
            else:
                stats['pending'] += 1

        return stats

    def get_completion_rate(self) -> float:
        """Get completion rate (0.0-1.0)."""
        if not self.tasks:
            return 0.0
        completed = sum(1 for task in self.tasks if task.status == TaskStatus.COMPLETED)
        return completed / len(self.tasks)

    def to_markdown(self) -> str:
        """Convert plan to markdown format.

        Returns:
            Markdown string
        """
        lines = [f"# {self.name}", ""]

        if self.description:
            lines.append(self.description)
            lines.append("")

        # Metadata
        lines.append("## Metadata")
        lines.append(f"- Created: {self.created_at.strftime('%Y-%m-%d %H:%M')}")
        if self.due_date:
            lines.append(f"- Due: {self.due_date.strftime('%Y-%m-%d')}")
        if self.tags:
            tags_str = " ".join(f"#{tag}" for tag in self.tags)
            lines.append(f"- Tags: {tags_str}")
        lines.append("")

        # Progress
        progress = self.get_progress()
        completion_rate = self.get_completion_rate() * 100
        lines.append("## Progress")
        lines.append(f"- Completion: {completion_rate:.1f}%")
        lines.append(f"- Total: {progress['total']}")
        lines.append(f"- Completed: {progress['completed']}")
        lines.append(f"- In Progress: {progress['in_progress']}")
        lines.append(f"- Pending: {progress['pending']}")
        if progress['blocked'] > 0:
            lines.append(f"- Blocked: {progress['blocked']}")
        lines.append("")

        # Tasks
        lines.append("## Tasks")
        lines.append("")
        for task in self.tasks:
            lines.append(task.to_markdown())
        lines.append("")

        return "\n".join(lines)


class PlanManager:
    """Manage plans for memory_tool."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize plan manager.

        Args:
            base_path: Base path for .memory/ (auto-detected if None)
        """
        if base_path is None:
            base_path = self._find_memory_root()

        self.base_path = base_path
        self.plans_path = base_path / "plans"
        self.plans_path.mkdir(parents=True, exist_ok=True)

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

    def create_plan(
        self,
        name: str,
        description: str = "",
        due_date: Optional[date] = None,
        tags: List[str] = None
    ) -> Plan:
        """Create a new plan.

        Args:
            name: Plan name
            description: Plan description
            due_date: Due date
            tags: Tags for plan

        Returns:
            New Plan instance
        """
        plan = Plan(
            name=name,
            description=description,
            due_date=due_date,
            tags=tags or []
        )
        return plan

    def save_plan(self, plan: Plan, filename: Optional[str] = None) -> Path:
        """Save plan to file.

        Args:
            plan: Plan to save
            filename: Filename (auto-generated if None)

        Returns:
            Path to saved file
        """
        if filename is None:
            # Generate filename from plan name
            safe_name = re.sub(r'[^\w\s-]', '', plan.name).strip()
            safe_name = re.sub(r'[-\s]+', '-', safe_name).lower()
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"{timestamp}-{safe_name}.md"

        filepath = self.plans_path / filename

        # Write plan to file
        filepath.write_text(plan.to_markdown(), encoding='utf-8')

        return filepath

    def load_plan(self, filename: str) -> Plan:
        """Load plan from file.

        Args:
            filename: Filename to load

        Returns:
            Loaded Plan instance
        """
        filepath = self.plans_path / filename
        content = filepath.read_text(encoding='utf-8')

        # Parse markdown
        return self._parse_plan_markdown(content)

    def _parse_plan_markdown(self, content: str) -> Plan:
        """Parse plan from markdown content.

        Args:
            content: Markdown content

        Returns:
            Plan instance
        """
        lines = content.split('\n')

        # Extract title (first # heading)
        name = "Untitled Plan"
        for line in lines:
            if line.startswith('# '):
                name = line[2:].strip()
                break

        # Create plan
        plan = Plan(name=name)

        # Parse tasks
        in_tasks_section = False
        for line in lines:
            if line.startswith('## Tasks'):
                in_tasks_section = True
                continue

            if in_tasks_section and line.startswith('- ['):
                task = Task.from_markdown(line)
                if task:
                    plan.add_task(task)

        return plan

    def list_plans(self) -> List[Dict]:
        """List all plans.

        Returns:
            List of plan info dicts
        """
        plans = []
        for filepath in self.plans_path.glob("*.md"):
            try:
                plan = self.load_plan(filepath.name)
                plans.append({
                    'filename': filepath.name,
                    'name': plan.name,
                    'tasks': len(plan.tasks),
                    'completion': plan.get_completion_rate() * 100,
                    'modified': datetime.fromtimestamp(filepath.stat().st_mtime)
                })
            except Exception:
                continue

        return sorted(plans, key=lambda x: x['modified'], reverse=True)

    def delete_plan(self, filename: str):
        """Delete a plan file.

        Args:
            filename: Filename to delete
        """
        filepath = self.plans_path / filename
        if filepath.exists():
            filepath.unlink()
