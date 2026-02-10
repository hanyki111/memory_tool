"""Update checker and installer for memory_tool.

Uses only stdlib (urllib.request) to avoid external dependencies.
Checks GitHub Tags API for latest version and installs via pip.

Cache/settings are stored globally at ~/.memory-tool/update.json:
{
    "auto_check": true,
    "check_interval_hours": 24,
    "last_check": "2026-02-10T14:30:00",
    "latest_version": "1.0.1"
}
"""

import json
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple

GITHUB_REPO = "hanyki111/memory_tool"
GITHUB_TAGS_URL = f"https://api.github.com/repos/{GITHUB_REPO}/tags"

# Global config directory
_UPDATE_DIR = Path.home() / ".memory-tool"
_UPDATE_FILE = _UPDATE_DIR / "update.json"

_DEFAULT_CACHE = {
    "auto_check": True,
    "check_interval_hours": 24,
    "last_check": None,
    "latest_version": None,
}


def get_current_version() -> str:
    """Return the currently installed version."""
    from memory_tool import __version__
    return __version__


def parse_version(version_str: str) -> Tuple[int, ...]:
    """Parse version string like '1.0.0' or 'v1.0.0' into tuple (1, 0, 0)."""
    v = version_str.lstrip("v").strip()
    parts = []
    for part in v.split("."):
        try:
            parts.append(int(part))
        except ValueError:
            break
    return tuple(parts) if parts else (0, 0, 0)


def check_latest_version() -> Optional[str]:
    """Fetch the latest version tag from GitHub.

    Returns the latest version string (without 'v' prefix), or None on failure.
    """
    try:
        req = urllib.request.Request(
            GITHUB_TAGS_URL,
            headers={"Accept": "application/vnd.github.v3+json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError):
        return None

    if not data or not isinstance(data, list):
        return None

    # Find the highest semver tag
    best_version: Optional[Tuple[int, ...]] = None
    best_tag: Optional[str] = None

    for tag_info in data:
        tag_name = tag_info.get("name", "")
        if not tag_name.startswith("v"):
            continue
        parsed = parse_version(tag_name)
        if parsed == (0, 0, 0):
            continue
        if best_version is None or parsed > best_version:
            best_version = parsed
            best_tag = tag_name

    if best_tag is None:
        return None

    return best_tag.lstrip("v")


def compare_versions(current: str, latest: str) -> int:
    """Compare two version strings.

    Returns:
        -1 if current < latest (update available)
         0 if current == latest (up to date)
         1 if current > latest (ahead)
    """
    cur = parse_version(current)
    lat = parse_version(latest)

    if cur < lat:
        return -1
    elif cur == lat:
        return 0
    else:
        return 1


def _is_in_virtualenv() -> bool:
    """Check if running inside a virtual environment."""
    return (
        hasattr(sys, "real_prefix")  # virtualenv
        or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)  # venv
    )


def do_update(version: str) -> Tuple[bool, str]:
    """Install a specific version from GitHub via pip.

    Handles PEP 668 (externally-managed-environment) by retrying with --user
    when not inside a virtual environment.

    Returns (success, message) tuple.
    """
    install_url = f"git+https://github.com/{GITHUB_REPO}.git@v{version}"
    base_cmd = [sys.executable, "-m", "pip", "install", "--upgrade"]

    try:
        result = subprocess.run(
            base_cmd + [install_url],
            capture_output=True,
            text=True,
            timeout=120,
        )

        # PEP 668: externally-managed-environment → retry with --user
        if result.returncode != 0 and "externally-managed-environment" in result.stderr:
            if _is_in_virtualenv():
                return False, "가상환경 내 설치 실패 — pip 권한을 확인하세요"
            result = subprocess.run(
                base_cmd + ["--user", install_url],
                capture_output=True,
                text=True,
                timeout=120,
            )

        if result.returncode == 0:
            return True, f"v{version} 설치 완료"
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return False, f"설치 실패: {error_msg}"

    except subprocess.TimeoutExpired:
        return False, "설치 시간 초과 (120초)"
    except FileNotFoundError:
        return False, "pip을 찾을 수 없습니다"
    except Exception as e:
        return False, f"설치 오류: {e}"


# ============================================================================
# Cache / Settings (global: ~/.memory-tool/update.json)
# ============================================================================


def _load_cache() -> dict:
    """Load update cache from disk. Returns defaults if missing/corrupt."""
    try:
        if _UPDATE_FILE.exists():
            data = json.loads(_UPDATE_FILE.read_text(encoding="utf-8"))
            # Merge with defaults so new keys are always present
            merged = {**_DEFAULT_CACHE, **data}
            return merged
    except (json.JSONDecodeError, OSError):
        pass
    return dict(_DEFAULT_CACHE)


def _save_cache(cache: dict) -> None:
    """Write update cache to disk."""
    try:
        _UPDATE_DIR.mkdir(parents=True, exist_ok=True)
        _UPDATE_FILE.write_text(
            json.dumps(cache, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass  # Non-critical — silently ignore write failures


def get_auto_check_enabled() -> bool:
    """Return whether auto update check is enabled."""
    return _load_cache().get("auto_check", True)


def set_auto_check_enabled(enabled: bool) -> None:
    """Enable or disable auto update check."""
    cache = _load_cache()
    cache["auto_check"] = enabled
    _save_cache(cache)


def auto_check_update() -> Optional[str]:
    """Perform a throttled update check for use in the CLI callback.

    Returns the latest version string if an update is available,
    or None if up-to-date / check skipped / error.
    This function is designed to be fast and silent on failure.
    """
    try:
        cache = _load_cache()

        if not cache.get("auto_check", True):
            return None

        interval = cache.get("check_interval_hours", 24)
        last_check_str = cache.get("last_check")

        # If we checked recently, use cached result
        if last_check_str:
            try:
                last_check = datetime.fromisoformat(last_check_str)
                if datetime.now() - last_check < timedelta(hours=interval):
                    # Still within interval — return cached result if update exists
                    cached_latest = cache.get("latest_version")
                    if cached_latest and compare_versions(get_current_version(), cached_latest) < 0:
                        return cached_latest
                    return None
            except (ValueError, TypeError):
                pass  # Invalid timestamp, proceed with fresh check

        # Time to check — hit GitHub
        latest = check_latest_version()

        # Update cache regardless of result
        cache["last_check"] = datetime.now().isoformat(timespec="seconds")
        cache["latest_version"] = latest
        _save_cache(cache)

        if latest and compare_versions(get_current_version(), latest) < 0:
            return latest

        return None

    except Exception:
        return None  # Never break the user's command
