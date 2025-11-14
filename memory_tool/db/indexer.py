"""SQLite indexing for timeline and documents."""

import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
import re


class IndexManager:
    """Manages SQLite FTS5 index for memory_tool."""

    def __init__(self, memory_root: Path):
        """Initialize index manager.

        Args:
            memory_root: Path to .memory/ directory
        """
        self.memory_root = memory_root
        self.index_path = memory_root / ".index.db"

    @staticmethod
    def available() -> bool:
        """Check if SQLite with FTS5 is available."""
        try:
            conn = sqlite3.connect(":memory:")
            conn.execute("CREATE VIRTUAL TABLE test USING fts5(content)")
            conn.close()
            return True
        except Exception:
            return False

    def create_database(self) -> None:
        """Create database schema."""
        conn = sqlite3.connect(self.index_path)
        cursor = conn.cursor()

        # FTS5 virtual table for full-text search
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
                content,
                file_path,
                entry_date,
                entry_time,
                entry_type,
                tokenize='porter unicode61'
            )
        """)

        # Metadata table for tracking file changes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS index_meta (
                file_path TEXT PRIMARY KEY,
                last_modified INTEGER,
                file_hash TEXT
            )
        """)

        conn.commit()
        conn.close()

    def _compute_file_hash(self, file_path: Path) -> str:
        """Compute SHA256 hash of file content."""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""

    def _parse_timeline_entry(self, line: str, file_path: Path) -> Optional[Tuple[str, str, str]]:
        """Parse timeline entry line.

        Args:
            line: Timeline line (e.g., "- 08:30 | message")
            file_path: Path to timeline file

        Returns:
            (time, message, date) or None if not a valid entry
        """
        # Match: "- HH:MM | message" or "- H:MM | message"
        match = re.match(r"^-\s+(\d{1,2}:\d{2})\s+\|\s+(.+)$", line.strip())
        if not match:
            return None

        time_str, message = match.groups()

        # Extract date from file path: timeline/YYYY-MM/DD.md
        parts = file_path.parts
        if len(parts) >= 3 and parts[-3] == "timeline":
            year_month = parts[-2]  # YYYY-MM
            day = parts[-1].replace(".md", "")  # DD
            date_str = f"{year_month}-{day}"
            return (time_str, message, date_str)

        return None

    def index_file(self, file_path: Path, force: bool = False) -> int:
        """Index a single file.

        Args:
            file_path: Path to file (relative to project root)
            force: Force reindex even if file hasn't changed

        Returns:
            Number of entries indexed
        """
        if not file_path.exists():
            return 0

        # Check if we need to reindex
        if not force and self.index_path.exists():
            try:
                conn = sqlite3.connect(self.index_path)
                cursor = conn.cursor()

                cursor.execute(
                    "SELECT file_hash FROM index_meta WHERE file_path = ?",
                    (str(file_path.relative_to(file_path.anchor)),),
                )
                row = cursor.fetchone()
                conn.close()

                current_hash = self._compute_file_hash(file_path)
                if row and row[0] == current_hash:
                    return 0  # No changes
            except Exception:
                # If any error, reindex the file
                pass

        # Determine entry type
        rel_path = file_path.relative_to(self.memory_root)
        if rel_path.parts[0] == "timeline":
            entry_type = "timeline"
        elif "decisions" in file_path.name:
            entry_type = "decision"
        elif "current" in file_path.name:
            entry_type = "current"
        elif rel_path.parts[0] == "concepts":
            entry_type = "concept"
        else:
            entry_type = "document"

        # Read and parse file
        entries = []
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            if entry_type == "timeline":
                # Parse timeline entries
                for line in lines:
                    parsed = self._parse_timeline_entry(line, file_path)
                    if parsed:
                        time_str, message, date_str = parsed
                        entries.append((
                            message,
                            str(rel_path),
                            date_str,
                            time_str,
                            entry_type,
                        ))
            else:
                # Index whole file as single entry
                content = "".join(lines)
                entries.append((
                    content,
                    str(rel_path),
                    "",  # No date
                    "",  # No time
                    entry_type,
                ))

        except Exception as e:
            print(f"Error indexing {file_path}: {e}")
            return 0

        if not entries:
            return 0

        # Insert into database
        conn = sqlite3.connect(self.index_path)
        cursor = conn.cursor()

        # Delete old entries for this file
        cursor.execute(
            "DELETE FROM entries_fts WHERE file_path = ?",
            (str(rel_path),),
        )

        # Insert new entries
        cursor.executemany(
            "INSERT INTO entries_fts (content, file_path, entry_date, entry_time, entry_type) VALUES (?, ?, ?, ?, ?)",
            entries,
        )

        # Update metadata
        cursor.execute(
            "INSERT OR REPLACE INTO index_meta (file_path, last_modified, file_hash) VALUES (?, ?, ?)",
            (
                str(rel_path),
                int(file_path.stat().st_mtime),
                self._compute_file_hash(file_path),
            ),
        )

        conn.commit()
        conn.close()

        return len(entries)

    def index_all(self, exclude_archive: bool = True) -> int:
        """Index all files in .memory/.

        Args:
            exclude_archive: Exclude archive/ directories

        Returns:
            Total number of entries indexed
        """
        # Always ensure database schema exists
        if not self.index_path.exists():
            self.create_database()
        else:
            # Check if schema is valid
            try:
                conn = sqlite3.connect(self.index_path)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='entries_fts'"
                )
                if not cursor.fetchone():
                    # Schema invalid, recreate
                    conn.close()
                    self.create_database()
                else:
                    conn.close()
            except Exception:
                # Database corrupted, recreate
                self.create_database()

        total_entries = 0

        # Timeline files
        timeline_dir = self.memory_root / "timeline"
        if timeline_dir.exists():
            for file_path in timeline_dir.rglob("*.md"):
                if exclude_archive and "archive" in file_path.parts:
                    continue
                total_entries += self.index_file(file_path)

        # Module files
        modules_dir = self.memory_root / "modules"
        if modules_dir.exists():
            for file_path in modules_dir.rglob("*.md"):
                if exclude_archive and "archive" in file_path.parts:
                    continue
                if file_path.name in ["decisions.md", "current.md"]:
                    total_entries += self.index_file(file_path)

        # Concept files
        concepts_dir = self.memory_root / "concepts"
        if concepts_dir.exists():
            for file_path in concepts_dir.rglob("*.md"):
                total_entries += self.index_file(file_path)

        return total_entries

    def is_index_fresh(self) -> bool:
        """Check if index is up to date with files.

        Returns:
            True if index is fresh, False if rebuild needed
        """
        if not self.index_path.exists():
            return False

        conn = sqlite3.connect(self.index_path)
        cursor = conn.cursor()

        # Check if schema exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='entries_fts'"
        )
        if not cursor.fetchone():
            conn.close()
            return False

        # Check if any tracked file has changed
        cursor.execute("SELECT file_path, file_hash FROM index_meta")
        rows = cursor.fetchall()
        conn.close()

        for rel_path_str, stored_hash in rows:
            file_path = self.memory_root / rel_path_str
            if not file_path.exists():
                return False  # File deleted, needs rebuild

            current_hash = self._compute_file_hash(file_path)
            if current_hash != stored_hash:
                return False  # File changed

        return True

    def get_stats(self) -> dict:
        """Get index statistics.

        Returns:
            Dictionary with index stats
        """
        if not self.index_path.exists():
            return {"status": "not_created"}

        conn = sqlite3.connect(self.index_path)
        cursor = conn.cursor()

        # Count entries by type
        cursor.execute("SELECT entry_type, COUNT(*) FROM entries_fts GROUP BY entry_type")
        counts = dict(cursor.fetchall())

        # Total entries
        cursor.execute("SELECT COUNT(*) FROM entries_fts")
        total = cursor.fetchone()[0]

        # Index size
        size_bytes = self.index_path.stat().st_size

        conn.close()

        return {
            "status": "ok",
            "total_entries": total,
            "by_type": counts,
            "size_bytes": size_bytes,
            "size_mb": round(size_bytes / 1024 / 1024, 2),
        }
