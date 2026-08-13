"""Configuration management for Memory Tool."""

from pathlib import Path
from typing import Optional, Any
import yaml


class ConfigError(Exception):
    """Base exception for configuration errors."""
    pass


class ConfigNotFoundError(ConfigError):
    """Raised when config.yaml not found."""
    pass


class ConfigValidationError(ConfigError):
    """Raised when config.yaml has invalid values."""
    pass


class Config:
    """Configuration manager for Memory Tool."""

    DEFAULT_CONFIG = {
        "version": "1.0",
        "kb": {
            "path": None,  # Knowledge base path (e.g., "~/memory/personal")
        },
        "timeline": {
            "auto_record": False,
            "granularity": "medium",
            "warn_old_days": 365,
        },
        "context": {
            "auto_update": False,
            "recent_days": 3,
        },
        "modules": {
            "auto_update_current": False,
        },
        "search": {
            "default_scope": "local",
            "include_archived": False,
            "max_file_size": 1048576,  # 1MB
            "exclude_patterns": [],
            "hybrid": False,  # Enable hybrid search by default
            "text_weight": 0.7,  # Keyword search weight (0-1)
            "semantic_weight": 0.3,  # Semantic search weight (0-1)
            "semantic_threshold": 0.5,  # Minimum similarity for semantic search (0-1)
        },
        "tag": {
            "storage_format": "bracket",  # "bracket" ([태그]) or "hashtag" (#태그)
            "display_format": "bracket",  # "bracket" ([태그]) or "hashtag" (#태그)
        },
        "tags": {
            "default_types": ["timeline"],  # Default file types to search
            "sort": "count",  # "count" (by frequency) or "alpha" (alphabetical)
            "min_count": 1,  # Minimum usage count to display
        },
        "llm": {
            "provider": "anthropic",
            "ollama_host": "http://localhost:11434",
            "ollama_model": "llama3.2",
            "anthropic_api_key": None,
            "anthropic_model": "claude-3-5-sonnet-20241022",
            "max_tokens": 4096,
            "temperature": 0.7,
        },
        "summary": {
            "default_language": "ko",  # ko, en, or auto
        },
        "help": {
            "language": "en",  # en, ko
        },
    }

    VALID_GRANULARITIES = {"low", "medium", "high"}
    VALID_SCOPES = {"local", "kb", "all"}
    VALID_LANGUAGES = {"ko", "en", "auto"}
    VALID_TAG_FORMATS = {"bracket", "hashtag"}

    def __init__(self, memory_path: Optional[Path] = None):
        """Initialize config manager.

        Args:
            memory_path: Path to the base folder. If None, it is resolved from
                the pointer file (or a legacy .memory/ directory).
        """
        if memory_path is None:
            memory_path = self._find_memory_path()

        self.memory_path = Path(memory_path) if memory_path else None
        self.config_path = self.memory_path / "config.yaml" if self.memory_path else None
        self._config = None

    def _find_memory_path(self) -> Optional[Path]:
        """Find the base folder, honouring the configurable base name.

        The base folder name is not necessarily ".memory", so this delegates to
        the central resolver rather than probing a hardcoded name.

        Returns:
            Path to the base folder if one exists, None otherwise
        """
        from memory_tool.utils.paths import get_paths

        paths = get_paths()
        return paths.base if paths.found else None

    def load(self, strict: bool = False) -> dict:
        """Load configuration from config.yaml.

        Args:
            strict: If True, raise error if config not found

        Returns:
            Configuration dictionary (merged with defaults)

        Raises:
            ConfigNotFoundError: If config.yaml not found and strict=True
            ConfigValidationError: If config has invalid values
        """
        # If already loaded, return cached
        if self._config is not None:
            return self._config

        # Start with defaults
        config = self._deep_copy(self.DEFAULT_CONFIG)

        # Try to load from file
        if self.config_path and self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    file_config = yaml.safe_load(f)
                    if file_config:
                        config = self._merge_configs(config, file_config)
            except yaml.YAMLError as e:
                raise ConfigValidationError(f"Invalid YAML in config.yaml: {e}")
        elif strict:
            raise ConfigNotFoundError(
                f"config.yaml not found at {self.config_path}. "
                f"Run 'minit' to initialize."
            )

        # Validate config
        self._validate(config)

        # Cache and return
        self._config = config
        return config

    def _deep_copy(self, d: dict) -> dict:
        """Deep copy a dictionary.

        Args:
            d: Dictionary to copy

        Returns:
            Deep copy of dictionary
        """
        import copy
        return copy.deepcopy(d)

    def _merge_configs(self, base: dict, override: dict) -> dict:
        """Merge two config dictionaries (override takes precedence).

        Args:
            base: Base configuration
            override: Override configuration

        Returns:
            Merged configuration
        """
        result = self._deep_copy(base)

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _validate(self, config: dict) -> None:
        """Validate configuration values.

        Args:
            config: Configuration to validate

        Raises:
            ConfigValidationError: If validation fails
        """
        # Validate timeline.granularity
        granularity = config.get("timeline", {}).get("granularity")
        if granularity not in self.VALID_GRANULARITIES:
            raise ConfigValidationError(
                f"Invalid timeline.granularity: '{granularity}'. "
                f"Must be one of: {', '.join(self.VALID_GRANULARITIES)}"
            )

        # Validate search.default_scope
        scope = config.get("search", {}).get("default_scope")
        if scope not in self.VALID_SCOPES:
            raise ConfigValidationError(
                f"Invalid search.default_scope: '{scope}'. "
                f"Must be one of: {', '.join(self.VALID_SCOPES)}"
            )

        # Validate context.recent_days
        recent_days = config.get("context", {}).get("recent_days")
        if not isinstance(recent_days, int) or recent_days < 1:
            raise ConfigValidationError(
                f"Invalid context.recent_days: {recent_days}. Must be >= 1"
            )

        # Validate timeline.warn_old_days
        warn_old_days = config.get("timeline", {}).get("warn_old_days")
        if not isinstance(warn_old_days, int) or warn_old_days < 1:
            raise ConfigValidationError(
                f"Invalid timeline.warn_old_days: {warn_old_days}. Must be >= 1"
            )

        # Validate search.max_file_size
        max_size = config.get("search", {}).get("max_file_size")
        if not isinstance(max_size, int) or max_size < 0:
            raise ConfigValidationError(
                f"Invalid search.max_file_size: {max_size}. Must be >= 0"
            )

        # Validate summary.default_language
        lang = config.get("summary", {}).get("default_language")
        if lang not in self.VALID_LANGUAGES:
            raise ConfigValidationError(
                f"Invalid summary.default_language: '{lang}'. "
                f"Must be one of: {', '.join(self.VALID_LANGUAGES)}"
            )

        # Validate tag.storage_format
        tag_storage = config.get("tag", {}).get("storage_format")
        if tag_storage and tag_storage not in self.VALID_TAG_FORMATS:
            raise ConfigValidationError(
                f"Invalid tag.storage_format: '{tag_storage}'. "
                f"Must be one of: {', '.join(self.VALID_TAG_FORMATS)}"
            )

        # Validate tag.display_format
        tag_display = config.get("tag", {}).get("display_format")
        if tag_display and tag_display not in self.VALID_TAG_FORMATS:
            raise ConfigValidationError(
                f"Invalid tag.display_format: '{tag_display}'. "
                f"Must be one of: {', '.join(self.VALID_TAG_FORMATS)}"
            )

    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path.

        Args:
            key_path: Dot-separated key path (e.g., "timeline.auto_record")
            default: Default value if key not found

        Returns:
            Configuration value or default

        Example:
            >>> config = Config()
            >>> config.get("timeline.auto_record")
            False
            >>> config.get("context.recent_days")
            3
        """
        config = self.load(strict=False)

        keys = key_path.split(".")
        value = config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def reload(self) -> dict:
        """Reload configuration from file.

        Returns:
            Reloaded configuration
        """
        self._config = None
        return self.load()

    @property
    def auto_update_enabled(self) -> bool:
        """Check if context auto-update is enabled.

        Returns:
            True if context.auto_update is True
        """
        return self.get("context.auto_update", False)

    @property
    def recent_days(self) -> int:
        """Get number of recent days for context.

        Returns:
            Number of recent days
        """
        return self.get("context.recent_days", 3)

    @property
    def warn_old_days(self) -> int:
        """Get threshold for old date warning.

        Returns:
            Number of days
        """
        return self.get("timeline.warn_old_days", 365)

    def get_kb_path(self) -> Optional[Path]:
        """Get knowledge base path from config.

        Checks in order:
        1. config.yaml kb.path
        2. config.yaml search.kb_path (legacy)
        3. kb.lock file (backward compatibility)

        Returns:
            KB path or None if not configured
        """
        # 1. Check kb.path (primary)
        kb_path = self.get("kb.path")
        if kb_path:
            return Path(kb_path).expanduser()

        # 2. Check search.kb_path (legacy)
        kb_path = self.get("search.kb_path")
        if kb_path:
            return Path(kb_path).expanduser()

        # 3. Check kb.lock file (backward compatibility)
        if self.memory_path:
            kb_lock = self.memory_path / "kb.lock"
            if kb_lock.exists():
                return self._read_kb_lock(kb_lock)

        return None

    def _read_kb_lock(self, kb_lock_path: Path) -> Optional[Path]:
        """Read KB path from legacy kb.lock file.

        Args:
            kb_lock_path: Path to kb.lock file

        Returns:
            KB path or None
        """
        try:
            content = kb_lock_path.read_text(encoding="utf-8").strip()

            # Plain text format
            if not content.startswith("kb_root:") and "\n" not in content:
                return Path(content).expanduser()

            # YAML format
            data = yaml.safe_load(content)
            if isinstance(data, dict) and "kb_root" in data:
                return Path(data["kb_root"]).expanduser()

            # Fallback: first line
            first_line = content.split("\n")[0].strip()
            if first_line.startswith("kb_root:"):
                return Path(first_line.replace("kb_root:", "").strip()).expanduser()
        except Exception:
            pass

        return None

    def set_kb_path(self, kb_path: str) -> None:
        """Set knowledge base path in config.yaml.

        Args:
            kb_path: Path to knowledge base
        """
        if not self.config_path:
            raise ConfigError("config.yaml path not found")

        config = self.load()
        if "kb" not in config:
            config["kb"] = {}
        config["kb"]["path"] = kb_path

        # Remove legacy search.kb_path if exists
        if "search" in config and "kb_path" in config["search"]:
            del config["search"]["kb_path"]

        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        # Clear cache
        self._config = None


def load_config(memory_path: Optional[Path] = None, strict: bool = False) -> dict:
    """Load configuration (convenience function).

    Args:
        memory_path: Path to .memory/ directory
        strict: If True, raise error if config not found

    Returns:
        Configuration dictionary
    """
    config = Config(memory_path)
    return config.load(strict=strict)
