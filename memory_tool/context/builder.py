"""Context builder for Claude Code integration."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

from memory_tool.utils.config import Config


class ContextError(Exception):
    """Base exception for context operations."""
    pass


class ContextBuilder:
    """Builder for Claude Code context."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize context builder.

        Args:
            base_path: Base path for project. Defaults to current directory.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"
        self.claude_path = self.base_path / ".claude"
        self.config = Config(self.memory_path)

    def is_initialized(self) -> bool:
        """Check if .memory/ exists.

        Returns:
            True if .memory/ exists
        """
        return self.memory_path.exists()

    def get_recent_timeline_paths(self, days: int = 3) -> List[Path]:
        """Get paths to recent timeline files.

        Args:
            days: Number of recent days to include

        Returns:
            List of timeline file paths (newest first)
        """
        timeline_path = self.memory_path / "timeline"
        if not timeline_path.exists():
            return []

        paths = []
        today = datetime.now().date()

        for i in range(days):
            date = today - timedelta(days=i)
            year_month = date.strftime("%Y-%m")
            day = date.strftime("%d")
            file_path = timeline_path / year_month / f"{day}.md"

            if file_path.exists():
                paths.append(file_path)

        return paths

    def get_module_statuses(self) -> Dict[str, Path]:
        """Get current.md paths for all modules (recursive).

        Returns:
            Dictionary mapping module names to current.md paths
        """
        modules_path = self.memory_path / "modules"
        if not modules_path.exists():
            return {}

        statuses = {}

        # Recursively find all current.md files
        for current_file in modules_path.rglob("current.md"):
            # Get module name as relative path from modules/
            module_rel_path = current_file.parent.relative_to(modules_path)
            module_name = str(module_rel_path).replace("\\", "/")
            statuses[module_name] = current_file

        return statuses

    def get_plan_summary(self) -> Dict[str, any]:
        """Get current plan information.

        Returns:
            Dictionary with plan summary:
            {
                "daily": {"path": Path, "progress": (completed, total), "tasks": [...]}
                "weekly": {"path": Path, "progress": (completed, total), "goals": [...]}
                "monthly": {"path": Path, "progress": (completed, total), "goals": [...]}
            }
        """
        from datetime import date
        import re

        plans_path = self.memory_path / "plans"
        summary = {}

        # Daily Plan
        today = date.today()
        daily_path = plans_path / "daily" / today.strftime("%Y-%m") / f"{today.strftime('%d')}.md"
        if daily_path.exists():
            try:
                content = daily_path.read_text(encoding='utf-8')
                # Count tasks
                total = len(re.findall(r'- \[[ x]\]', content))
                completed = len(re.findall(r'- \[x\]', content))
                # Get pending tasks (limit to 3)
                pending_tasks = []
                for line in content.splitlines():
                    if line.strip().startswith('- [ ]'):
                        task = line.strip()[6:].strip()
                        if task:
                            pending_tasks.append(task)
                        if len(pending_tasks) >= 3:
                            break

                summary["daily"] = {
                    "path": daily_path,
                    "progress": (completed, total),
                    "tasks": pending_tasks
                }
            except Exception:
                pass

        # Weekly Plan
        iso_cal = today.isocalendar()
        week_num = iso_cal[1]
        weekly_path = plans_path / "weekly" / str(today.year) / f"W{week_num:02d}.md"
        if weekly_path.exists():
            try:
                content = weekly_path.read_text(encoding='utf-8')
                total = len(re.findall(r'- \[[ x]\]', content))
                completed = len(re.findall(r'- \[x\]', content))
                # Get pending goals (limit to 3)
                pending_goals = []
                for line in content.splitlines():
                    if line.strip().startswith('- [ ]'):
                        goal = line.strip()[6:].strip()
                        if goal:
                            pending_goals.append(goal)
                        if len(pending_goals) >= 3:
                            break

                summary["weekly"] = {
                    "path": weekly_path,
                    "progress": (completed, total),
                    "goals": pending_goals
                }
            except Exception:
                pass

        # Monthly Plan
        monthly_path = plans_path / "monthly" / str(today.year) / f"{today.month:02d}.md"
        if monthly_path.exists():
            try:
                content = monthly_path.read_text(encoding='utf-8')
                total = len(re.findall(r'- \[[ x]\]', content))
                completed = len(re.findall(r'- \[x\]', content))
                # Get pending goals (limit to 2)
                pending_goals = []
                for line in content.splitlines():
                    if line.strip().startswith('- [ ]'):
                        goal = line.strip()[6:].strip()
                        if goal:
                            pending_goals.append(goal)
                        if len(pending_goals) >= 2:
                            break

                summary["monthly"] = {
                    "path": monthly_path,
                    "progress": (completed, total),
                    "goals": pending_goals
                }
            except Exception:
                pass

        return summary

    def load_config(self) -> dict:
        """Load config.yaml settings.

        Returns:
            Configuration dictionary
        """
        return self.config.load(strict=False)

    def get_document_health(self) -> List[Dict[str, any]]:
        """Get document health check for modules with large files.

        Returns:
            List of dictionaries with module, file, lines, and suggestion
        """
        health_issues = []
        modules_path = self.memory_path / "modules"

        if not modules_path.exists():
            return health_issues

        # Check all modules for large decisions.md or current.md files
        for module_path in modules_path.rglob("*"):
            if not module_path.is_dir():
                continue

            # Get relative module name
            try:
                module_name = str(module_path.relative_to(modules_path)).replace("\\", "/")
            except ValueError:
                continue

            # Check decisions.md
            decisions_file = module_path / "decisions.md"
            if decisions_file.exists():
                try:
                    content = decisions_file.read_text(encoding="utf-8")
                    line_count = len(content.split("\n"))

                    if line_count > 300:
                        if line_count > 600:
                            suggestion = "⚠️ Very large, should archive soon"
                        else:
                            suggestion = "Consider archiving"
                        health_issues.append({
                            "module": module_name,
                            "file": "decisions.md",
                            "lines": line_count,
                            "suggestion": suggestion,
                        })
                except Exception:
                    pass  # Skip files that can't be read

            # Check current.md
            current_file = module_path / "current.md"
            if current_file.exists():
                try:
                    content = current_file.read_text(encoding="utf-8")
                    line_count = len(content.split("\n"))

                    if line_count > 200:
                        if line_count > 400:
                            suggestion = "⚠️ Very large, consider archiving"
                        else:
                            suggestion = "Consider reviewing"
                        health_issues.append({
                            "module": module_name,
                            "file": "current.md",
                            "lines": line_count,
                            "suggestion": suggestion,
                        })
                except Exception:
                    pass  # Skip files that can't be read

        return health_issues

    def build_context_content(self) -> str:
        """Build context markdown content.

        Returns:
            Markdown content for memory-context.md
        """
        lines = []

        # Header
        lines.append("# Memory Context")
        lines.append("")
        lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Recent Timeline
        config = self.load_config()
        recent_days = config.get("context", {}).get("recent_days", 3)
        timeline_paths = self.get_recent_timeline_paths(recent_days)

        if timeline_paths:
            lines.append("## Recent Timeline")
            lines.append("")
            for path in timeline_paths:
                rel_path = path.relative_to(self.base_path)
                # Extract date from path
                date_str = path.parent.name + "-" + path.stem
                lines.append(f"- **{date_str}**: `./{rel_path}`")
            lines.append("")
        else:
            lines.append("## Recent Timeline")
            lines.append("")
            lines.append("*No recent timeline entries found.*")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Current Plans
        plan_summary = self.get_plan_summary()

        if plan_summary:
            lines.append("## Current Plans")
            lines.append("")

            # Daily Plan
            if "daily" in plan_summary:
                daily = plan_summary["daily"]
                completed, total = daily["progress"]
                percentage = (completed / total * 100) if total > 0 else 0
                lines.append(f"### Today's Plan")
                lines.append(f"- **Progress:** {completed}/{total} ({percentage:.0f}%)")
                if daily["tasks"]:
                    lines.append("- **Pending Tasks:**")
                    for task in daily["tasks"]:
                        lines.append(f"  - {task}")
                lines.append("")

            # Weekly Plan
            if "weekly" in plan_summary:
                weekly = plan_summary["weekly"]
                completed, total = weekly["progress"]
                percentage = (completed / total * 100) if total > 0 else 0
                lines.append(f"### This Week's Plan")
                lines.append(f"- **Progress:** {completed}/{total} ({percentage:.0f}%)")
                if weekly["goals"]:
                    lines.append("- **Pending Goals:**")
                    for goal in weekly["goals"]:
                        lines.append(f"  - {goal}")
                lines.append("")

            # Monthly Plan
            if "monthly" in plan_summary:
                monthly = plan_summary["monthly"]
                completed, total = monthly["progress"]
                percentage = (completed / total * 100) if total > 0 else 0
                lines.append(f"### This Month's Plan")
                lines.append(f"- **Progress:** {completed}/{total} ({percentage:.0f}%)")
                if monthly["goals"]:
                    lines.append("- **Pending Goals:**")
                    for goal in monthly["goals"]:
                        lines.append(f"  - {goal}")
                lines.append("")
        else:
            lines.append("## Current Plans")
            lines.append("")
            lines.append("*No active plans found.*")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Module Status
        module_statuses = self.get_module_statuses()

        if module_statuses:
            lines.append("## Module Status")
            lines.append("")
            for module_name, status_path in sorted(module_statuses.items()):
                rel_path = status_path.relative_to(self.base_path)
                lines.append(f"- **{module_name}**: `./{rel_path}`")
            lines.append("")
        else:
            lines.append("## Module Status")
            lines.append("")
            lines.append("*No modules found.*")
            lines.append("")

        lines.append("---")
        lines.append("")

        # Document Health (Archive Suggestions)
        doc_health = self.get_document_health()

        if doc_health:
            # Group by severity
            critical = [item for item in doc_health if "⚠️ Very large" in item["suggestion"]]
            warning = [item for item in doc_health if item not in critical]

            lines.append("## Document Health")
            lines.append("")

            if critical:
                lines.append("### 🔴 CRITICAL (>600/400 lines)")
                lines.append("")
                for item in critical:
                    module_name = item["module"]
                    file_name = item["file"]
                    line_count = item["lines"]
                    lines.append(f"- **{module_name}/{file_name}**: {line_count} lines - ⚠️ Very large, should archive soon")
                    lines.append(f"  - Quick action: `marchive {file_name.replace('.md', '')} --module {module_name} --interactive`")
                lines.append("")

            if warning:
                lines.append("### 🟡 WARNING (300-600/200-400 lines)")
                lines.append("")
                for item in warning:
                    module_name = item["module"]
                    file_name = item["file"]
                    line_count = item["lines"]
                    suggestion = item["suggestion"]
                    lines.append(f"- **{module_name}/{file_name}**: {line_count} lines - {suggestion}")
                lines.append("")

            lines.append("### ✅ Quick Actions")
            lines.append("")
            lines.append("```bash")
            lines.append("# 1. View suggestions for all modules")
            lines.append("marchive decisions --suggest")
            lines.append("")
            lines.append("# 2. Interactive archive (select which decisions to archive)")
            lines.append("marchive decisions --module <module-name> --interactive")
            lines.append("")
            lines.append("# 3. LLM-powered analysis (analyze and categorize)")
            lines.append("msummary --module <module-name> --decisions")
            lines.append("")
            lines.append("# 4. Check health anytime")
            lines.append("mcontext")
            lines.append("```")
            lines.append("")
            lines.append("---")
            lines.append("")

        # Footer
        lines.append("## Usage")
        lines.append("")
        lines.append("This context file is automatically generated by `mcontext` command.")
        lines.append("Use it to quickly understand the current state of the project.")
        lines.append("")
        lines.append("```bash")
        lines.append("# Update this file")
        lines.append("python -m memory_tool context")
        lines.append("```")
        lines.append("")

        return "\n".join(lines)

    def write_context(
        self,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Write context to file.

        Args:
            output_path: Output file path. Defaults to .claude/memory-context.md

        Returns:
            Path to written file

        Raises:
            ContextError: If writing fails
        """
        if not self.is_initialized():
            raise ContextError(
                f".memory/ not found at {self.memory_path}. "
                f"Run 'minit' to initialize."
            )

        # Default output path
        if output_path is None:
            output_path = self.claude_path / "memory-context.md"

        # Ensure .claude/ directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build content
        content = self.build_context_content()

        # Write file
        try:
            output_path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise ContextError(f"Failed to write context: {e}")

        return output_path
