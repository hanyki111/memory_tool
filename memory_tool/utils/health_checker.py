"""Document health checking utilities for memory_tool."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class HealthIssue:
    """Represents a document health issue."""

    module_name: str
    file_type: str  # "decisions" or "current"
    file_path: Path
    line_count: int
    severity: str  # "critical", "warning", "ok"

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

    # Thresholds for different file types
    DECISIONS_WARNING = 300
    DECISIONS_CRITICAL = 600
    CURRENT_WARNING = 200
    CURRENT_CRITICAL = 400

    def __init__(self, memory_dir: Path):
        """Initialize health checker.

        Args:
            memory_dir: Path to .memory directory
        """
        self.memory_dir = Path(memory_dir)
        self.modules_dir = self.memory_dir / "modules"

    def check_all_modules(self) -> list[HealthIssue]:
        """Check health of all modules.

        Returns:
            List of health issues found, sorted by severity
        """
        if not self.modules_dir.exists():
            return []

        issues = []

        # Recursively find all module directories
        for module_dir in self._find_module_dirs():
            module_name = self._get_module_name(module_dir)

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

        # Sort by severity (critical first) and line count (largest first)
        severity_order = {"critical": 0, "warning": 1, "ok": 2}
        issues.sort(key=lambda x: (severity_order[x.severity], -x.line_count))

        return issues

    def check_module(self, module_name: str) -> list[HealthIssue]:
        """Check health of a specific module.

        Args:
            module_name: Name of module (e.g., "projects/memory-tool/core-system")

        Returns:
            List of health issues found
        """
        module_dir = self.modules_dir / module_name
        if not module_dir.exists():
            return []

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
            file_type: Type of file ("decisions" or "current")
            file_path: Path to file

        Returns:
            HealthIssue if issue found, None if file is healthy
        """
        try:
            line_count = len(file_path.read_text(encoding="utf-8").splitlines())
        except Exception:
            return None

        # Determine severity based on file type and line count
        if file_type == "decisions":
            if line_count >= self.DECISIONS_CRITICAL:
                severity = "critical"
            elif line_count >= self.DECISIONS_WARNING:
                severity = "warning"
            else:
                return None  # Healthy, no issue
        else:  # current
            if line_count >= self.CURRENT_CRITICAL:
                severity = "critical"
            elif line_count >= self.CURRENT_WARNING:
                severity = "warning"
            else:
                return None  # Healthy, no issue

        return HealthIssue(
            module_name=module_name,
            file_type=file_type,
            file_path=file_path,
            line_count=line_count,
            severity=severity
        )
