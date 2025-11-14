"""Alias management for Windows batch files and PowerShell profiles."""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Tuple


class AliasError(Exception):
    """Base exception for alias operations."""
    pass


class AliasManager:
    """Manager for command aliases."""

    # Alias definitions: alias_name -> (command_name, description)
    ALIASES = {
        "m": ("record", "Record to timeline"),
        "minit": ("init", "Initialize .memory/ structure"),
        "ms": ("search", "Search timeline and modules"),
        "mcontext": ("context", "Build Claude Code context"),
        "msort": ("sort", "Sort timeline by time"),
        "msummary": ("summary", "Summarize timeline or module"),
        "marchive": ("archive", "Archive documentation"),
        "mtoday": ("today", "Show today's timeline"),
        "mweek": ("week", "Show this week's timeline"),
        "mstatus": ("status", "Show statistics"),
    }

    def __init__(self):
        """Initialize alias manager."""
        self.python_exe = sys.executable
        self.package_name = "memory_tool"

    def get_default_install_dir(self) -> Path:
        """Get default installation directory for aliases.

        Returns:
            Path to user's local bin directory
        """
        # Use user's AppData\Local\Programs\memory-tool directory on Windows
        # This avoids permission issues with system Python directories
        if sys.platform == "win32":
            local_appdata = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
            bin_dir = local_appdata / "Programs" / "memory-tool"
        else:
            # Unix: use ~/.local/bin
            bin_dir = Path.home() / ".local" / "bin"

        bin_dir.mkdir(parents=True, exist_ok=True)
        return bin_dir

    def generate_batch_content(self, command: str) -> str:
        """Generate batch file content for a command.

        Args:
            command: Memory tool command name (e.g., "record")

        Returns:
            Batch file content
        """
        return f"""@echo off
REM Memory Tool alias - auto-generated
"{self.python_exe}" -m {self.package_name} {command} %*
"""

    def install_alias(
        self,
        alias_name: str,
        install_dir: Optional[Path] = None,
    ) -> Path:
        """Install a single alias.

        Args:
            alias_name: Name of the alias (e.g., "m")
            install_dir: Installation directory (default: Scripts)

        Returns:
            Path to created batch file

        Raises:
            AliasError: If alias is unknown or installation fails
        """
        if alias_name not in self.ALIASES:
            raise AliasError(f"Unknown alias: {alias_name}")

        command, _ = self.ALIASES[alias_name]

        # Default installation directory
        if install_dir is None:
            install_dir = self.get_default_install_dir()

        # Ensure directory exists
        install_dir.mkdir(parents=True, exist_ok=True)

        # Create batch file
        batch_file = install_dir / f"{alias_name}.bat"
        content = self.generate_batch_content(command)

        try:
            batch_file.write_text(content, encoding="utf-8")
        except Exception as e:
            raise AliasError(f"Failed to create batch file: {e}")

        return batch_file

    def uninstall_alias(
        self,
        alias_name: str,
        install_dir: Optional[Path] = None,
    ) -> bool:
        """Uninstall a single alias.

        Args:
            alias_name: Name of the alias
            install_dir: Installation directory

        Returns:
            True if removed, False if didn't exist

        Raises:
            AliasError: If removal fails
        """
        if install_dir is None:
            install_dir = self.get_default_install_dir()

        batch_file = install_dir / f"{alias_name}.bat"

        if not batch_file.exists():
            return False

        try:
            batch_file.unlink()
            return True
        except Exception as e:
            raise AliasError(f"Failed to remove batch file: {e}")

    def install_all(
        self,
        install_dir: Optional[Path] = None,
    ) -> Dict[str, Path]:
        """Install all aliases.

        Args:
            install_dir: Installation directory

        Returns:
            Dictionary mapping alias names to batch file paths

        Raises:
            AliasError: If installation fails
        """
        installed = {}

        for alias_name in self.ALIASES.keys():
            batch_file = self.install_alias(alias_name, install_dir)
            installed[alias_name] = batch_file

        return installed

    def uninstall_all(
        self,
        install_dir: Optional[Path] = None,
    ) -> List[str]:
        """Uninstall all aliases.

        Args:
            install_dir: Installation directory

        Returns:
            List of removed alias names

        Raises:
            AliasError: If removal fails
        """
        removed = []

        for alias_name in self.ALIASES.keys():
            if self.uninstall_alias(alias_name, install_dir):
                removed.append(alias_name)

        return removed

    def list_installed(
        self,
        install_dir: Optional[Path] = None,
    ) -> Dict[str, bool]:
        """List installation status of all aliases.

        Args:
            install_dir: Installation directory

        Returns:
            Dictionary mapping alias names to installation status
        """
        if install_dir is None:
            install_dir = self.get_default_install_dir()

        status = {}

        for alias_name in self.ALIASES.keys():
            batch_file = install_dir / f"{alias_name}.bat"
            status[alias_name] = batch_file.exists()

        return status

    def is_in_path(self, directory: Path) -> bool:
        """Check if directory is in PATH.

        Args:
            directory: Directory to check

        Returns:
            True if in PATH
        """
        path_env = os.environ.get("PATH", "")
        path_dirs = [Path(p) for p in path_env.split(os.pathsep)]

        # Resolve to absolute paths for comparison
        directory = directory.resolve()

        for path_dir in path_dirs:
            try:
                if path_dir.resolve() == directory:
                    return True
            except Exception:
                continue

        return False

    def get_path_instructions(self, install_dir: Path) -> str:
        """Get instructions for adding directory to PATH.

        Args:
            install_dir: Installation directory

        Returns:
            Instructions text
        """
        if self.is_in_path(install_dir):
            return f"✓ {install_dir} is already in PATH"

        return f"""
To use aliases, add this directory to your PATH:

Windows (PowerShell - Administrator):
  [Environment]::SetEnvironmentVariable("Path", $env:Path + ";{install_dir}", "User")

Windows (GUI):
  1. Win + R → sysdm.cpl → Advanced → Environment Variables
  2. Under "User variables", select "Path" → Edit
  3. Add: {install_dir}
  4. Restart terminal

Then you can use:
  m "message"
  ms "query"
  mcontext
  etc.
"""

    # ============================================================================
    # PowerShell Profile Support
    # ============================================================================

    def get_powershell_profile_path(self) -> Optional[Path]:
        """Get PowerShell profile path that works for all hosts (VSCode, Terminal, etc).

        Returns:
            Path to CurrentUserAllHosts profile, or None if PowerShell not available
        """
        if sys.platform != "win32":
            return None

        try:
            # Get PowerShell profile path for CurrentUserAllHosts
            # This works in: PowerShell, VSCode, Windows Terminal, etc.
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "echo $PROFILE.CurrentUserAllHosts"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                profile_path = result.stdout.strip()
                if profile_path:
                    return Path(profile_path)

        except Exception:
            pass

        return None

    def generate_powershell_function(self, alias_name: str, command: str) -> str:
        """Generate PowerShell function for an alias.

        Args:
            alias_name: Name of the alias (e.g., "m")
            command: Memory tool command name (e.g., "record")

        Returns:
            PowerShell function definition
        """
        return f'function {alias_name} {{ python -m {self.package_name} {command} $args }}'

    def read_powershell_profile(self, profile_path: Path) -> str:
        """Read PowerShell profile content.

        Args:
            profile_path: Path to profile file

        Returns:
            Profile content (empty string if file doesn't exist)
        """
        if not profile_path.exists():
            return ""

        try:
            return profile_path.read_text(encoding="utf-8")
        except Exception:
            # Try with default encoding
            return profile_path.read_text()

    def write_powershell_profile(self, profile_path: Path, content: str) -> None:
        """Write PowerShell profile content.

        Args:
            profile_path: Path to profile file
            content: Content to write

        Raises:
            AliasError: If write fails
        """
        try:
            # Ensure parent directory exists
            profile_path.parent.mkdir(parents=True, exist_ok=True)

            profile_path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise AliasError(f"Failed to write PowerShell profile: {e}")

    def is_alias_in_profile(self, profile_content: str, alias_name: str) -> bool:
        """Check if alias is already defined in PowerShell profile.

        Args:
            profile_content: Content of PowerShell profile
            alias_name: Name of alias to check

        Returns:
            True if alias is defined
        """
        # Look for function definition
        marker = f"function {alias_name} {{"
        return marker in profile_content

    def install_powershell_alias(
        self,
        alias_name: str,
        profile_path: Optional[Path] = None,
    ) -> Tuple[Path, bool]:
        """Install alias to PowerShell profile.

        Args:
            alias_name: Name of the alias (e.g., "m")
            profile_path: Custom profile path (default: auto-detect)

        Returns:
            Tuple of (profile_path, was_added)
            was_added is False if alias already existed

        Raises:
            AliasError: If installation fails or PowerShell not available
        """
        if alias_name not in self.ALIASES:
            raise AliasError(f"Unknown alias: {alias_name}")

        # Get profile path
        if profile_path is None:
            profile_path = self.get_powershell_profile_path()
            if profile_path is None:
                raise AliasError("PowerShell not available or profile path not found")

        command, _ = self.ALIASES[alias_name]

        # Read existing profile
        profile_content = self.read_powershell_profile(profile_path)

        # Check if already installed
        if self.is_alias_in_profile(profile_content, alias_name):
            return (profile_path, False)

        # Add function definition
        function_def = self.generate_powershell_function(alias_name, command)

        # Add to profile with section marker
        if not profile_content:
            # New profile
            new_content = f"""# Memory Tool aliases (auto-generated)
{function_def}
"""
        else:
            # Append to existing profile
            if not profile_content.endswith("\n"):
                profile_content += "\n"

            # Check if we have a memory tool section
            if "# Memory Tool aliases" in profile_content:
                # Add to existing section
                lines = profile_content.split("\n")
                insert_index = -1
                for i, line in enumerate(lines):
                    if "# Memory Tool aliases" in line:
                        # Find last non-empty line in section
                        for j in range(i + 1, len(lines)):
                            if lines[j].startswith("function ") and self.package_name in lines[j]:
                                insert_index = j + 1
                            elif lines[j].strip() and not lines[j].startswith("function "):
                                break

                if insert_index > 0:
                    lines.insert(insert_index, function_def)
                    new_content = "\n".join(lines)
                else:
                    # Section exists but empty, add after marker
                    new_content = profile_content.replace(
                        "# Memory Tool aliases (auto-generated)",
                        f"# Memory Tool aliases (auto-generated)\n{function_def}",
                    )
            else:
                # Add new section
                new_content = f"""{profile_content}
# Memory Tool aliases (auto-generated)
{function_def}
"""

        # Write updated profile
        self.write_powershell_profile(profile_path, new_content)

        return (profile_path, True)

    def uninstall_powershell_alias(
        self,
        alias_name: str,
        profile_path: Optional[Path] = None,
    ) -> Tuple[Optional[Path], bool]:
        """Uninstall alias from PowerShell profile.

        Args:
            alias_name: Name of the alias
            profile_path: Custom profile path (default: auto-detect)

        Returns:
            Tuple of (profile_path, was_removed)
            profile_path is None if PowerShell not available
            was_removed is False if alias didn't exist

        Raises:
            AliasError: If removal fails
        """
        # Get profile path
        if profile_path is None:
            profile_path = self.get_powershell_profile_path()
            if profile_path is None:
                return (None, False)

        # Read existing profile
        if not profile_path.exists():
            return (profile_path, False)

        profile_content = self.read_powershell_profile(profile_path)

        # Check if alias exists
        if not self.is_alias_in_profile(profile_content, alias_name):
            return (profile_path, False)

        # Remove function definition
        command, _ = self.ALIASES.get(alias_name, ("", ""))
        function_def = self.generate_powershell_function(alias_name, command)

        # Remove the line
        lines = profile_content.split("\n")
        new_lines = [line for line in lines if line.strip() != function_def.strip()]

        # Clean up empty section
        cleaned_lines = []
        skip_next_empty = False
        for i, line in enumerate(new_lines):
            if "# Memory Tool aliases" in line:
                # Check if section is now empty
                section_empty = True
                for j in range(i + 1, len(new_lines)):
                    if new_lines[j].strip():
                        if new_lines[j].startswith("function ") and self.package_name in new_lines[j]:
                            section_empty = False
                            break
                        else:
                            # Hit non-memory-tool content
                            break

                if section_empty:
                    skip_next_empty = True
                    continue  # Skip the section header

            if skip_next_empty and not line.strip():
                skip_next_empty = False
                continue

            cleaned_lines.append(line)

        new_content = "\n".join(cleaned_lines)

        # Write updated profile
        self.write_powershell_profile(profile_path, new_content)

        return (profile_path, True)

    def install_all_powershell(
        self,
        profile_path: Optional[Path] = None,
    ) -> Dict[str, bool]:
        """Install all aliases to PowerShell profile.

        Args:
            profile_path: Custom profile path (default: auto-detect)

        Returns:
            Dictionary mapping alias names to whether they were added (not already existing)

        Raises:
            AliasError: If installation fails
        """
        installed = {}

        for alias_name in self.ALIASES.keys():
            _, was_added = self.install_powershell_alias(alias_name, profile_path)
            installed[alias_name] = was_added

        return installed

    def uninstall_all_powershell(
        self,
        profile_path: Optional[Path] = None,
    ) -> List[str]:
        """Uninstall all aliases from PowerShell profile.

        Args:
            profile_path: Custom profile path (default: auto-detect)

        Returns:
            List of removed alias names

        Raises:
            AliasError: If removal fails
        """
        removed = []

        for alias_name in self.ALIASES.keys():
            _, was_removed = self.uninstall_powershell_alias(alias_name, profile_path)
            if was_removed:
                removed.append(alias_name)

        return removed

    def list_powershell_installed(
        self,
        profile_path: Optional[Path] = None,
    ) -> Dict[str, bool]:
        """List installation status of aliases in PowerShell profile.

        Args:
            profile_path: Custom profile path (default: auto-detect)

        Returns:
            Dictionary mapping alias names to installation status
        """
        # Get profile path
        if profile_path is None:
            profile_path = self.get_powershell_profile_path()
            if profile_path is None:
                return {alias: False for alias in self.ALIASES.keys()}

        # Read profile
        if not profile_path.exists():
            return {alias: False for alias in self.ALIASES.keys()}

        profile_content = self.read_powershell_profile(profile_path)

        # Check each alias
        status = {}
        for alias_name in self.ALIASES.keys():
            status[alias_name] = self.is_alias_in_profile(profile_content, alias_name)

        return status
