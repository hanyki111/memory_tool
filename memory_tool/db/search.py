"""SQLite-based search for memory_tool."""

import sqlite3
from pathlib import Path
from typing import List, Dict, Optional


class SQLiteSearcher:
    """Performs full-text search using SQLite FTS5."""

    def __init__(self, memory_root: Path):
        """Initialize searcher.

        Args:
            memory_root: Path to .memory/ directory
        """
        self.memory_root = memory_root
        self.index_path = memory_root / ".index.db"

    @staticmethod
    def available(memory_root: Path) -> bool:
        """Check if SQLite index is available and valid.

        Args:
            memory_root: Path to .memory/ directory

        Returns:
            True if index exists and schema is valid
        """
        index_path = memory_root / ".index.db"
        if not index_path.exists():
            return False

        try:
            conn = sqlite3.connect(index_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='entries_fts'"
            )
            result = cursor.fetchone()
            conn.close()
            return result is not None
        except Exception:
            return False

    def search(
        self,
        pattern: str,
        entry_type: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        max_results: Optional[int] = None,
    ) -> List[Dict]:
        """Perform full-text search.

        Args:
            pattern: Search pattern (FTS5 query)
            entry_type: Filter by entry type ('timeline', 'decision', etc.)
            date_from: Filter by date >= this (YYYY-MM-DD)
            date_to: Filter by date <= this (YYYY-MM-DD)
            max_results: Maximum number of results

        Returns:
            List of search results with metadata
        """
        if not self.index_path.exists():
            return []

        conn = sqlite3.connect(self.index_path)
        cursor = conn.cursor()

        # Build query
        query = "SELECT content, file_path, entry_date, entry_time, entry_type FROM entries_fts WHERE entries_fts MATCH ?"
        params = [pattern]

        # Add filters
        if entry_type:
            query += " AND entry_type = ?"
            params.append(entry_type)

        if date_from:
            query += " AND entry_date >= ?"
            params.append(date_from)

        if date_to:
            query += " AND entry_date <= ?"
            params.append(date_to)

        # Order by relevance (FTS5 rank)
        query += " ORDER BY rank"

        # Limit results
        if max_results:
            query += f" LIMIT {max_results}"

        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        except Exception as e:
            print(f"Search error: {e}")
            return []
        finally:
            conn.close()

        # Format results
        results = []
        for content, file_path, entry_date, entry_time, entry_type in rows:
            result = {
                "content": content,
                "file_path": file_path,
                "entry_type": entry_type,
            }

            if entry_date:
                result["entry_date"] = entry_date
            if entry_time:
                result["entry_time"] = entry_time

            results.append(result)

        return results

    def get_context(self, file_path: str, target_content: str, lines_before: int = 2, lines_after: int = 2) -> Optional[str]:
        """Get context lines around a match in a file.

        Args:
            file_path: Relative file path from .memory/
            target_content: Content to find
            lines_before: Number of lines before match
            lines_after: Number of lines after match

        Returns:
            Context string or None if file not found
        """
        full_path = self.memory_root / file_path
        if not full_path.exists():
            return None

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Find matching line
            target_line_idx = None
            for idx, line in enumerate(lines):
                if target_content.strip() in line:
                    target_line_idx = idx
                    break

            if target_line_idx is None:
                return None

            # Extract context
            start_idx = max(0, target_line_idx - lines_before)
            end_idx = min(len(lines), target_line_idx + lines_after + 1)

            context_lines = lines[start_idx:end_idx]
            return "".join(context_lines)

        except Exception:
            return None
