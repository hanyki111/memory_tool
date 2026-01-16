import json
import os
from pathlib import Path
from typing import Dict, Optional

class NotionCache:
    """Manages local cache for Notion page IDs to reduce API calls."""
    
    def __init__(self):
        # Determine cache path: .memory/cache/notion_pages.json
        self.base_path = Path.cwd() / ".memory"
        self.cache_dir = self.base_path / "cache"
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
