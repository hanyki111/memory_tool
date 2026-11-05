"""Module management functionality."""

import getpass
import re
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Sequence, Tuple
from datetime import datetime
import yaml

from memory_tool.utils.module_docs import discover_module_paths, resolve_module_document
from memory_tool.utils.paths import base_dir_for_root, get_project_root


def _yaml_value(value: str) -> str:
    """Quote a frontmatter value only when plain YAML would misread it."""
    if not value:
        return ""
    dumped = yaml.safe_dump(value, allow_unicode=True, default_flow_style=True)
    return dumped.split("\n")[0].strip()


def default_author() -> str:
    """Name the person writing a new document, as ``human:<id>``."""
    try:
        return f"human:{getpass.getuser()}"
    except Exception:
        return "human:unknown"


def render_new_document(
    title: str,
    doc_type: Optional[str] = None,
    description: str = "",
    tags: Optional[Sequence[str]] = None,
    generated_by: Optional[str] = None,
) -> str:
    """Build a new document: frontmatter and a title.

    Empty fields stay visible so they can be filled in later without having to
    remember their names. There are no required sections and no instructions in
    the document: it is the writer's text, and guidance lives in ``mmodule guide``.

    Args:
        title: Document title
        doc_type: Document type
        description: One sentence on what the document answers
        tags: Tags
        generated_by: Who writes it. Defaults to the current user.

    Returns:
        The document's text.
    """
    tag_values = ", ".join(_yaml_value(tag) for tag in (tags or []))
    author = generated_by or default_author()
    at = datetime.now().astimezone().isoformat(timespec="seconds")

    lines = [
        "---",
        f"type: {_yaml_value(doc_type or '')}".rstrip(),
        f"description: {_yaml_value(description or '')}".rstrip(),
        f"tags: [{tag_values}]",
        "generated:",
        f"  by: {_yaml_value(author)}",
        f"  at: {at}",
        "---",
        "",
        f"# {title}",
        "",
    ]
    return "\n".join(lines)


class ModuleError(Exception):
    """Base exception for module operations."""
    pass


class ModuleManager:
    """Manager for memory modules."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize module manager.

        Args:
            base_path: Base path for project. Defaults to current directory.
        """
        if base_path is None:
            base_path = get_project_root()
        self.base_path = Path(base_path)
        self.memory_path = base_dir_for_root(self.base_path)
        self.modules_path = self.memory_path / "modules"
        self.archive_path = self.modules_path / "archive"

    def is_initialized(self) -> bool:
        """Check if .memory/modules/ exists."""
        return self.modules_path.exists()

    def _validate_module_name(self, name: str) -> None:
        """Validate module name or path."""
        parts = name.split('/')
        reserved = ["archive", "templates", ".git"]

        for part in parts:
            if not part:
                raise ModuleError(f"Invalid module path: {name}. Empty path component.")

            if not re.match(r'^[\w\s-]+$', part):
                raise ModuleError(
                    f"Invalid module path component: {part}. "
                    f"Use only letters, numbers, spaces, dashes, and underscores."
                )

            if part.lower() in reserved:
                raise ModuleError(f"Reserved name in path: {part}")

    def get_module_file_path(self, name: str) -> Path:
        """Get file path for a module following [Folder]/[Folder].md convention."""
        mod_basename = Path(name).name
        return self.modules_path / name / f"{mod_basename}.md"

    def module_exists(self, name: str) -> bool:
        """Check if module exists (as single file in folder or old format)."""
        file_path = self.get_module_file_path(name)
        if file_path.exists() and file_path.is_file():
            return True
        # Check flat single file format (e.g., .memory/modules/name.md)
        flat_file = self.modules_path / f"{name}.md"
        if flat_file.exists() and flat_file.is_file():
            return True
        # Check legacy directory format
        dir_path = self.modules_path / name
        return dir_path.exists() and dir_path.is_dir() and ((dir_path / "module.md").exists() or (dir_path / "current.md").exists())

    def resolve_module_doc(self, name: str) -> Optional[Path]:
        """Find a module's primary markdown document.

        Three layouts exist and all are still readable:
          1. ``<name>/<basename>.md``  -- current single-file encapsulation
          2. ``<name>.md``             -- flat single file
          3. ``<name>/current.md``     -- legacy multi-file

        Callers that only checked for ``current.md`` silently skipped every
        module in the first two layouts.

        Args:
            name: Module name or relative path

        Returns:
            Path to the module's main document, or None if none exists.
        """
        return resolve_module_document(self.modules_path / name)

    def is_archived(self, name: str) -> bool:
        """Check if module is archived."""
        if not self.archive_path.exists():
            return False

        mod_basename = Path(name).name
        archive_encapsulated = self.archive_path / name / f"{mod_basename}.md"
        archive_flat = self.archive_path / f"{name}.md"
        archive_dir = self.archive_path / name
        return archive_encapsulated.exists() or archive_flat.exists() or (archive_dir.exists() and archive_dir.is_dir())

    def create(
        self,
        name: str,
        description: str = "",
        tags: Optional[List[str]] = None,
        kind: Optional[str] = None,
        nature: Optional[str] = None,
        draft: bool = False,
        doc_type: Optional[str] = None,
        generated_by: Optional[str] = None,
    ) -> Path:
        """Create a module.

        Without a kind, this writes a new document: frontmatter and a title, in
        one file. ``kind``, ``nature`` and ``draft`` select a deprecated template,
        written to [Folder]/[Folder].md.

        Args:
            name: Module name or path (e.g. 'memory-tool' or 'memory-tool/core-system')
            description: Module description
            tags: Module tags
            kind: Template kind -- "knowledge", "implementation" or "intent".
                When omitted, the value of ``modules.default_kind`` in config is
                used; if that is unset too, the original generic template is
                produced.
            nature: Body outline. knowledge takes concept, reference, analysis,
                tracker or method; intent takes idea, inquiry or plan.
            draft: Write the seed document instead of the full skeleton. Grow it
                later with ``grow()``. Requires a kind, since the seed is
                kind-specific.

        Returns:
            Path to created single markdown file

        Raises:
            ModuleError: If creation fails
        """
        if not self.is_initialized():
            raise ModuleError(
                f"Modules directory not found at {self.modules_path}. "
                f"Run 'minit' to initialize."
            )

        self._validate_module_name(name)

        if self.module_exists(name):
            raise ModuleError(f"Module already exists: {name}")

        resolved_kind = self._resolve_kind(kind, nature)

        if draft and resolved_kind is None:
            raise ModuleError(
                "--draft needs a kind, because the seed document differs per "
                "kind. Pass --kind knowledge|implementation|intent, or set "
                "modules.default_kind."
            )

        if resolved_kind is None:
            return self._create_document(name, doc_type, description, tags, generated_by)

        file_path = self.get_module_file_path(name)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        return self._create_from_template(
            file_path=file_path,
            name=name,
            kind=resolved_kind,
            nature=nature,
            description=description,
            tags=tags,
            draft=draft,
        )

    def documents_moved_by_creating(self, name: str) -> List[Tuple[Path, Path]]:
        """List the documents that move when a module is created at ``name``.

        A document is one file until it gets children. It then moves into a
        folder of its own name, so that renaming or archiving handles the whole
        subject as one folder. Its file name stays the same, so ``[[topic]]``
        links keep working.

        Args:
            name: The module about to be created

        Returns:
            (current path, new path) pairs, outermost parent first.
        """
        moves = []
        parts = Path(name).parts

        for depth in range(1, len(parts)):
            ancestor = Path(*parts[:depth])
            flat = self.modules_path / f"{ancestor.as_posix()}.md"
            encapsulated = self.get_module_file_path(ancestor.as_posix())

            if flat.is_file() and not encapsulated.exists():
                moves.append((flat, encapsulated))

        return moves

    def _create_document(
        self,
        name: str,
        doc_type: Optional[str],
        description: str,
        tags: Optional[Sequence[str]],
        generated_by: Optional[str],
    ) -> Path:
        """Write a new document: frontmatter and a title, nothing else.

        Args:
            name: Module name or path
            doc_type: Document type. Free text; see ``mmodule guide``.
            description: One sentence on what the document answers
            tags: Tags
            generated_by: Who writes it, ``human:<id>`` or ``<producer>/<version>``

        Returns:
            Path to the new document.
        """
        for current, target in self.documents_moved_by_creating(name):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(current), str(target))

        folder = self.modules_path / name
        if folder.is_dir():
            path = self.get_module_file_path(name)
        else:
            path = self.modules_path / f"{name}.md"

        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            path.write_text(
                render_new_document(Path(name).name, doc_type, description, tags, generated_by),
                encoding="utf-8",
            )
        except OSError as e:
            raise ModuleError(f"Failed to create module file: {e}")

        return path

    def _resolve_kind(self, kind: Optional[str], nature: Optional[str]) -> Optional[str]:
        """Decide which template kind to use.

        Explicit ``kind`` wins. Otherwise ``modules.default_kind`` from config
        applies, which lets a knowledge-oriented project opt in once instead of
        passing --kind on every create. A bare ``nature`` names its own kind,
        since no nature name is shared between kinds.

        Returns:
            The kind name, or None to use the original generic template.
        """
        if kind:
            return kind
        if nature:
            from memory_tool.core.module_templates import (
                NATURE_KIND,
                kind_for_nature,
            )

            # An unknown name still resolves to a kind so that the template
            # layer reports it, rather than silently producing a bare module.
            return kind_for_nature(nature) or NATURE_KIND

        try:
            from memory_tool.utils.config import Config

            configured = Config(self.memory_path).get("modules.default_kind")
        except Exception:
            return None

        return configured or None

    #: The classification line a templated module carries, e.g.
    #: "**Kind:** intent | **Nature:** plan | **Stage:** 착상 | ..."
    _KIND_LINE = re.compile(r"^\*\*Kind:\*\*.*$", re.MULTILINE)
    _KIND_VALUE = re.compile(r"\*\*Kind:\*\*\s*([a-z]+)")
    _NATURE_VALUE = re.compile(r"\*\*Nature:\*\*\s*([a-z]+)\s*(?:\||$)")

    def read_classification(self, name: str) -> Dict[str, Optional[str]]:
        """Read a module's Kind and Nature from its own header.

        Growing a draft needs the same classification the draft was created
        with; asking for it again would invite a different answer, and a module
        whose header says one thing and whose body outline says another is worse
        than either.

        Args:
            name: Module name or path

        Returns:
            {"kind": str or None, "nature": str or None}. Both are None for a
            module made from the generic template, which carries no Kind line.
        """
        doc = self.resolve_module_doc(name)
        if doc is None:
            raise ModuleError(f"Module not found: {name}")

        text = doc.read_text(encoding="utf-8")
        line_match = self._KIND_LINE.search(text)
        if line_match is None:
            return {"kind": None, "nature": None}

        line = line_match.group(0)
        kind = self._KIND_VALUE.search(line)
        nature = self._NATURE_VALUE.search(line)

        return {
            "kind": kind.group(1) if kind else None,
            "nature": nature.group(1) if nature else None,
        }

    def grow(
        self,
        name: str,
        kind: Optional[str] = None,
        nature: Optional[str] = None,
        to_level: Optional[int] = None,
        parts: Sequence[str] = (),
        complete: bool = False,
    ) -> tuple:
        """Advance a module one rung up the growth ladder, or attach parts.

        The second half of the draft workflow: a seed thickens toward the full
        document one step at a time, at the pace the thinking does. What is
        already written is left exactly as it is.

        Args:
            name: Module name or path
            kind: Override the kind in the module's header
            nature: Override the nature in the module's header
            to_level: Stop at this rung instead of the next one. Pass MAX_LEVEL
                for the whole ladder in one call.
            parts: Parts to attach whatever the rung (decisions, scope, ...).
                Given alone, the module does not climb.
            complete: The whole skeleton: every rung and every attachable part.

        Returns:
            (path, parts added, level before, level after). The parts list is
            empty when there was nothing to add.

        Raises:
            ModuleError: If the module is missing, carries no kind, the level or
                a part is not valid, or the templates cannot be loaded.
        """
        from memory_tool.core.module_templates import (
            MAX_LEVEL,
            TemplateError,
            attachable_parts,
            grow_module_document,
        )

        doc = self.resolve_module_doc(name)
        if doc is None:
            hint = self.diagnose_missing(name)
            message = f"Module not found: {name}"
            if hint:
                message += "\n" + hint
            raise ModuleError(message)

        found = self.read_classification(name)
        resolved_kind = kind or found["kind"]
        resolved_nature = nature or found["nature"]

        if resolved_kind is None:
            raise ModuleError(
                f"'{name}' has no '**Kind:**' line, so there is no skeleton to "
                f"grow into. Pass --kind knowledge|implementation|intent."
            )

        existing = doc.read_text(encoding="utf-8")

        try:
            if complete:
                to_level = MAX_LEVEL
                parts = attachable_parts(resolved_kind)

            grown, added, before, after = grow_module_document(
                existing,
                name=name,
                kind=resolved_kind,
                nature=resolved_nature,
                memory_path=self.memory_path,
                to_level=to_level,
                parts=parts,
            )
        except TemplateError as e:
            raise ModuleError(str(e)) from e

        if added:
            try:
                doc.write_text(grown, encoding="utf-8")
            except Exception as e:
                raise ModuleError(f"Failed to write module file: {e}")

        return doc, added, before, after

    def _create_from_template(
        self,
        file_path: Path,
        name: str,
        kind: str,
        nature: Optional[str],
        description: str,
        tags: Optional[List[str]],
        draft: bool = False,
    ) -> Path:
        """Write a module assembled from the MOP templates."""
        from memory_tool.core.module_templates import (
            TemplateError,
            build_module_document,
        )

        try:
            content = build_module_document(
                name=name,
                kind=kind,
                nature=nature,
                description=description,
                tags=tags,
                memory_path=self.memory_path,
                draft=draft,
            )
        except TemplateError as e:
            raise ModuleError(str(e)) from e

        try:
            file_path.write_text(content, encoding="utf-8")
        except Exception as e:
            raise ModuleError(f"Failed to create module file: {e}")

        return file_path

    def discover_all_modules(self, include_archived: bool = False) -> List[Path]:
        """Discover all modules recursively by finding module markdown files.

        Args:
            include_archived: Also return modules that live under an archive
                folder. They are excluded by default.

        Returns:
            List of module relative paths (without .md extension) sorted by path.
        """
        return discover_module_paths(self.modules_path, include_archived)

    def find_module_by_name(self, name: str, exact: bool = False) -> List[str]:
        """Find module(s) by name, searching all module paths.

        Comparison is on the forward-slash form. Everything else in the system
        writes module paths that way -- ``mmodule create "a/b"``, ``[[a/b]]``
        wiki links, the docs -- but discovery yields ``Path`` objects, whose
        ``str()`` uses a backslash on Windows. A nested module therefore never
        matched the name its own creation command was given.
        """
        wanted = Path(name).as_posix()
        matches = []

        for module_path in self.discover_all_modules():
            module_str = module_path.as_posix()

            if exact:
                if module_str == wanted:
                    matches.append(module_str)
            else:
                if module_str == wanted or module_path.parts[-1] == wanted:
                    matches.append(module_str)

        return matches

    def diagnose_missing(self, name: str) -> Optional[str]:
        """Explain a failed lookup when the reason is guessable, else None.

        One mistake accounts for most of them, and it is invisible from the
        error alone: a module document must be named after its own folder.
        `modules/asyncio/초안.md` is not the module "asyncio" -- discovery reads
        it as a separate module called "asyncio/초안" -- so the name the author
        meant reports as missing while the file sits right there.

        This matters most for documents written by hand, which is the only way
        to start a module on mobile: the CLI cannot run there, so the file is
        created from a template and named by whoever typed it.

        Args:
            name: The module name that did not resolve

        Returns:
            A sentence naming the likely cause and its fix, or None when there
            is nothing specific to say.
        """
        # Only failed lookups get a diagnosis. Without this the message fires on
        # a perfectly good module and reports its own document as missing.
        if self.resolve_module_doc(name) is not None:
            return None

        folder = self.modules_path / name
        if not folder.is_dir():
            return None

        expected = f"{Path(name).name}.md"
        docs = sorted(p.name for p in folder.glob("*.md"))

        if not docs:
            return (
                f"The folder for '{name}' exists but holds no markdown document. "
                f"A module's document is named after its folder: {expected}."
            )

        return (
            f"The folder for '{name}' exists but has no {expected} in it. "
            f"A module's document is named after its folder, so what is there "
            f"({', '.join(docs)}) reads as separate modules under '{name}/'. "
            f"Renaming one of them to {expected} makes '{name}' resolve."
        )

    def list_modules(self, include_archived: bool = False) -> Dict[str, List[str]]:
        """List all modules."""
        result = {"active": []}

        if not self.modules_path.exists():
            return result

        # Forward slashes, matching what users type and what wiki links use.
        discovered = self.discover_all_modules()
        result["active"] = [p.as_posix() for p in discovered]

        if include_archived and self.archive_path.exists():
            archived = []
            for item in self.archive_path.rglob("*.md"):
                if "archive" in item.parts and not item.name.startswith("_") and not item.name.isupper():
                    if item.stem == item.parent.name:
                        rel = item.parent.relative_to(self.archive_path)
                        archived.append(str(rel))
                    else:
                        rel = item.relative_to(self.archive_path).with_suffix("")
                        archived.append(str(rel))
            archived = list(set(archived))
            archived.sort()
            result["archived"] = archived

        return result

    def build_module_tree(self) -> Dict:
        """Build hierarchical tree structure of modules."""
        modules = self.discover_all_modules()
        tree = {}

        for module_path in modules:
            parts = module_path.parts
            current = tree

            for part in parts:
                if part not in current:
                    current[part] = {}
                current = current[part]

        return tree

    def get_module_info(self, name: str) -> Dict:
        """Get information about a module."""
        file_path = self.get_module_file_path(name)
        flat_file = self.modules_path / f"{name}.md"
        legacy_dir = self.modules_path / name

        exists = file_path.exists() or flat_file.exists() or (legacy_dir.exists() and legacy_dir.is_dir())
        if not exists:
            raise ModuleError(f"Module not found: {name}")

        rel_path = Path(name)
        parent = str(rel_path.parent) if rel_path.parent != Path(".") else None

        all_modules = self.discover_all_modules()
        children = []
        for mod in all_modules:
            mod_str = str(mod)
            if mod_str != name and mod_str.startswith(f"{name}/"):
                sub = mod_str[len(name) + 1:]
                if "/" not in sub:
                    children.append(mod_str)

        children.sort()

        actual_path = file_path if file_path.exists() else (flat_file if flat_file.exists() else legacy_dir)

        return {
            "name": name,
            "path": actual_path,
            "parent": parent,
            "children": children,
        }

    def migrate_module(self, name_or_path: str) -> Path:
        """Migrate legacy multi-file or flat module into [Folder]/[Folder].md directory encapsulated structure.

        Args:
            name_or_path: Module relative path (e.g. 'memory-tool/core-system')

        Returns:
            Path to newly created single module markdown file (.md) inside its own folder.
        """
        target_file = self.get_module_file_path(name_or_path)
        flat_file = self.modules_path / f"{name_or_path}.md"
        dir_path = self.modules_path / name_or_path

        # Case A: Module is flat file (e.g., .memory/modules/memory-tool/core-system.md)
        if flat_file.exists() and flat_file.is_file() and flat_file != target_file:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.move(str(flat_file), str(target_file))
            return target_file

        # Case B: Already in target format
        if target_file.exists() and target_file.is_file():
            return target_file

        # Case C: Legacy directory with multiple files
        if not dir_path.exists() or not dir_path.is_dir():
            raise ModuleError(f"Legacy module directory not found: {name_or_path}")

        std_files = ["module.md", "current.md", "decisions.md", "dependencies.md", "interface.md"]
        combined_sections = []

        module_md_path = dir_path / "module.md"
        if module_md_path.exists():
            combined_sections.append(module_md_path.read_text(encoding="utf-8").strip())
        else:
            combined_sections.append(f"# Module: {Path(name_or_path).name}\n")

        section_titles = {
            "current.md": "## Current Status",
            "decisions.md": "## Decisions",
            "dependencies.md": "## Dependencies",
            "interface.md": "## Interface",
        }

        for fname, default_title in section_titles.items():
            fpath = dir_path / fname
            if fpath.exists():
                content = fpath.read_text(encoding="utf-8").strip()
                if not content.startswith("#"):
                    content = f"{default_title}\n\n{content}"
                combined_sections.append(content)

        for extra_file in dir_path.iterdir():
            if extra_file.is_file() and extra_file.suffix == ".md" and extra_file.name not in std_files and extra_file.name != target_file.name:
                content = extra_file.read_text(encoding="utf-8").strip()
                combined_sections.append(f"## {extra_file.stem.capitalize()}\n\n{content}")

        combined_content = "\n\n---\n\n".join(combined_sections) + "\n"

        target_file.parent.mkdir(parents=True, exist_ok=True)
        target_file.write_text(combined_content, encoding="utf-8")

        for fname in std_files:
            fpath = dir_path / fname
            if fpath.exists():
                fpath.unlink()

        return target_file

    def migrate_all_modules(self) -> List[Path]:
        """Find and migrate all legacy multi-file or flat module files into [Folder]/[Folder].md format.

        Returns:
            List of created/migrated single module .md file paths.
        """
        migrated = []
        if not self.modules_path.exists():
            return migrated

        # 1. First discover all existing module names
        all_modules = self.discover_all_modules()

        # Sort deeper modules first so submodules migrate before parents
        all_modules.sort(key=lambda p: len(p.parts), reverse=True)

        for mod_path in all_modules:
            mod_str = str(mod_path).replace("\\", "/")
            try:
                res = self.migrate_module(mod_str)
                migrated.append(res)
            except Exception as e:
                print(f"Warning: Failed to migrate module '{mod_str}': {e}")

        return migrated

    def archive(self, name: str, reason: str = "") -> Path:
        """Archive a module."""
        if not self.is_initialized():
            raise ModuleError(
                f"Modules directory not found at {self.modules_path}. "
                f"Run 'minit' to initialize."
            )

        file_path = self.get_module_file_path(name)
        dir_path = self.modules_path / name
        flat_path = self.modules_path / f"{name}.md"

        if not dir_path.is_dir() and not flat_path.is_file():
            raise ModuleError(f"Module not found: {name}")

        if self.is_archived(name):
            raise ModuleError(f"Module already archived: {name}")

        self.archive_path.mkdir(parents=True, exist_ok=True)

        target_archive = self.archive_path / f"{name}.md"
        target_archive.parent.mkdir(parents=True, exist_ok=True)

        if flat_path.is_file():
            shutil.move(str(flat_path), str(target_archive))
        elif file_path.is_file() and sum(1 for _ in dir_path.iterdir()) == 1:
            # The folder holds nothing else, so nothing is left behind.
            shutil.move(str(file_path), str(target_archive))
            dir_path.rmdir()

        # What remains is a subject with children, or a legacy module: it moves
        # as a whole, because the children belong to it.
        if dir_path.is_dir():
            target_folder = self.archive_path / name
            shutil.move(str(dir_path), str(target_folder))
            if not target_archive.exists():
                target_archive = target_folder

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        index_path = self.archive_path / "_index.md"

        if index_path.exists():
            index_content = index_path.read_text(encoding="utf-8")
        else:
            index_content = "# Archived Modules\n\n"

        new_entry = f"""## {name}
- **Archived:** {timestamp}
- **Reason:** {reason if reason else "No reason specified"}
- **Location:** ./{name}.md

"""
        index_content += new_entry
        index_path.write_text(index_content, encoding="utf-8")

        return target_archive

    def unarchive(self, name: str) -> Path:
        """Restore module from archive."""
        if not self.archive_path.exists():
            raise ModuleError("Archive directory not found")

        archive_file = self.archive_path / f"{name}.md"
        archive_dir = self.archive_path / name

        if not archive_file.exists() and not archive_dir.exists():
            raise ModuleError(f"Module not found in archive: {name}")

        if self.module_exists(name):
            raise ModuleError(
                f"Active module with name '{name}' already exists. Archive or rename it first."
            )

        restored = self.modules_path / name
        restored.parent.mkdir(parents=True, exist_ok=True)
        result = restored

        if archive_dir.is_dir():
            shutil.move(str(archive_dir), str(restored))

        if archive_file.is_file():
            result = self.modules_path / f"{name}.md"
            shutil.move(str(archive_file), str(result))

        return result

    def rename(self, old_name: str, new_name: str) -> Path:
        """Rename a module."""
        if not self.is_initialized():
            raise ModuleError(
                f"Modules directory not found at {self.modules_path}. "
                f"Run 'minit' to initialize."
            )

        self._validate_module_name(new_name)

        old_dir = self.modules_path / old_name
        old_flat = self.modules_path / f"{old_name}.md"

        if not old_dir.is_dir() and not old_flat.is_file():
            raise ModuleError(f"Module not found: {old_name}")

        new_dir = self.modules_path / new_name
        new_flat = self.modules_path / f"{new_name}.md"

        old_parts = Path(old_name).parts
        if Path(new_name).parts[: len(old_parts)] == old_parts:
            raise ModuleError(f"Cannot move module inside itself: {old_name} -> {new_name}")

        # A folder at the target is refused even without a document of its own:
        # moving into it would merge two trees and nest this one inside it.
        if self.module_exists(new_name) or new_dir.exists() or new_flat.exists():
            raise ModuleError(f"Module already exists: {new_name}")

        old_doc_name = f"{Path(old_name).name}.md"
        new_doc_name = f"{Path(new_name).name}.md"
        moves_document = old_dir.is_dir() and (old_dir / old_doc_name).is_file()

        if moves_document and (old_dir / new_doc_name).exists():
            raise ModuleError(
                f"Cannot rename {old_name}: its folder already holds {new_doc_name}, "
                f"which would be overwritten."
            )

        new_dir.parent.mkdir(parents=True, exist_ok=True)

        if old_dir.is_dir():
            shutil.move(str(old_dir), str(new_dir))
            if moves_document:
                (new_dir / old_doc_name).rename(new_dir / new_doc_name)

        if old_flat.is_file():
            shutil.move(str(old_flat), str(new_flat))

        renamed_doc = None
        if moves_document:
            renamed_doc = new_dir / new_doc_name
        elif new_flat.is_file():
            renamed_doc = new_flat

        if renamed_doc is None:
            return new_dir

        self._update_module_title(renamed_doc, old_name, new_name)
        return renamed_doc

    @staticmethod
    def _update_module_title(document: Path, old_name: str, new_name: str) -> None:
        """Rewrite the ``# Module:`` title of a renamed document, if it has one."""
        try:
            content = document.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return

        for old_title, new_title in (
            (Path(old_name).name, Path(new_name).name),
            (old_name, new_name),
        ):
            content = content.replace(f"# Module: {old_title}", f"# Module: {new_title}")

        document.write_text(content, encoding="utf-8")

