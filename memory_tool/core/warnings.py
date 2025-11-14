"""File size warning system for documentation management."""

from pathlib import Path
from typing import List, Tuple, Optional
import re


class FileSizeWarning:
    """Check and warn about large documentation files."""

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize warning system.

        Args:
            base_path: Base path for project. Defaults to current directory.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"
        self.module_path = self.memory_path / "modules" / "memory-system"

    def check_sizes(self) -> List[Tuple[str, int, int]]:
        """
        Check file sizes against thresholds.

        Returns:
            List of (filename, current_lines, threshold) for files exceeding threshold
        """
        from ..utils.config import Config

        warnings = []
        config = Config()

        # Check if warnings are enabled
        if not config.get("modules.warn_on_record", True):
            return warnings

        # Check decisions.md
        decisions_path = self.module_path / "decisions.md"
        if decisions_path.exists():
            lines = len(decisions_path.read_text(encoding="utf-8").splitlines())
            threshold = config.get("modules.warn_size_decisions", 500)

            if lines > threshold:
                warnings.append(("decisions.md", lines, threshold))

        # Check current.md
        current_path = self.module_path / "current.md"
        if current_path.exists():
            lines = len(current_path.read_text(encoding="utf-8").splitlines())
            threshold = config.get("modules.warn_size_current", 300)

            if lines > threshold:
                warnings.append(("current.md", lines, threshold))

        return warnings

    def format_warning(self, warnings: List[Tuple[str, int, int]]) -> str:
        """
        Format warnings for display.

        Args:
            warnings: List of (filename, current_lines, threshold)

        Returns:
            Formatted warning string (empty if no warnings)
        """
        if not warnings:
            return ""

        output = []

        for filename, lines, threshold in warnings:
            output.append(f"[yellow]⚠️  {filename} exceeds {threshold} lines (current: {lines})[/yellow]")

            if filename == "decisions.md":
                # Detect current phase
                current_phase = self._detect_current_phase()
                if current_phase:
                    output.append(f"[dim]💡 Consider: marchive decisions --phase {current_phase - 1}[/dim]")
                else:
                    output.append(f"[dim]💡 Consider: marchive decisions --phase N[/dim]")

            elif filename == "current.md":
                # Detect current phase
                current_phase = self._detect_current_phase()
                if current_phase:
                    output.append(f"[dim]💡 Consider: marchive current --phase {current_phase}[/dim]")
                else:
                    output.append(f"[dim]💡 Consider: marchive current --phase N[/dim]")

        return "\n".join(output)

    def _detect_current_phase(self) -> Optional[int]:
        """
        Detect current phase from decisions.md.

        Returns:
            Current phase number or None if cannot detect
        """
        decisions_path = self.module_path / "decisions.md"

        if not decisions_path.exists():
            return None

        try:
            content = decisions_path.read_text(encoding="utf-8")

            # Look for "Recent decisions for Phase N"
            match = re.search(r'Recent decisions for Phase (\d+)', content)
            if match:
                return int(match.group(1))

            # Look for highest decision number
            decision_numbers = re.findall(r'\*\*결정 #(\d+)\*\*', content)
            if decision_numbers:
                max_decision = max(int(n) for n in decision_numbers)

                # Heuristic: map decision number to phase
                if max_decision <= 23:
                    return 4
                elif max_decision <= 28:
                    return 5
                else:
                    return 6

        except Exception:
            pass

        return None
