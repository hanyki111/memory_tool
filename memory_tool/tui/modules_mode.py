"""Modules mode for TUI browser."""

from pathlib import Path
from typing import Optional, List, Dict

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, VerticalScroll
from textual.widgets import (
    Static,
    Label,
    Tree,
)
from textual.widgets.tree import TreeNode
from rich.text import Text


class ModulesMode(Static):
    """Modules mode widget for TUI browser.

    Features:
    - Hierarchical module tree
    - Module details panel
    - Connection viewer
    - Quick navigation
    """

    CSS = """
    ModulesMode {
        layout: horizontal;
        height: 1fr;
    }

    #module-tree-container {
        width: 35;
        border-right: solid $primary;
        padding: 1;
    }

    #module-details-container {
        width: 1fr;
        padding: 1 2;
    }

    Tree {
        height: 1fr;
    }

    #details-content {
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
        Binding("c", "show_connections", "Connections", show=True),
    ]

    def __init__(self, base_path: Path, **kwargs):
        super().__init__(**kwargs)
        self.base_path = base_path
        self.modules_path = base_path / ".memory" / "modules"
        self.selected_module: Optional[str] = None
        self.module_tree_data: Dict = {}

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        with Container(id="module-tree-container"):
            yield Label("Module Hierarchy", id="tree-header")
            yield Tree("Modules", id="module-tree")

        with Container(id="module-details-container"):
            with Container(id="stats-panel"):
                yield Label("Select a module to view details", id="stats-label")

            with VerticalScroll(id="details-content"):
                yield Static("Select a module from the tree", id="details-text")

    def on_mount(self) -> None:
        """Handle widget mount."""
        self.load_modules()
        self.populate_tree()

    def load_modules(self) -> None:
        """Load module hierarchy."""
        from memory_tool.core.module import ModuleManager

        try:
            manager = ModuleManager(base_path=self.base_path)
            self.module_tree_data = manager.build_module_tree()
        except Exception:
            self.module_tree_data = {}

    def populate_tree(self) -> None:
        """Populate the module tree."""
        tree = self.query_one("#module-tree", Tree)
        tree.clear()

        root = tree.root
        root.expand()

        # Recursively build tree
        self._build_tree_recursive(root, self.module_tree_data)

    def _build_tree_recursive(self, parent_node: TreeNode, tree_dict: Dict):
        """Recursively build tree from nested dict."""
        for name, children in sorted(tree_dict.items()):
            # Determine if this is a module (has current.md)
            module_path = self.modules_path / name

            if isinstance(children, dict) and children:
                # Has children - create expandable node
                node = parent_node.add(f"[bold cyan]{name}[/]", expand=False)
                self._build_tree_recursive(node, children)
            else:
                # Leaf node
                if module_path.exists() and (module_path / "current.md").exists():
                    parent_node.add_leaf(f"[green]{name}[/]")
                else:
                    parent_node.add_leaf(f"{name}")

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle module selection."""
        if event.node.label:
            # Extract module name (remove markup)
            label_text = str(event.node.label)
            # Remove rich markup
            import re
            module_name = re.sub(r'\[.*?\]', '', label_text)

            self.selected_module = module_name
            self.show_module_details(module_name)

    def show_module_details(self, module_name: str) -> None:
        """Show details for selected module."""
        module_path = self.modules_path / module_name

        if not module_path.exists():
            return

        # Build details text
        content = Text()

        # Header
        content.append(f"Module: ", style="bold")
        content.append(f"{module_name}\n\n", style="bold cyan")

        # Read current.md
        current_file = module_path / "current.md"
        if current_file.exists():
            try:
                current_content = current_file.read_text(encoding="utf-8")

                # Extract first section (before first ##)
                lines = current_content.split("\n")
                preview_lines = []
                for line in lines[:20]:  # First 20 lines
                    if line.startswith("##") and preview_lines:
                        break
                    preview_lines.append(line)

                content.append("Current Status:\n", style="bold green")
                content.append("\n".join(preview_lines), style="white")
                content.append("\n\n", style="white")

            except Exception:
                pass

        # Check for connections
        from memory_tool.core.connections import ConnectionGraph

        try:
            graph = ConnectionGraph(db_path=self.base_path / ".memory" / ".connections.db")

            # Get outgoing connections
            outgoing = graph.get_connections_from(module_name)
            if outgoing:
                content.append("Connections (outgoing):\n", style="bold yellow")
                for target in outgoing[:10]:
                    content.append(f"  → [[{target}]]\n", style="yellow")
                if len(outgoing) > 10:
                    content.append(f"  ... and {len(outgoing) - 10} more\n", style="dim yellow")
                content.append("\n", style="white")

            # Get incoming connections
            incoming = graph.get_connections_to(module_name)
            if incoming:
                content.append("Backlinks (incoming):\n", style="bold blue")
                for source in incoming[:10]:
                    content.append(f"  ← [[{source}]]\n", style="blue")
                if len(incoming) > 10:
                    content.append(f"  ... and {len(incoming) - 10} more\n", style="dim blue")

        except Exception:
            pass

        # Update details view
        details_text = self.query_one("#details-text", Static)
        details_text.update(content)

        # Update stats
        stats_label = self.query_one("#stats-label", Label)
        stats_label.update(f"Module: {module_name}")

    def action_refresh(self) -> None:
        """Refresh module tree."""
        self.load_modules()
        self.populate_tree()

        # Re-show details if a module was selected
        if self.selected_module:
            self.show_module_details(self.selected_module)

    def action_show_connections(self) -> None:
        """Show connections for selected module."""
        if self.selected_module:
            # For now, just refresh to show connections
            # In the future, could open a separate connection viewer
            self.show_module_details(self.selected_module)
