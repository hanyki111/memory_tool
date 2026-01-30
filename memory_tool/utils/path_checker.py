"""Path validation for module Related Files sections."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from memory_tool.context.related_files import (
    RelatedFiles,
    RelatedFilesParser,
    get_module_related_files,
)


@dataclass
class PathCheckResult:
    """Result of checking a single path."""

    path: str
    exists: bool
    is_file: bool = False
    is_directory: bool = False
    # Source tracking for error reporting
    source_file: str = ""
    line_number: int = 0
    # Resolved path (where it was actually found)
    resolved_path: str = ""

    @property
    def status_icon(self) -> str:
        """Get status icon for display."""
        if self.exists:
            return "[OK]"
        return "[X]"

    def format_error(self) -> str:
        """Format as standard error message (file:line: error: message)."""
        if self.exists:
            return ""
        if self.source_file and self.line_number > 0:
            return f"{self.source_file}:{self.line_number}: error: '{self.path}' not found"
        return f"error: '{self.path}' not found"


@dataclass
class ModuleCheckResult:
    """Result of checking all paths in a module."""

    module_name: str
    module_path: Path
    related_files: RelatedFiles
    path_results: List[PathCheckResult] = field(default_factory=list)

    @property
    def valid_count(self) -> int:
        """Count of valid paths."""
        return sum(1 for r in self.path_results if r.exists)

    @property
    def missing_count(self) -> int:
        """Count of missing paths."""
        return sum(1 for r in self.path_results if not r.exists)

    @property
    def total_count(self) -> int:
        """Total number of paths checked."""
        return len(self.path_results)

    @property
    def has_issues(self) -> bool:
        """Check if there are any missing paths."""
        return self.missing_count > 0

    @property
    def has_related_files(self) -> bool:
        """Check if module has Related Files section."""
        return self.related_files.format_type != "none"

    @property
    def status_icon(self) -> str:
        """Get overall status icon."""
        if not self.has_related_files:
            return "[!]"
        if self.missing_count == 0:
            return "[OK]"
        return "[X]"

    def get_valid_paths(self) -> List[str]:
        """Get list of valid paths."""
        return [r.path for r in self.path_results if r.exists]

    def get_missing_paths(self) -> List[str]:
        """Get list of missing paths."""
        return [r.path for r in self.path_results if not r.exists]


@dataclass
class CheckSummary:
    """Summary of all module checks."""

    results: List[ModuleCheckResult] = field(default_factory=list)
    checked_at: datetime = field(default_factory=datetime.now)

    @property
    def modules_checked(self) -> int:
        """Number of modules checked."""
        return len(self.results)

    @property
    def modules_with_issues(self) -> int:
        """Number of modules with missing paths."""
        return sum(1 for r in self.results if r.has_issues)

    @property
    def modules_without_related_files(self) -> int:
        """Number of modules without Related Files section."""
        return sum(1 for r in self.results if not r.has_related_files)

    @property
    def total_valid(self) -> int:
        """Total valid paths across all modules."""
        return sum(r.valid_count for r in self.results)

    @property
    def total_missing(self) -> int:
        """Total missing paths across all modules."""
        return sum(r.missing_count for r in self.results)

    @property
    def has_issues(self) -> bool:
        """Check if any module has issues."""
        return self.total_missing > 0 or self.modules_without_related_files > 0

    def to_dict(self) -> dict:
        """Convert to dictionary for caching."""
        return {
            "checked_at": self.checked_at.isoformat(),
            "modules_checked": self.modules_checked,
            "modules_with_issues": self.modules_with_issues,
            "modules_without_related_files": self.modules_without_related_files,
            "total_valid": self.total_valid,
            "total_missing": self.total_missing,
            "has_issues": self.has_issues,
            "results": [
                {
                    "module_name": r.module_name,
                    "has_issues": r.has_issues,
                    "missing_paths": r.get_missing_paths(),
                }
                for r in self.results
                if r.has_issues or not r.has_related_files
            ],
        }


class PathChecker:
    """Check validity of paths in module Related Files sections."""

    CACHE_FILE = ".path_check_cache.json"

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize path checker.

        Args:
            base_path: Base path for the project. Defaults to cwd.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"
        self.modules_path = self.memory_path / "modules"
        self.cache_path = self.memory_path / self.CACHE_FILE
        self.parser = RelatedFilesParser()

    def check_path(
        self,
        path_str: str,
        module_path: Optional[Path] = None,
        source_file: str = "",
        line_number: int = 0,
    ) -> PathCheckResult:
        """Check if a path exists using smart resolution.

        Resolution order:
        1. Module directory (if module_path provided)
        2. Project root (base_path)
        3. .memory directory

        Args:
            path_str: Path string to check
            module_path: Optional module directory for relative resolution
            source_file: Source file where path was referenced
            line_number: Line number in source file

        Returns:
            PathCheckResult with existence info
        """
        # Normalize path (remove ./ prefix if present, but preserve .memory etc)
        if path_str.startswith("./"):
            normalized_path = path_str[2:]
        else:
            normalized_path = path_str

        # 1. Try module directory first (for relative paths like spec.md)
        if module_path and module_path.exists():
            module_full_path = module_path / normalized_path
            if module_full_path.exists():
                return PathCheckResult(
                    path=path_str,
                    exists=True,
                    is_file=module_full_path.is_file(),
                    is_directory=module_full_path.is_dir(),
                    source_file=source_file,
                    line_number=line_number,
                    resolved_path=str(module_full_path),
                )

        # 2. Try project root
        root_path = self.base_path / normalized_path
        if root_path.exists():
            return PathCheckResult(
                path=path_str,
                exists=True,
                is_file=root_path.is_file(),
                is_directory=root_path.is_dir(),
                source_file=source_file,
                line_number=line_number,
                resolved_path=str(root_path),
            )

        # 3. Try .memory directory
        memory_path = self.memory_path / normalized_path
        if memory_path.exists():
            return PathCheckResult(
                path=path_str,
                exists=True,
                is_file=memory_path.is_file(),
                is_directory=memory_path.is_dir(),
                source_file=source_file,
                line_number=line_number,
                resolved_path=str(memory_path),
            )

        # Not found in any location
        return PathCheckResult(
            path=path_str,
            exists=False,
            is_file=False,
            is_directory=False,
            source_file=source_file,
            line_number=line_number,
            resolved_path="",
        )

    def check_module(self, module_name: str) -> ModuleCheckResult:
        """Check all Related Files paths in a module.

        Args:
            module_name: Module name (e.g., "projects/memory-tool/core-system")

        Returns:
            ModuleCheckResult with all path checks
        """
        module_path = self.modules_path / module_name
        related_files = get_module_related_files(module_path)

        # Determine source file path for error reporting
        current_md_path = module_path / "current.md"
        source_file = str(current_md_path.relative_to(self.base_path))

        result = ModuleCheckResult(
            module_name=module_name,
            module_path=module_path,
            related_files=related_files,
        )

        # Check all paths with smart resolution
        for path_str in related_files.all_paths():
            line_number = related_files.get_line_number(path_str)
            path_result = self.check_path(
                path_str,
                module_path=module_path,
                source_file=source_file,
                line_number=line_number,
            )
            result.path_results.append(path_result)

        return result

    def check_all_modules(self, include_archived: bool = False) -> CheckSummary:
        """Check all modules in the project.

        Args:
            include_archived: Include archived modules (default: False)

        Returns:
            CheckSummary with all results
        """
        summary = CheckSummary()

        if not self.modules_path.exists():
            return summary

        # Find all modules (directories with current.md)
        for current_file in self.modules_path.rglob("current.md"):
            module_dir = current_file.parent
            module_name = str(
                module_dir.relative_to(self.modules_path)
            ).replace("\\", "/")

            # Skip archived modules unless explicitly included
            if not include_archived:
                # Check if module is in archive folder
                if module_name.startswith("archive/") or "/archive/" in module_name:
                    continue

            result = self.check_module(module_name)
            summary.results.append(result)

        return summary

    def save_cache(self, summary: CheckSummary) -> None:
        """Save check results to cache.

        Args:
            summary: Check summary to cache
        """
        try:
            cache_data = summary.to_dict()
            self.cache_path.write_text(
                json.dumps(cache_data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception:
            pass  # Silently fail on cache write errors

    def load_cache(self) -> Optional[dict]:
        """Load cached check results.

        Returns:
            Cached data dict or None if not available
        """
        if not self.cache_path.exists():
            return None

        try:
            content = self.cache_path.read_text(encoding="utf-8")
            return json.loads(content)
        except Exception:
            return None

    def has_cached_issues(self) -> bool:
        """Quick check if cached results show issues.

        Returns:
            True if cached results indicate issues
        """
        cache = self.load_cache()
        if cache is None:
            return False
        return cache.get("has_issues", False)

    def get_cached_summary(self) -> Optional[str]:
        """Get a brief summary from cache for display.

        Returns:
            Summary string or None if no cache
        """
        cache = self.load_cache()
        if cache is None:
            return None

        if not cache.get("has_issues"):
            return None

        parts = []
        missing = cache.get("total_missing", 0)
        no_section = cache.get("modules_without_related_files", 0)

        if missing > 0:
            parts.append(f"{missing} missing path(s)")
        if no_section > 0:
            parts.append(f"{no_section} module(s) without Related Files")

        if parts:
            return ", ".join(parts)
        return None


def format_check_result(
    summary: CheckSummary,
    verbose: bool = False,
    standard_format: bool = False,
) -> str:
    """Format check results for display.

    Args:
        summary: Check summary
        verbose: Show all paths, not just issues
        standard_format: Use compiler-style error format (file:line: error: message)

    Returns:
        Formatted string for display
    """
    lines = []

    if standard_format:
        # Standard compiler-style error format
        for result in sorted(summary.results, key=lambda r: r.module_name):
            if result.has_related_files:
                for path_result in result.path_results:
                    if not path_result.exists:
                        lines.append(path_result.format_error())
            else:
                # No Related Files section - also report as error
                source_file = f".memory/modules/{result.module_name}/current.md"
                lines.append(f"{source_file}:1: warning: No Related Files section found")

        # Summary at the end
        if lines:
            lines.append("")
        lines.append(f"Checked {summary.modules_checked} modules: "
                     f"{summary.total_valid} valid, {summary.total_missing} missing")
    else:
        # Original grouped format
        for result in sorted(summary.results, key=lambda r: r.module_name):
            # Module header
            if result.has_related_files:
                if verbose or result.has_issues:
                    lines.append(f"\n{result.status_icon} {result.module_name}")

                    # Show paths
                    for path_result in result.path_results:
                        if verbose or not path_result.exists:
                            type_indicator = ""
                            if path_result.exists:
                                type_indicator = " (dir)" if path_result.is_directory else " (file)"
                            lines.append(
                                f"  {path_result.status_icon} {path_result.path}{type_indicator}"
                            )
            else:
                # No Related Files section
                lines.append(f"\n[!] {result.module_name}")
                lines.append("  No Related Files section found")
                if result.related_files.format_type == "legacy":
                    lines.append("  (using legacy Key Files format)")

        # Summary
        lines.append("")
        lines.append("-" * 40)
        lines.append("Summary:")
        lines.append(f"  Modules checked: {summary.modules_checked}")
        lines.append(f"  Valid paths: {summary.total_valid}")

        if summary.total_missing > 0:
            lines.append(f"  Missing paths: {summary.total_missing}")

        if summary.modules_without_related_files > 0:
            lines.append(
                f"  Modules without Related Files: {summary.modules_without_related_files}"
            )

    return "\n".join(lines)
