"""Graph version management and history tracking."""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Tuple
from datetime import datetime


class GraphVersion:
    """Represents a snapshot of the graph at a point in time."""

    def __init__(
        self,
        version_id: int,
        timestamp: datetime,
        total_connections: int,
        total_modules: int,
        connections_data: str,
        notes: str = "",
    ):
        """Initialize graph version.

        Args:
            version_id: Unique version ID
            timestamp: When this version was created
            total_connections: Total number of connections
            total_modules: Total number of modules
            connections_data: JSON string of connection data
            notes: Optional notes about this version
        """
        self.version_id = version_id
        self.timestamp = timestamp
        self.total_connections = total_connections
        self.total_modules = total_modules
        self.connections_data = connections_data
        self.notes = notes

    def get_connections(self) -> List[Tuple[str, str]]:
        """Parse and return connections.

        Returns:
            List of (source, target) tuples
        """
        try:
            data = json.loads(self.connections_data)
            return [(c["source"], c["target"]) for c in data]
        except (json.JSONDecodeError, KeyError):
            return []


class GraphVersionManager:
    """Manage graph version history."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize version manager.

        Args:
            db_path: Path to connections database (defaults to .memory/.connections.db)
        """
        if db_path is None:
            db_path = Path.cwd() / ".memory" / ".connections.db"

        self.db_path = db_path
        self._ensure_version_table()

    def _ensure_version_table(self):
        """Create version table if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Create versions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS graph_versions (
                    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_connections INTEGER NOT NULL,
                    total_modules INTEGER NOT NULL,
                    connections_data TEXT NOT NULL,
                    notes TEXT DEFAULT ''
                )
            """)

            # Create index on timestamp
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_version_timestamp
                ON graph_versions(timestamp DESC)
            """)

            conn.commit()

        finally:
            conn.close()

    def create_snapshot(self, notes: str = "") -> int:
        """Create a snapshot of the current graph state.

        Args:
            notes: Optional notes about this version

        Returns:
            Version ID of the created snapshot
        """
        from memory_tool.core.connections import ConnectionGraph

        graph = ConnectionGraph(self.db_path)

        # Get current graph state
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Get all connections
            cursor.execute("""
                SELECT DISTINCT source_module, target_module
                FROM connections
                ORDER BY source_module, target_module
            """)

            connections = cursor.fetchall()

            # Get stats
            stats = graph.get_graph_stats()

            # Serialize connections to JSON
            connections_json = json.dumps([
                {"source": source, "target": target}
                for source, target in connections
            ])

            # Insert version
            cursor.execute("""
                INSERT INTO graph_versions
                (total_connections, total_modules, connections_data, notes)
                VALUES (?, ?, ?, ?)
            """, (
                stats["total_connections"],
                stats["connected_modules"],
                connections_json,
                notes,
            ))

            version_id = cursor.lastrowid
            conn.commit()

            return version_id

        finally:
            conn.close()

    def get_version(self, version_id: int) -> Optional[GraphVersion]:
        """Get a specific version.

        Args:
            version_id: Version ID to retrieve

        Returns:
            GraphVersion object or None if not found
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT version_id, timestamp, total_connections, total_modules,
                       connections_data, notes
                FROM graph_versions
                WHERE version_id = ?
            """, (version_id,))

            row = cursor.fetchone()

            if row:
                return GraphVersion(
                    version_id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    total_connections=row[2],
                    total_modules=row[3],
                    connections_data=row[4],
                    notes=row[5],
                )

            return None

        finally:
            conn.close()

    def get_latest_version(self) -> Optional[GraphVersion]:
        """Get the most recent version.

        Returns:
            GraphVersion object or None if no versions exist
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT version_id, timestamp, total_connections, total_modules,
                       connections_data, notes
                FROM graph_versions
                ORDER BY timestamp DESC
                LIMIT 1
            """)

            row = cursor.fetchone()

            if row:
                return GraphVersion(
                    version_id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    total_connections=row[2],
                    total_modules=row[3],
                    connections_data=row[4],
                    notes=row[5],
                )

            return None

        finally:
            conn.close()

    def list_versions(self, limit: int = 10) -> List[GraphVersion]:
        """List recent versions.

        Args:
            limit: Maximum number of versions to return

        Returns:
            List of GraphVersion objects (most recent first)
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT version_id, timestamp, total_connections, total_modules,
                       connections_data, notes
                FROM graph_versions
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()

            return [
                GraphVersion(
                    version_id=row[0],
                    timestamp=datetime.fromisoformat(row[1]),
                    total_connections=row[2],
                    total_modules=row[3],
                    connections_data=row[4],
                    notes=row[5],
                )
                for row in rows
            ]

        finally:
            conn.close()

    def diff_versions(
        self,
        version1_id: int,
        version2_id: int,
    ) -> Dict[str, List[Tuple[str, str]]]:
        """Compare two versions and return differences.

        Args:
            version1_id: First version ID (older)
            version2_id: Second version ID (newer)

        Returns:
            Dictionary with 'added', 'removed', 'unchanged' keys
        """
        v1 = self.get_version(version1_id)
        v2 = self.get_version(version2_id)

        if not v1 or not v2:
            return {"added": [], "removed": [], "unchanged": []}

        # Get connections from both versions
        conn1 = set(v1.get_connections())
        conn2 = set(v2.get_connections())

        # Calculate differences
        added = list(conn2 - conn1)
        removed = list(conn1 - conn2)
        unchanged = list(conn1 & conn2)

        # Sort for consistent output
        added.sort()
        removed.sort()
        unchanged.sort()

        return {
            "added": added,
            "removed": removed,
            "unchanged": unchanged,
        }

    def get_version_count(self) -> int:
        """Get total number of versions.

        Returns:
            Total version count
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM graph_versions")
            count = cursor.fetchone()[0]

            return count

        finally:
            conn.close()

    def delete_old_versions(self, keep_count: int = 50) -> int:
        """Delete old versions, keeping only the most recent ones.

        Args:
            keep_count: Number of versions to keep

        Returns:
            Number of versions deleted
        """
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Get version ID threshold
            cursor.execute("""
                SELECT version_id FROM graph_versions
                ORDER BY timestamp DESC
                LIMIT 1 OFFSET ?
            """, (keep_count - 1,))

            row = cursor.fetchone()

            if not row:
                # Not enough versions to delete
                return 0

            threshold_id = row[0]

            # Delete old versions
            cursor.execute("""
                DELETE FROM graph_versions
                WHERE version_id < ?
            """, (threshold_id,))

            deleted_count = cursor.rowcount
            conn.commit()

            return deleted_count

        finally:
            conn.close()

    def analyze_growth(self, days: int = 30) -> Dict:
        """Analyze graph growth over time.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with growth statistics
        """
        from datetime import timedelta

        cutoff_date = datetime.now() - timedelta(days=days)

        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Get versions within time range
            cursor.execute("""
                SELECT version_id, timestamp, total_connections, total_modules
                FROM graph_versions
                WHERE timestamp >= ?
                ORDER BY timestamp ASC
            """, (cutoff_date.isoformat(),))

            rows = cursor.fetchall()

            if not rows:
                return {
                    "period_days": days,
                    "versions_count": 0,
                    "connections_growth": 0,
                    "modules_growth": 0,
                }

            # First and last versions
            first = rows[0]
            last = rows[-1]

            connections_growth = last[2] - first[2]
            modules_growth = last[3] - first[3]

            return {
                "period_days": days,
                "versions_count": len(rows),
                "start_date": first[1],
                "end_date": last[1],
                "connections_start": first[2],
                "connections_end": last[2],
                "connections_growth": connections_growth,
                "modules_start": first[3],
                "modules_end": last[3],
                "modules_growth": modules_growth,
            }

        finally:
            conn.close()
