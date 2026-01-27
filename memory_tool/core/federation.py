"""Federated Knowledge System - Core logic for KB federation.

This module provides:
- Registry: KB registry.json management
- Publisher: Local module -> KB publishing
- Importer: KB -> Local project importing
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from memory_tool.utils.frontmatter import Frontmatter


@dataclass
class ModuleInfo:
    """Information about a published module."""
    module_path: str  # e.g., "projects/memory-tool/search-system"
    origin_project: str
    source_hash: str
    published_at: str
    version: int = 1
    tags: List[str] = field(default_factory=list)
    kb_path: str = ""  # Path within KB (e.g., "modules/Projects/memory-tool/search-system/")


@dataclass
class ProjectInfo:
    """Information about a project in KB."""
    name: str
    display_name: str
    published_at: str


class Registry:
    """Manages KB registry.json for tracking published modules."""

    REGISTRY_VERSION = "1.0"

    def __init__(self, kb_path: Path):
        """Initialize registry manager.

        Args:
            kb_path: Path to knowledge base
        """
        self.kb_path = kb_path
        self.registry_dir = kb_path / "modules" / "_Registry"
        self.registry_file = self.registry_dir / "registry.json"

    def ensure_registry(self) -> None:
        """Ensure registry directory and file exist."""
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        if not self.registry_file.exists():
            self._write_registry(self._empty_registry())

    def _empty_registry(self) -> Dict[str, Any]:
        """Create empty registry structure."""
        return {
            "version": self.REGISTRY_VERSION,
            "last_updated": datetime.now().isoformat(),
            "projects": {},
            "modules": {},
        }

    def _read_registry(self) -> Dict[str, Any]:
        """Read registry from file."""
        if not self.registry_file.exists():
            return self._empty_registry()

        with open(self.registry_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write_registry(self, data: Dict[str, Any]) -> None:
        """Write registry to file."""
        data["last_updated"] = datetime.now().isoformat()
        with open(self.registry_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_project(self, project_name: str) -> Optional[ProjectInfo]:
        """Get project info from registry."""
        registry = self._read_registry()
        if project_name in registry.get("projects", {}):
            proj = registry["projects"][project_name]
            return ProjectInfo(
                name=project_name,
                display_name=proj.get("display_name", project_name),
                published_at=proj.get("published_at", ""),
            )
        return None

    def register_project(self, project_name: str, display_name: str = None) -> None:
        """Register or update a project in registry."""
        registry = self._read_registry()

        if "projects" not in registry:
            registry["projects"] = {}

        registry["projects"][project_name] = {
            "display_name": display_name or project_name,
            "published_at": datetime.now().isoformat(),
        }

        self._write_registry(registry)

    def get_module(self, module_key: str) -> Optional[ModuleInfo]:
        """Get module info from registry.

        Args:
            module_key: Module key (e.g., "projects/memory-tool/search-system")
        """
        registry = self._read_registry()
        if module_key in registry.get("modules", {}):
            mod = registry["modules"][module_key]
            return ModuleInfo(
                module_path=module_key,
                origin_project=mod.get("origin_project", ""),
                source_hash=mod.get("source_hash", ""),
                published_at=mod.get("published_at", ""),
                version=mod.get("version", 1),
                tags=mod.get("tags", []),
                kb_path=mod.get("kb_path", ""),
            )
        return None

    def register_module(self, module_info: ModuleInfo) -> None:
        """Register or update a module in registry."""
        registry = self._read_registry()

        if "modules" not in registry:
            registry["modules"] = {}

        registry["modules"][module_info.module_path] = {
            "origin_project": module_info.origin_project,
            "source_hash": module_info.source_hash,
            "published_at": module_info.published_at,
            "version": module_info.version,
            "tags": module_info.tags,
            "kb_path": module_info.kb_path,
        }

        self._write_registry(registry)

    def list_modules(
        self,
        project: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[ModuleInfo]:
        """List all modules in registry.

        Args:
            project: Filter by project name
            category: Filter by category (e.g., "Projects", "Topics")

        Returns:
            List of module info
        """
        registry = self._read_registry()
        modules = []

        for key, mod in registry.get("modules", {}).items():
            # Filter by project
            if project and mod.get("origin_project") != project:
                continue

            # Filter by category
            if category:
                kb_path = mod.get("kb_path", "")
                if not kb_path.startswith(f"modules/{category}/"):
                    continue

            modules.append(ModuleInfo(
                module_path=key,
                origin_project=mod.get("origin_project", ""),
                source_hash=mod.get("source_hash", ""),
                published_at=mod.get("published_at", ""),
                version=mod.get("version", 1),
                tags=mod.get("tags", []),
                kb_path=mod.get("kb_path", ""),
            ))

        return modules


class Publisher:
    """Publishes local modules to knowledge base."""

    def __init__(self, memory_path: Path, kb_path: Path):
        """Initialize publisher.

        Args:
            memory_path: Path to local .memory directory
            kb_path: Path to knowledge base
        """
        self.memory_path = memory_path
        self.kb_path = kb_path
        self.registry = Registry(kb_path)
        self.modules_path = memory_path / "modules"

        # Try to get project name from path
        self.project_name = self._detect_project_name()

    def _detect_project_name(self) -> str:
        """Detect project name from directory structure."""
        # Try to get from .memory/config.yaml or parent directory name
        config_file = self.memory_path / "config.yaml"
        if config_file.exists():
            import yaml
            with open(config_file, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
                if "project_name" in config:
                    return config["project_name"]

        # Fall back to parent directory name
        return self.memory_path.parent.name

    def _find_module(self, module_name: str) -> Optional[Path]:
        """Find module path by name.

        Args:
            module_name: Module name (e.g., "search-system" or "projects/memory-tool/search-system")

        Returns:
            Path to module directory or None
        """
        if not self.modules_path.exists():
            return None

        # Direct path check
        direct_path = self.modules_path / module_name
        if direct_path.exists() and direct_path.is_dir():
            return direct_path

        # Search recursively
        for module_dir in self.modules_path.rglob("*"):
            if module_dir.is_dir() and module_dir.name == module_name:
                return module_dir

        return None

    def _get_module_key(self, module_path: Path) -> str:
        """Get module key from path.

        Args:
            module_path: Path to module directory

        Returns:
            Module key (e.g., "projects/memory-tool/search-system")
        """
        rel_path = module_path.relative_to(self.modules_path)
        return str(rel_path).replace("\\", "/")

    def _compute_module_hash(self, module_path: Path) -> str:
        """Compute hash of module contents.

        Args:
            module_path: Path to module directory

        Returns:
            Combined hash of all files
        """
        import hashlib

        hasher = hashlib.sha256()
        for file_path in sorted(module_path.rglob("*.md")):
            content = file_path.read_text(encoding="utf-8")
            # Hash body only (exclude frontmatter)
            _, body = Frontmatter.parse(content)
            hasher.update(body.encode("utf-8"))

        return hasher.hexdigest()[:8]

    def publish(
        self,
        module_name: str,
        category: str = "Projects",
        tags: Optional[List[str]] = None,
        force: bool = False,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Publish a module to knowledge base.

        Args:
            module_name: Module name or path
            category: KB category ("Projects" or "Topics")
            tags: Optional tags for the module
            force: Force republish even if unchanged
            dry_run: Preview without making changes

        Returns:
            Dictionary with publish result info
        """
        result = {
            "success": False,
            "module_name": module_name,
            "action": "none",
            "files_published": [],
            "message": "",
        }

        # Find module
        module_path = self._find_module(module_name)
        if not module_path:
            result["message"] = f"Module '{module_name}' not found"
            return result

        # Get module key and compute hash
        module_key = self._get_module_key(module_path)
        source_hash = self._compute_module_hash(module_path)

        # Check if already published with same hash
        existing = self.registry.get_module(module_key)
        if existing and existing.source_hash == source_hash and not force:
            result["success"] = True
            result["action"] = "unchanged"
            result["message"] = f"Module '{module_key}' is up to date (hash: {source_hash})"
            return result

        # Determine version
        version = 1
        if existing:
            version = existing.version + 1

        # Determine KB path
        kb_module_path = f"modules/{category}/{self.project_name}/{module_path.name}"
        kb_dest = self.kb_path / kb_module_path

        if dry_run:
            result["success"] = True
            result["action"] = "dry_run"
            result["message"] = f"Would publish '{module_key}' to '{kb_module_path}'"
            result["source_hash"] = source_hash
            result["version"] = version
            result["files_to_publish"] = [str(f.name) for f in module_path.rglob("*.md")]
            return result

        # Ensure registry exists
        self.registry.ensure_registry()

        # Register project if needed
        if not self.registry.get_project(self.project_name):
            self.registry.register_project(self.project_name)

        # Create KB directory
        kb_dest.mkdir(parents=True, exist_ok=True)

        # Copy files with frontmatter injection
        published_at = datetime.now().isoformat()
        files_published = []

        for file_path in module_path.rglob("*.md"):
            rel_file = file_path.relative_to(module_path)
            dest_file = kb_dest / rel_file
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Read and inject frontmatter
            content = file_path.read_text(encoding="utf-8")
            metadata = {
                "origin_project": self.project_name,
                "origin_path": module_key,
                "published_at": published_at,
                "source_hash": source_hash,
                "version": version,
            }
            if tags:
                metadata["tags"] = tags

            new_content = Frontmatter.inject(content, metadata)
            dest_file.write_text(new_content, encoding="utf-8")
            files_published.append(str(rel_file))

        # Register module
        module_info = ModuleInfo(
            module_path=module_key,
            origin_project=self.project_name,
            source_hash=source_hash,
            published_at=published_at,
            version=version,
            tags=tags or [],
            kb_path=kb_module_path + "/",
        )
        self.registry.register_module(module_info)

        result["success"] = True
        result["action"] = "published" if not existing else "updated"
        result["message"] = f"Published '{module_key}' to KB (version {version})"
        result["files_published"] = files_published
        result["source_hash"] = source_hash
        result["version"] = version
        result["kb_path"] = kb_module_path

        return result


class Importer:
    """Imports modules from knowledge base to local project."""

    def __init__(self, memory_path: Path, kb_path: Path):
        """Initialize importer.

        Args:
            memory_path: Path to local .memory directory
            kb_path: Path to knowledge base
        """
        self.memory_path = memory_path
        self.kb_path = kb_path
        self.registry = Registry(kb_path)
        self.modules_path = memory_path / "modules"

    def list_available(
        self,
        project: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[ModuleInfo]:
        """List available modules in KB.

        Args:
            project: Filter by project
            category: Filter by category

        Returns:
            List of available modules
        """
        return self.registry.list_modules(project=project, category=category)

    def import_module(
        self,
        kb_module_path: str,
        target_path: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Import a module from KB to local project.

        Args:
            kb_module_path: Path within KB (e.g., "Projects/memory-tool/search-system")
            target_path: Local target path (e.g., "ref/search-system")
            dry_run: Preview without making changes

        Returns:
            Dictionary with import result info
        """
        result = {
            "success": False,
            "kb_module_path": kb_module_path,
            "action": "none",
            "files_imported": [],
            "message": "",
        }

        # Normalize path
        if not kb_module_path.startswith("modules/"):
            kb_module_path = f"modules/{kb_module_path}"

        # Find source in KB
        source_path = self.kb_path / kb_module_path
        if not source_path.exists():
            result["message"] = f"Module not found in KB: {kb_module_path}"
            return result

        # Determine target path
        if target_path:
            dest_path = self.modules_path / target_path
        else:
            # Default: imported/<module-name>
            module_name = source_path.name
            dest_path = self.modules_path / "imported" / module_name

        if dry_run:
            result["success"] = True
            result["action"] = "dry_run"
            result["message"] = f"Would import '{kb_module_path}' to '{dest_path.relative_to(self.memory_path)}'"
            result["files_to_import"] = [str(f.name) for f in source_path.rglob("*.md")]
            return result

        # Create destination directory
        dest_path.mkdir(parents=True, exist_ok=True)

        # Copy files (preserve frontmatter as-is)
        files_imported = []
        for file_path in source_path.rglob("*.md"):
            rel_file = file_path.relative_to(source_path)
            dest_file = dest_path / rel_file
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy content
            content = file_path.read_text(encoding="utf-8")
            dest_file.write_text(content, encoding="utf-8")
            files_imported.append(str(rel_file))

        result["success"] = True
        result["action"] = "imported"
        result["message"] = f"Imported {len(files_imported)} file(s) to '{dest_path.relative_to(self.memory_path)}'"
        result["files_imported"] = files_imported
        result["target_path"] = str(dest_path.relative_to(self.memory_path))

        return result

    def preview_module(
        self,
        kb_module_path: str,
    ) -> Dict[str, Any]:
        """Preview contents of a KB module without importing.

        Args:
            kb_module_path: Path within KB (e.g., "Projects/memory-tool/search-system")

        Returns:
            Dictionary with module info and file contents
        """
        result = {
            "success": False,
            "kb_module_path": kb_module_path,
            "module_info": None,
            "files": [],
            "message": "",
        }

        # Normalize path
        normalized_path = kb_module_path
        if not kb_module_path.startswith("modules/"):
            normalized_path = f"modules/{kb_module_path}"

        # Find source in KB
        source_path = self.kb_path / normalized_path
        if not source_path.exists():
            result["message"] = f"Module not found in KB: {kb_module_path}"
            return result

        # Try to get module info from registry
        # Find matching module by kb_path
        all_modules = self.registry.list_modules()
        module_info = None
        for mod in all_modules:
            # Compare normalized paths
            mod_kb_path = mod.kb_path.rstrip("/")
            if mod_kb_path == normalized_path or mod_kb_path == normalized_path.rstrip("/"):
                module_info = mod
                break

        # Collect file contents
        files = []
        for file_path in sorted(source_path.rglob("*.md")):
            rel_file = file_path.relative_to(source_path)
            content = file_path.read_text(encoding="utf-8")

            # Parse frontmatter
            frontmatter, body = Frontmatter.parse(content)

            files.append({
                "name": str(rel_file),
                "frontmatter": frontmatter,
                "content": body,
                "full_content": content,
            })

        result["success"] = True
        result["module_info"] = module_info
        result["files"] = files
        result["message"] = f"Found {len(files)} file(s) in module"

        return result
