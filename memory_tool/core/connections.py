"""Module connection graph management.

Parses wiki-style [[module-name]] links from Markdown files
and builds a connection graph stored in SQLite.
"""

import os
import posixpath
import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional
from datetime import datetime
from urllib.parse import unquote

from memory_tool.utils.module_docs import module_documents
from memory_tool.utils.paths import get_base_path


class ConnectionError(Exception):
    """Base exception for connection operations."""
    pass


class LinkResolver:
    """Find the module a wiki link names, the way Obsidian does.

    Obsidian does not require a full path: ``[[core-principles]]`` names the
    document called core-principles wherever it is, and ``[[principles/core-
    principles]]`` narrows that down. Comparing links against full module paths
    only reported every such link as broken.

    Rules, in order:
      1. the full module path
      2. a ``./`` or ``../`` path, read from the linking module's folder
      3. a module whose path ends with the target -- "b" or "a/b" for "x/a/b".
         When several do, the one nearest the linking module wins; a tie is
         ambiguous and resolves to nothing.
    """

    def __init__(self, module_paths):
        self.modules = {self.normalize(str(m)) for m in module_paths}

    @staticmethod
    def normalize(target: str) -> str:
        """Forward slashes, no surrounding slashes or spaces, no ``.md``."""
        target = target.replace("\\", "/").strip().strip("/")
        if target.lower().endswith(".md"):
            target = target[:-3]
        return target

    def candidates(self, target: str, source: Optional[str] = None) -> List[str]:
        """Every module the link could name, best first; one entry if certain."""
        wanted = self.normalize(target)
        if not wanted:
            return []

        if wanted in self.modules:
            return [wanted]

        if source is not None and wanted.startswith(("./", "../")):
            # A module is a folder holding its document, or a document beside
            # its siblings, so "here" is either the module or its parent.
            source = self.normalize(source)
            for folder in (source, posixpath.dirname(source)):
                relative = posixpath.normpath(posixpath.join(folder, wanted))
                if relative in self.modules:
                    return [relative]
            return []

        matches = [m for m in self.modules if m.endswith("/" + wanted)]
        if len(matches) <= 1 or source is None:
            return sorted(matches)

        source_parts = self.normalize(source).split("/")

        def shared(module: str) -> int:
            count = 0
            for mine, theirs in zip(source_parts, module.split("/")[:-1]):
                if mine != theirs:
                    break
                count += 1
            return count

        matches.sort(key=lambda m: (-shared(m), m))
        best = shared(matches[0])
        nearest = [m for m in matches if shared(m) == best]
        return nearest if len(nearest) > 1 else [matches[0]]

    def resolve(self, target: str, source: Optional[str] = None) -> Optional[str]:
        """The module the link names, or None if missing or ambiguous."""
        found = self.candidates(target, source)
        return found[0] if len(found) == 1 else None


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

    #: Matches [text](path.md) and [text](path.md#section), but not images.
    MARKDOWN_LINK_PATTERN = re.compile(r'(?<!!)\[[^\]]*\]\(([^()\s#]+\.md)(?:#[^()\s]*)?\)')

    #: Matches [[target]], [[target|alias]], [[target#section]], [[target^block]].
    #:
    #: The target is "anything that is not structural punctuation" rather than an
    #: explicit character class. The previous class -- [a-zA-Z0-9_/-]+ -- was
    #: ASCII-only, so every link to a non-English module was invisible to the
    #: graph: no connection, no backlink, and no broken-link warning either,
    #: because a link that never parses cannot be reported as broken.
    #:
    #: Only the target is captured. Obsidian resolves the alias, section and
    #: block parts for display; they are not part of the module's identity.
    LINK_PATTERN = re.compile(
        r'\[\['
        r'\s*([^\[\]|#^]+?)\s*'     # target, trimmed
        r'(?:[#^][^\[\]|]*)?'       # optional #section / ^block
        r'(?:\|[^\[\]]*)?'          # optional |alias
        r'\]\]'
    )

    @classmethod
    def parse_file(
        cls,
        file_path: Path,
        module_path: str,
        modules_root: Optional[Path] = None,
    ) -> List[Connection]:
        """Parse connections from a Markdown file.

        Wiki links are always read. Markdown links to other documents are read
        when ``modules_root`` is given, since they are relative to the file and
        need it to become a module name.

        Args:
            file_path: Path to Markdown file
            module_path: Path of the module containing this file (e.g., 'projects/website')
            modules_root: The modules directory

        Returns:
            List of connections found in the file
        """
        if not file_path.exists():
            return []

        connections = []

        try:
            content = file_path.read_text(encoding="utf-8")

            for line_num, line in cls.linkable_lines(content):
                targets = [match.group(1) for match in cls.LINK_PATTERN.finditer(line)]

                if modules_root is not None:
                    for match in cls.MARKDOWN_LINK_PATTERN.finditer(line):
                        target = cls._markdown_target(match.group(1), file_path, modules_root)
                        if target and target != module_path:
                            targets.append(target)

                for target_module in targets:
                    connections.append(Connection(
                        source=module_path,
                        target=target_module,
                        source_file=str(file_path),
                        line_number=line_num,
                    ))

        except Exception as e:
            # Skip files that can't be read
            pass

        return connections

    _INLINE_CODE = re.compile(r"(`+).*?\1")

    @classmethod
    def linkable_lines(cls, content: str):
        """Yield (line number, line) with code and HTML comments removed.

        Obsidian does not follow a link written inside code or a comment, so an
        example such as ``[[module-name]]`` there is not a link. Line numbers
        stay those of the file.
        """
        in_fence = False
        in_comment = False

        for line_num, line in enumerate(content.split("\n"), 1):
            if line.lstrip().startswith(("```", "~~~")):
                in_fence = not in_fence
                yield line_num, ""
                continue
            if in_fence:
                yield line_num, ""
                continue

            kept = []
            rest = line
            while rest:
                if in_comment:
                    end = rest.find("-->")
                    if end < 0:
                        rest = ""
                    else:
                        rest = rest[end + 3:]
                        in_comment = False
                else:
                    start = rest.find("<!--")
                    if start < 0:
                        kept.append(rest)
                        rest = ""
                    else:
                        kept.append(rest[:start])
                        rest = rest[start + 4:]
                        in_comment = True

            yield line_num, cls._INLINE_CODE.sub("", "".join(kept))

    @staticmethod
    def _markdown_target(link: str, file_path: Path, modules_root: Path) -> Optional[str]:
        """Turn a relative Markdown link into a module name.

        Returns:
            The module name, or None for a link outside the modules directory.
        """
        if "://" in link or link.startswith(("/", "mailto:")):
            return None

        resolved = os.path.normpath(os.path.join(file_path.parent, unquote(link)))
        try:
            relative = Path(resolved).relative_to(os.path.normpath(modules_root))
        except ValueError:
            return None

        if relative.stem == relative.parent.name:
            return relative.parent.as_posix()
        return relative.with_suffix("").as_posix()

    @classmethod
    def parse_module(cls, module_dir: Path, module_path: str) -> List[Connection]:
        """Parse all connections from a module's own documents.

        Children in the same folder are modules themselves, so their links are
        theirs and are not counted here.

        Args:
            module_dir: The module's folder, or its path without a suffix
            module_path: Module path (e.g., 'projects/website')

        Returns:
            List of all connections in the module
        """
        modules_root = module_dir
        for _ in Path(module_path).parts:
            modules_root = modules_root.parent

        all_connections = []

        for document in module_documents(module_dir):
            all_connections.extend(cls.parse_file(document, module_path, modules_root))

        return all_connections


class ConnectionGraph:
    """Manage module connection graph in SQLite."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize connection graph.

        Args:
            db_path: Path to SQLite database (defaults to .memory/.connections.db)
        """
        if db_path is None:
            db_path = get_base_path() / ".connections.db"

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
            modules_path = get_base_path() / "modules"

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

        # Parse connections from each module. A target is stored as the module
        # it resolves to, so [[core-principles]] and [[a/core-principles]] are
        # one edge; a target that resolves to nothing is kept as written.
        resolver = LinkResolver(all_modules)
        all_connections = []
        for module_path in all_modules:
            module_dir = modules_path / module_path
            module_path_str = str(module_path).replace('\\', '/')  # Normalize to forward slashes

            for connection in ConnectionParser.parse_module(module_dir, module_path_str):
                resolved = resolver.resolve(connection.target, module_path_str)
                if resolved is not None:
                    connection.target = resolved
                all_connections.append(connection)

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

    def find_unresolved_links(
        self,
    ) -> Tuple[Dict[str, List[str]], Dict[str, List[Tuple[str, List[str]]]]]:
        """Links that name no module, and links that could name several.

        Read from the graph, so it is only as current as the last rebuild;
        ``mmodule check-links`` rebuilds first. Links from a module that no
        longer exists are left out: a deleted document has no link to fix.

        Returns:
            (broken, ambiguous). ``broken`` maps a source module to targets
            that match nothing; ``ambiguous`` maps it to (target, candidates).
        """
        from memory_tool.core.module import ModuleManager

        existing_modules = {
            str(m).replace('\\', '/') for m in ModuleManager().discover_all_modules()
        }
        resolver = LinkResolver(existing_modules)

        conn = sqlite3.connect(self.db_path)
        try:
            rows = conn.execute(
                "SELECT DISTINCT source_module, target_module FROM connections"
            ).fetchall()
        finally:
            conn.close()

        broken: Dict[str, List[str]] = {}
        ambiguous: Dict[str, List[Tuple[str, List[str]]]] = {}
        for source, target in sorted(rows):
            if source not in existing_modules:
                continue
            found = resolver.candidates(target, source)
            if not found:
                broken.setdefault(source, []).append(target)
            elif len(found) > 1:
                ambiguous.setdefault(source, []).append((target, found))

        return broken, ambiguous

    def check_broken_links(self) -> Dict[str, List[str]]:
        """Links that name no module, by source module.

        See :meth:`find_unresolved_links`, which also reports ambiguous links.
        """
        return self.find_unresolved_links()[0]

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
        modules_dir = get_base_path() / "modules"
        module_dir = modules_dir / module_path
        return module_dir.exists() and module_dir.is_dir()

    def _get_parent_module(self, module_path: str) -> Optional[str]:
        """Get parent module path from child path.

        Args:
            module_path: Child module path (e.g., 'projects/memory-note/context-builder')

        Returns:
            Parent module path (e.g., 'projects/memory-note') or None if no parent
        """
        parts = module_path.split('/')
        if len(parts) <= 1:
            return None
        return '/'.join(parts[:-1])

    def _build_hierarchical_edges(self, all_module_paths: Set[str]) -> List[dict]:
        """Build parent-child edges from directory structure.

        Args:
            all_module_paths: Set of all module paths

        Returns:
            List of edge dictionaries with type "parent-child"
        """
        edges = []
        for module_path in all_module_paths:
            parent_path = self._get_parent_module(module_path)
            if parent_path and parent_path in all_module_paths:
                edges.append({
                    "source": parent_path,
                    "target": module_path,
                    "type": "parent-child"
                })
        return edges

    def _get_module_description(self, module_path: str) -> Optional[str]:
        """Get module description from module.md.

        Args:
            module_path: Module path

        Returns:
            Description string or None if not found
        """
        modules_dir = get_base_path() / "modules"
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
        """Export graph as JSON structure with hierarchical relationships.

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
                        "type": "parent-child"
                    },
                    {
                        "source": "projects/memory-note",
                        "target": "projects/memory-note/context-builder",
                        "type": "connection",
                        "source_file": ".memory/modules/...",
                        "line_number": 42
                    }
                ],
                "stats": {
                    "total_connections": 2,
                    "total_modules": 2,
                    "connected_modules": 2,
                    "orphaned_modules": 0,
                    "wiki_links": 1,
                    "parent_child_links": 1
                }
            }
        """
        # Get ALL modules (not just connected ones)
        from memory_tool.core.module import ModuleManager
        manager = ModuleManager()
        all_modules_list = manager.discover_all_modules()
        # Use as_posix() for consistent path handling across platforms
        # This also ensures proper encoding for non-ASCII characters (e.g., Korean)
        all_module_paths = {m.as_posix() for m in all_modules_list}

        # Build nodes for ALL modules
        nodes = []
        for module_path in sorted(all_module_paths):
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

        # Build edges: wiki-links + hierarchical
        edges = []

        # 1. Wiki-link edges (existing functionality)
        for module in sorted(all_module_paths):
            connections = self.get_outgoing_connections(module)
            for conn in connections:
                edges.append({
                    "source": conn.source,
                    "target": conn.target,
                    "type": "connection",
                    "source_file": conn.source_file,
                    "line_number": conn.line_number,
                })

        # 2. Hierarchical edges (parent-child relationships)
        hierarchical_edges = self._build_hierarchical_edges(all_module_paths)
        edges.extend(hierarchical_edges)

        # Calculate stats
        wiki_links = [e for e in edges if e["type"] == "connection"]
        parent_child_links = [e for e in edges if e["type"] == "parent-child"]

        stats = {
            "total_connections": len(edges),
            "total_modules": len(all_module_paths),
            "connected_modules": len(all_module_paths),  # All modules are now included
            "orphaned_modules": 0,  # With hierarchy, no modules are truly orphaned
            "wiki_links": len(wiki_links),
            "parent_child_links": len(parent_child_links),
        }

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": stats,
        }
