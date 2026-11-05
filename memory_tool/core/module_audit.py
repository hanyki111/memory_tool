"""Find modules worth splitting or merging.

Nothing here calls an LLM or changes a document. It measures document structure
and embedding similarity, and reports candidates for a person to judge.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from memory_tool.utils.module_docs import discover_module_paths, module_documents

from .embedding_cache import (
    SimilarityCalculator,
    get_embedding_cache,
    get_model_manager,
)

_HEADING = re.compile(r"^#{1,2}\s+\S")


class SuggestionType(Enum):
    """Type of audit candidate."""

    SPLIT = "split"
    MERGE = "merge"


@dataclass
class ModuleInfo:
    """Measurements of a single module."""

    name: str
    path: Path
    line_count: int
    section_count: int
    content_preview: str


@dataclass
class AuditSuggestion:
    """One candidate found by an audit."""

    type: SuggestionType
    module_name: str
    reason: str
    suggested_action: str
    details: Dict = field(default_factory=dict)


@dataclass
class AuditReport:
    """The outcome of an audit.

    ``merges_checked`` distinguishes "no similar modules" from "similarity could
    not be measured", so an absent result is never read as a clean one.
    """

    suggestions: List[AuditSuggestion]
    modules_examined: int
    merges_checked: bool


def count_sections(text: str) -> int:
    """Count level 1 and 2 headings, ignoring those inside code fences."""
    count = 0
    in_fence = False

    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        elif not in_fence and _HEADING.match(line):
            count += 1

    return count


class ModuleAnalyzer:
    """Gathers measurements for the modules under a folder."""

    #: A document this long may be worth splitting...
    LARGE_MODULE_LINES = 300
    #: ...but only if it covers several topics. A long lookup table is fine.
    MIN_SECTIONS_TO_SPLIT = 5
    #: Only modules this small are merge candidates.
    MAX_LINES_TO_MERGE = 200
    MIN_SIMILARITY_FOR_MERGE = 0.65

    def __init__(self, modules_path: Path, cache_dir: Optional[Path] = None):
        """Initialize analyzer.

        Args:
            modules_path: Path to the modules directory
            cache_dir: Directory for the embedding cache
        """
        self.modules_path = modules_path
        self._model_manager = get_model_manager()
        self._cache_dir = cache_dir or modules_path.parent / ".cache"

    def get_module_info(self, module_path: Path) -> ModuleInfo:
        """Measure one module, whichever layout it uses.

        Args:
            module_path: The module's folder, or its path without a suffix

        Returns:
            Its measurements. A module with no readable document measures zero.
        """
        total_lines = 0
        total_sections = 0
        content_parts = []

        for document in module_documents(module_path):
            try:
                content = document.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            total_lines += len(content.splitlines())
            total_sections += count_sections(content)
            content_parts.append(content[:2000])

        return ModuleInfo(
            name=module_path.relative_to(self.modules_path).as_posix(),
            path=module_path,
            line_count=total_lines,
            section_count=total_sections,
            content_preview="\n".join(content_parts)[:2000],
        )

    def discover_all_modules(self) -> List[ModuleInfo]:
        """Measure every module."""
        return [
            self.get_module_info(self.modules_path / relative)
            for relative in discover_module_paths(self.modules_path)
        ]

    def find_split_candidates(self, modules: List[ModuleInfo]) -> List[ModuleInfo]:
        """Find long modules that cover several sections, longest first."""
        candidates = [
            m for m in modules
            if m.line_count >= self.LARGE_MODULE_LINES
            and m.section_count >= self.MIN_SECTIONS_TO_SPLIT
        ]
        return sorted(candidates, key=lambda m: m.line_count, reverse=True)

    def can_measure_similarity(self) -> bool:
        """Tell whether the embedding model can be used."""
        return self._model_manager.is_available()

    def find_similar_modules(
        self,
        modules: List[ModuleInfo],
        threshold: float = MIN_SIMILARITY_FOR_MERGE,
    ) -> List[Tuple[ModuleInfo, ModuleInfo, float]]:
        """Find pairs of similar modules using embeddings.

        Args:
            modules: Modules to compare
            threshold: Minimum similarity score

        Returns:
            (module1, module2, similarity) tuples
        """
        if len(modules) < 2 or not self.can_measure_similarity():
            return []

        model = self._model_manager.get_model()
        if model is None:
            return []

        contents = [m.content_preview for m in modules]
        cache = get_embedding_cache(self._cache_dir)

        if cache:
            embeddings = cache.get_many(contents, model)
        else:
            embeddings = [e.tolist() for e in model.encode(contents, convert_to_tensor=False)]

        pairs = SimilarityCalculator.find_all_pairs_above_threshold(
            embeddings, [m.name for m in modules], threshold
        )

        by_name = {m.name: m for m in modules}
        return [(by_name[a], by_name[b], score) for a, b, score in pairs]


class ModuleAuditor:
    """Turns measurements into candidates a person can judge."""

    def __init__(self, modules_path: Path):
        self.analyzer = ModuleAnalyzer(modules_path)

    def audit(self, scope: Optional[str] = None, include_merges: bool = True) -> AuditReport:
        """Audit modules.

        Args:
            scope: A module path. Limits the audit to it and what is under it.
            include_merges: Compare modules for merging. Loads an embedding
                model, so it is the slow part of an audit.

        Returns:
            The candidates, split candidates first.
        """
        modules = self.analyzer.discover_all_modules()

        if scope:
            prefix = scope.replace("\\", "/").rstrip("/")
            modules = [
                m for m in modules
                if m.name == prefix or m.name.startswith(prefix + "/")
            ]

        suggestions = self._split_suggestions(modules)

        merges_checked = include_merges and self.analyzer.can_measure_similarity()
        if merges_checked:
            suggestions.extend(self._merge_suggestions(modules))

        return AuditReport(
            suggestions=suggestions,
            modules_examined=len(modules),
            merges_checked=merges_checked,
        )

    def _split_suggestions(self, modules: List[ModuleInfo]) -> List[AuditSuggestion]:
        return [
            AuditSuggestion(
                type=SuggestionType.SPLIT,
                module_name=m.name,
                reason=f"{m.line_count} lines across {m.section_count} sections",
                suggested_action="Check whether its sections answer different questions",
                details={"line_count": m.line_count, "section_count": m.section_count},
            )
            for m in self.analyzer.find_split_candidates(modules)
        ]

    def _merge_suggestions(self, modules: List[ModuleInfo]) -> List[AuditSuggestion]:
        limit = ModuleAnalyzer.MAX_LINES_TO_MERGE
        suggestions = []

        for first, second, similarity in self.analyzer.find_similar_modules(modules):
            if first.line_count < limit and second.line_count < limit:
                suggestions.append(
                    AuditSuggestion(
                        type=SuggestionType.MERGE,
                        module_name=first.name,
                        reason=f"{similarity:.0%} similar to {second.name}",
                        suggested_action=f"Check whether it belongs with {second.name}",
                        details={"other_module": second.name, "similarity": round(similarity, 2)},
                    )
                )

        return suggestions


def format_report(report: AuditReport, limit: Optional[int] = None) -> str:
    """Render an audit report as console markup.

    Args:
        report: The report
        limit: Show at most this many candidates of each type

    Returns:
        Text for a rich console, ASCII-safe for Windows terminals.
    """
    lines = [f"[bold]Module audit[/bold]: {report.modules_examined} modules examined", ""]

    titles = {
        SuggestionType.SPLIT: "[red][!][/red] Split candidates",
        SuggestionType.MERGE: "[blue][?][/blue] Merge candidates",
    }

    for suggestion_type, title in titles.items():
        items = [s for s in report.suggestions if s.type == suggestion_type]
        if not items:
            continue

        lines.append(f"{title} ({len(items)}):")
        shown = items if limit is None else items[:limit]

        for item in shown:
            lines.append(f"   {item.module_name}")
            lines.append(f"   -> {item.suggested_action}")
            lines.append(f"   [dim]{item.reason}[/dim]")
            lines.append("")

        if len(shown) < len(items):
            lines.append(f"   [dim]... and {len(items) - len(shown)} more (use --limit)[/dim]")
            lines.append("")

    if not report.suggestions:
        lines.append("[green]No candidates found.[/green]")
        lines.append("")

    if not report.merges_checked:
        lines.append(
            "[yellow]Merge candidates were not checked:[/yellow] "
            "[dim]install sentence-transformers to compare modules.[/dim]"
        )
        lines.append("")

    lines.append("[dim]These are candidates only. Nothing was changed.[/dim]")
    return "\n".join(lines)
