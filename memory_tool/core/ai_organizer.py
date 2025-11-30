"""AI-based module organization suggestions."""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class SuggestionType(Enum):
    """Type of organization suggestion."""
    SPLIT = "split"          # Module too large, should be split
    MERGE = "merge"          # Similar modules, could be merged
    MOVE = "move"            # Module in wrong location
    HIERARCHY = "hierarchy"  # Suggest parent-child structure


@dataclass
class ModuleInfo:
    """Information about a single module."""
    name: str
    path: Path
    line_count: int
    file_count: int
    has_current: bool
    has_decisions: bool
    has_module_md: bool
    content_preview: str


@dataclass
class OrganizationSuggestion:
    """A single organization suggestion."""
    type: SuggestionType
    priority: str  # "high", "medium", "low"
    module_name: str
    reason: str
    suggested_action: str
    details: Dict


class ModuleAnalyzer:
    """Analyzes module structure and gathers metrics."""

    # Thresholds for suggestions
    LARGE_MODULE_LINES = 300
    VERY_LARGE_MODULE_LINES = 500
    MIN_SIMILARITY_FOR_MERGE = 0.65

    def __init__(self, modules_path: Path):
        """Initialize analyzer.

        Args:
            modules_path: Path to .memory/modules/ directory
        """
        self.modules_path = modules_path

    def get_module_info(self, module_path: Path) -> ModuleInfo:
        """Get detailed information about a module.

        Args:
            module_path: Path to module directory

        Returns:
            ModuleInfo with metrics
        """
        name = str(module_path.relative_to(self.modules_path))

        # Count lines in key files
        total_lines = 0
        file_count = 0
        content_parts = []

        key_files = ["current.md", "decisions.md", "module.md", "interface.md", "README.md"]
        has_current = False
        has_decisions = False
        has_module_md = False

        for filename in key_files:
            file_path = module_path / filename
            if file_path.exists():
                file_count += 1
                try:
                    content = file_path.read_text(encoding="utf-8")
                    lines = len(content.splitlines())
                    total_lines += lines
                    content_parts.append(content[:500])

                    if filename == "current.md":
                        has_current = True
                    elif filename == "decisions.md":
                        has_decisions = True
                    elif filename == "module.md":
                        has_module_md = True
                except Exception:
                    pass

        return ModuleInfo(
            name=name,
            path=module_path,
            line_count=total_lines,
            file_count=file_count,
            has_current=has_current,
            has_decisions=has_decisions,
            has_module_md=has_module_md,
            content_preview="\n".join(content_parts)[:2000]
        )

    def discover_all_modules(self) -> List[ModuleInfo]:
        """Discover all modules and gather their info.

        Returns:
            List of ModuleInfo for all modules
        """
        modules = []

        if not self.modules_path.exists():
            return modules

        # Find all directories that look like modules
        for item in self.modules_path.rglob("*"):
            if item.is_dir():
                # Check if it's a module (has module files)
                has_module_files = any(
                    (item / f).exists()
                    for f in ["module.md", "current.md", "README.md"]
                )
                if has_module_files:
                    modules.append(self.get_module_info(item))

        return modules

    def find_large_modules(self, modules: List[ModuleInfo]) -> List[ModuleInfo]:
        """Find modules that exceed size thresholds.

        Args:
            modules: List of ModuleInfo

        Returns:
            List of large modules sorted by size (largest first)
        """
        large = [m for m in modules if m.line_count >= self.LARGE_MODULE_LINES]
        return sorted(large, key=lambda m: m.line_count, reverse=True)

    def find_similar_modules(
        self,
        modules: List[ModuleInfo],
        threshold: float = MIN_SIMILARITY_FOR_MERGE
    ) -> List[Tuple[ModuleInfo, ModuleInfo, float]]:
        """Find pairs of similar modules using embedding similarity.

        Args:
            modules: List of ModuleInfo
            threshold: Minimum similarity score

        Returns:
            List of (module1, module2, similarity) tuples
        """
        try:
            from sentence_transformers import SentenceTransformer
            import math
        except ImportError:
            return []

        if len(modules) < 2:
            return []

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        # Get embeddings for all modules
        contents = [m.content_preview for m in modules]
        embeddings = model.encode(contents, convert_to_tensor=False)

        # Compute pairwise similarities
        similar_pairs = []
        for i in range(len(modules)):
            for j in range(i + 1, len(modules)):
                # Cosine similarity
                dot = sum(a * b for a, b in zip(embeddings[i], embeddings[j]))
                norm_i = math.sqrt(sum(a * a for a in embeddings[i]))
                norm_j = math.sqrt(sum(b * b for b in embeddings[j]))

                if norm_i > 0 and norm_j > 0:
                    similarity = dot / (norm_i * norm_j)
                    if similarity >= threshold:
                        similar_pairs.append((modules[i], modules[j], similarity))

        return sorted(similar_pairs, key=lambda x: x[2], reverse=True)

    def find_namespace_issues(self, modules: List[ModuleInfo]) -> List[ModuleInfo]:
        """Find modules with inconsistent namespace patterns.

        Args:
            modules: List of ModuleInfo

        Returns:
            List of modules with potential namespace issues
        """
        issues = []

        for module in modules:
            name = module.name.replace("\\", "/")
            parts = name.split("/")

            # Check for inconsistent patterns
            # e.g., "memory-system.backup" vs "projects/memory-tool/..."
            if "." in parts[0] and len(parts) == 1:
                # Top-level module with dot notation (legacy pattern)
                issues.append(module)
            elif len(parts) == 1 and not name.startswith("projects"):
                # Top-level module not under projects/
                issues.append(module)

        return issues


class ModuleOrganizer:
    """Generates organization suggestions for modules."""

    def __init__(self, modules_path: Path):
        """Initialize organizer.

        Args:
            modules_path: Path to .memory/modules/ directory
        """
        self.modules_path = modules_path
        self.analyzer = ModuleAnalyzer(modules_path)

    def analyze_and_suggest(
        self,
        scope: Optional[str] = None,
        include_merges: bool = True
    ) -> List[OrganizationSuggestion]:
        """Analyze modules and generate organization suggestions.

        Args:
            scope: Optional path prefix to limit analysis (e.g., "projects/")
            include_merges: Whether to include merge suggestions (slower)

        Returns:
            List of OrganizationSuggestion sorted by priority
        """
        # Discover all modules
        all_modules = self.analyzer.discover_all_modules()

        # Filter by scope if specified
        if scope:
            scope_normalized = scope.replace("\\", "/").rstrip("/")
            all_modules = [
                m for m in all_modules
                if m.name.replace("\\", "/").startswith(scope_normalized)
            ]

        suggestions = []

        # 1. Find modules that need splitting
        suggestions.extend(self._suggest_splits(all_modules))

        # 2. Find potential merges (if enabled)
        if include_merges:
            suggestions.extend(self._suggest_merges(all_modules))

        # 3. Find namespace issues
        suggestions.extend(self._suggest_moves(all_modules))

        # 4. Suggest hierarchy improvements
        suggestions.extend(self._suggest_hierarchy(all_modules))

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        suggestions.sort(key=lambda s: priority_order.get(s.priority, 3))

        return suggestions

    def _suggest_splits(self, modules: List[ModuleInfo]) -> List[OrganizationSuggestion]:
        """Generate split suggestions for large modules."""
        suggestions = []
        large_modules = self.analyzer.find_large_modules(modules)

        for module in large_modules:
            is_very_large = module.line_count >= ModuleAnalyzer.VERY_LARGE_MODULE_LINES
            priority = "high" if is_very_large else "medium"

            # Analyze content to suggest split points
            split_suggestions = self._analyze_split_points(module)

            suggestions.append(OrganizationSuggestion(
                type=SuggestionType.SPLIT,
                priority=priority,
                module_name=module.name,
                reason=f"Module has {module.line_count} lines (threshold: {ModuleAnalyzer.LARGE_MODULE_LINES})",
                suggested_action=f"Split into {len(split_suggestions)} sub-modules",
                details={
                    "line_count": module.line_count,
                    "suggested_splits": split_suggestions
                }
            ))

        return suggestions

    def _analyze_split_points(self, module: ModuleInfo) -> List[str]:
        """Analyze module content to suggest split points.

        Args:
            module: ModuleInfo to analyze

        Returns:
            List of suggested sub-module names
        """
        suggestions = []
        name_parts = module.name.replace("\\", "/").split("/")
        base_name = name_parts[-1]

        # Common split patterns based on module name
        if "core" in base_name.lower():
            suggestions.extend([
                f"{base_name}/storage",
                f"{base_name}/initialization"
            ])
        elif "system" in base_name.lower():
            suggestions.extend([
                f"{base_name}/core",
                f"{base_name}/utils"
            ])
        else:
            # Generic suggestions
            suggestions.extend([
                f"{base_name}/core",
                f"{base_name}/features"
            ])

        return suggestions

    def _suggest_merges(self, modules: List[ModuleInfo]) -> List[OrganizationSuggestion]:
        """Generate merge suggestions for similar modules."""
        suggestions = []
        similar_pairs = self.analyzer.find_similar_modules(modules)

        for module1, module2, similarity in similar_pairs:
            # Only suggest merge if both modules are small
            if module1.line_count < 200 and module2.line_count < 200:
                suggestions.append(OrganizationSuggestion(
                    type=SuggestionType.MERGE,
                    priority="low",
                    module_name=module1.name,
                    reason=f"High similarity ({similarity:.0%}) with {module2.name}",
                    suggested_action=f"Consider merging with {module2.name}",
                    details={
                        "other_module": module2.name,
                        "similarity": round(similarity, 2),
                        "combined_lines": module1.line_count + module2.line_count
                    }
                ))

        return suggestions

    def _suggest_moves(self, modules: List[ModuleInfo]) -> List[OrganizationSuggestion]:
        """Generate move suggestions for namespace consistency."""
        suggestions = []
        issues = self.analyzer.find_namespace_issues(modules)

        for module in issues:
            name = module.name.replace("\\", "/")

            # Suggest new location
            if "." in name:
                # Convert dot notation to path
                new_name = name.replace(".", "/")
                suggested_path = f"projects/{new_name}"
            else:
                suggested_path = f"projects/{name}"

            suggestions.append(OrganizationSuggestion(
                type=SuggestionType.MOVE,
                priority="medium",
                module_name=module.name,
                reason="Inconsistent namespace pattern",
                suggested_action=f"Move to {suggested_path}",
                details={
                    "current_path": module.name,
                    "suggested_path": suggested_path
                }
            ))

        return suggestions

    def _suggest_hierarchy(self, modules: List[ModuleInfo]) -> List[OrganizationSuggestion]:
        """Generate hierarchy suggestions based on module relationships."""
        suggestions = []

        # Group modules by common prefixes
        prefix_groups: Dict[str, List[ModuleInfo]] = {}
        for module in modules:
            name = module.name.replace("\\", "/")
            parts = name.split("/")
            if len(parts) >= 2:
                prefix = "/".join(parts[:-1])
                if prefix not in prefix_groups:
                    prefix_groups[prefix] = []
                prefix_groups[prefix].append(module)

        # Look for groups that could benefit from restructuring
        for prefix, group in prefix_groups.items():
            if len(group) >= 4:
                # Many modules under same parent - suggest sub-grouping
                # Analyze names for potential groupings
                ai_related = [m for m in group if any(
                    kw in m.name.lower()
                    for kw in ["ai", "llm", "embed", "vector", "graph"]
                )]

                if len(ai_related) >= 2:
                    suggestions.append(OrganizationSuggestion(
                        type=SuggestionType.HIERARCHY,
                        priority="low",
                        module_name=prefix,
                        reason=f"Found {len(ai_related)} AI-related modules that could be grouped",
                        suggested_action=f"Create {prefix}/ai/ sub-directory",
                        details={
                            "modules_to_move": [m.name for m in ai_related],
                            "new_parent": f"{prefix}/ai"
                        }
                    ))

        return suggestions

    def format_suggestions(self, suggestions: List[OrganizationSuggestion]) -> str:
        """Format suggestions for display.

        Args:
            suggestions: List of suggestions

        Returns:
            Formatted string for console output (ASCII-safe for Windows)
        """
        if not suggestions:
            return "No organization suggestions at this time."

        lines = [f"[bold]Module Structure Analysis[/bold] ({len(suggestions)} suggestions)\n"]

        # Group by type
        by_type: Dict[SuggestionType, List[OrganizationSuggestion]] = {}
        for s in suggestions:
            if s.type not in by_type:
                by_type[s.type] = []
            by_type[s.type].append(s)

        # Format each type (using ASCII-safe markers for Windows compatibility)
        type_markers = {
            SuggestionType.SPLIT: "[red][!][/red]",
            SuggestionType.MERGE: "[blue][?][/blue]",
            SuggestionType.MOVE: "[yellow][>][/yellow]",
            SuggestionType.HIERARCHY: "[green][+][/green]"
        }

        type_titles = {
            SuggestionType.SPLIT: "SPLIT RECOMMENDED",
            SuggestionType.MERGE: "MERGE CANDIDATES",
            SuggestionType.MOVE: "MOVE RECOMMENDED",
            SuggestionType.HIERARCHY: "HIERARCHY SUGGESTION"
        }

        for stype in [SuggestionType.SPLIT, SuggestionType.MOVE,
                      SuggestionType.HIERARCHY, SuggestionType.MERGE]:
            if stype in by_type:
                items = by_type[stype]
                marker = type_markers[stype]
                title = type_titles[stype]

                lines.append(f"{marker} {title} ({len(items)}):")

                for s in items:
                    # Normalize path separators for display
                    display_name = s.module_name.replace("\\", "/")
                    lines.append(f"   {display_name}")
                    lines.append(f"   -> {s.suggested_action}")
                    lines.append(f"   [dim]Reason: {s.reason}[/dim]")
                    lines.append("")

        return "\n".join(lines)
