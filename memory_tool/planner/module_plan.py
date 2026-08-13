"""Module Plan management for memory_tool.

Provides module-level sprint, backlog, and technical debt management.
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from memory_tool.utils.paths import get_base_path


class ModulePlan:
    """Manage module plans."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize module plan manager.

        Args:
            base_path: Base path for .memory/ (auto-detected if None)
        """
        if base_path is None:
            base_path = self._find_memory_root()

        self.base_path = base_path
        self.modules_path = base_path / "modules"

    def _find_memory_root(self) -> Path:
        """Find the knowledge base folder.

        Delegates to the central resolver so the configurable base folder
        name (and a base of ".") is honoured.
        """
        return get_base_path()

    def get_plan_path(self, module_name: str) -> Path:
        """Get path for module plan file.

        Args:
            module_name: Module name (supports hierarchical paths)

        Returns:
            Path to plan file
        """
        module_dir = self.modules_path / module_name
        return module_dir / "PLAN.md"

    def create_plan(self, module_name: str) -> Path:
        """Create module plan.

        Args:
            module_name: Module name

        Returns:
            Path to created plan
        """
        plan_path = self.get_plan_path(module_name)

        # Check if already exists
        if plan_path.exists():
            return plan_path

        # Ensure module directory exists
        plan_path.parent.mkdir(parents=True, exist_ok=True)

        # Create plan
        content = f"""# Module Plan: {module_name}

## Current Sprint

- [ ]

## Backlog

- [ ]

## Technical Debt

- [ ]

---

**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        plan_path.write_text(content, encoding='utf-8')
        return plan_path

    def show_plan(self, module_name: str) -> str:
        """Show module plan content.

        Args:
            module_name: Module name

        Returns:
            Plan content
        """
        plan_path = self.get_plan_path(module_name)

        if not plan_path.exists():
            return f"No plan found for module: {module_name}\nCreate one with: mplan module {module_name}"

        return plan_path.read_text(encoding='utf-8')

    def add_task(self, module_name: str, section: str, task: str) -> bool:
        """Add task to module plan section.

        Args:
            module_name: Module name
            section: Section name (sprint, backlog, debt)
            task: Task description

        Returns:
            True if added
        """
        plan_path = self.get_plan_path(module_name)

        if not plan_path.exists():
            # Auto-create plan
            self.create_plan(module_name)

        content = plan_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Map section names
        section_map = {
            'sprint': '## Current Sprint',
            'backlog': '## Backlog',
            'debt': '## Technical Debt',
        }

        section_header = section_map.get(section.lower())
        if not section_header:
            return False

        # Find section and add task
        insert_index = None
        for i, line in enumerate(lines):
            if line.startswith(section_header):
                insert_index = i + 2
                break

        if insert_index is None:
            return False

        lines.insert(insert_index, f"- [ ] {task}")

        # Update last updated timestamp
        updated_content = '\n'.join(lines)
        updated_content = self._update_timestamp(updated_content)

        plan_path.write_text(updated_content, encoding='utf-8')
        return True

    def mark_done(self, module_name: str, section: str, task: str) -> bool:
        """Mark task as completed.

        Args:
            module_name: Module name
            section: Section name (sprint, backlog, debt)
            task: Task description (partial match)

        Returns:
            True if marked, False if not found
        """
        plan_path = self.get_plan_path(module_name)

        if not plan_path.exists():
            return False

        content = plan_path.read_text(encoding='utf-8')
        lines = content.split('\n')

        # Map section names
        section_map = {
            'sprint': '## Current Sprint',
            'backlog': '## Backlog',
            'debt': '## Technical Debt',
        }

        section_header = section_map.get(section.lower())
        if not section_header:
            return False

        # Find section
        in_section = False
        marked = False

        for i, line in enumerate(lines):
            if line.startswith('## '):
                in_section = line.startswith(section_header)
                continue

            if in_section and line.strip().startswith('- [ ]') and task.lower() in line.lower():
                lines[i] = line.replace('- [ ]', '- [x]')
                marked = True
                break

        if not marked:
            return False

        # Update last updated timestamp
        updated_content = '\n'.join(lines)
        updated_content = self._update_timestamp(updated_content)

        plan_path.write_text(updated_content, encoding='utf-8')
        return True

    def get_progress(self, module_name: str, section: Optional[str] = None) -> Tuple[int, int]:
        """Get progress statistics.

        Args:
            module_name: Module name
            section: Section name or None for total

        Returns:
            Tuple of (completed, total) tasks
        """
        plan_path = self.get_plan_path(module_name)

        if not plan_path.exists():
            return (0, 0)

        content = plan_path.read_text(encoding='utf-8')

        if section:
            # Get section-specific progress
            section_map = {
                'sprint': '## Current Sprint',
                'backlog': '## Backlog',
                'debt': '## Technical Debt',
            }

            section_header = section_map.get(section.lower())
            if not section_header:
                return (0, 0)

            lines = content.split('\n')
            in_section = False
            section_content = []

            for line in lines:
                if line.startswith('## '):
                    in_section = line.startswith(section_header)
                    continue

                if in_section:
                    if line.startswith('## '):
                        break
                    section_content.append(line)

            section_text = '\n'.join(section_content)
            total = len(re.findall(r'- \[[ x]\]', section_text))
            completed = len(re.findall(r'- \[x\]', section_text))
        else:
            # Total progress
            total = len(re.findall(r'- \[[ x]\]', content))
            completed = len(re.findall(r'- \[x\]', content))

        return (completed, total)

    def _update_timestamp(self, content: str) -> str:
        """Update last updated timestamp.

        Args:
            content: Plan content

        Returns:
            Updated content
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        content = re.sub(
            r'\*\*Last Updated:\*\* .*',
            f'**Last Updated:** {timestamp}',
            content
        )
        return content
