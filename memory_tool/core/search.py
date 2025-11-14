"""Search functionality for timeline and modules."""

import re
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import date, datetime
from fnmatch import fnmatch

# Import db for SQLite search (optional)
try:
    from ..db import SQLiteSearcher, IndexManager
    SQLITE_AVAILABLE = True
except Exception:
    SQLITE_AVAILABLE = False


@dataclass
class SearchResult:
    """A single search result."""
    file_path: Path
    line_number: int
    line_content: str
    match_context: str  # Surrounding context
    score: float = 1.0  # Relevance score (default: 1.0)
    date: Optional[datetime] = None  # Document date (for timeline files)


class SearchError(Exception):
    """Base exception for search operations."""
    pass


class MemorySearcher:
    """Searcher for memory content."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize memory searcher.

        Args:
            base_path: Base path for project. Defaults to current directory.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"

        # Load config
        from memory_tool.utils.config import Config
        config_loader = Config()
        config = config_loader.load()

        # Get search settings
        self.exclude_patterns = config_loader.get("search.exclude_patterns", [])
        self.max_file_size = config_loader.get("search.max_file_size", 10 * 1024 * 1024)

    def is_initialized(self) -> bool:
        """Check if .memory/ exists.

        Returns:
            True if .memory/ exists
        """
        return self.memory_path.exists()

    def _extract_date_from_path(self, path: Path) -> Optional[date]:
        """Extract date from timeline file path.

        Args:
            path: File path (e.g., .memory/timeline/2025-11/14.md)

        Returns:
            Date object or None if not a timeline file
        """
        # Check if it's in timeline directory
        parts = path.parts
        if "timeline" not in parts:
            return None

        try:
            # Find timeline index
            timeline_idx = parts.index("timeline")

            # Next part should be YYYY-MM
            if timeline_idx + 1 >= len(parts):
                return None
            year_month = parts[timeline_idx + 1]

            # File name should be DD.md
            if timeline_idx + 2 >= len(parts):
                return None
            day_file = parts[timeline_idx + 2]

            # Parse YYYY-MM
            year, month = year_month.split("-")

            # Parse DD from DD.md
            day = day_file.replace(".md", "")

            return date(int(year), int(month), int(day))
        except (ValueError, IndexError):
            return None

    def _is_in_date_range(
        self,
        path: Path,
        from_date: Optional[date],
        to_date: Optional[date],
    ) -> bool:
        """Check if timeline file is within date range.

        Args:
            path: File path
            from_date: Start date (inclusive)
            to_date: End date (inclusive)

        Returns:
            True if within range or not a timeline file
        """
        # If no date filter, include all
        if from_date is None and to_date is None:
            return True

        # Extract date from path
        file_date = self._extract_date_from_path(path)

        # If not a timeline file, include it
        if file_date is None:
            return True

        # Check range
        if from_date and file_date < from_date:
            return False
        if to_date and file_date > to_date:
            return False

        return True

    def _should_exclude(self, path: Path, base_path: Path) -> bool:
        """Check if path should be excluded based on patterns.

        Args:
            path: File path to check
            base_path: Base path for relative matching

        Returns:
            True if should exclude
        """
        if not self.exclude_patterns:
            return False

        try:
            # Get relative path for pattern matching
            rel_path = path.relative_to(base_path)
            rel_path_str = str(rel_path).replace("\\", "/")  # Unix-style for patterns

            # Check against each pattern
            for pattern in self.exclude_patterns:
                if fnmatch(rel_path_str, pattern):
                    return True
                # Also check if any parent directory matches
                if fnmatch(path.name, pattern):
                    return True

            return False
        except (ValueError, Exception):
            return False

    def get_search_paths(
        self,
        scope: str = "local",
        with_kb: bool = False,
    ) -> List[Path]:
        """Get paths to search based on scope.

        Args:
            scope: Search scope ("local", "kb", "all")
            with_kb: Include KB in local search

        Returns:
            List of paths to search
        """
        paths = []

        # Local .memory/
        if scope in ("local", "all"):
            if self.memory_path.exists():
                paths.append(self.memory_path)

        # Knowledge base
        if scope == "kb" or with_kb or scope == "all":
            kb_lock = self.memory_path / "kb.lock"
            if kb_lock.exists():
                kb_path = kb_lock.read_text(encoding="utf-8").strip()
                kb_path_obj = Path(kb_path).expanduser()
                if kb_path_obj.exists():
                    paths.append(kb_path_obj)

        return paths

    def search_file(
        self,
        file_path: Path,
        pattern: str,
        case_sensitive: bool = False,
        context_lines: int = 0,
    ) -> List[SearchResult]:
        """Search a single file for pattern.

        Args:
            file_path: Path to file to search
            pattern: Search pattern (regex)
            case_sensitive: Whether to match case
            context_lines: Number of context lines to include

        Returns:
            List of search results
        """
        results = []

        # Check file size
        try:
            if file_path.stat().st_size > self.max_file_size:
                # Skip files larger than limit
                return results
        except Exception:
            return results

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines()
        except Exception:
            # Skip files that can't be read
            return results

        # Compile regex
        flags = 0 if case_sensitive else re.IGNORECASE
        try:
            regex = re.compile(pattern, flags)
        except re.error:
            # If regex is invalid, try literal search
            regex = re.compile(re.escape(pattern), flags)

        # Search each line
        for i, line in enumerate(lines):
            if regex.search(line):
                # Get context
                start = max(0, i - context_lines)
                end = min(len(lines), i + context_lines + 1)
                context = "\n".join(lines[start:end])

                results.append(
                    SearchResult(
                        file_path=file_path,
                        line_number=i + 1,
                        line_content=line,
                        match_context=context,
                    )
                )

        return results

    def search_directory(
        self,
        directory: Path,
        pattern: str,
        case_sensitive: bool = False,
        context_lines: int = 0,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[SearchResult]:
        """Search all markdown files in directory recursively.

        Args:
            directory: Directory to search
            pattern: Search pattern
            case_sensitive: Whether to match case
            context_lines: Number of context lines
            from_date: Start date filter (for timeline files)
            to_date: End date filter (for timeline files)

        Returns:
            List of all search results
        """
        results = []

        # Find all .md files
        for md_file in directory.rglob("*.md"):
            # Skip .gitkeep and other hidden files
            if md_file.name.startswith("."):
                continue

            # Check exclude patterns
            if self._should_exclude(md_file, directory):
                continue

            # Check date range (for timeline files)
            if not self._is_in_date_range(md_file, from_date, to_date):
                continue

            file_results = self.search_file(
                md_file,
                pattern,
                case_sensitive,
                context_lines,
            )
            results.extend(file_results)

        return results

    def search(
        self,
        query: str,
        scope: str = "local",
        with_kb: bool = False,
        case_sensitive: bool = False,
        context_lines: int = 1,
        max_results: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        use_index: bool = True,
    ) -> Dict[str, List[SearchResult]]:
        """Search memory for query.

        Args:
            query: Search query (regex pattern)
            scope: Search scope ("local", "kb", "all")
            with_kb: Include KB in local search
            case_sensitive: Whether to match case
            context_lines: Number of context lines
            max_results: Maximum number of results (None = unlimited)
            from_date: Start date filter (for timeline files)
            to_date: End date filter (for timeline files)
            use_index: Whether to use SQLite index (default True)

        Returns:
            Dictionary mapping source paths to results

        Raises:
            SearchError: If search fails
        """
        if not self.is_initialized() and scope != "kb":
            raise SearchError(
                f".memory/ not found at {self.memory_path}. "
                f"Run 'minit' to initialize."
            )

        # Try SQLite search first (if enabled and available)
        if use_index and SQLITE_AVAILABLE and scope == "local" and not with_kb:
            if SQLiteSearcher.available(self.memory_path):
                try:
                    # Check if index is fresh
                    indexer = IndexManager(self.memory_path)
                    if not indexer.is_index_fresh():
                        # Rebuild index if stale
                        indexer.index_all()

                    # Perform SQLite search
                    searcher = SQLiteSearcher(self.memory_path)

                    # Convert dates to strings for SQLite
                    date_from_str = from_date.isoformat() if from_date else None
                    date_to_str = to_date.isoformat() if to_date else None

                    sql_results = searcher.search(
                        query,
                        date_from=date_from_str,
                        date_to=date_to_str,
                        max_results=max_results,
                    )

                    # Convert SQLite results to SearchResult format
                    if sql_results:
                        all_results = {}
                        search_results = []

                        for sql_result in sql_results:
                            file_path = self.memory_path / sql_result["file_path"]

                            # Parse content to find line number
                            try:
                                with open(file_path, "r", encoding="utf-8") as f:
                                    lines = f.readlines()

                                content = sql_result["content"]
                                line_number = 1

                                # Find matching line
                                for i, line in enumerate(lines):
                                    if content.strip() in line:
                                        line_number = i + 1
                                        break

                                # Get context
                                start = max(0, line_number - 1 - context_lines)
                                end = min(len(lines), line_number + context_lines)
                                context = "".join(lines[start:end])

                                search_results.append(
                                    SearchResult(
                                        file_path=file_path,
                                        line_number=line_number,
                                        line_content=content,
                                        match_context=context,
                                    )
                                )
                            except Exception:
                                # Skip files we can't read
                                continue

                        if search_results:
                            all_results[str(self.memory_path)] = search_results
                            return all_results

                except Exception:
                    # Fall through to file-based search on any error
                    pass

        # Get search paths
        search_paths = self.get_search_paths(scope, with_kb)

        if not search_paths:
            raise SearchError("No search paths available. Check .memory/ and kb.lock.")

        # Search each path
        all_results = {}
        total_count = 0

        for path in search_paths:
            results = self.search_directory(
                path,
                query,
                case_sensitive,
                context_lines,
                from_date,
                to_date,
            )

            if results:
                # Limit results if needed
                if max_results:
                    remaining = max_results - total_count
                    if remaining <= 0:
                        break
                    results = results[:remaining]

                all_results[str(path)] = results
                total_count += len(results)

        return all_results

    def format_results(
        self,
        results: Dict[str, List[SearchResult]],
        show_context: bool = True,
    ) -> str:
        """Format search results for display.

        Args:
            results: Search results by source
            show_context: Whether to show context

        Returns:
            Formatted string
        """
        if not results:
            return "No results found."

        lines = []
        total_count = sum(len(r) for r in results.values())

        lines.append(f"Found {total_count} result(s)\n")

        for source, source_results in results.items():
            lines.append(f"\n## {source}")
            lines.append(f"{len(source_results)} match(es)\n")

            for result in source_results:
                # Relative path
                try:
                    rel_path = result.file_path.relative_to(self.base_path)
                except ValueError:
                    rel_path = result.file_path

                lines.append(f"  {rel_path}:{result.line_number}")

                if show_context:
                    # Indent context
                    context_lines = result.match_context.split("\n")
                    for ctx_line in context_lines:
                        # Remove problematic characters for Windows console
                        safe_line = self._sanitize_output(ctx_line)
                        lines.append(f"    {safe_line}")
                else:
                    safe_line = self._sanitize_output(result.line_content)
                    lines.append(f"    {safe_line}")

                lines.append("")  # Empty line between results

        return "\n".join(lines)

    def _sanitize_output(self, text: str) -> str:
        """Remove characters that cause issues with Windows console.

        Args:
            text: Input text

        Returns:
            Sanitized text
        """
        # Replace common problematic characters
        replacements = {
            '⭐': '*',
            '✅': '[OK]',
            '❌': '[X]',
            '⚠': '[!]',
            '🎯': '[TARGET]',
            '🚀': '[ROCKET]',
            '📍': '[PIN]',
            '📚': '[BOOKS]',
            '🔄': '[CYCLE]',
            '⚡': '[BOLT]',
        }

        result = text
        for emoji, replacement in replacements.items():
            result = result.replace(emoji, replacement)

        return result
