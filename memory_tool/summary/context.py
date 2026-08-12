"""Context gathering for enhanced summarization."""

from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Literal
import re


class ContextGatherer:
    """Gather relevant context for summarization."""

    def __init__(self, memory_root: Optional[Path] = None):
        """
        Initialize context gatherer.

        Args:
            memory_root: Path to .memory/ directory. Defaults to .memory/ in cwd.
        """
        if memory_root is None:
            memory_root = Path.cwd() / ".memory"
        self.memory_root = Path(memory_root)

    def gather_for_timeline(
        self,
        scope: Literal["today", "week", "range"],
        start_date: date,
        end_date: date,
    ) -> Dict[str, any]:
        """
        Gather context for timeline summary.

        Args:
            scope: Summary scope
            start_date: Start date of summary
            end_date: End date of summary

        Returns:
            Dictionary with context:
            {
                "project_context": str,  # from memory-context.md
                "recent_decisions": list[str],
                "module_state": str,
                "categories": list[str],
            }
        """
        context = {}

        # Project context (for week/range scopes)
        if scope in ("week", "range"):
            context["project_context"] = self._get_project_context()

        # Recent decisions (from date range)
        context["recent_decisions"] = self._get_recent_decisions(start_date, end_date)

        # Module state (current.md - for week/range)
        if scope in ("week", "range"):
            context["module_state"] = self._get_module_state()

        # Custom categories from config
        context["categories"] = self._get_custom_categories()

        return context

    def gather_for_module(self, module_name: str) -> Dict[str, any]:
        """
        Gather context for module summary.

        Args:
            module_name: Name of module

        Returns:
            Dictionary with context:
            {
                "project_context": str,
                "related_modules": list[str],
                "recent_decisions": list[str],
            }
        """
        context = {}

        # Project context
        context["project_context"] = self._get_project_context()

        # Related modules
        modules_dir = self.memory_root / "modules"
        if modules_dir.exists():
            context["related_modules"] = [
                d.name
                for d in modules_dir.iterdir()
                if d.is_dir() and d.name != module_name
            ]
        else:
            context["related_modules"] = []

        # Recent decisions (last 30 days)
        today = date.today()
        thirty_days_ago = today - timedelta(days=30)
        context["recent_decisions"] = self._get_recent_decisions(
            thirty_days_ago, today
        )

        return context

    def _get_project_context(self) -> Optional[str]:
        """
        Get project context from .claude/memory-context.md.

        Returns:
            Context string or None if not found
        """
        context_path = self.memory_root.parent / ".claude" / "memory-context.md"

        if not context_path.exists():
            return None

        try:
            content = context_path.read_text(encoding="utf-8")

            # Truncate if too long (keep first 2000 chars)
            if len(content) > 2000:
                content = content[:2000] + "\n\n[... truncated for brevity ...]"

            return content

        except Exception:
            return None

    def _get_recent_decisions(
        self,
        start_date: date,
        end_date: date,
    ) -> List[str]:
        """
        Get decisions made in date range.

        Looks for decisions.md and extracts entries with dates in range.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of decision strings
        """
        decisions = []

        # Find decisions.md files in modules
        modules_dir = self.memory_root / "modules"
        if not modules_dir.exists():
            return decisions

        for module_dir in modules_dir.iterdir():
            if not module_dir.is_dir():
                continue

            decisions_file = module_dir / "decisions.md"
            if not decisions_file.exists():
                continue

            try:
                content = decisions_file.read_text(encoding="utf-8")

                # Extract decisions with dates in range
                # Pattern: ### YYYY-MM-DD: Title
                pattern = r"###\s+(\d{4}-\d{2}-\d{2}):\s+(.+?)(?=###|\Z)"
                matches = re.finditer(pattern, content, re.DOTALL)

                for match in matches:
                    decision_date_str = match.group(1)
                    decision_content = match.group(2).strip()

                    try:
                        decision_date = datetime.strptime(
                            decision_date_str, "%Y-%m-%d"
                        ).date()

                        if start_date <= decision_date <= end_date:
                            # Truncate long decisions
                            if len(decision_content) > 300:
                                decision_content = (
                                    decision_content[:300] + "... [truncated]"
                                )

                            decisions.append(
                                f"**{decision_date_str}**: {decision_content[:200]}"
                            )

                    except ValueError:
                        continue

            except Exception:
                continue

        # Limit to most recent 5 decisions
        return decisions[-5:] if len(decisions) > 5 else decisions

    def _get_module_state(self) -> Optional[str]:
        """
        Get current module state from current.md.

        Returns:
            Current state string or None
        """
        # Look for single-file modules or legacy current.md
        modules_dir = self.memory_root / "modules"
        if not modules_dir.exists():
            return None

        for item in modules_dir.rglob("*.md"):
            if "archive" in item.parts or item.name.startswith("_") or item.name.isupper():
                continue

            try:
                content = item.read_text(encoding="utf-8")
                status_pattern = r"##\s+Current\s+Status(.+?)(?=##|\Z)"
                match = re.search(status_pattern, content, re.DOTALL | re.IGNORECASE)

                if match:
                    status = match.group(1).strip()
                    if len(status) > 500:
                        status = status[:500] + "... [truncated]"
                    return status
            except Exception:
                continue

        return None

    def _get_custom_categories(self) -> List[str]:
        """
        Get custom categories from config.

        Returns:
            List of category names
        """
        try:
            from ..utils.config import Config
            from .categories import get_default_categories

            config = Config()
            categories = config.get("llm.custom_categories", [])

            # Return default categories if none configured
            if not categories:
                return get_default_categories()

            return categories

        except Exception:
            # Return default categories on error
            from .categories import get_default_categories
            return get_default_categories()

    def get_token_estimate(self, context: Dict[str, any]) -> int:
        """
        Estimate token count for context.

        Rough estimate: 1 token ≈ 4 characters

        Args:
            context: Context dictionary

        Returns:
            Estimated token count
        """
        total_chars = 0

        for key, value in context.items():
            if isinstance(value, str) and value:
                total_chars += len(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        total_chars += len(item)

        return total_chars // 4
