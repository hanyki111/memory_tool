"""Sync state management for Notion synchronization."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any

from memory_tool.notion.models import (
    FileSyncState,
    ModuleSyncState,
    TimelineDaySyncState,
    SyncDirection,
    ConflictResolution,
)


class SyncStateManager:
    """Manages sync state persistence and change detection."""

    STATE_VERSION = "1.0"
    CLOCK_SKEW_BUFFER = timedelta(seconds=5)

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize state manager.

        Args:
            base_path: Base path for .memory directory. Defaults to cwd.
        """
        self.base_path = base_path or Path.cwd() / ".memory"
        self.cache_dir = self.base_path / "cache"
        self.state_file = self.cache_dir / "notion_sync_state.json"
        self._state: Optional[Dict[str, Any]] = None

    def _ensure_cache_dir(self):
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> Dict[str, Any]:
        """Load state from disk."""
        if self._state is not None:
            return self._state

        if not self.state_file.exists():
            self._state = self._empty_state()
            return self._state

        try:
            content = self.state_file.read_text(encoding="utf-8")
            self._state = json.loads(content)

            # Check version and migrate if needed
            if self._state.get("version") != self.STATE_VERSION:
                self._state = self._migrate_state(self._state)

            return self._state
        except (json.JSONDecodeError, Exception):
            self._state = self._empty_state()
            return self._state

    def _empty_state(self) -> Dict[str, Any]:
        """Create empty state structure."""
        return {
            "version": self.STATE_VERSION,
            "last_full_sync": None,
            "modules": {},
            "timeline": {},
        }

    def _migrate_state(self, old_state: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate state from older versions."""
        # Currently just reset if version mismatch
        return self._empty_state()

    def save_state(self):
        """Save state to disk."""
        if self._state is None:
            return

        self._ensure_cache_dir()

        try:
            content = json.dumps(self._state, indent=2, ensure_ascii=False)
            self.state_file.write_text(content, encoding="utf-8")
        except Exception:
            pass

    def get_module_state(self, module_path: str) -> ModuleSyncState:
        """Get sync state for a module.

        Args:
            module_path: Module path (e.g., "projects/memory-tool")

        Returns:
            ModuleSyncState for the module
        """
        state = self._load_state()
        module_data = state.get("modules", {}).get(module_path, {})

        if module_data:
            return ModuleSyncState.from_dict(module_data)
        return ModuleSyncState()

    def set_module_state(self, module_path: str, module_state: ModuleSyncState):
        """Set sync state for a module.

        Args:
            module_path: Module path
            module_state: State to save
        """
        state = self._load_state()
        if "modules" not in state:
            state["modules"] = {}
        state["modules"][module_path] = module_state.to_dict()
        self.save_state()

    def get_file_state(self, module_path: str, file_name: str) -> FileSyncState:
        """Get sync state for a specific file.

        Args:
            module_path: Module path
            file_name: File name (e.g., "current.md")

        Returns:
            FileSyncState for the file
        """
        module_state = self.get_module_state(module_path)
        return module_state.files.get(file_name, FileSyncState())

    def set_file_state(
        self,
        module_path: str,
        file_name: str,
        file_state: FileSyncState
    ):
        """Set sync state for a specific file.

        Args:
            module_path: Module path
            file_name: File name
            file_state: State to save
        """
        module_state = self.get_module_state(module_path)
        module_state.files[file_name] = file_state
        self.set_module_state(module_path, module_state)

    def get_timeline_day_state(
        self,
        year_month: str,
        day: str
    ) -> TimelineDaySyncState:
        """Get sync state for a timeline day.

        Args:
            year_month: Year-month string (e.g., "2026-01")
            day: Day string (e.g., "16")

        Returns:
            TimelineDaySyncState for the day
        """
        state = self._load_state()
        timeline = state.get("timeline", {})
        month_data = timeline.get(year_month, {}).get("days", {})
        day_data = month_data.get(day, {})

        if day_data:
            return TimelineDaySyncState.from_dict(day_data)
        return TimelineDaySyncState()

    def set_timeline_day_state(
        self,
        year_month: str,
        day: str,
        day_state: TimelineDaySyncState
    ):
        """Set sync state for a timeline day.

        Args:
            year_month: Year-month string
            day: Day string
            day_state: State to save
        """
        state = self._load_state()

        if "timeline" not in state:
            state["timeline"] = {}
        if year_month not in state["timeline"]:
            state["timeline"][year_month] = {"days": {}}
        if "days" not in state["timeline"][year_month]:
            state["timeline"][year_month]["days"] = {}

        state["timeline"][year_month]["days"][day] = day_state.to_dict()
        self.save_state()

    def determine_sync_direction(
        self,
        local_mtime: Optional[datetime],
        notion_edited: Optional[datetime],
        last_sync: Optional[datetime],
        resolution: ConflictResolution = ConflictResolution.LAST_WRITE_WINS
    ) -> SyncDirection:
        """Determine sync direction based on timestamps.

        Args:
            local_mtime: Local file modification time
            notion_edited: Notion page last edited time
            last_sync: Last sync time
            resolution: Conflict resolution strategy

        Returns:
            SyncDirection indicating what action to take
        """
        # New file cases
        if local_mtime is None and notion_edited is None:
            return SyncDirection.SKIP

        if local_mtime is None and notion_edited is not None:
            return SyncDirection.PULL

        if local_mtime is not None and notion_edited is None:
            return SyncDirection.PUSH

        # Both exist - compare timestamps
        local_changed = (
            last_sync is None or
            local_mtime > last_sync + self.CLOCK_SKEW_BUFFER
        )
        notion_changed = (
            last_sync is None or
            notion_edited > last_sync + self.CLOCK_SKEW_BUFFER
        )

        # Neither changed
        if not local_changed and not notion_changed:
            return SyncDirection.SKIP

        # Only one changed
        if local_changed and not notion_changed:
            return SyncDirection.PUSH
        if notion_changed and not local_changed:
            return SyncDirection.PULL

        # Both changed - conflict
        if resolution == ConflictResolution.LOCAL_WINS:
            return SyncDirection.PUSH
        elif resolution == ConflictResolution.NOTION_WINS:
            return SyncDirection.PULL
        elif resolution == ConflictResolution.LAST_WRITE_WINS:
            # Compare modification times
            if local_mtime > notion_edited + self.CLOCK_SKEW_BUFFER:
                return SyncDirection.PUSH
            elif notion_edited > local_mtime + self.CLOCK_SKEW_BUFFER:
                return SyncDirection.PULL
            else:
                return SyncDirection.SKIP  # Too close to call
        else:
            # ASK - return conflict for manual resolution
            return SyncDirection.CONFLICT

    def update_last_full_sync(self):
        """Update the last full sync timestamp."""
        state = self._load_state()
        state["last_full_sync"] = datetime.now().isoformat()
        self.save_state()

    def get_last_full_sync(self) -> Optional[datetime]:
        """Get the last full sync timestamp."""
        state = self._load_state()
        last_sync = state.get("last_full_sync")
        if last_sync:
            return datetime.fromisoformat(last_sync)
        return None

    def clear_state(self):
        """Clear all sync state."""
        self._state = self._empty_state()
        self.save_state()

    def clear_module_state(self, module_path: str):
        """Clear sync state for a specific module."""
        state = self._load_state()
        if "modules" in state and module_path in state["modules"]:
            del state["modules"][module_path]
            self.save_state()

    def clear_file_state(self, module_path: str, file_name: str):
        """Clear sync state for a specific file within a module.

        Args:
            module_path: Module path
            file_name: File name to clear (e.g., "current.md")
        """
        module_state = self.get_module_state(module_path)
        if file_name in module_state.files:
            del module_state.files[file_name]
            self.set_module_state(module_path, module_state)
