"""Search mode for TUI browser."""

import re
from pathlib import Path
from typing import Optional, List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import (
    Input,
    DataTable,
    Static,
    Checkbox,
    Label,
)
from textual.reactive import reactive
from rich.text import Text


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

        if "context" in entry and entry["context"]:
            content.append("\nContext:\n", style="bold blue")
            for ctx_line in entry["context"]:
                content.append(f"{ctx_line}\n", style="dim white")

        if "score" in entry:
            content.append("\nScore: ", style="bold magenta")
            content.append(f"{entry['score']:.4f}", style="magenta")

        self.update(content)
        self.visible = True


class SearchMode(Static):
    """Search mode widget for TUI browser.

    Features:
    - Live search input
    - Filter toggles (timeline/modules/decisions)
    - Results table with navigation
    - Detail view
    """

    CSS = """
    SearchMode {
        layout: vertical;
        height: 1fr;
    }

    #search-controls {
        height: auto;
        padding: 1;
    }

    #filter-container {
        height: auto;
        layout: horizontal;
        padding: 0 1;
    }

    #results-container {
        height: 1fr;
    }

    SearchResultsTable {
        height: 1fr;
    }

    DetailPanel {
        height: 1fr;
        border: solid cyan;
        padding: 1 2;
        overflow-y: auto;
        display: none;
    }

    DetailPanel.visible {
        display: block;
    }
    """

    BINDINGS = [
        Binding("/", "focus_search", "Search", show=True),
        Binding("enter", "show_detail", "Detail", show=True),
        Binding("escape", "close_detail", "Close", show=False),
    ]

    def __init__(self, base_path: Path, initial_query: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.base_path = base_path
        self.initial_query = initial_query
        self.current_results: List[dict] = []
        self.filter_timeline = True
        self.filter_modules = True
        self.filter_decisions = True

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="search-controls"):
            yield Input(
                placeholder="Enter search query... (press / to focus)",
                id="search-input",
                value=self.initial_query or ""
            )

        with Container(id="filter-container"):
            yield Checkbox("Timeline", value=True, id="filter-timeline")
            yield Checkbox("Modules", value=True, id="filter-modules")
            yield Checkbox("Decisions", value=True, id="filter-decisions")

        with Container(id="results-container"):
            yield SearchResultsTable(id="results-table", cursor_type="row")
            yield DetailPanel(id="detail-panel")

    def on_mount(self) -> None:
        """Handle widget mount."""
        # Setup results table
        table = self.query_one("#results-table", SearchResultsTable)
        table.add_columns("Date", "Time", "Type", "Content", "Score")
        table.cursor_type = "row"
        table.zebra_stripes = True

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

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Handle filter checkbox changes."""
        checkbox_id = event.checkbox.id

        if checkbox_id == "filter-timeline":
            self.filter_timeline = event.value
        elif checkbox_id == "filter-modules":
            self.filter_modules = event.value
        elif checkbox_id == "filter-decisions":
            self.filter_decisions = event.value

        # Re-run search if there's a query
        search_input = self.query_one("#search-input", Input)
        if search_input.value:
            self.perform_search(search_input.value)

    def perform_search(self, query: str) -> None:
        """Perform search and update results table."""
        from memory_tool.core.search import MemorySearcher

        try:
            # Create searcher and perform search
            searcher = MemorySearcher(base_path=self.base_path)

            # Build scope filter
            include_types = []
            if self.filter_timeline:
                include_types.append("timeline")
            if self.filter_modules:
                include_types.append("module")
            if self.filter_decisions:
                include_types.append("decision")

            # search() returns Dict[str, List[SearchResult]]
            results_dict = searcher.search(query, scope="local", max_results=100)

            # Flatten and filter results
            all_results = []
            for group_name, group_results in results_dict.items():
                for result in group_results:
                    # Determine result type
                    result_type = "timeline"
                    if "modules" in str(result.file_path):
                        result_type = "module"
                    if "decisions" in str(result.file_path):
                        result_type = "decision"

                    # Apply filter
                    if (result_type == "timeline" and self.filter_timeline) or \
                       (result_type == "module" and self.filter_modules) or \
                       (result_type == "decision" and self.filter_decisions):
                        all_results.append((result, result_type))

            # Store results
            self.current_results = []
            for result, result_type in all_results:
                self.current_results.append({
                    "file": str(result.file_path),
                    "line": result.line_number,
                    "content": result.line_content,
                    "context": result.match_context,
                    "score": result.score,
                    "date": result.date.strftime("%Y-%m-%d") if result.date else "",
                    "type": result_type,
                })

            # Update table
            table = self.query_one("#results-table", SearchResultsTable)
            table.clear()

            for result in self.current_results:
                # Extract date and time
                date_str = result.get("date", "")
                time_str = ""

                # Extract time from content
                content = result.get("content", "")
                if "|" in content:
                    parts = content.split("|", 1)
                    if len(parts) == 2:
                        time_part = parts[0].strip()
                        if re.match(r'^\d{1,2}:\d{2}$', time_part):
                            time_str = time_part
                            content = parts[1].strip()

                # Truncate content
                if len(content) > 70:
                    content = content[:67] + "..."

                # Get type and score
                result_type = result.get("type", "")
                score = result.get("score", 0.0)
                score_str = f"{score:.2f}" if score > 0 else ""

                table.add_row(
                    date_str,
                    time_str,
                    result_type,
                    content,
                    score_str,
                )

        except Exception as e:
            # Show error in status (need to access parent app)
            pass

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
