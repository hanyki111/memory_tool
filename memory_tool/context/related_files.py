"""Parser for Related Files section in module current.md files."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class PathEntry:
    """Single path entry with metadata."""

    path: str
    line_number: int
    category: str = "other"


@dataclass
class RelatedFiles:
    """Parsed Related Files data from a module."""

    source: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)
    docs: List[str] = field(default_factory=list)
    other: List[str] = field(default_factory=list)

    # Raw data for non-standard categories
    raw: Dict[str, List[str]] = field(default_factory=dict)

    # Metadata
    format_type: str = "none"  # "standard", "legacy", "none"

    # Line number tracking: path -> line_number
    line_numbers: Dict[str, int] = field(default_factory=dict)

    def all_paths(self) -> List[str]:
        """Get all paths from all categories."""
        paths = []
        paths.extend(self.source)
        paths.extend(self.tests)
        paths.extend(self.docs)
        paths.extend(self.other)
        return paths

    def all_entries(self) -> List[PathEntry]:
        """Get all paths as PathEntry objects with line numbers."""
        entries = []
        for path in self.source:
            entries.append(PathEntry(
                path=path,
                line_number=self.line_numbers.get(path, 0),
                category="source"
            ))
        for path in self.tests:
            entries.append(PathEntry(
                path=path,
                line_number=self.line_numbers.get(path, 0),
                category="tests"
            ))
        for path in self.docs:
            entries.append(PathEntry(
                path=path,
                line_number=self.line_numbers.get(path, 0),
                category="docs"
            ))
        for path in self.other:
            entries.append(PathEntry(
                path=path,
                line_number=self.line_numbers.get(path, 0),
                category="other"
            ))
        return entries

    def get_line_number(self, path: str) -> int:
        """Get line number for a specific path."""
        return self.line_numbers.get(path, 0)

    def is_empty(self) -> bool:
        """Check if no paths were found."""
        return len(self.all_paths()) == 0


class RelatedFilesParser:
    """Parse Related Files section from module current.md files.

    Supports two formats:
    1. Standard format (new):
       ## 📂 Related Files
       - **Source:** `path/to/source/`
       - **Tests:** `path/to/tests/`

    2. Legacy format:
       **Key Files:**
       - `path/to/file.py`
       - `path/to/another.py`
    """

    # Standard section headers
    STANDARD_HEADERS = [
        r"^##\s*📂\s*Related\s+Files",
        r"^##\s*Related\s+Files",
    ]

    # Legacy section patterns
    LEGACY_PATTERNS = [
        r"^\*\*Key\s+Files:?\*\*",
        r"^###?\s*Key\s+Files",
    ]

    # Standard category patterns (case-insensitive)
    STANDARD_CATEGORIES = {
        "source": ["source", "src", "code"],
        "tests": ["tests", "test", "testing"],
        "docs": ["docs", "documentation", "doc"],
    }

    # Pattern to extract category and path from a line
    # Matches: - **Category:** `path` or - **Category:** path
    CATEGORY_LINE_PATTERN = re.compile(
        r"^\s*[-*]\s*\*\*([^:*]+):?\*\*:?\s*`?([^`\n]+)`?",
        re.IGNORECASE
    )

    # Pattern to extract just a path (for legacy format)
    # Matches: - `path` or - path
    PATH_LINE_PATTERN = re.compile(
        r"^\s*[-*]\s*`([^`]+)`|^\s*[-*]\s*([^\s*`][^\n]*\.py\b[^\n]*)",
        re.IGNORECASE
    )

    def parse(self, content: str) -> RelatedFiles:
        """Parse Related Files from content.

        Args:
            content: Full content of current.md file

        Returns:
            RelatedFiles object with parsed paths
        """
        # Try standard format first
        result = self._parse_standard(content)
        if not result.is_empty():
            result.format_type = "standard"
            return result

        # Fall back to legacy format
        result = self._parse_legacy(content)
        if not result.is_empty():
            result.format_type = "legacy"
            return result

        # No Related Files found
        return RelatedFiles(format_type="none")

    def _parse_standard(self, content: str) -> RelatedFiles:
        """Parse standard Related Files format."""
        result = RelatedFiles()

        # Find the Related Files section
        section_content, section_start_line = self._extract_section(
            content, self.STANDARD_HEADERS
        )
        if not section_content:
            return result

        # Parse each line
        for line_offset, line in enumerate(section_content.split("\n")):
            match = self.CATEGORY_LINE_PATTERN.match(line)
            if match:
                category = match.group(1).strip().lower()
                path = match.group(2).strip()

                # Clean up path (remove trailing backticks, etc.)
                path = path.rstrip("`").strip()

                if not path:
                    continue

                # Calculate actual line number (1-based)
                actual_line = section_start_line + line_offset

                # Categorize
                categorized = False
                for std_cat, aliases in self.STANDARD_CATEGORIES.items():
                    if category in aliases:
                        getattr(result, std_cat).append(path)
                        result.line_numbers[path] = actual_line
                        categorized = True
                        break

                if not categorized:
                    # Put in "other" category
                    result.other.append(path)
                    result.line_numbers[path] = actual_line
                    # Also store in raw with original category name
                    if category not in result.raw:
                        result.raw[category] = []
                    result.raw[category].append(path)

        return result

    def _parse_legacy(self, content: str) -> RelatedFiles:
        """Parse legacy Key Files format."""
        result = RelatedFiles()

        # Find the Key Files section
        section_content, section_start_line = self._extract_section(
            content, self.LEGACY_PATTERNS
        )
        if not section_content:
            return result

        # Parse each line for paths
        for line_offset, line in enumerate(section_content.split("\n")):
            match = self.PATH_LINE_PATTERN.match(line)
            if match:
                # Get path from either group
                path = match.group(1) or match.group(2)
                if path:
                    path = path.strip()
                    # Calculate actual line number (1-based)
                    actual_line = section_start_line + line_offset
                    # Legacy format goes to "source" by default
                    result.source.append(path)
                    result.line_numbers[path] = actual_line

        return result

    def _extract_section(
        self,
        content: str,
        header_patterns: List[str]
    ) -> Tuple[Optional[str], int]:
        """Extract a section from content based on header patterns.

        Args:
            content: Full content
            header_patterns: Regex patterns to match section header

        Returns:
            Tuple of (section content excluding header, start line number)
            Line numbers are 1-based for editor compatibility.
        """
        lines = content.split("\n")

        # Find section start
        start_idx = None
        for i, line in enumerate(lines):
            for pattern in header_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    start_idx = i + 1
                    break
            if start_idx is not None:
                break

        if start_idx is None:
            return None, 0

        # Find section end (next ## header or ---)
        end_idx = len(lines)
        for i in range(start_idx, len(lines)):
            line = lines[i].strip()
            # Stop at next major section
            if line.startswith("##") or line == "---":
                end_idx = i
                break

        # Extract section content
        section_lines = lines[start_idx:end_idx]
        # Return 1-based line number for the start of content
        return "\n".join(section_lines), start_idx + 1

    def parse_file(self, file_path: Path) -> RelatedFiles:
        """Parse Related Files from a file.

        Args:
            file_path: Path to current.md file

        Returns:
            RelatedFiles object
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            return self.parse(content)
        except Exception:
            return RelatedFiles(format_type="none")


def get_module_related_files(
    module_path: Path,
    current_file: str = "current.md"
) -> RelatedFiles:
    """Convenience function to get Related Files from a module directory.

    Args:
        module_path: Path to module directory
        current_file: Name of the current status file

    Returns:
        RelatedFiles object
    """
    parser = RelatedFilesParser()
    current_path = module_path / current_file

    if current_path.exists():
        return parser.parse_file(current_path)

    return RelatedFiles(format_type="none")
