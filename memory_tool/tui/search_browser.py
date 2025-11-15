"""Interactive TUI search browser for memory_tool.

Provides a rich terminal interface for searching and browsing timeline entries.
"""

import re
from pathlib import Path
from typing import Optional, List

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import (
    Header,
    Footer,
    Input,
    DataTable,
    Static,
    Label,
)
from textual.reactive import reactive
from rich.text import Text
from rich.panel import Panel


class SearchResultsTable(DataTable):
    """DataTable for displaying search results."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]


class DetailPanel(Static):
    """Panel for displaying detailed information about selected entry."""

    visible = reactive(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Detail View"

    def watch_visible(self, visible: bool):
        """Handle visibility changes."""
        self.display = visible

    def show_entry(self, entry: dict):
        """Display detailed entry information."""
        content = Text()
        content.append("Date: ", style="bold cyan")
        content.append(f"{entry.get('date', 'Unknown')}\n\n", style="cyan")

        content.append("Content:\n", style="bold green")
        content.append(f"{entry.get('content', '')}\n\n", style="white")

        if "file" in entry:
            content.append("File: ", style="bold yellow")
            content.append(f"{entry['file']}", style="yellow")
            if "line" in entry:
                content.append(f" (line {entry['line']})\n", style="dim yellow")
            else:
                content.append("\n", style="yellow")

        if "score" in entry:
            content.append("\nScore: ", style="bold magenta")
            content.append(f"{entry['score']:.4f}", style="magenta")

        self.update(content)
        self.visible = True


class SearchBrowser(App):
    """Interactive TUI search browser for memory_tool.

    Features:
    - Search input with live filtering
    - Results table with keyboard navigation
    - Detail view for selected entries
    - Vim-style keybindings (j/k for navigation)

    Keybindings:
    - /: Focus search input
    - Enter: Show detail view
    - Esc: Close detail view / exit search input
    - q: Quit application
    - j/k: Navigate results (Vim-style)
    - Up/Down: Navigate results (arrow keys)
    """

    CSS = """
    Screen {
        layout: vertical;
    }

    #search-container {
        height: 3;
        padding: 0 1;
    }

    #results-table {
        height: 1fr;
    }

    DetailPanel {
        height: 1fr;
        border: solid cyan;
        padding: 1 2;
        overflow-y: auto;
    }

    #status-bar {
        height: 1;
        background: $boost;
        color: $text;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("/", "focus_search", "Search", show=True),
        Binding("q", "quit", "Quit", show=True),
        Binding("escape", "close_detail", "Close", show=False),
        Binding("enter", "show_detail", "Detail", show=True),
    ]

    def __init__(
        self,
        base_path: Optional[Path] = None,
        initial_query: Optional[str] = None,
        **kwargs
    ):
        """Initialize search browser.

        Args:
            base_path: Base path for project (parent of .memory/)
            initial_query: Initial search query to execute
        """
        super().__init__(**kwargs)
        self.base_path = base_path or self._find_project_root()
        self.initial_query = initial_query
        self.current_results: List[dict] = []
        self.title = "Memory Tool - Search Browser"

    def _find_project_root(self) -> Path:
        """Find project root (parent of .memory/) directory."""
        current = Path.cwd()
        while current != current.parent:
            memory_path = current / ".memory"
            if memory_path.exists() and memory_path.is_dir():
                return current  # Return project root, not .memory
            current = current.parent

        # Default to current directory
        return Path.cwd()

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Container(id="search-container"):
            yield Input(
                placeholder="Enter search query...",
                id="search-input",
                value=self.initial_query or ""
            )

        yield SearchResultsTable(id="results-table", cursor_type="row")
        yield DetailPanel(id="detail-panel")

        with Horizontal(id="status-bar"):
            yield Label("Press / to search, Enter for details, q to quit", id="status-text")

        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount."""
        # Setup results table
        table = self.query_one("#results-table", SearchResultsTable)
        table.add_columns("Date", "Time", "Content", "Score")
        table.cursor_type = "row"
        table.zebra_stripes = True

        # Focus search input
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

        # Execute initial query if provided
        if self.initial_query:
            self.perform_search(self.initial_query)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle search input submission."""
        if event.input.id == "search-input":
            query = event.value.strip()
            if query:
                self.perform_search(query)
                # Focus results table
                table = self.query_one("#results-table", SearchResultsTable)
                table.focus()

    def perform_search(self, query: str) -> None:
        """Perform search and update results table.

        Args:
            query: Search query
        """
        from memory_tool.core.search import MemorySearcher, SearchResult

        # Update status
        self.update_status(f"Searching for: {query}")

        try:
            # Create searcher and perform search
            searcher = MemorySearcher(base_path=self.base_path)

            # search() returns Dict[str, List[SearchResult]]
            results_dict = searcher.search(query, scope="local", max_results=100)

            # Flatten results from all groups
            all_results = []
            for group_name, group_results in results_dict.items():
                all_results.extend(group_results)

            # Store results (convert to dict for compatibility)
            self.current_results = []
            for result in all_results:
                self.current_results.append({
                    "file": str(result.file_path),
                    "line": result.line_number,
                    "content": result.line_content,
                    "context": result.match_context,
                    "score": result.score,
                    "date": result.date.strftime("%Y-%m-%d") if result.date else ""
                })

            # Update table
            table = self.query_one("#results-table", SearchResultsTable)
            table.clear()

            for result in self.current_results:
                # Extract date and time from result
                date_str = result.get("date", "")
                time_str = ""

                # Try to extract time from content (format: HH:MM | content)
                content = result.get("content", "")
                if "|" in content:
                    parts = content.split("|", 1)
                    if len(parts) == 2:
                        time_part = parts[0].strip()
                        # Check if it looks like a time
                        if re.match(r'^\d{1,2}:\d{2}$', time_part):
                            time_str = time_part
                            content = parts[1].strip()

                # Truncate content if too long
                if len(content) > 80:
                    content = content[:77] + "..."

                # Get score
                score = result.get("score", 0.0)
                score_str = f"{score:.2f}" if score > 0 else ""

                table.add_row(
                    date_str,
                    time_str,
                    content,
                    score_str,
                )

            # Update status
            self.update_status(f"Found {len(self.current_results)} results for: {query}")

        except Exception as e:
            self.update_status(f"Search error: {str(e)}", error=True)

    def update_status(self, message: str, error: bool = False) -> None:
        """Update status bar message.

        Args:
            message: Status message
            error: Whether this is an error message
        """
        status_label = self.query_one("#status-text", Label)
        if error:
            status_label.update(f"[bold red]{message}[/]")
        else:
            status_label.update(message)

    def action_focus_search(self) -> None:
        """Focus search input."""
        search_input = self.query_one("#search-input", Input)
        search_input.focus()

        # Hide detail panel
        detail_panel = self.query_one("#detail-panel", DetailPanel)
        detail_panel.visible = False

    def action_show_detail(self) -> None:
        """Show detail view for selected entry."""
        table = self.query_one("#results-table", SearchResultsTable)

        if table.cursor_row is not None and table.cursor_row < len(self.current_results):
            entry = self.current_results[table.cursor_row]
            detail_panel = self.query_one("#detail-panel", DetailPanel)
            detail_panel.show_entry(entry)

    def action_close_detail(self) -> None:
        """Close detail panel."""
        detail_panel = self.query_one("#detail-panel", DetailPanel)
        if detail_panel.visible:
            detail_panel.visible = False
        else:
            # If detail not visible, blur search input
            search_input = self.query_one("#search-input", Input)
            if search_input.has_focus:
                table = self.query_one("#results-table", SearchResultsTable)
                table.focus()


def run_search_browser(
    base_path: Optional[Path] = None,
    initial_query: Optional[str] = None
) -> None:
    """Run the search browser TUI application.

    Args:
        base_path: Base path for project (parent of .memory/)
        initial_query: Initial search query to execute
    """
    app = SearchBrowser(base_path=base_path, initial_query=initial_query)
    app.run()
