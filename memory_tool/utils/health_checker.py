"""Document health checking utilities for memory_tool."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Tuple

from memory_tool.context.related_files import resolve_module_document
from memory_tool.utils.module_docs import is_meta_document


#: Files of the legacy layout, which split a module into several files.
LEGACY_FILES = ("module.md", "current.md", "decisions.md", "dependencies.md", "interface.md")


@dataclass
class HealthIssue:
    """Represents a document health issue."""

    module_name: str
    file_type: str  # "decisions", "current" (legacy files) or "module" (one document)
    file_path: Path
    line_count: int
    severity: str  # "critical", "warning", "ok"
    #: The file to show, relative to the modules folder
    display_path: str = ""

    @property
    def archive_command(self) -> str:
        """The marchive command for this file.

        A single document keeps its decisions as sections, which marchive
        decisions archives, so only a legacy current.md takes "current".
        """
        kind = "current" if self.file_type == "current" else "decisions"
        return f"marchive {kind} --module {self.module_name}"

    @property
    def severity_emoji(self) -> str:
        """Get emoji for severity level."""
        return {"critical": "🔴", "warning": "🟡", "ok": "✅"}[self.severity]

    @property
    def severity_label(self) -> str:
        """Get label for severity level."""
        return {"critical": "CRITICAL", "warning": "WARNING", "ok": "OK"}[self.severity]


class DocumentHealthChecker:
    """Check document health across modules."""

    # Thresholds for different file types. A single document holds what the
    # legacy layout spread over five files, so it gets the combined budget.
    DECISIONS_WARNING = 300
    DECISIONS_CRITICAL = 600
    CURRENT_WARNING = 200
    CURRENT_CRITICAL = 400
    MODULE_WARNING = 600
    MODULE_CRITICAL = 1000

    def __init__(self, memory_dir: Path):
        """Initialize health checker.

        Args:
            memory_dir: Path to .memory directory
        """
        self.memory_dir = Path(memory_dir)
        self.modules_dir = self.memory_dir / "modules"

    def check_all_modules(self, only: Optional[Iterable[Path]] = None) -> list[HealthIssue]:
        """Check health of all modules.

        Args:
            only: Check only these files, for example the ones about to be
                committed. None checks every document.

        Returns:
            List of health issues found, sorted by severity
        """
        if not self.modules_dir.exists():
            return []

        wanted = None if only is None else {Path(path).resolve() for path in only}

        def skipped(path: Path) -> bool:
            return wanted is not None and path.resolve() not in wanted

        issues = []

        # Recursively find all module files (.md) or legacy directories
        for module_file in self.modules_dir.rglob("*.md"):
            if "archive" in module_file.relative_to(self.modules_dir).parts or is_meta_document(module_file.name):
                continue
            # A legacy main document is one document too; its other files are
            # checked with the legacy folders below.
            if module_file.name in LEGACY_FILES and module_file.name != "module.md":
                continue
            if skipped(module_file):
                continue

            module_name = self._module_name_for(module_file)
            issue = self._check_file(module_name, "module", module_file)
            if issue:
                issues.append(issue)

        # Check legacy directories if any exist
        for module_dir in self._find_module_dirs():
            module_name = self._get_module_name(module_dir)
            for file_type, fname in [("decisions", "decisions.md"), ("current", "current.md")]:
                fpath = module_dir / fname
                if fpath.exists() and not skipped(fpath):
                    issue = self._check_file(module_name, file_type, fpath)
                    if issue:
                        issues.append(issue)

        severity_order = {"critical": 0, "warning": 1, "ok": 2}
        issues.sort(key=lambda x: (severity_order[x.severity], -x.line_count))

        return issues

    def _module_name_for(self, module_file: Path) -> str:
        """Name a module after its folder when the document is named for it.

        ``a/b/b.md`` is the module ``a/b``, not ``a/b/b``: repeating the folder
        name produced a module name that no other command could resolve. The
        legacy ``a/b/module.md`` is the module ``a/b`` as well.
        """
        if module_file.stem == module_file.parent.name or module_file.name in LEGACY_FILES:
            try:
                return module_file.parent.relative_to(self.modules_dir).as_posix()
            except ValueError:
                pass

        return module_file.relative_to(self.modules_dir).with_suffix("").as_posix()

    def check_module(self, module_name: str) -> list[HealthIssue]:
        """Check health of a specific module.

        Args:
            module_name: Name of module (e.g., "projects/memory-tool/core-system")

        Returns:
            List of health issues found
        """
        module_dir = self.modules_dir / module_name

        # A consolidated module is one document, so there is no decisions.md or
        # current.md beside it to measure -- the document itself is the subject.
        if not module_dir.is_dir():
            doc_path = resolve_module_document(module_dir)
            if doc_path is None:
                return []
            issue = self._check_file(module_name, "module", doc_path)
            return [issue] if issue else []

        issues = []

        # Check decisions.md
        decisions_path = module_dir / "decisions.md"
        if decisions_path.exists():
            issue = self._check_file(module_name, "decisions", decisions_path)
            if issue:
                issues.append(issue)

        # Check current.md
        current_path = module_dir / "current.md"
        if current_path.exists():
            issue = self._check_file(module_name, "current", current_path)
            if issue:
                issues.append(issue)

        if issues:
            return issues

        # Folder present but holding a single consolidated document.
        doc_path = resolve_module_document(module_dir)
        if doc_path is not None:
            issue = self._check_file(module_name, "module", doc_path)
            if issue:
                issues.append(issue)

        return issues

    def get_critical_issues(self) -> list[HealthIssue]:
        """Get only critical issues.

        Returns:
            List of critical issues
        """
        all_issues = self.check_all_modules()
        return [issue for issue in all_issues if issue.severity == "critical"]

    def get_warning_issues(self) -> list[HealthIssue]:
        """Get only warning issues.

        Returns:
            List of warning issues
        """
        all_issues = self.check_all_modules()
        return [issue for issue in all_issues if issue.severity == "warning"]

    def has_issues(self, min_severity: str = "warning") -> bool:
        """Check if there are any issues at or above min severity.

        Args:
            min_severity: Minimum severity to check ("critical" or "warning")

        Returns:
            True if issues found
        """
        all_issues = self.check_all_modules()
        if min_severity == "critical":
            return any(issue.severity == "critical" for issue in all_issues)
        else:
            return any(issue.severity in ["critical", "warning"] for issue in all_issues)

    def _find_module_dirs(self) -> list[Path]:
        """Find all module directories recursively.

        Returns:
            List of module directory paths
        """
        module_dirs = []

        for path in self.modules_dir.rglob("*"):
            if path.is_dir():
                # Skip archive directories and their children
                rel = path.relative_to(self.modules_dir)
                parts = rel.parts
                if "archive" in parts:
                    continue
                # Check if it contains module.md or decisions.md or current.md
                if any((path / f).exists() for f in ["module.md", "decisions.md", "current.md"]):
                    module_dirs.append(path)

        return module_dirs

    def _get_module_name(self, module_dir: Path) -> str:
        """Get module name from directory path.

        Args:
            module_dir: Path to module directory

        Returns:
            Module name (relative to modules directory)
        """
        try:
            return str(module_dir.relative_to(self.modules_dir)).replace("\\", "/")
        except ValueError:
            return str(module_dir.name)

    def _check_file(self, module_name: str, file_type: str, file_path: Path) -> Optional[HealthIssue]:
        """Check a single file's health.

        Args:
            module_name: Name of module
            file_type: "decisions" or "current" for legacy files, "module" for a document
            file_path: Path to file

        Returns:
            HealthIssue if issue found, None if file is healthy
        """
        try:
            line_count = len(file_path.read_text(encoding="utf-8").splitlines())
        except Exception:
            return None

        warning_at, critical_at = self.thresholds(file_type, file_path)

        if line_count >= critical_at:
            severity = "critical"
        elif line_count >= warning_at:
            severity = "warning"
        else:
            return None  # Healthy, no issue

        try:
            shown = file_path.relative_to(self.modules_dir).as_posix()
        except ValueError:
            shown = file_path.name

        return HealthIssue(
            module_name=module_name,
            file_type=file_type,
            file_path=file_path,
            line_count=line_count,
            severity=severity,
            display_path=shown,
        )

    def thresholds(self, file_type: str, file_path: Path) -> Tuple[int, int]:
        """The line counts at which a file gets a warning and becomes critical."""
        if file_type == "decisions":
            return self.DECISIONS_WARNING, self.DECISIONS_CRITICAL
        # A legacy main document held only the current state.
        if file_type == "current" or file_path.name in ("current.md", "module.md"):
            return self.CURRENT_WARNING, self.CURRENT_CRITICAL
        return self.MODULE_WARNING, self.MODULE_CRITICAL
