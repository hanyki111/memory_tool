"""Data models for Notion sync operations."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class SyncDirection(Enum):
    """Sync direction enum."""
    PUSH = "push"      # Local -> Notion
    PULL = "pull"      # Notion -> Local
    SKIP = "skip"      # No change needed
    CONFLICT = "conflict"  # Both changed (for manual resolution)


class ConflictResolution(Enum):
    """Conflict resolution strategy."""
    LAST_WRITE_WINS = "last-write-wins"
    LOCAL_WINS = "local-wins"
    NOTION_WINS = "notion-wins"
    ASK = "ask"


@dataclass
class FileSyncState:
    """State of a single file sync."""
    notion_page_id: Optional[str] = None
    last_sync: Optional[datetime] = None
    local_mtime: Optional[datetime] = None
    notion_edited: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "notion_page_id": self.notion_page_id,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "local_mtime": self.local_mtime.isoformat() if self.local_mtime else None,
            "notion_edited": self.notion_edited.isoformat() if self.notion_edited else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FileSyncState":
        """Create from dictionary."""
        return cls(
            notion_page_id=data.get("notion_page_id"),
            last_sync=datetime.fromisoformat(data["last_sync"]) if data.get("last_sync") else None,
            local_mtime=datetime.fromisoformat(data["local_mtime"]) if data.get("local_mtime") else None,
            notion_edited=datetime.fromisoformat(data["notion_edited"]) if data.get("notion_edited") else None,
        )


@dataclass
class ModuleSyncState:
    """State of a module sync."""
    notion_page_id: Optional[str] = None
    last_sync: Optional[datetime] = None
    files: Dict[str, FileSyncState] = field(default_factory=dict)
    children: Dict[str, "ModuleSyncState"] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "notion_page_id": self.notion_page_id,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "files": {k: v.to_dict() for k, v in self.files.items()},
            "children": {k: v.to_dict() for k, v in self.children.items()},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ModuleSyncState":
        """Create from dictionary."""
        return cls(
            notion_page_id=data.get("notion_page_id"),
            last_sync=datetime.fromisoformat(data["last_sync"]) if data.get("last_sync") else None,
            files={k: FileSyncState.from_dict(v) for k, v in data.get("files", {}).items()},
            children={k: ModuleSyncState.from_dict(v) for k, v in data.get("children", {}).items()},
        )


@dataclass
class TimelineDaySyncState:
    """State of a single day's timeline sync."""
    notion_page_id: Optional[str] = None
    last_sync: Optional[datetime] = None
    local_mtime: Optional[datetime] = None
    notion_edited: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "notion_page_id": self.notion_page_id,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "local_mtime": self.local_mtime.isoformat() if self.local_mtime else None,
            "notion_edited": self.notion_edited.isoformat() if self.notion_edited else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimelineDaySyncState":
        """Create from dictionary."""
        return cls(
            notion_page_id=data.get("notion_page_id"),
            last_sync=datetime.fromisoformat(data["last_sync"]) if data.get("last_sync") else None,
            local_mtime=datetime.fromisoformat(data["local_mtime"]) if data.get("local_mtime") else None,
            notion_edited=datetime.fromisoformat(data["notion_edited"]) if data.get("notion_edited") else None,
        )


@dataclass
class SyncTarget:
    """A target for synchronization."""
    module_path: str
    local_path: str  # Full local filesystem path
    notion_page_id: Optional[str] = None
    include_children: bool = False


@dataclass
class SyncAction:
    """A single sync action to perform."""
    file_path: str  # Relative path within module (e.g., "current.md")
    module_path: str  # Module path (e.g., "projects/memory-tool")
    direction: SyncDirection
    local_mtime: Optional[datetime] = None
    notion_edited: Optional[datetime] = None
    notion_page_id: Optional[str] = None

    def __str__(self) -> str:
        if self.direction == SyncDirection.PUSH:
            return f"PUSH: {self.module_path}/{self.file_path} -> Notion"
        elif self.direction == SyncDirection.PULL:
            return f"PULL: {self.module_path}/{self.file_path} <- Notion"
        elif self.direction == SyncDirection.SKIP:
            return f"SKIP: {self.module_path}/{self.file_path} (unchanged)"
        else:
            return f"CONFLICT: {self.module_path}/{self.file_path}"


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool
    action: SyncAction
    message: str = ""
    error: Optional[Exception] = None

    def __str__(self) -> str:
        status = "OK" if self.success else "FAILED"
        return f"[{status}] {self.action}"


@dataclass
class SyncSummary:
    """Summary of a complete sync operation."""
    total_actions: int = 0
    pushed: int = 0
    pulled: int = 0
    skipped: int = 0
    failed: int = 0
    results: List[SyncResult] = field(default_factory=list)

    def add_result(self, result: SyncResult):
        """Add a sync result to the summary."""
        self.results.append(result)
        self.total_actions += 1

        if not result.success:
            self.failed += 1
        elif result.action.direction == SyncDirection.PUSH:
            self.pushed += 1
        elif result.action.direction == SyncDirection.PULL:
            self.pulled += 1
        else:
            self.skipped += 1

    def __str__(self) -> str:
        return (
            f"Sync complete: {self.total_actions} total "
            f"({self.pushed} pushed, {self.pulled} pulled, "
            f"{self.skipped} skipped, {self.failed} failed)"
        )


@dataclass
class SyncConfig:
    """Configuration for sync operations."""
    enabled: bool = False
    root_page_id: Optional[str] = None
    targets: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    conflict_resolution: ConflictResolution = ConflictResolution.LAST_WRITE_WINS
    timeline_enabled: bool = False
    timeline_bidirectional: bool = False
    timeline_sync_days: int = 30

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SyncConfig":
        """Create from config dictionary."""
        timeline_config = data.get("timeline", {})

        resolution_str = data.get("conflict_resolution", "last-write-wins")
        try:
            resolution = ConflictResolution(resolution_str)
        except ValueError:
            resolution = ConflictResolution.LAST_WRITE_WINS

        return cls(
            enabled=data.get("enabled", False),
            root_page_id=data.get("root_page_id"),
            targets=data.get("targets", []),
            exclude_patterns=data.get("exclude_patterns", []),
            conflict_resolution=resolution,
            timeline_enabled=timeline_config.get("enabled", False),
            timeline_bidirectional=timeline_config.get("bidirectional", False),
            timeline_sync_days=timeline_config.get("sync_days", 30),
        )
