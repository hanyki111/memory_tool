"""Module summarization functionality."""

import hashlib
import re
from pathlib import Path
from datetime import datetime
from typing import Optional, Literal
from ..llm.client import LLMClient
from ..llm.prompts import get_prompt_for_language, detect_language
from ..utils.config import Config


class ModuleSummarizer:
    """Summarize module documentation using LLM."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize module summarizer.

        Args:
            llm_client: LLM client (optional, creates one if not provided)
        """
        self.llm_client = llm_client or LLMClient()
        self.config = Config()

        # Summary directory
        self.summary_dir = Path.cwd() / ".memory" / "summaries"
        self.summary_dir.mkdir(parents=True, exist_ok=True)

    def _get_output_language(
        self,
        cli_language: Optional[str],
        content: str,
    ) -> Literal["ko", "en"]:
        """
        Determine output language based on priority.

        Priority:
        1. CLI flag (highest)
        2. Config setting
        3. Auto-detect from content (fallback)

        Args:
            cli_language: Language from CLI flag (ko/en/auto/None)
            content: Content to analyze for auto-detection

        Returns:
            "ko" or "en"
        """
        # 1. CLI flag (highest priority)
        if cli_language and cli_language != "auto":
            return cli_language

        # 2. Config setting
        config_lang = self.config.get("llm.output_language", "auto")
        if config_lang != "auto":
            return config_lang

        # 3. Auto-detect from content
        return detect_language(content)

    def get_content_hash(self, file_path: Path) -> str:
        """
        Calculate SHA256 hash of file content.

        Args:
            file_path: Path to file

        Returns:
            SHA256 hash as hex string
        """
        if not file_path.exists():
            return ""

        content = file_path.read_text(encoding="utf-8")
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get_summary_file(self, module_relative_path: str) -> Path:
        """
        Get path for summary file.

        Args:
            module_relative_path: Relative path to module (e.g., "projects/memory-tool/core-system")

        Returns:
            Path to summary file
        """
        # Replace path separators with underscores for filename
        safe_name = module_relative_path.replace("/", "_").replace("\\", "_")
        summary_dir = self.summary_dir / "modules"
        summary_dir.mkdir(parents=True, exist_ok=True)
        return summary_dir / f"{safe_name}.md"

    def extract_hash_from_summary(self, summary_file: Path) -> Optional[str]:
        """
        Extract source hash from summary metadata.

        Args:
            summary_file: Path to summary file

        Returns:
            Source hash or None if not found
        """
        if not summary_file.exists():
            return None

        content = summary_file.read_text(encoding="utf-8")

        # Look for metadata comment
        match = re.search(r"<!-- metadata\n.*?source_hash:\s*(\w+)", content, re.DOTALL)
        if match:
            return match.group(1)

        return None

    def is_cache_valid(self, source_files: list[Path], summary_file: Path) -> bool:
        """
        Check if cached summary is still valid.

        Args:
            source_files: List of source files (module docs)
            summary_file: Path to summary file

        Returns:
            True if cache is valid (content unchanged)
        """
        if not summary_file.exists():
            return False

        # Calculate combined hash of all source files
        combined_content = "".join([f.read_text(encoding="utf-8") for f in source_files if f.exists()])
        current_hash = hashlib.sha256(combined_content.encode("utf-8")).hexdigest()

        # Get cached hash
        cached_hash = self.extract_hash_from_summary(summary_file)

        return current_hash == cached_hash and cached_hash is not None

    def save_summary_with_metadata(
        self,
        summary: str,
        summary_file: Path,
        module_path: Path,
        source_hash: str,
    ) -> None:
        """
        Save summary with metadata.

        Args:
            summary: Summary text
            summary_file: Path to save summary
            module_path: Path to module directory
            source_hash: Hash of source content
        """
        # Get timestamp
        timestamp = datetime.now().isoformat()

        # Get relative path, handling both absolute and relative paths
        try:
            if module_path.is_absolute():
                source_path = module_path.relative_to(Path.cwd()).as_posix()
            else:
                source_path = module_path.as_posix()
        except ValueError:
            # If relative_to fails, just use the path as is
            source_path = str(module_path)

        # Build metadata comment
        metadata = f"""<!-- metadata
source: {source_path}
source_hash: {source_hash}
generated: {timestamp}
-->

"""

        # Save with metadata
        full_content = metadata + summary
        summary_file.write_text(full_content, encoding="utf-8")

    def summarize_module(
        self,
        module_path: Path,
        force: bool = False,
        output_language: Optional[str] = None,
    ) -> str:
        """
        Summarize a module's documentation.

        Args:
            module_path: Path to module directory
            force: Force regeneration ignoring cache
            output_language: Output language (ko/en/auto/None)

        Returns:
            Summary text

        Raises:
            FileNotFoundError: If module doesn't exist
            ValueError: If module has no documentation files
        """
        if not module_path.exists():
            raise FileNotFoundError(f"Module not found: {module_path}")

        if not module_path.is_dir():
            raise ValueError(f"Not a directory: {module_path}")

        # Collect module documentation files
        doc_files = [
            "module.md",
            "README.md",
            "interface.md",
            "dependencies.md",
            "current.md",
        ]

        module_content = []
        module_name = module_path.name
        source_files = []

        for doc_file in doc_files:
            file_path = module_path / doc_file
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                if content.strip():
                    module_content.append(f"## File: {doc_file}\n\n{content}")
                    source_files.append(file_path)

        if not module_content:
            raise ValueError(f"No documentation files found in: {module_path}")

        # Get module relative path for summary filename
        try:
            module_relative = module_path.relative_to(Path.cwd() / ".memory" / "modules")
            module_relative_path = module_relative.as_posix()
        except ValueError:
            # If not in standard location, use module name
            module_relative_path = module_name

        # Check cache if not forced
        summary_file = self.get_summary_file(module_relative_path)
        if not force and self.is_cache_valid(source_files, summary_file):
            # Return cached summary
            cached_content = summary_file.read_text(encoding="utf-8")
            # Remove metadata comment
            cached_summary = re.sub(r"<!-- metadata.*?-->\n\n", "", cached_content, flags=re.DOTALL)
            return cached_summary

        # Combine module documentation
        full_content = f"""# Module: {module_name}

{chr(10).join(module_content)}
"""

        # Determine output language
        lang = self._get_output_language(output_language, full_content)

        # Get language-specific prompt
        system_prompt = get_prompt_for_language("module", lang)

        # Generate summary
        summary = self.llm_client.summarize(
            content=full_content,
            system_prompt=system_prompt,
        )

        # Calculate combined hash and save with metadata
        combined_content = "".join([f.read_text(encoding="utf-8") for f in source_files])
        combined_hash = hashlib.sha256(combined_content.encode("utf-8")).hexdigest()
        self.save_summary_with_metadata(summary, summary_file, module_path, combined_hash)

        return summary

    def summarize_all_modules(self, modules_root: Optional[Path] = None, force: bool = False) -> dict[str, str]:
        """
        Summarize all modules in the modules directory.

        Args:
            modules_root: Path to modules directory (optional, uses .memory/modules if not provided)
            force: Force regeneration ignoring cache

        Returns:
            Dictionary mapping module name to summary

        Raises:
            FileNotFoundError: If modules directory doesn't exist
        """
        if modules_root is None:
            modules_root = Path.cwd() / ".memory" / "modules"

        if not modules_root.exists():
            raise FileNotFoundError(f"Modules directory not found: {modules_root}")

        # Find all module directories (exclude archive and _index.md)
        module_dirs = [
            d for d in modules_root.iterdir()
            if d.is_dir() and d.name != "archive" and not d.name.startswith("_")
        ]

        summaries = {}
        for module_dir in module_dirs:
            try:
                summary = self.summarize_module(module_dir, force=force)
                summaries[module_dir.name] = summary
            except (FileNotFoundError, ValueError) as e:
                # Skip modules without documentation
                summaries[module_dir.name] = f"Error: {e}"

        return summaries
