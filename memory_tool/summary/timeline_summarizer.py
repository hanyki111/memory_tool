"""Timeline summarization functionality."""

import hashlib
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Literal
from ..llm.client import LLMClient
from ..llm.prompts import detect_language
from ..llm.prompt_builder import PromptBuilder
from ..core.timeline import Timeline
from ..utils.config import Config
from .context import ContextGatherer
from memory_tool.utils.paths import display_path, get_base_path


class TimelineSummarizer:
    """Summarize timeline entries using LLM."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize timeline summarizer.

        Args:
            llm_client: LLM client (optional, creates one if not provided)
        """
        self.llm_client = llm_client or LLMClient()
        self.timeline = Timeline(Path.cwd())
        self.config = Config()
        self.context_gatherer = ContextGatherer()

        # Get max context tokens from config
        max_tokens = self.config.get("llm.max_context_tokens", 2000)
        self.prompt_builder = PromptBuilder(max_context_tokens=max_tokens)

        # Summary directory
        self.summary_dir = get_base_path() / "summaries"
        self.summary_dir.mkdir(parents=True, exist_ok=True)

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

    def get_summary_file(self, summary_type: str, identifier: str) -> Path:
        """
        Get path for summary file.

        Args:
            summary_type: Type of summary (daily/weekly/range)
            identifier: Identifier (date or date range)

        Returns:
            Path to summary file
        """
        summary_dir = self.summary_dir / summary_type
        summary_dir.mkdir(parents=True, exist_ok=True)
        return summary_dir / f"{identifier}.md"

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

    def is_cache_valid(self, source_file: Path, summary_file: Path) -> bool:
        """
        Check if cached summary is still valid.

        Args:
            source_file: Path to source file (timeline)
            summary_file: Path to summary file

        Returns:
            True if cache is valid (content unchanged)
        """
        if not summary_file.exists():
            return False

        # Calculate current hash
        current_hash = self.get_content_hash(source_file)

        # Get cached hash
        cached_hash = self.extract_hash_from_summary(summary_file)

        return current_hash == cached_hash and cached_hash is not None

    def save_summary_with_metadata(
        self,
        summary: str,
        summary_file: Path,
        source_file: Path,
        source_hash: str,
        language: str,
    ) -> None:
        """
        Save summary with metadata.

        Args:
            summary: Summary text
            summary_file: Path to save summary
            source_file: Path to source file
            source_hash: Hash of source content
            language: Output language
        """
        # Get timestamp
        timestamp = datetime.now().isoformat()

        # Get relative path, handling both absolute and relative paths
        try:
            if source_file.is_absolute():
                source_path = display_path(source_file).as_posix()
            else:
                source_path = source_file.as_posix()
        except ValueError:
            # If relative_to fails, just use the path as is
            source_path = str(source_file)

        # Build metadata comment
        metadata = f"""<!-- metadata
source: {source_path}
source_hash: {source_hash}
generated: {timestamp}
language: {language}
-->

"""

        # Save with metadata
        full_content = metadata + summary
        summary_file.write_text(full_content, encoding="utf-8")

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

    def summarize_today(
        self,
        output_language: Optional[str] = None,
        force: bool = False,
    ) -> str:
        """
        Summarize today's timeline.

        Args:
            output_language: Output language (ko/en/auto/None)
            force: Force regeneration ignoring cache

        Returns:
            Summary text

        Raises:
            FileNotFoundError: If today's timeline doesn't exist
            ValueError: If timeline is empty
        """
        today = datetime.now().date()
        return self.summarize_date(today, output_language=output_language, force=force)

    def summarize_date(
        self,
        date: datetime.date,
        output_language: Optional[str] = None,
        force: bool = False,
    ) -> str:
        """
        Summarize a specific date's timeline.

        Args:
            date: Date to summarize
            output_language: Output language (ko/en/auto/None)
            force: Force regeneration ignoring cache

        Returns:
            Summary text

        Raises:
            FileNotFoundError: If timeline file doesn't exist
            ValueError: If timeline is empty
        """
        # Get timeline file path
        dt = datetime.combine(date, datetime.min.time())
        timeline_file = self.timeline.get_timeline_file(dt)

        if not timeline_file.exists():
            raise FileNotFoundError(f"Timeline not found: {timeline_file}")

        # Read timeline content
        content = timeline_file.read_text(encoding="utf-8")

        if not content.strip():
            raise ValueError(f"Timeline is empty: {timeline_file}")

        # Check cache if not forced
        summary_file = self.get_summary_file("daily", date.isoformat())
        if not force and self.is_cache_valid(timeline_file, summary_file):
            # Return cached summary
            cached_content = summary_file.read_text(encoding="utf-8")
            # Remove metadata comment
            cached_summary = re.sub(r"<!-- metadata.*?-->\n\n", "", cached_content, flags=re.DOTALL)
            return cached_summary

        # Add metadata to content
        full_content = f"""# Timeline: {date.isoformat()}

{content}
"""

        # Determine output language
        lang = self._get_output_language(output_language, content)

        # Gather context (minimal for single day)
        context = self.context_gatherer.gather_for_timeline("today", date, date)

        # Build prompt with context
        system_prompt = self.prompt_builder.build_timeline_prompt(lang, context)

        # Generate summary
        summary = self.llm_client.summarize(
            content=full_content,
            system_prompt=system_prompt,
        )

        # Calculate hash and save with metadata
        source_hash = self.get_content_hash(timeline_file)
        self.save_summary_with_metadata(summary, summary_file, timeline_file, source_hash, lang)

        return summary

    def summarize_week(
        self,
        start_date: Optional[datetime.date] = None,
        output_language: Optional[str] = None,
        force: bool = False,
    ) -> str:
        """
        Summarize a week's timeline.

        Args:
            start_date: Start of week (Monday). If None, uses current week.
            output_language: Output language (ko/en/auto/None)
            force: Force regeneration ignoring cache

        Returns:
            Summary text

        Raises:
            FileNotFoundError: If no timeline files found for the week
        """
        # Get week start (Monday)
        if start_date is None:
            today = datetime.now().date()
            start_date = today - timedelta(days=today.weekday())

        # Get ISO week number for identifier
        year, week_num, _ = start_date.isocalendar()
        week_identifier = f"{year}-W{week_num:02d}"

        # Collect week's timeline files and content
        week_content = []
        week_files = []
        for i in range(7):
            date = start_date + timedelta(days=i)
            dt = datetime.combine(date, datetime.min.time())
            timeline_file = self.timeline.get_timeline_file(dt)

            if timeline_file.exists():
                content = timeline_file.read_text(encoding="utf-8")
                if content.strip():
                    week_content.append(f"## {date.isoformat()}\n\n{content}")
                    week_files.append(timeline_file)

        if not week_content:
            raise FileNotFoundError(
                f"No timeline entries found for week starting {start_date}"
            )

        # Check cache if not forced
        summary_file = self.get_summary_file("weekly", week_identifier)
        if not force and week_files:
            # Calculate combined hash of all week files
            combined_content = "".join([f.read_text(encoding="utf-8") for f in week_files])
            combined_hash = hashlib.sha256(combined_content.encode("utf-8")).hexdigest()

            if summary_file.exists():
                cached_hash = self.extract_hash_from_summary(summary_file)
                if cached_hash == combined_hash:
                    # Return cached summary
                    cached_content = summary_file.read_text(encoding="utf-8")
                    cached_summary = re.sub(r"<!-- metadata.*?-->\n\n", "", cached_content, flags=re.DOTALL)
                    return cached_summary

        # Combine week's timeline
        full_content = f"""# Timeline: Week of {start_date.isoformat()}

{chr(10).join(week_content)}
"""

        # Determine output language
        lang = self._get_output_language(output_language, full_content)

        # Gather context (full context for week)
        end_date = start_date + timedelta(days=6)
        context = self.context_gatherer.gather_for_timeline("week", start_date, end_date)

        # Build prompt with context
        system_prompt = self.prompt_builder.build_timeline_prompt(lang, context)

        # Generate summary
        summary = self.llm_client.summarize(
            content=full_content,
            system_prompt=system_prompt,
        )

        # Calculate combined hash and save with metadata
        combined_content = "".join([f.read_text(encoding="utf-8") for f in week_files])
        combined_hash = hashlib.sha256(combined_content.encode("utf-8")).hexdigest()

        # For metadata, list first file as representative
        source_file = week_files[0] if week_files else Path("(multiple)")
        self.save_summary_with_metadata(summary, summary_file, source_file, combined_hash, lang)

        return summary

    def summarize_range(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        output_language: Optional[str] = None,
        force: bool = False,
    ) -> str:
        """
        Summarize a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            output_language: Output language (ko/en/auto/None)
            force: Force regeneration ignoring cache

        Returns:
            Summary text

        Raises:
            FileNotFoundError: If no timeline files found in range
            ValueError: If date range is invalid
        """
        if end_date < start_date:
            raise ValueError(f"Invalid date range: {start_date} to {end_date}")

        # Range identifier
        range_identifier = f"{start_date.isoformat()}_to_{end_date.isoformat()}"

        # Collect range timeline files and content
        range_content = []
        range_files = []
        current_date = start_date

        while current_date <= end_date:
            dt = datetime.combine(current_date, datetime.min.time())
            timeline_file = self.timeline.get_timeline_file(dt)

            if timeline_file.exists():
                content = timeline_file.read_text(encoding="utf-8")
                if content.strip():
                    range_content.append(
                        f"## {current_date.isoformat()}\n\n{content}"
                    )
                    range_files.append(timeline_file)

            current_date += timedelta(days=1)

        if not range_content:
            raise FileNotFoundError(
                f"No timeline entries found between {start_date} and {end_date}"
            )

        # Check cache if not forced
        summary_file = self.get_summary_file("range", range_identifier)
        if not force and range_files:
            # Calculate combined hash of all range files
            combined_content = "".join([f.read_text(encoding="utf-8") for f in range_files])
            combined_hash = hashlib.sha256(combined_content.encode("utf-8")).hexdigest()

            if summary_file.exists():
                cached_hash = self.extract_hash_from_summary(summary_file)
                if cached_hash == combined_hash:
                    # Return cached summary
                    cached_content = summary_file.read_text(encoding="utf-8")
                    cached_summary = re.sub(r"<!-- metadata.*?-->\n\n", "", cached_content, flags=re.DOTALL)
                    return cached_summary

        # Combine range timeline
        full_content = f"""# Timeline: {start_date.isoformat()} to {end_date.isoformat()}

{chr(10).join(range_content)}
"""

        # Determine output language
        lang = self._get_output_language(output_language, full_content)

        # Gather context (full context for range)
        context = self.context_gatherer.gather_for_timeline("range", start_date, end_date)

        # Build prompt with context
        system_prompt = self.prompt_builder.build_timeline_prompt(lang, context)

        # Generate summary
        summary = self.llm_client.summarize(
            content=full_content,
            system_prompt=system_prompt,
        )

        # Calculate combined hash and save with metadata
        combined_content = "".join([f.read_text(encoding="utf-8") for f in range_files])
        combined_hash = hashlib.sha256(combined_content.encode("utf-8")).hexdigest()

        # For metadata, list first file as representative
        source_file = range_files[0] if range_files else Path("(multiple)")
        self.save_summary_with_metadata(summary, summary_file, source_file, combined_hash, lang)

        return summary
