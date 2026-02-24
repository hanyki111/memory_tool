"""Multi-backend management for Notion sync.

Supports Primary-Secondary architecture:
- Primary: existing notion: config, bidirectional sync (Local <-> Notion A)
- Secondary: additional-backends entries, push-only mirror (Local -> Notion B, C, ...)

Config structure:
    notion:
      api_key: "secret_personal"     # Primary (existing config, unchanged)
      mode: "default"
      sync:
        module:
          root_page_id: "abc123"
        timeline:
          root_page_id: "def456"
        plan:
          root_page_id: "ghi789"

      additional-backends:           # NEW: secondary backends (optional)
        team:
          api_key: "secret_team"
          mode: "default"
          sync:
            module:
              root_page_id: "xyz999"
            timeline:
              root_page_id: "uvw888"
            plan:
              root_page_id: "rst777"
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from memory_tool.utils.config import Config


@dataclass
class BackendConfig:
    """Configuration for a single Notion backend."""
    name: str                          # "primary", "team", etc.
    role: str                          # "primary" or "secondary"
    client_config: Optional[dict]      # None for primary (uses existing NotionClient())
    sync_config: dict = field(default_factory=dict)  # sync type -> root_page_id mapping

    def get_module_root_page_id(self) -> Optional[str]:
        """Get module sync root_page_id for this backend."""
        return self.sync_config.get("module", {}).get("root_page_id")

    def get_timeline_root_page_id(self) -> Optional[str]:
        """Get timeline sync root_page_id for this backend."""
        return self.sync_config.get("timeline", {}).get("root_page_id")

    def get_plan_root_page_id(self) -> Optional[str]:
        """Get plan sync root_page_id for this backend."""
        return self.sync_config.get("plan", {}).get("root_page_id")


class BackendManager:
    """Manages multiple Notion backends from config.

    Primary backend is always the existing notion: config.
    Secondary backends come from notion.additional-backends section.
    If additional-backends is absent, get_secondaries() returns [].
    """

    def __init__(self):
        self.config = Config()
        self._primary: Optional[BackendConfig] = None
        self._secondaries: List[BackendConfig] = []
        self._loaded = False

    def _ensure_loaded(self):
        """Load backends from config (lazy)."""
        if self._loaded:
            return
        self._load()
        self._loaded = True

    def _load(self):
        """Load backend configurations from config.yaml."""
        notion_config = self.config.get("notion", {})

        # Primary: existing notion: config (client_config=None means use default NotionClient())
        self._primary = BackendConfig(
            name="primary",
            role="primary",
            client_config=None,
            sync_config=notion_config.get("sync", {}),
        )

        # Secondaries: from additional-backends section
        self._secondaries = []
        additional = notion_config.get("additional-backends", {})

        for name, data in additional.items():
            # Build client_config dict for NotionClient(backend_config=...)
            client_config = {
                "api_key": data.get("api_key"),
                "mode": data.get("mode", "default"),
            }

            # PAT mode support
            if data.get("mode") == "pat":
                pat_config = data.get("pat", {})
                client_config["pat"] = pat_config
                if pat_config.get("base_url"):
                    client_config["base_url"] = pat_config["base_url"]
                if pat_config.get("notion_version"):
                    client_config["notion_version"] = pat_config["notion_version"]

            self._secondaries.append(BackendConfig(
                name=name,
                role="secondary",
                client_config=client_config,
                sync_config=data.get("sync", {}),
            ))

    def get_primary(self) -> BackendConfig:
        """Get the primary backend config."""
        self._ensure_loaded()
        return self._primary

    def get_secondaries(self) -> List[BackendConfig]:
        """Get all secondary backend configs. Empty list if none configured."""
        self._ensure_loaded()
        return self._secondaries

    def get_all(self) -> List[BackendConfig]:
        """Get all backends (primary + secondaries)."""
        self._ensure_loaded()
        return [self._primary] + self._secondaries

    def get_backend(self, name: str) -> Optional[BackendConfig]:
        """Get a specific backend by name."""
        self._ensure_loaded()
        if name == "primary":
            return self._primary
        for sec in self._secondaries:
            if sec.name == name:
                return sec
        return None

    def has_secondaries(self) -> bool:
        """Check if any secondary backends are configured."""
        self._ensure_loaded()
        return len(self._secondaries) > 0

    def create_client(self, backend: BackendConfig):
        """Create a NotionClient for the given backend.

        Args:
            backend: Backend configuration

        Returns:
            NotionClient instance
        """
        from memory_tool.notion.client import NotionClient

        if backend.client_config is None:
            # Primary: use default constructor
            return NotionClient()
        else:
            # Secondary: pass backend_config
            return NotionClient(
                backend_config=backend.client_config,
                backend_name=backend.name,
            )

    def get_backend_names(self) -> List[str]:
        """Get list of all backend names."""
        self._ensure_loaded()
        names = ["primary"]
        names.extend(sec.name for sec in self._secondaries)
        return names
