"""Git hook generation and management for memory_tool."""

import sys
from pathlib import Path
from typing import Optional


class GitHookError(Exception):
    """Base exception for git hook operations."""
    pass


class GitHookManager:
    """Manage git hooks for memory_tool."""

    PRE_COMMIT_HOOK_TEMPLATE = """#!/bin/sh
# memory_tool pre-commit hook (auto-generated)
#
# This hook rebuilds the module connection graph before each commit
# to ensure the graph is always up-to-date.

echo "Rebuilding module connection graph..."

# Run rebuild-graph command
python -m memory_tool module rebuild-graph --quiet 2>&1

if [ $? -ne 0 ]; then
    echo "Warning: Failed to rebuild connection graph"
    # Don't block commit on failure, just warn
fi

exit 0
"""

    POST_CHECKOUT_HOOK_TEMPLATE = """#!/bin/sh
# memory_tool post-checkout hook (auto-generated)
#
# This hook rebuilds the module connection graph after checkout
# to sync with the checked-out state.

echo "Rebuilding module connection graph..."

# Run rebuild-graph command
python -m memory_tool module rebuild-graph --quiet 2>&1

exit 0
"""

    DOCUMENT_HEALTH_HOOK_TEMPLATE = """#!/bin/sh
# memory_tool document-health pre-commit hook (auto-generated)
#
# This hook checks document health before each commit
# and warns if any files need archiving.

echo "🔍 Checking document health..."

# Run health check
python -m memory_tool context --check-health-only --quiet 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 1 ]; then
    echo ""
    echo "⚠️  Large files detected. Commit will proceed in 3 seconds..."
    echo "   (Press Ctrl+C to cancel and archive first)"
    sleep 3
elif [ $EXIT_CODE -eq 2 ]; then
    # Critical issues - give more time
    echo ""
    echo "🔴 CRITICAL: Very large files detected!"
    echo "   Strongly recommend archiving before commit."
    echo "   Commit will proceed in 5 seconds... (Ctrl+C to cancel)"
    sleep 5
fi

exit 0
"""

    def __init__(self, repo_path: Optional[Path] = None):
        """Initialize git hook manager.

        Args:
            repo_path: Path to git repository (defaults to current directory)
        """
        if repo_path is None:
            repo_path = Path.cwd()

        self.repo_path = Path(repo_path)
        self.git_dir = self.repo_path / ".git"
        self.hooks_dir = self.git_dir / "hooks"

    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository.

        Returns:
            True if .git directory exists
        """
        return self.git_dir.exists() and self.git_dir.is_dir()

    def install_pre_commit_hook(self, force: bool = False) -> Path:
        """Install pre-commit hook.

        Args:
            force: Overwrite existing hook if True

        Returns:
            Path to installed hook

        Raises:
            GitHookError: If installation fails
        """
        if not self.is_git_repo():
            raise GitHookError(f"Not a git repository: {self.repo_path}")

        # Ensure hooks directory exists
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

        hook_path = self.hooks_dir / "pre-commit"

        # Check if hook already exists
        if hook_path.exists() and not force:
            raise GitHookError(
                f"Hook already exists: {hook_path}\n"
                f"Use --force to overwrite"
            )

        # Write hook script
        try:
            hook_path.write_text(self.PRE_COMMIT_HOOK_TEMPLATE, encoding="utf-8")

            # Make executable (Unix)
            if sys.platform != "win32":
                import stat
                hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        except Exception as e:
            raise GitHookError(f"Failed to install hook: {e}")

        return hook_path

    def install_post_checkout_hook(self, force: bool = False) -> Path:
        """Install post-checkout hook.

        Args:
            force: Overwrite existing hook if True

        Returns:
            Path to installed hook

        Raises:
            GitHookError: If installation fails
        """
        if not self.is_git_repo():
            raise GitHookError(f"Not a git repository: {self.repo_path}")

        # Ensure hooks directory exists
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

        hook_path = self.hooks_dir / "post-checkout"

        # Check if hook already exists
        if hook_path.exists() and not force:
            raise GitHookError(
                f"Hook already exists: {hook_path}\n"
                f"Use --force to overwrite"
            )

        # Write hook script
        try:
            hook_path.write_text(self.POST_CHECKOUT_HOOK_TEMPLATE, encoding="utf-8")

            # Make executable (Unix)
            if sys.platform != "win32":
                import stat
                hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        except Exception as e:
            raise GitHookError(f"Failed to install hook: {e}")

        return hook_path

    def install_document_health_hook(self, force: bool = False) -> Path:
        """Install document-health pre-commit hook.

        Args:
            force: Overwrite existing hook if True

        Returns:
            Path to installed hook

        Raises:
            GitHookError: If installation fails
        """
        if not self.is_git_repo():
            raise GitHookError(f"Not a git repository: {self.repo_path}")

        # Ensure hooks directory exists
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

        hook_path = self.hooks_dir / "pre-commit"

        # Check if hook already exists
        if hook_path.exists() and not force:
            # Check if it's our graph rebuild hook
            content = hook_path.read_text(encoding="utf-8")
            if "module rebuild-graph" in content:
                raise GitHookError(
                    f"Pre-commit hook already exists (graph rebuild).\n"
                    f"Cannot install document-health hook. Use --force to replace."
                )
            else:
                raise GitHookError(
                    f"Pre-commit hook already exists.\n"
                    f"Use --force to overwrite"
                )

        # Write hook script
        try:
            hook_path.write_text(self.DOCUMENT_HEALTH_HOOK_TEMPLATE, encoding="utf-8")

            # Make executable (Unix)
            if sys.platform != "win32":
                import stat
                hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        except Exception as e:
            raise GitHookError(f"Failed to install hook: {e}")

        return hook_path

    def uninstall_hook(self, hook_name: str) -> bool:
        """Uninstall a git hook.

        Args:
            hook_name: Name of hook (e.g., "pre-commit")

        Returns:
            True if hook was removed, False if it didn't exist

        Raises:
            GitHookError: If uninstall fails
        """
        if not self.is_git_repo():
            raise GitHookError(f"Not a git repository: {self.repo_path}")

        hook_path = self.hooks_dir / hook_name

        if not hook_path.exists():
            return False

        try:
            hook_path.unlink()
            return True
        except Exception as e:
            raise GitHookError(f"Failed to uninstall hook: {e}")

    def list_installed_hooks(self) -> dict[str, str]:
        """List memory_tool hooks and their installation status.

        Returns:
            Dictionary mapping hook names to their type or "not installed"
            Possible types: "graph-rebuild", "document-health", "not installed"
        """
        if not self.is_git_repo():
            return {}

        hooks = {
            "pre-commit": "not installed",
            "post-checkout": "not installed",
        }

        # Check pre-commit hook
        pre_commit_path = self.hooks_dir / "pre-commit"
        if pre_commit_path.exists():
            try:
                content = pre_commit_path.read_text(encoding="utf-8")
                if "memory_tool" in content:
                    if "document-health" in content or "check-health" in content:
                        hooks["pre-commit"] = "document-health"
                    elif "rebuild-graph" in content:
                        hooks["pre-commit"] = "graph-rebuild"
                    else:
                        hooks["pre-commit"] = "unknown"
            except Exception:
                pass

        # Check post-checkout hook
        post_checkout_path = self.hooks_dir / "post-checkout"
        if post_checkout_path.exists():
            try:
                content = post_checkout_path.read_text(encoding="utf-8")
                if "memory_tool" in content:
                    hooks["post-checkout"] = "graph-rebuild"
            except Exception:
                pass

        return hooks
