"""Module connection graph management.

Parses wiki-style [[module-name]] links from Markdown files
and builds a connection graph stored in SQLite.
"""

import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime


class ConnectionError(Exception):
    """Base exception for connection operations."""
    pass


class Connection:
    """Represents a connection between two modules."""

    def __init__(
        self,
        source: str,
        target: str,
        source_file: str,
        line_number: int,
        created_at: Optional[datetime] = None,
    ):
        """Initialize connection.

        Args:
            source: Source module path
            target: Target module path
            source_file: File where link was found
            line_number: Line number of the link
            created_at: Timestamp (defaults to now)
        """
        self.source = source
        self.target = target
        self.source_file = source_file
        self.line_number = line_number
        self.created_at = created_at or datetime.now()

    def __repr__(self):
        return f"Connection({self.source} -> {self.target})"

    def __eq__(self, other):
        if not isinstance(other, Connection):
            return False
        return (
            self.source == other.source
            and self.target == other.target
            and self.source_file == other.source_file
        )

    def __hash__(self):
        return hash((self.source, self.target, self.source_file))


class ConnectionParser:
    """Parse wiki-style links from Markdown files."""

    # Regex pattern for [[module-name]] or [[module/path]]
    LINK_PATTERN = re.compile(r'\[\[([a-zA-Z0-9_/-]+)\]\]')

    @classmethod
    def parse_file(cls, file_path: Path, module_path: str) -> List[Connection]:
        """Parse connections from a Markdown file.

        Args:
            file_path: Path to Markdown file
            module_path: Path of the module containing this file (e.g., 'projects/website')

        Returns:
            List of connections found in the file
        """
        if not file_path.exists():
            return []

        connections = []

        try:
            content = file_path.read_text(encoding="utf-8")
            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                # Find all [[module-name]] patterns
                matches = cls.LINK_PATTERN.finditer(line)

                for match in matches:
                    target_module = match.group(1)

                    # Create connection
                    conn = Connection(
                        source=module_path,
                        target=target_module,
                        source_file=str(file_path),
                        line_number=line_num,
                    )
                    connections.append(conn)

        except Exception as e:
            # Skip files that can't be read
            pass

        return connections

    @classmethod
    def parse_module(cls, module_dir: Path, module_path: str) -> List[Connection]:
        """Parse all connections from a module's Markdown files.

        Args:
            module_dir: Path to module directory
            module_path: Module path (e.g., 'projects/website')

        Returns:
            List of all connections in the module
        """
        if not module_dir.exists() or not module_dir.is_dir():
            return []

        all_connections = []

        # Parse all .md files in module
        for md_file in module_dir.glob("*.md"):
            # Skip archive directory
            if "archive" in md_file.parts:
                continue

            connections = cls.parse_file(md_file, module_path)
            all_connections.extend(connections)

        return all_connections


class ConnectionGraph:
    """Manage module connection graph in SQLite."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize connection graph.

        Args:
            db_path: Path to SQLite database (defaults to .memory/.connections.db)
        """
        if db_path is None:
            db_path = Path.cwd() / ".memory" / ".connections.db"

        self.db_path = db_path
        self._ensure_database()

    def _ensure_database(self):
        """Create database and tables if they don't exist."""
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Create connections table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connections (
                    source_module TEXT NOT NULL,
                    target_module TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    line_number INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (source_module, target_module, source_file)
                )
            """)

            # Create indexes for fast lookups
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_source
                ON connections(source_module)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_target
                ON connections(target_module)
            """)

            conn.commit()

        finally:
            conn.close()

    def add_connection(self, connection: Connection):
        """Add a connection to the graph.

        Args:
            connection: Connection to add
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO connections
                (source_module, target_module, source_file, line_number, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (
                connection.source,
                connection.target,
                connection.source_file,
                connection.line_number,
                connection.created_at,
            ))

            conn.commit()

        finally:
            conn.close()

    def add_connections(self, connections: List[Connection]):
        """Add multiple connections at once.

        Args:
            connections: List of connections to add
        """
        if not connections:
            return

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            cursor.executemany("""
                INSERT OR REPLACE INTO connections
                (source_module, target_module, source_file, line_number, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, [
                (c.source, c.target, c.source_file, c.line_number, c.created_at)
                for c in connections
            ])

            conn.commit()

        finally:
            conn.close()

    def remove_module_connections(self, module_path: str):
        """Remove all connections from a module.

        Args:
            module_path: Module path
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM connections
                WHERE source_module = ?
            """, (module_path,))

            conn.commit()

        finally:
            conn.close()

    def get_outgoing_connections(self, module_path: str) -> List[Connection]:
        """Get all outgoing connections from a module.

        Args:
            module_path: Module path

        Returns:
            List of connections where this module is the source
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT source_module, target_module, source_file, line_number, created_at
                FROM connections
                WHERE source_module = ?
                ORDER BY target_module
            """, (module_path,))

            rows = cursor.fetchall()

            return [
                Connection(
                    source=row[0],
                    target=row[1],
                    source_file=row[2],
                    line_number=row[3],
                    created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                )
                for row in rows
            ]

        finally:
            conn.close()

    def get_incoming_connections(self, module_path: str) -> List[Connection]:
        """Get all incoming connections to a module.

        Args:
            module_path: Module path

        Returns:
            List of connections where this module is the target
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT source_module, target_module, source_file, line_number, created_at
                FROM connections
                WHERE target_module = ?
                ORDER BY source_module
            """, (module_path,))

            rows = cursor.fetchall()

            return [
                Connection(
                    source=row[0],
                    target=row[1],
                    source_file=row[2],
                    line_number=row[3],
                    created_at=datetime.fromisoformat(row[4]) if row[4] else None,
                )
                for row in rows
            ]

        finally:
            conn.close()

    def get_all_modules(self) -> Set[str]:
        """Get all modules that have connections.

        Returns:
            Set of module paths
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT DISTINCT source_module FROM connections
                UNION
                SELECT DISTINCT target_module FROM connections
            """)

            rows = cursor.fetchall()
            return {row[0] for row in rows}

        finally:
            conn.close()

    def get_graph_stats(self) -> Dict[str, int]:
        """Get statistics about the connection graph.

        Returns:
            Dictionary with stats (total_connections, total_modules, etc.)
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Total connections
            cursor.execute("SELECT COUNT(*) FROM connections")
            total_connections = cursor.fetchone()[0]

            # Total modules
            modules = self.get_all_modules()
            total_modules = len(modules)

            # Orphaned modules (no connections)
            from memory_tool.core.module import ModuleManager
            manager = ModuleManager()
            all_modules = manager.discover_all_modules()
            all_module_paths = {str(m) for m in all_modules}

            orphaned = all_module_paths - modules
            orphaned_count = len(orphaned)

            return {
                "total_connections": total_connections,
                "total_modules": total_modules,
                "connected_modules": total_modules,
                "orphaned_modules": orphaned_count,
            }

        finally:
            conn.close()

    def rebuild_from_modules(self, modules_path: Optional[Path] = None) -> int:
        """Rebuild connection graph from all modules.

        Args:
            modules_path: Path to modules directory (defaults to .memory/modules)

        Returns:
            Number of connections found
        """
        if modules_path is None:
            modules_path = Path.cwd() / ".memory" / "modules"

        if not modules_path.exists():
            raise ConnectionError(f"Modules directory not found: {modules_path}")

        # Clear existing connections
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM connections")
            conn.commit()
        finally:
            conn.close()

        # Discover all modules
        from memory_tool.core.module import ModuleManager
        manager = ModuleManager()
        all_modules = manager.discover_all_modules()

        # Parse connections from each module
        all_connections = []
        for module_path in all_modules:
            module_dir = modules_path / module_path
            module_path_str = str(module_path).replace('\\', '/')  # Normalize to forward slashes

            connections = ConnectionParser.parse_module(module_dir, module_path_str)
            all_connections.extend(connections)

        # Add all connections to database
        self.add_connections(all_connections)

        return len(all_connections)

    def clear(self):
        """Clear all connections from the graph."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM connections")
            conn.commit()
        finally:
            conn.close()

    def export_mermaid(self) -> str:
        """Export graph as Mermaid diagram.

        Returns:
            Mermaid diagram syntax
        """
        lines = ["graph LR"]

        # Get all unique connections (deduplicate by source-target pair)
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT source_module, target_module
                FROM connections
                ORDER BY source_module, target_module
            """)

            rows = cursor.fetchall()

            # Generate node IDs (sanitize module names)
            def sanitize_id(module_path: str) -> str:
                """Convert module path to valid Mermaid node ID."""
                return module_path.replace('/', '_').replace('-', '_')

            # Generate connections
            for source, target in rows:
                source_id = sanitize_id(source)
                target_id = sanitize_id(target)

                # Use display names with paths
                source_label = source.replace('/', ' / ')
                target_label = target.replace('/', ' / ')

                lines.append(f'    {source_id}["{source_label}"] --> {target_id}["{target_label}"]')

            return '\n'.join(lines)

        finally:
            conn.close()

    def export_graphviz(self) -> str:
        """Export graph as Graphviz DOT format.

        Returns:
            DOT format graph
        """
        lines = ["digraph ModuleGraph {"]
        lines.append("    rankdir=LR;")
        lines.append("    node [shape=box, style=rounded];")
        lines.append("")

        # Get all modules
        all_modules = self.get_all_modules()

        # Define nodes
        for module in sorted(all_modules):
            # Sanitize label
            label = module.replace('/', ' / ')
            node_id = module.replace('/', '_').replace('-', '_')
            lines.append(f'    {node_id} [label="{label}"];')

        lines.append("")

        # Get all unique connections
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT source_module, target_module
                FROM connections
                ORDER BY source_module, target_module
            """)

            rows = cursor.fetchall()

            # Generate edges
            for source, target in rows:
                source_id = source.replace('/', '_').replace('-', '_')
                target_id = target.replace('/', '_').replace('-', '_')
                lines.append(f'    {source_id} -> {target_id};')

            lines.append("}")
            return '\n'.join(lines)

        finally:
            conn.close()

    def check_broken_links(self) -> Dict[str, List[str]]:
        """Check for broken links (links to non-existent modules).

        Returns:
            Dictionary mapping source modules to list of broken target modules
        """
        from memory_tool.core.module import ModuleManager

        # Get all existing modules
        manager = ModuleManager()
        existing_modules = {str(m).replace('\\', '/') for m in manager.discover_all_modules()}

        # Get all connections
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT source_module, target_module
                FROM connections
            """)

            rows = cursor.fetchall()

            broken = {}
            for source, target in rows:
                # Normalize paths
                target_normalized = target.replace('\\', '/')

                if target_normalized not in existing_modules:
                    if source not in broken:
                        broken[source] = []
                    broken[source].append(target)

            return broken

        finally:
            conn.close()

    def get_orphaned_modules(self) -> Set[str]:
        """Get modules with no connections (neither incoming nor outgoing).

        Returns:
            Set of orphaned module paths
        """
        from memory_tool.core.module import ModuleManager

        # Get all existing modules
        manager = ModuleManager()
        all_modules = {str(m).replace('\\', '/') for m in manager.discover_all_modules()}

        # Get connected modules
        connected = self.get_all_modules()

        # Orphaned = all modules - connected modules
        return all_modules - connected

    def suggest_backlinks(self, module_path: str, max_suggestions: int = 5) -> List[Tuple[str, str]]:
        """Suggest potential backlinks for a module.

        Args:
            module_path: Module path to suggest links for
            max_suggestions: Maximum number of suggestions

        Returns:
            List of (module_path, reason) tuples
        """
        from memory_tool.core.module import ModuleManager

        suggestions = []

        # Get all existing modules
        manager = ModuleManager()
        all_modules = [str(m).replace('\\', '/') for m in manager.discover_all_modules()]

        # Get existing connections to avoid suggesting them again
        existing_outgoing = {c.target for c in self.get_outgoing_connections(module_path)}
        existing_incoming = {c.source for c in self.get_incoming_connections(module_path)}

        # Filter out self and existing connections
        candidates = [
            m for m in all_modules
            if m != module_path
            and m not in existing_outgoing
            and m not in existing_incoming
        ]

        # Suggestion strategy 1: Similar path prefix
        module_parts = module_path.split('/')
        if len(module_parts) > 1:
            parent = '/'.join(module_parts[:-1])

            for candidate in candidates:
                if candidate.startswith(parent + '/'):
                    suggestions.append((candidate, f"Sibling module under {parent}"))

        # Suggestion strategy 2: Same top-level category
        if len(module_parts) > 0:
            top_level = module_parts[0]

            for candidate in candidates:
                candidate_parts = candidate.split('/')
                if len(candidate_parts) > 0 and candidate_parts[0] == top_level:
                    if candidate not in [s[0] for s in suggestions]:
                        suggestions.append((candidate, f"Related {top_level} module"))

        # Suggestion strategy 3: Modules that link to similar targets
        outgoing = self.get_outgoing_connections(module_path)
        if outgoing:
            target_modules = {c.target for c in outgoing}

            for candidate in candidates:
                candidate_outgoing = self.get_outgoing_connections(candidate)
                candidate_targets = {c.target for c in candidate_outgoing}

                # Find common targets
                common = target_modules & candidate_targets
                if common and candidate not in [s[0] for s in suggestions]:
                    suggestions.append((candidate, f"Links to {len(common)} common module(s)"))

        return suggestions[:max_suggestions]

    def _module_exists(self, module_path: str) -> bool:
        """Check if a module directory exists.

        Args:
            module_path: Module path (e.g., 'projects/website')

        Returns:
            True if module directory exists
        """
        modules_dir = Path.cwd() / ".memory" / "modules"
        module_dir = modules_dir / module_path
        return module_dir.exists() and module_dir.is_dir()

    def _get_module_description(self, module_path: str) -> Optional[str]:
        """Get module description from module.md.

        Args:
            module_path: Module path

        Returns:
            Description string or None if not found
        """
        modules_dir = Path.cwd() / ".memory" / "modules"
        module_md = modules_dir / module_path / "module.md"

        if not module_md.exists():
            return None

        try:
            content = module_md.read_text(encoding="utf-8")
            lines = content.split('\n')

            # Look for description patterns:
            # 1. "**Description:** ..." or "**목적:** ..."
            # 2. First paragraph after title
            for i, line in enumerate(lines):
                line_stripped = line.strip()

                # Pattern 1: Explicit description field
                if line_stripped.startswith("**Description:**") or line_stripped.startswith("**목적:**"):
                    desc = line_stripped.split(":", 1)[1].strip()
                    if desc:
                        return desc

                # Pattern 2: First non-empty paragraph after # title
                if line_stripped.startswith("#") and i + 1 < len(lines):
                    # Skip empty lines
                    j = i + 1
                    while j < len(lines) and not lines[j].strip():
                        j += 1

                    if j < len(lines):
                        desc = lines[j].strip()
                        # Don't return lines that are headings or markdown syntax
                        if desc and not desc.startswith("#") and not desc.startswith("**"):
                            return desc

            return None

        except Exception:
            return None

    def to_json(self) -> dict:
        """Export graph as JSON structure.

        Returns:
            Dictionary with nodes, edges, and stats:
            {
                "nodes": [
                    {
                        "id": "projects/memory-note",
                        "name": "memory-note",
                        "path": "projects/memory-note",
                        "type": "module",
                        "has_files": true,
                        "description": "..."
                    }
                ],
                "edges": [
                    {
                        "source": "projects/memory-note",
                        "target": "projects/memory-note/search-system",
                        "type": "connection",
                        "source_file": ".memory/modules/...",
                        "line_number": 42
                    }
                ],
                "stats": {
                    "total_connections": 1,
                    "connected_modules": 2,
                    "orphaned_modules": 0
                }
            }
        """
        # Get all modules from graph
        all_modules = self.get_all_modules()

        # Build nodes
        nodes = []
        for module_path in sorted(all_modules):
            # Get module info
            node = {
                "id": module_path,
                "name": module_path.split('/')[-1],
                "path": module_path,
                "type": "module",
                "has_files": self._module_exists(module_path),
            }

            # Optional: read description from module.md
            desc = self._get_module_description(module_path)
            if desc:
                node["description"] = desc

            nodes.append(node)

        # Build edges
        edges = []
        for module in sorted(all_modules):
            connections = self.get_outgoing_connections(module)
            for conn in connections:
                edges.append({
                    "source": conn.source,
                    "target": conn.target,
                    "type": "connection",
                    "source_file": conn.source_file,
                    "line_number": conn.line_number,
                })

        # Get stats
        stats = self.get_graph_stats()

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": stats,
        }
