import json
import os
from pathlib import Path
from typing import Dict, Optional
from memory_tool.utils.paths import get_base_path

class NotionCache:
    """Manages local cache for Notion page IDs to reduce API calls."""

    def __init__(self, backend_name: str = None):
        """Initialize cache.

        Args:
            backend_name: Optional backend name for cache isolation.
                         None/primary uses default 'notion_pages.json'.
                         Secondary uses 'notion_pages_{backend_name}.json'.
        """
        # Determine cache path: .memory/cache/notion_pages.json
        self.base_path = get_base_path()
        self.cache_dir = self.base_path / "cache"
        if backend_name and backend_name != "primary":
            self.cache_file = self.cache_dir / f"notion_pages_{backend_name}.json"
        else:
            self.cache_file = self.cache_dir / "notion_pages.json"
        
        self._ensure_cache_dir()
        self.cache: Dict[str, str] = self._load_cache()

    def _ensure_cache_dir(self):
        """Ensure cache directory exists."""
        if not self.base_path.exists():
            # If .memory doesn't exist (not initialized), try to use home dir or tmp
            # But normally .memory should exist. We'll proceed silently if possible.
            pass
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_cache(self) -> Dict[str, str]:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return {}
        try:
            return json.loads(self.cache_file.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_cache(self):
        """Save cache to disk."""
        try:
            self.cache_file.write_text(json.dumps(self.cache, indent=2), encoding="utf-8")
        except Exception:
            pass

    def get_page_id(self, key: str) -> Optional[str]:
        """Get page ID for a key (e.g., '2026-01-16')."""
        return self.cache.get(key)

    def set_page_id(self, key: str, page_id: str):
        """Set page ID for a key and save."""
        self.cache[key] = page_id
        self._save_cache()

    def invalidate(self, key: str):
        """Remove a specific key from cache and save to disk."""
        if key in self.cache:
            del self.cache[key]
            self._save_cache()

    def invalidate_date(self, date_str: str):
        """Invalidate cache entries for a specific date.

        Removes both the day key (day_YYYY-MM-DD) and the month key (month_YYYY-MM)
        so that the next lookup will fetch fresh data from Notion.

        Args:
            date_str: Date string in YYYY-MM-DD format
        """
        # Invalidate day key
        day_key = f"day_{date_str}"
        self.invalidate(day_key)

        # Invalidate month key
        parts = date_str.rsplit("-", 1)
        if len(parts) == 2:
            month_key = f"month_{parts[0]}"
            self.invalidate(month_key)
