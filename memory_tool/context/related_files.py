"""Parser for the Related Files section of a module document."""

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
    """Parse Related Files sections from a module document.

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

        # Every matching section, not only the first. Consolidating a module
        # into a single document concatenates the sections its former files
        # each carried, so stopping at the first one drops most of the paths.
        for section_content, section_start_line in self._extract_sections(
            content, self.STANDARD_HEADERS
        ):
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
                            self._add_path(result, std_cat, path, actual_line)
                            categorized = True
                            break

                    if not categorized:
                        # Put in "other" category
                        if self._add_path(result, "other", path, actual_line):
                            # Also store in raw with original category name
                            if category not in result.raw:
                                result.raw[category] = []
                            result.raw[category].append(path)

        return result

    @staticmethod
    def _add_path(
        result: RelatedFiles,
        category: str,
        path: str,
        line_number: int,
    ) -> bool:
        """Record a path once, keeping the line number of its first mention.

        Returns:
            True if the path was new, False if it had already been recorded.
        """
        if path in result.line_numbers:
            return False

        getattr(result, category).append(path)
        result.line_numbers[path] = line_number
        return True

    def _parse_legacy(self, content: str) -> RelatedFiles:
        """Parse legacy Key Files format."""
        result = RelatedFiles()

        # A consolidated document keeps one Key Files block per feature it
        # absorbed, so every block has to be read.
        for section_content, section_start_line in self._extract_sections(
            content, self.LEGACY_PATTERNS
        ):
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
                        self._add_path(result, "source", path, actual_line)

        return result

    def _extract_sections(
        self,
        content: str,
        header_patterns: List[str]
    ) -> List[Tuple[str, int]]:
        """Extract every section whose header matches one of the patterns.

        Args:
            content: Full content
            header_patterns: Regex patterns to match section header

        Returns:
            List of (section content excluding header, start line number)
            tuples, in document order. Line numbers are 1-based for editor
            compatibility.
        """
        lines = content.split("\n")
        sections = []

        for i, line in enumerate(lines):
            if not self._matches_header(line, header_patterns):
                continue

            start_idx = i + 1

            # Find section end (next ## header or ---)
            end_idx = len(lines)
            for j in range(start_idx, len(lines)):
                stripped = lines[j].strip()
                # Stop at next major section
                if stripped.startswith("##") or stripped == "---":
                    end_idx = j
                    break

            # Extract section content
            section_lines = lines[start_idx:end_idx]
            # Store a 1-based line number for the start of content
            sections.append(("\n".join(section_lines), start_idx + 1))

        return sections

    @staticmethod
    def _matches_header(line: str, header_patterns: List[str]) -> bool:
        """Check whether a line opens one of the wanted sections."""
        return any(
            re.match(pattern, line, re.IGNORECASE) for pattern in header_patterns
        )

    def parse_file(self, file_path: Path) -> RelatedFiles:
        """Parse Related Files from a file.

        Args:
            file_path: Path to the module document

        Returns:
            RelatedFiles object
        """
        try:
            content = file_path.read_text(encoding="utf-8")
            return self.parse(content)
        except Exception:
            return RelatedFiles(format_type="none")


#: Names a module document can take inside its own folder, in the order they
#: should be preferred. ``<folder>.md`` is the current single-file layout and is
#: resolved separately, because it is named after the folder rather than fixed.
MODULE_DOC_NAMES = ("current.md", "module.md")


def resolve_module_document(module_path: Path) -> Optional[Path]:
    """Find the markdown document that holds a module's Related Files.

    Three layouts are in use and all remain readable:
      1. ``<folder>/<folder>.md`` -- current single-file layout
      2. ``<folder>.md``          -- flat single file
      3. ``<folder>/current.md``  -- legacy multi-file layout

    Args:
        module_path: Either the module's folder or its document itself

    Returns:
        Path to the module document, or None when the module has none.
    """
    if module_path.is_file():
        return module_path

    if module_path.is_dir():
        encapsulated = module_path / f"{module_path.name}.md"
        if encapsulated.is_file():
            return encapsulated

        for doc_name in MODULE_DOC_NAMES:
            legacy = module_path / doc_name
            if legacy.is_file():
                return legacy

    # Appended rather than substituted: with_suffix would read a dot in the
    # module's own name as an extension and truncate it.
    flat = module_path.parent / f"{module_path.name}.md"
    if flat.is_file():
        return flat

    return None


def get_module_related_files(
    module_path: Path,
    current_file: Optional[str] = None
) -> RelatedFiles:
    """Convenience function to get Related Files from a module.

    Consolidating a module into one document leaves nothing named
    ``current.md`` behind, so the document is resolved by layout rather than by
    a fixed filename. Callers that pass the document itself are handled too.

    Args:
        module_path: Module folder, or the module document itself
        current_file: Explicit document name inside the folder, when the caller
            knows it. Defaults to resolving the layout.

    Returns:
        RelatedFiles object
    """
    parser = RelatedFilesParser()

    if current_file is not None:
        named_path = module_path / current_file
        if named_path.is_file():
            return parser.parse_file(named_path)
        return RelatedFiles(format_type="none")

    doc_path = resolve_module_document(module_path)
    if doc_path is not None:
        return parser.parse_file(doc_path)

    return RelatedFiles(format_type="none")
