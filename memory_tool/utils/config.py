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
    }

    VALID_GRANULARITIES = {"low", "medium", "high"}
    VALID_SCOPES = {"local", "kb", "all"}
    VALID_LANGUAGES = {"ko", "en", "auto"}

    def __init__(self, memory_path: Optional[Path] = None):
        """Initialize config manager.

        Args:
            memory_path: Path to .memory/ directory. If None, searches from cwd.
        """
        if memory_path is None:
            memory_path = self._find_memory_path()

        self.memory_path = Path(memory_path) if memory_path else None
        self.config_path = self.memory_path / "config.yaml" if self.memory_path else None
        self._config = None

    def _find_memory_path(self) -> Optional[Path]:
        """Find .memory/ directory from current directory upwards.

        Returns:
            Path to .memory/ if found, None otherwise
        """
        current = Path.cwd()

        # Check current and parent directories (up to 5 levels)
        for _ in range(5):
            memory_path = current / ".memory"
            if memory_path.exists() and memory_path.is_dir():
                return memory_path

            if current.parent == current:
                break
            current = current.parent

        return None

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
