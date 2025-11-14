"""Module summarization functionality."""

from pathlib import Path
from typing import Optional
from ..llm.client import LLMClient
from ..llm.prompts import MODULE_SUMMARY_PROMPT


class ModuleSummarizer:
    """Summarize module documentation using LLM."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize module summarizer.

        Args:
            llm_client: LLM client (optional, creates one if not provided)
        """
        self.llm_client = llm_client or LLMClient()

    def summarize_module(self, module_path: Path) -> str:
        """
        Summarize a module's documentation.

        Args:
            module_path: Path to module directory

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

        for doc_file in doc_files:
            file_path = module_path / doc_file
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                if content.strip():
                    module_content.append(f"## File: {doc_file}\n\n{content}")

        if not module_content:
            raise ValueError(f"No documentation files found in: {module_path}")

        # Combine module documentation
        full_content = f"""# Module: {module_name}

{chr(10).join(module_content)}
"""

        # Generate summary
        summary = self.llm_client.summarize(
            content=full_content,
            system_prompt=MODULE_SUMMARY_PROMPT,
        )

        return summary

    def summarize_all_modules(self, modules_root: Optional[Path] = None) -> dict[str, str]:
        """
        Summarize all modules in the modules directory.

        Args:
            modules_root: Path to modules directory (optional, uses .memory/modules if not provided)

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
                summary = self.summarize_module(module_dir)
                summaries[module_dir.name] = summary
            except (FileNotFoundError, ValueError) as e:
                # Skip modules without documentation
                summaries[module_dir.name] = f"Error: {e}"

        return summaries
