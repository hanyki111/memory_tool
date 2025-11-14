"""Search result caching with TTL support."""

import json
import hashlib
import time
from pathlib import Path
from typing import List, Optional
from ..core.search import SearchResult
from datetime import datetime


class SearchCache:
    """Cache search results with time-to-live (TTL) support."""

    def __init__(self, cache_dir: Path, ttl_seconds: int = 3600):
        """
        Initialize search cache.

        Args:
            cache_dir: Directory to store cache files
            ttl_seconds: Time-to-live for cache entries (default: 1 hour)
        """
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_key(self, query: str, **kwargs) -> str:
        """
        Generate cache key from query and parameters.

        Args:
            query: Search query
            **kwargs: Additional search parameters (filters, etc.)

        Returns:
            Hash-based cache key
        """
        # Combine query and kwargs into a string
        cache_str = f"{query}|{sorted(kwargs.items())}"

        # Generate hash
        return hashlib.sha256(cache_str.encode()).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get cache file path for given key."""
        return self.cache_dir / f"{cache_key}.json"

    def get(
        self,
        query: str,
        **kwargs
    ) -> Optional[List[SearchResult]]:
        """
        Retrieve cached search results.

        Args:
            query: Search query
            **kwargs: Search parameters

        Returns:
            Cached results if found and not expired, None otherwise
        """
        cache_key = self._get_cache_key(query, **kwargs)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return None

        try:
            # Load cache data
            data = json.loads(cache_path.read_text(encoding='utf-8'))

            # Check TTL
            cached_at = data.get("cached_at", 0)
            now = time.time()

            if now - cached_at > self.ttl_seconds:
                # Cache expired
                cache_path.unlink()  # Delete expired cache
                return None

            # Parse results
            results = []
            for item in data.get("results", []):
                result = SearchResult(
                    file_path=Path(item["file_path"]),
                    line_number=item["line_number"],
                    line_content=item["line_content"],
                    match_context=item["match_context"],
                    score=item.get("score", 1.0),
                    date=datetime.fromisoformat(item["date"]) if item.get("date") else None,
                )
                results.append(result)

            return results

        except (json.JSONDecodeError, KeyError, ValueError):
            # Cache corrupted, delete it
            if cache_path.exists():
                cache_path.unlink()
            return None

    def set(
        self,
        query: str,
        results: List[SearchResult],
        **kwargs
    ):
        """
        Cache search results.

        Args:
            query: Search query
            results: Search results to cache
            **kwargs: Search parameters
        """
        cache_key = self._get_cache_key(query, **kwargs)
        cache_path = self._get_cache_path(cache_key)

        try:
            # Serialize results
            serialized_results = []
            for result in results:
                serialized_results.append({
                    "file_path": str(result.file_path),
                    "line_number": result.line_number,
                    "line_content": result.line_content,
                    "match_context": result.match_context,
                    "score": result.score,
                    "date": result.date.isoformat() if result.date else None,
                })

            # Build cache data
            cache_data = {
                "cached_at": time.time(),
                "query": query,
                "params": kwargs,
                "results": serialized_results,
            }

            # Write to file
            cache_path.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2), encoding='utf-8')

        except (IOError, TypeError):
            # Failed to cache, silently ignore
            pass

    def clear(self):
        """Clear all cache entries."""
        for cache_file in self.cache_dir.glob("*.json"):
            try:
                cache_file.unlink()
            except OSError:
                pass

    def clear_expired(self):
        """Clear expired cache entries."""
        now = time.time()

        for cache_file in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(cache_file.read_text(encoding='utf-8'))
                cached_at = data.get("cached_at", 0)

                if now - cached_at > self.ttl_seconds:
                    cache_file.unlink()

            except (json.JSONDecodeError, IOError, KeyError):
                # Corrupted cache, delete it
                cache_file.unlink()

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (entries, size, oldest/newest)
        """
        cache_files = list(self.cache_dir.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files if f.exists())

        timestamps = []
        for cache_file in cache_files:
            try:
                data = json.loads(cache_file.read_text(encoding='utf-8'))
                timestamps.append(data.get("cached_at", 0))
            except (json.JSONDecodeError, IOError, KeyError):
                pass

        return {
            "entries": len(cache_files),
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "oldest": datetime.fromtimestamp(min(timestamps)).isoformat() if timestamps else None,
            "newest": datetime.fromtimestamp(max(timestamps)).isoformat() if timestamps else None,
        }
