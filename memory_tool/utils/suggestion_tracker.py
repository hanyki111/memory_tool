"""Track suggestion display to avoid spam."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


class SuggestionTracker:
    """Track when suggestions were last shown to avoid spam."""

    def __init__(self, memory_dir: Path):
        """Initialize suggestion tracker.

        Args:
            memory_dir: Path to .memory directory
        """
        self.memory_dir = Path(memory_dir)
        self.cache_file = self.memory_dir / ".suggestion_cache.json"

    def should_show_suggestion(
        self,
        suggestion_type: str,
        cooldown_hours: int = 24,
        force: bool = False
    ) -> bool:
        """Check if enough time has passed since last suggestion.

        Args:
            suggestion_type: Type of suggestion (e.g., "document-health-m", "document-health-module")
            cooldown_hours: Hours to wait between suggestions (default: 24)
            force: If True, always show suggestion

        Returns:
            True if suggestion should be shown
        """
        if force:
            return True

        cache = self._load_cache()

        # Check if this suggestion type was shown recently
        if suggestion_type in cache:
            last_shown = datetime.fromisoformat(cache[suggestion_type])
            cooldown = timedelta(hours=cooldown_hours)

            if datetime.now() - last_shown < cooldown:
                return False

        return True

    def mark_suggestion_shown(self, suggestion_type: str):
        """Mark that a suggestion was shown.

        Args:
            suggestion_type: Type of suggestion
        """
        cache = self._load_cache()
        cache[suggestion_type] = datetime.now().isoformat()
        self._save_cache(cache)

    def reset(self, suggestion_type: Optional[str] = None):
        """Reset suggestion tracking.

        Args:
            suggestion_type: If provided, reset only this type. If None, reset all.
        """
        if suggestion_type is None:
            # Reset all
            self.cache_file.unlink(missing_ok=True)
        else:
            # Reset specific type
            cache = self._load_cache()
            if suggestion_type in cache:
                del cache[suggestion_type]
                self._save_cache(cache)

    def get_last_shown(self, suggestion_type: str) -> Optional[datetime]:
        """Get when a suggestion was last shown.

        Args:
            suggestion_type: Type of suggestion

        Returns:
            datetime when last shown, or None if never shown
        """
        cache = self._load_cache()
        if suggestion_type in cache:
            return datetime.fromisoformat(cache[suggestion_type])
        return None

    def _load_cache(self) -> dict:
        """Load suggestion cache from file.

        Returns:
            Dictionary mapping suggestion types to last shown timestamps
        """
        if not self.cache_file.exists():
            return {}

        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_cache(self, cache: dict):
        """Save suggestion cache to file.

        Args:
            cache: Dictionary to save
        """
        try:
            # Ensure .memory directory exists
            self.memory_dir.mkdir(parents=True, exist_ok=True)

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # Fail silently, not critical
