"""Enhanced formatting for search results."""

import re
import sys
from pathlib import Path
from typing import List, Optional, Dict
from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from ..core.search import SearchResult


def deduplicate_results(
    results: List[SearchResult],
    context_lines: int = 1
) -> List[SearchResult]:
    """
    Deduplicate search results that have overlapping line numbers.

    When searching with context lines, adjacent matches can produce
    overlapping results. This function merges such results.

    Args:
        results: List of search results
        context_lines: Number of context lines used in search

    Returns:
        Deduplicated list of results
    """
    if not results:
        return results

    # Group by file path
    by_file: Dict[Path, List[SearchResult]] = {}
    for r in results:
        if r.file_path not in by_file:
            by_file[r.file_path] = []
        by_file[r.file_path].append(r)

    deduplicated = []

    for file_path, file_results in by_file.items():
        # Sort by line number
        file_results.sort(key=lambda r: r.line_number)

        # Merge overlapping results
        merged = []
        for result in file_results:
            if not merged:
                merged.append(result)
                continue

            last = merged[-1]
            # Check if this result overlaps with the last one
            # Two results overlap if their line numbers are within 2*context_lines+1
            threshold = 2 * context_lines + 1
            if result.line_number - last.line_number <= threshold:
                # Merge: keep the one with better score, or first one if equal
                if result.score > last.score:
                    merged[-1] = result
                # Otherwise keep the existing one
            else:
                merged.append(result)

        deduplicated.extend(merged)

    # Sort by score (descending), then by file path and line number
    deduplicated.sort(key=lambda r: (-r.score, str(r.file_path), r.line_number))

    return deduplicated


class ResultFormatter:
    """Format search results with rich output."""

    def __init__(self, base_path: Path):
        """
        Initialize result formatter.

        Args:
            base_path: Base path for relative path display
        """
        self.base_path = base_path
        # Configure console for Windows compatibility
        # safe_box=False prevents box-drawing character issues
        # legacy_windows=False uses modern console features
        self.console = Console(safe_box=False, legacy_windows=False)

    def format_result(
        self,
        result: SearchResult,
        query: str = "",
        show_score: bool = False,
        show_context: bool = True,
        context_lines: int = 2,
        highlight: bool = True,
    ) -> str:
        """
        Format a single search result.

        Args:
            result: Search result
            query: Original query (for highlighting)
            show_score: Show relevance score
            show_context: Show context lines
            context_lines: Number of context lines
            highlight: Enable highlighting

        Returns:
            Formatted string
        """
        lines = []

        # File path and line number
        try:
            rel_path = result.file_path.relative_to(self.base_path)
        except ValueError:
            rel_path = result.file_path

        location = f"{rel_path}:{result.line_number}"

        # Add source prefix for KB results
        source_prefix = ""
        if result.source == "kb" and result.origin_project:
            source_prefix = f"[magenta][KB: {result.origin_project}][/magenta] "
        elif result.source == "kb":
            source_prefix = "[magenta][KB][/magenta] "

        # Add score if requested
        if show_score:
            lines.append(f"{source_prefix}[cyan]Score: {result.score:.2f}[/cyan] | {location}")
        else:
            lines.append(f"{source_prefix}[bold]{location}[/bold]")

        # Add date if available
        if result.date:
            date_str = result.date.strftime("%Y-%m-%d %H:%M")
            lines.append(f"[dim]{date_str}[/dim]")

        # Add content
        if show_context:
            content = result.match_context
        else:
            content = result.line_content

        # Highlight matches
        if highlight and query:
            content = self._highlight_matches(content, query)

        # Indent content
        for line in content.split("\n"):
            lines.append(f"  {line}")

        return "\n".join(lines)

    def _highlight_matches(self, text: str, query: str) -> str:
        """
        Highlight matched terms in text.

        Args:
            text: Text to highlight
            query: Search query

        Returns:
            Text with highlighted matches
        """
        # Extract query terms
        terms = re.findall(r'\w+', query.lower())

        # Highlight each term
        for term in terms:
            # Case-insensitive matching
            pattern = re.compile(re.escape(term), re.IGNORECASE)

            # Replace with highlighted version
            def replacer(match):
                return f"[bold yellow]{match.group()}[/bold yellow]"

            text = pattern.sub(replacer, text)

        return text

    def format_results(
        self,
        results: List[SearchResult],
        query: str = "",
        show_score: bool = False,
        show_context: bool = True,
        context_lines: int = 2,
        highlight: bool = True,
        show_summary: bool = False,
    ) -> str:
        """
        Format all search results.

        Args:
            results: List of search results
            query: Original query
            show_score: Show relevance scores
            show_context: Show context lines
            context_lines: Number of context lines
            highlight: Enable highlighting
            show_summary: Show summary statistics

        Returns:
            Formatted string
        """
        if not results:
            return "[yellow]No results found.[/yellow]"

        lines = []

        # Summary statistics
        if show_summary:
            summary = self._format_summary(results)
            lines.append(summary)
            lines.append("")

        # Format each result
        for i, result in enumerate(results):
            if i > 0:
                lines.append("")  # Blank line between results

            formatted = self.format_result(
                result,
                query,
                show_score,
                show_context,
                context_lines,
                highlight,
            )
            lines.append(formatted)

        return "\n".join(lines)

    def _format_summary(self, results: List[SearchResult]) -> str:
        """
        Format summary statistics.

        Args:
            results: Search results

        Returns:
            Formatted summary string
        """
        lines = []

        # Total count
        lines.append(f"[bold]Found {len(results)} result(s)[/bold]")

        # Unique files
        unique_files = len(set(r.file_path for r in results))
        lines.append(f"Files: {unique_files}")

        # Date range (if dates available)
        dated_results = [r for r in results if r.date is not None]
        if dated_results:
            dates = [r.date for r in dated_results]
            min_date = min(dates).strftime("%Y-%m-%d")
            max_date = max(dates).strftime("%Y-%m-%d")
            lines.append(f"Date range: {min_date} to {max_date}")

        # Average score
        if any(r.score != 1.0 for r in results):
            avg_score = sum(r.score for r in results) / len(results)
            lines.append(f"Avg score: {avg_score:.2f}")

        return "\n".join(lines)

    def _sanitize_for_console(self, text: str) -> str:
        """
        Sanitize text for Windows console output.

        Removes or replaces characters that may cause encoding issues.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text safe for console output
        """
        # On Windows, remove emojis and other problematic Unicode characters
        if sys.platform == "win32":
            # Remove emojis (U+1F300 to U+1F9FF)
            text = re.sub(r'[\U0001F300-\U0001F9FF]+', '', text)
            # Remove other high Unicode characters that cp949 can't handle
            text = text.encode('cp949', errors='ignore').decode('cp949', errors='ignore')
        return text

    def print_results(
        self,
        results: List[SearchResult],
        query: str = "",
        show_score: bool = False,
        show_context: bool = True,
        context_lines: int = 2,
        highlight: bool = True,
        show_summary: bool = False,
    ):
        """
        Print formatted results to console.

        Args:
            results: Search results
            query: Original query
            show_score: Show relevance scores
            show_context: Show context lines
            context_lines: Number of context lines
            highlight: Enable highlighting
            show_summary: Show summary statistics
        """
        formatted = self.format_results(
            results,
            query,
            show_score,
            show_context,
            context_lines,
            highlight,
            show_summary,
        )

        # Sanitize content for console output (handles Windows encoding issues)
        formatted = self._sanitize_for_console(formatted)

        try:
            self.console.print(formatted)
        except UnicodeEncodeError:
            # Fallback: print without rich formatting
            print(formatted)
