"""Enhanced multi-mode TUI browser for memory_tool.

Provides tabbed interface with multiple views:
- Search: Interactive search with filters
- Timeline: Date-based timeline explorer
- Modules: Hierarchical module browser
- Graph: Module connection graph viewer
"""

from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

from memory_tool.utils.paths import base_dir_for_root, get_project_root

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, Horizontal, VerticalScroll
from textual.widgets import (
    Header,
    Footer,
    TabbedContent,
    TabPane,
    Static,
    Label,
    Tree,
)
from textual.reactive import reactive

from .search_mode import SearchMode
from .timeline_mode import TimelineMode
from .modules_mode import ModulesMode
from .graph_mode import GraphMode


class MemoryBrowser(App):
    """Enhanced multi-mode TUI browser for memory_tool.

    Features:
    - Tabbed interface with 4 modes
    - Search mode: Interactive search with filters
    - Timeline mode: Date-based timeline explorer
    - Modules mode: Hierarchical module browser
    - Graph mode: Module connection graph viewer

    Keybindings:
    - Tab: Switch between modes
    - /: Focus search (in search mode)
    - q: Quit application
    - ?: Show help
    """

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        height: 1fr;
    }

    TabbedContent {
        height: 1fr;
    }

    #status-bar {
        height: 1;
        background: $boost;
        color: $text;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("?", "show_help", "Help", show=True),
        Binding("tab", "next_tab", "Next Tab", show=False),
        Binding("shift+tab", "previous_tab", "Previous Tab", show=False),
    ]

    def __init__(
        self,
        base_path: Optional[Path] = None,
        initial_mode: str = "search",
        initial_query: Optional[str] = None,
        **kwargs
    ):
        """Initialize memory browser.

        Args:
            base_path: Base path for project (parent of .memory/)
            initial_mode: Initial mode to show (search/timeline/modules/graph)
            initial_query: Initial search query (for search mode)
        """
        super().__init__(**kwargs)
        self.base_path = base_path or self._find_project_root()
        self.initial_mode = initial_mode
        self.initial_query = initial_query
        self.title = "Memory Tool - Enhanced Browser"

    def _find_project_root(self) -> Path:
        """Find the project root (the directory containing the base folder)."""
        return get_project_root()

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()

        with Container(id="main-container"):
            with TabbedContent(id="tabs"):
                with TabPane("Search", id="tab-search"):
                    yield SearchMode(base_path=self.base_path, initial_query=self.initial_query)

                with TabPane("Timeline", id="tab-timeline"):
                    yield TimelineMode(base_path=self.base_path)

                with TabPane("Modules", id="tab-modules"):
                    yield ModulesMode(base_path=self.base_path)

                with TabPane("Graph", id="tab-graph"):
                    yield GraphMode(base_path=self.base_path)

        with Horizontal(id="status-bar"):
            yield Label("Tab to switch modes | / for search | ? for help | q to quit", id="status-text")

        yield Footer()

    def on_mount(self) -> None:
        """Handle app mount."""
        # Set initial tab
        tabs = self.query_one("#tabs", TabbedContent)

        tab_map = {
            "search": "tab-search",
            "timeline": "tab-timeline",
            "modules": "tab-modules",
            "graph": "tab-graph",
        }

        if self.initial_mode in tab_map:
            tabs.active = tab_map[self.initial_mode]

    def action_next_tab(self) -> None:
        """Switch to next tab."""
        tabs = self.query_one("#tabs", TabbedContent)
        # Textual's TabbedContent handles tab switching automatically
        # This action is just for the binding

    def action_previous_tab(self) -> None:
        """Switch to previous tab."""
        tabs = self.query_one("#tabs", TabbedContent)
        # Textual's TabbedContent handles tab switching automatically

    def action_show_help(self) -> None:
        """Show help overlay."""
        self.update_status("Help: Tab=Switch modes | /=Search | Enter=Details | q=Quit")

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


def run_browser(
    base_path: Optional[Path] = None,
    mode: str = "search",
    query: Optional[str] = None
) -> None:
    """Run the enhanced memory browser TUI application.

    Args:
        base_path: Base path for project (parent of .memory/)
        mode: Initial mode to show (search/timeline/modules/graph)
        query: Initial search query (for search mode)
    """
    app = MemoryBrowser(base_path=base_path, initial_mode=mode, initial_query=query)
    app.run()
