"""Find modules worth splitting or merging.

Nothing here calls an LLM or changes a document. It measures document structure
and embedding similarity, and reports candidates for a person to judge.
"""

import math
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Tuple

from memory_tool.utils.frontmatter import Frontmatter
from memory_tool.utils.module_docs import discover_module_paths, module_documents

from .embedding_cache import (
    SimilarityCalculator,
    get_embedding_cache,
    get_model_manager,
)

_HEADING = re.compile(r"^#{1,2}\s+\S")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")

#: Characters per piece of text embedded. The model reads 128 tokens and drops
#: the rest; Korean runs about 0.6 tokens a character, so 200 characters fit.
CHUNK_CHARS = 200
#: Pieces embedded per module, to bound the work on a very long document.
MAX_CHUNKS = 64


#: Stands in for the module name when templates are built, so a line holding
#: the name ("Current Knowledge State: <name>") still matches its template.
_NAME_MARK = "zqxtemplatenamezqx"
#: A field label left without a value: "- **전제:**", "- **제외** —".
_EMPTY_FIELD = re.compile(r"^[>*+\-\s]*\*\*[^*]+\*\*[\s:—–|-]*$")
#: Placeholders a writer replaces. Older templates left them in plain text.
_PLACEHOLDER = re.compile(r"\[\[모듈명\]\]|\[주제\]|YYYY-MM-DD|____-__-__")
#: A line found in this many modules is shared wording, not a subject.
SHARED_LINE_MODULES = 3


def normalized_lines(content: str) -> List[str]:
    """Lines of a document's body, trimmed, with frontmatter and comments gone."""
    _, body = Frontmatter.parse(content)
    return [line.strip() for line in _COMMENT.sub("", body).splitlines()]


@dataclass
class Boilerplate:
    """Text documents share because they started from a template.

    Documents made from one template share most of their text until they are
    filled in. Compared as is, two unrelated documents looked alike because
    their headings and guidance did.
    """

    exact: FrozenSet[str] = frozenset()
    patterns: Tuple[re.Pattern, ...] = ()

    def matches(self, line: str) -> bool:
        return (
            line in self.exact
            or bool(_EMPTY_FIELD.match(line))
            or bool(_PLACEHOLDER.search(line))
            or any(p.fullmatch(line) for p in self.patterns)
        )

    def with_lines(self, lines) -> "Boilerplate":
        return Boilerplate(self.exact | frozenset(lines), self.patterns)


def template_boilerplate(memory_path: Optional[Path] = None) -> Boilerplate:
    """Every line a new document starts with, for every kind and outline."""
    from .module_templates import KINDS, build_module_document, natures_for

    lines = set()
    for kind in KINDS:
        for nature in (None, *natures_for(kind)):
            for draft in (False, True):
                try:
                    doc = build_module_document(
                        name=_NAME_MARK, kind=kind, nature=nature,
                        memory_path=memory_path, draft=draft,
                    )
                except Exception:
                    continue
                lines.update(normalized_lines(doc))

    lines.discard("")
    named = {line for line in lines if _NAME_MARK in line}
    patterns = tuple(
        re.compile(".+".join(re.escape(part) for part in line.split(_NAME_MARK)))
        for line in sorted(named)
    )
    return Boilerplate(frozenset(lines - named), patterns)


def comparable_text(content: str, boilerplate: Optional[Boilerplate] = None) -> str:
    """The part of a document that says something about its subject.

    Frontmatter, HTML comments, code fence markers and template wording are
    dropped. Headings stay, without their marks: a title such as "AI 기초" is
    about the subject.
    """
    boilerplate = boilerplate or Boilerplate()

    kept = []
    for line in normalized_lines(content):
        if not line:
            if kept and kept[-1]:
                kept.append("")
        elif not line.startswith(("```", "~~~")) and not boilerplate.matches(line):
            kept.append(line.lstrip("#").strip())

    return "\n".join(kept).strip()


def split_into_chunks(text: str, size: int = CHUNK_CHARS, limit: int = MAX_CHUNKS) -> List[str]:
    """Pieces of at most ``size`` characters, cut at paragraphs, then spaces."""
    chunks = []
    for paragraph in _PARAGRAPH_BREAK.split(text):
        paragraph = " ".join(paragraph.split())
        while paragraph:
            if len(paragraph) <= size:
                chunks.append(paragraph)
                break
            cut = paragraph.rfind(" ", 0, size)
            if cut < size // 2:
                cut = size
            chunks.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        if len(chunks) >= limit:
            break
    return chunks[:limit]


def mean_vector(vectors: List[Optional[List[float]]], weights: List[int]) -> Optional[List[float]]:
    """Length-weighted mean of unit vectors, or None if there are none."""
    total = None
    for vector, weight in zip(vectors, weights):
        if vector is None:
            continue
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        scaled = [v * weight / norm for v in vector]
        total = scaled if total is None else [a + b for a, b in zip(total, scaled)]
    return total


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
    #: What the document says about its subject; see ``comparable_text``.
    body: str


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
        self._boilerplate: Optional[Boilerplate] = None

    @property
    def boilerplate(self) -> Boilerplate:
        """Template wording, built on first use."""
        if self._boilerplate is None:
            self._boilerplate = template_boilerplate(self.modules_path.parent)
        return self._boilerplate

    def _read(self, module_path: Path) -> List[str]:
        contents = []
        for document in module_documents(module_path):
            try:
                contents.append(document.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                continue
        return contents

    def get_module_info(
        self,
        module_path: Path,
        boilerplate: Optional[Boilerplate] = None,
    ) -> ModuleInfo:
        """Measure one module, whichever layout it uses.

        Args:
            module_path: The module's folder, or its path without a suffix
            boilerplate: Wording to leave out of the body; the templates' if
                not given

        Returns:
            Its measurements. A module with no readable document measures zero.
        """
        boilerplate = boilerplate or self.boilerplate
        total_lines = 0
        total_sections = 0
        bodies = []

        for content in self._read(module_path):
            total_lines += len(content.splitlines())
            total_sections += count_sections(content)
            bodies.append(comparable_text(content, boilerplate))

        # A template writes the description into several places; a line said
        # again adds nothing but weight.
        seen = set()
        kept = []
        for line in "\n\n".join(bodies).splitlines():
            if line and line in seen:
                continue
            seen.add(line)
            kept.append(line)

        return ModuleInfo(
            name=module_path.relative_to(self.modules_path).as_posix(),
            path=module_path,
            line_count=total_lines,
            section_count=total_sections,
            body="\n".join(kept).strip(),
        )

    def discover_all_modules(self) -> List[ModuleInfo]:
        """Measure every module.

        Wording found in several modules counts as template wording as well.
        That covers documents made from an older template or a project's own,
        which the current templates do not match.
        """
        paths = [self.modules_path / r for r in discover_module_paths(self.modules_path)]

        seen_in: Dict[str, int] = {}
        for path in paths:
            lines = {line for c in self._read(path) for line in normalized_lines(c) if line}
            for line in lines:
                seen_in[line] = seen_in.get(line, 0) + 1
        shared = [line for line, count in seen_in.items() if count >= SHARED_LINE_MODULES]

        boilerplate = self.boilerplate.with_lines(shared)
        return [self.get_module_info(path, boilerplate) for path in paths]

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

        # Embed every piece of every body in one batch, then average each
        # module's pieces. The model reads only the start of a long text, so
        # one embedding per module compared the first lines alone.
        chunked = [split_into_chunks(m.body) for m in modules]
        flat = [chunk for chunks in chunked for chunk in chunks]
        cache = get_embedding_cache(self._cache_dir, self._model_manager.model_name)

        if not flat:
            return []
        if cache:
            vectors = cache.get_many(flat, model)
        else:
            vectors = [e.tolist() for e in model.encode(flat, convert_to_tensor=False)]

        embeddings: List[Optional[List[float]]] = []
        start = 0
        for chunks in chunked:
            # A module with nothing of its own to say has no vector, and is
            # left out rather than matched on emptiness.
            embeddings.append(
                mean_vector(vectors[start:start + len(chunks)], [len(c) for c in chunks])
            )
            start += len(chunks)

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
