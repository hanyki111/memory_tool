"""Context gathering for enhanced summarization."""

from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Literal, Tuple
import re
from memory_tool.utils.paths import get_base_path

#: The document type for decisions, analyses and predictions.
JUDGMENT_TYPE = "판단"

#: "### 2026-11-06: Title", the dated entries of a legacy decisions log
DATED_DECISION = re.compile(r"###\s+(\d{4}-\d{2}-\d{2}):\s+(.+?)(?=###|\Z)", re.DOTALL)


class ContextGatherer:
    """Gather relevant context for summarization."""

    def __init__(self, memory_root: Optional[Path] = None):
        """
        Initialize context gatherer.

        Args:
            memory_root: Path to .memory/ directory. Defaults to .memory/ in cwd.
        """
        if memory_root is None:
            memory_root = get_base_path()
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
        Get decisions made in date range, at most the five most recent.

        Two places hold them:
        - ``판단`` documents, dated by ``generated.at``. A judgment document is
          not rewritten later -- a new one replaces it -- so the day it was
          made is the day of the decision.
        - Dated "### YYYY-MM-DD: Title" entries in a legacy ``decisions.md`` or
          a document's Decisions section, in any module, nested ones included.

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            List of decision strings, oldest first
        """
        from memory_tool.utils.module_docs import discover_module_paths, resolve_module_document

        modules_dir = self.memory_root / "modules"
        if not modules_dir.exists():
            return []

        found: List[Tuple[str, str]] = []
        for module in discover_module_paths(modules_dir):
            module_path = modules_dir / module

            document = resolve_module_document(module_path)
            if document is not None:
                judgment = self._judgment(document, module.as_posix(), start_date, end_date)
                if judgment:
                    found.append(judgment)

            found.extend(self._dated_decisions(module_path, start_date, end_date))

        found.sort(key=lambda item: item[0])
        return [text for _, text in found[-5:]]

    @staticmethod
    def _made_on(value) -> Optional[date]:
        """Read ``generated.at``, which YAML may already have turned into a datetime."""
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        try:
            return date.fromisoformat(str(value)[:10])
        except ValueError:
            return None

    def _judgment(
        self, document: Path, module: str, start_date: date, end_date: date
    ) -> Optional[Tuple[str, str]]:
        """A judgment document made in the range, as (date, text)."""
        from memory_tool.utils.frontmatter import Frontmatter

        try:
            metadata, body = Frontmatter.parse(document.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, AttributeError, ValueError):
            return None
        if not isinstance(metadata, dict) or metadata.get("type") != JUDGMENT_TYPE:
            return None

        generated = metadata.get("generated")
        made = self._made_on(generated.get("at")) if isinstance(generated, dict) else None
        if made is None or not (start_date <= made <= end_date):
            return None

        title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else module
        description = str(metadata.get("description") or "").strip()
        text = f"{title}: {description}" if description else title
        return made.isoformat(), f"**{made.isoformat()}**: {text[:200]}"

    @staticmethod
    def _dated_decisions(module_path: Path, start_date: date, end_date: date) -> List[Tuple[str, str]]:
        """Dated entries of a legacy decisions log, as (date, text)."""
        from memory_tool.core.doc_sections import read_decisions_text

        try:
            content = read_decisions_text(module_path)
        except Exception:
            return []
        if not content:
            return []

        found = []
        for match in DATED_DECISION.finditer(content):
            try:
                made = datetime.strptime(match.group(1), "%Y-%m-%d").date()
            except ValueError:
                continue
            if start_date <= made <= end_date:
                found.append((match.group(1), f"**{match.group(1)}**: {match.group(2).strip()[:200]}"))
        return found

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
