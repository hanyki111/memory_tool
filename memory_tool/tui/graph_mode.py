"""Graph mode for TUI browser."""

from pathlib import Path
from typing import Optional, List, Dict, Set, Tuple

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widgets import (
    Static,
    Label,
    ListItem,
    ListView,
)
from rich.text import Text
from memory_tool.utils.paths import base_dir_for_root


class NodeList(ListView):
    """ListView for displaying graph nodes."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]


class GraphMode(Static):
    """Graph mode widget for TUI browser.

    Features:
    - Module list (sorted by connection count)
    - Connection visualization
    - Graph statistics
    - Interactive navigation
    """

    CSS = """
    GraphMode {
        layout: horizontal;
        height: 1fr;
    }

    #node-list-container {
        width: 30;
        border-right: solid $primary;
        padding: 1;
    }

    #graph-view-container {
        width: 1fr;
        padding: 1 2;
    }

    NodeList {
        height: 1fr;
    }

    #graph-content {
        height: 1fr;
        overflow-y: auto;
    }

    #stats-panel {
        height: auto;
        padding: 1;
        background: $boost;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("r", "refresh", "Refresh", show=True),
        Binding("s", "toggle_sort", "Sort", show=True),
    ]

    def __init__(self, base_path: Path, **kwargs):
        super().__init__(**kwargs)
        self.base_path = base_path
        self.db_path = base_dir_for_root(base_path) / ".connections.db"
        self.selected_node: Optional[str] = None
        self.nodes: List[Tuple[str, int]] = []  # (module_name, connection_count)
        self.sort_by_connections = True

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="node-list-container"):
            yield Label("Modules (by connections)", id="node-list-header")
            yield NodeList(id="node-list")

        with Container(id="graph-view-container"):
            with Container(id="stats-panel"):
                yield Label("Graph Statistics", id="stats-label")

            with VerticalScroll(id="graph-content"):
                yield Static("Select a module to view connections", id="graph-text")

    def on_mount(self) -> None:
        """Handle widget mount."""
        self.load_graph()
        self.populate_node_list()
        self.show_graph_stats()

    def load_graph(self) -> None:
        """Load graph data."""
        from memory_tool.core.connections import ConnectionGraph

        try:
            graph = ConnectionGraph(db_path=self.db_path)

            # Get all modules with their connection counts
            stats = graph.get_graph_stats()
            all_connections = graph.get_all_connections()

            # Count connections per module
            connection_counts: Dict[str, int] = {}

            for source, target in all_connections:
                connection_counts[source] = connection_counts.get(source, 0) + 1
                connection_counts[target] = connection_counts.get(target, 0) + 1

            # Sort by connection count (descending)
            if self.sort_by_connections:
                self.nodes = sorted(
                    connection_counts.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            else:
                self.nodes = sorted(connection_counts.items())

        except Exception:
            self.nodes = []

    def populate_node_list(self) -> None:
        """Populate the node list."""
        node_list = self.query_one("#node-list", NodeList)
        node_list.clear()

        for module_name, count in self.nodes:
            # Format with connection count
            if count > 10:
                label = f"[bold green]{module_name}[/] ({count})"
            elif count > 5:
                label = f"[green]{module_name}[/] ({count})"
            elif count > 2:
                label = f"[yellow]{module_name}[/] ({count})"
            else:
                label = f"{module_name} ({count})"

            node_list.append(ListItem(Label(label)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle node selection."""
        if event.list_view.id == "node-list":
            index = event.list_view.index
            if 0 <= index < len(self.nodes):
                module_name, _ = self.nodes[index]
                self.selected_node = module_name
                self.show_node_connections(module_name)

    def show_node_connections(self, module_name: str) -> None:
        """Show connections for selected node."""
        from memory_tool.core.connections import ConnectionGraph

        try:
            graph = ConnectionGraph(db_path=self.db_path)

            # Get connections
            outgoing = graph.get_connections_from(module_name)
            incoming = graph.get_connections_to(module_name)

            # Build visualization text
            content = Text()

            # Header
            content.append(f"Module: ", style="bold")
            content.append(f"{module_name}\n\n", style="bold cyan")

            # Stats
            total_connections = len(outgoing) + len(incoming)
            content.append(f"Total connections: {total_connections}\n", style="bold white")
            content.append(f"Outgoing: {len(outgoing)} | Incoming: {len(incoming)}\n\n", style="dim white")

            # Outgoing connections
            if outgoing:
                content.append("Outgoing Connections:\n", style="bold green")
                content.append("(modules this connects to)\n\n", style="dim")

                for target in sorted(outgoing)[:20]:
                    # Get connection count to target
                    target_connections = len(graph.get_connections_to(target))
                    content.append(f"  → ", style="green")
                    content.append(f"[[{target}]]", style="cyan")
                    content.append(f" ({target_connections} total)\n", style="dim")

                if len(outgoing) > 20:
                    content.append(f"\n  ... and {len(outgoing) - 20} more\n", style="dim green")

                content.append("\n")

            # Incoming connections
            if incoming:
                content.append("Incoming Connections:\n", style="bold yellow")
                content.append("(modules that connect here)\n\n", style="dim")

                for source in sorted(incoming)[:20]:
                    # Get connection count from source
                    source_connections = len(graph.get_connections_from(source))
                    content.append(f"  ← ", style="yellow")
                    content.append(f"[[{source}]]", style="cyan")
                    content.append(f" ({source_connections} total)\n", style="dim")

                if len(incoming) > 20:
                    content.append(f"\n  ... and {len(incoming) - 20} more\n", style="dim yellow")

            # If no connections
            if not outgoing and not incoming:
                content.append("No connections found.\n", style="dim")
                content.append("This module is orphaned.\n", style="dim yellow")

            # Update graph view
            graph_text = self.query_one("#graph-text", Static)
            graph_text.update(content)

            # Update stats
            stats_label = self.query_one("#stats-label", Label)
            stats_label.update(f"Module: {module_name} | Connections: {total_connections}")

        except Exception as e:
            # Show error
            graph_text = self.query_one("#graph-text", Static)
            graph_text.update(f"Error loading connections: {e}")

    def show_graph_stats(self) -> None:
        """Show overall graph statistics."""
        from memory_tool.core.connections import ConnectionGraph

        try:
            graph = ConnectionGraph(db_path=self.db_path)
            stats = graph.get_graph_stats()

            # Build stats text
            content = Text()

            content.append("Graph Overview\n\n", style="bold cyan")

            content.append("Total Connections: ", style="bold")
            content.append(f"{stats['total_connections']}\n", style="green")

            content.append("Connected Modules: ", style="bold")
            content.append(f"{stats['connected_modules']}\n", style="cyan")

            content.append("Orphaned Modules: ", style="bold")
            content.append(f"{stats['orphaned_modules']}\n", style="yellow")

            content.append("\n")
            content.append("Top Connected Modules:\n", style="bold")

            # Show top 10
            for i, (module_name, count) in enumerate(self.nodes[:10], 1):
                content.append(f"{i}. ", style="dim")
                content.append(f"{module_name}", style="cyan")
                content.append(f" ({count} connections)\n", style="dim")

            # Update view
            graph_text = self.query_one("#graph-text", Static)
            graph_text.update(content)

            # Update stats label
            stats_label = self.query_one("#stats-label", Label)
            stats_label.update(
                f"Connections: {stats['total_connections']} | "
                f"Modules: {stats['connected_modules']} | "
                f"Orphaned: {stats['orphaned_modules']}"
            )

        except Exception:
            pass

    def action_refresh(self) -> None:
        """Refresh graph data."""
        self.load_graph()
        self.populate_node_list()

        if self.selected_node:
            self.show_node_connections(self.selected_node)
        else:
            self.show_graph_stats()

    def action_toggle_sort(self) -> None:
        """Toggle sort order."""
        self.sort_by_connections = not self.sort_by_connections

        # Update header
        header = self.query_one("#node-list-header", Label)
        if self.sort_by_connections:
            header.update("Modules (by connections)")
        else:
            header.update("Modules (alphabetical)")

        # Reload and repopulate
        self.load_graph()
        self.populate_node_list()
