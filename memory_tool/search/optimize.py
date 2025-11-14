"""Search index optimization utilities."""

import sqlite3
from pathlib import Path
from typing import Dict


class IndexOptimizer:
    """Optimize SQLite FTS5 search indexes for better performance."""

    def __init__(self, db_path: Path):
        """
        Initialize index optimizer.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path

    def optimize_fts5(self) -> Dict[str, any]:
        """
        Optimize FTS5 full-text search index.

        Performs:
        - FTS5 'optimize' command (merges b-tree segments)
        - Statistics gathering

        Returns:
            Dictionary with optimization statistics
        """
        if not self.db_path.exists():
            return {"error": "Database not found"}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get stats before optimization
            cursor.execute("SELECT COUNT(*) FROM search_fts")
            entry_count = cursor.fetchone()[0]

            # Check if search_fts table exists
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='search_fts'"
            )
            if not cursor.fetchone():
                conn.close()
                return {"error": "FTS5 table not found"}

            # Optimize FTS5 index
            # This merges b-tree segments for better query performance
            cursor.execute("INSERT INTO search_fts(search_fts) VALUES('optimize')")

            conn.commit()
            conn.close()

            return {
                "success": True,
                "entries_indexed": entry_count,
                "message": "FTS5 index optimized successfully",
            }

        except sqlite3.Error as e:
            return {
                "error": f"Optimization failed: {str(e)}"
            }

    def vacuum_database(self) -> Dict[str, any]:
        """
        Vacuum database to reclaim space and defragment.

        Returns:
            Dictionary with vacuum statistics
        """
        if not self.db_path.exists():
            return {"error": "Database not found"}

        try:
            # Get size before vacuum
            size_before = self.db_path.stat().st_size

            conn = sqlite3.connect(self.db_path)
            conn.execute("VACUUM")
            conn.close()

            # Get size after vacuum
            size_after = self.db_path.stat().st_size
            size_reduced = size_before - size_after
            percent_reduced = (size_reduced / size_before * 100) if size_before > 0 else 0

            return {
                "success": True,
                "size_before_mb": size_before / (1024 * 1024),
                "size_after_mb": size_after / (1024 * 1024),
                "size_reduced_mb": size_reduced / (1024 * 1024),
                "percent_reduced": percent_reduced,
                "message": "Database vacuumed successfully",
            }

        except sqlite3.Error as e:
            return {
                "error": f"Vacuum failed: {str(e)}"
            }

    def analyze_database(self) -> Dict[str, any]:
        """
        Analyze database to gather statistics for query optimization.

        Returns:
            Dictionary with analysis statistics
        """
        if not self.db_path.exists():
            return {"error": "Database not found"}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Run ANALYZE to gather query planning statistics
            cursor.execute("ANALYZE")

            # Get table statistics
            cursor.execute("SELECT COUNT(*) FROM search_fts")
            fts_entries = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM timeline_entries")
            timeline_entries = cursor.fetchone()[0]

            conn.commit()
            conn.close()

            return {
                "success": True,
                "fts_entries": fts_entries,
                "timeline_entries": timeline_entries,
                "message": "Database analyzed successfully",
            }

        except sqlite3.Error as e:
            return {
                "error": f"Analysis failed: {str(e)}"
            }

    def full_optimize(self) -> Dict[str, any]:
        """
        Perform full optimization: optimize FTS5, vacuum, and analyze.

        Returns:
            Dictionary with combined statistics
        """
        results = {}

        # Step 1: Optimize FTS5
        fts_result = self.optimize_fts5()
        results["fts5_optimize"] = fts_result

        # Step 2: Analyze
        analyze_result = self.analyze_database()
        results["analyze"] = analyze_result

        # Step 3: Vacuum
        vacuum_result = self.vacuum_database()
        results["vacuum"] = vacuum_result

        # Determine overall success
        all_success = all(
            r.get("success", False) or r.get("error") is None
            for r in [fts_result, analyze_result, vacuum_result]
        )

        results["overall_success"] = all_success
        results["message"] = "Full optimization completed" if all_success else "Optimization completed with errors"

        return results

    def get_index_stats(self) -> Dict[str, any]:
        """
        Get current index statistics without modifying the database.

        Returns:
            Dictionary with index statistics
        """
        if not self.db_path.exists():
            return {"error": "Database not found"}

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Database size
            db_size = self.db_path.stat().st_size

            # Entry counts
            cursor.execute("SELECT COUNT(*) FROM search_fts")
            fts_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM timeline_entries")
            timeline_count = cursor.fetchone()[0]

            conn.close()

            return {
                "success": True,
                "database_size_mb": db_size / (1024 * 1024),
                "fts_entries": fts_count,
                "timeline_entries": timeline_count,
            }

        except sqlite3.Error as e:
            return {
                "error": f"Failed to get stats: {str(e)}"
            }
