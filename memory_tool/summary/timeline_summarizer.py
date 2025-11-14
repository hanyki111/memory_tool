"""Timeline summarization functionality."""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Literal
from ..llm.client import LLMClient
from ..llm.prompts import detect_language
from ..llm.prompt_builder import PromptBuilder
from ..core.timeline import Timeline
from ..utils.config import Config
from .context import ContextGatherer


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
    ) -> str:
        """
        Summarize today's timeline.

        Args:
            output_language: Output language (ko/en/auto/None)

        Returns:
            Summary text

        Raises:
            FileNotFoundError: If today's timeline doesn't exist
            ValueError: If timeline is empty
        """
        today = datetime.now().date()
        return self.summarize_date(today, output_language=output_language)

    def summarize_date(
        self,
        date: datetime.date,
        output_language: Optional[str] = None,
    ) -> str:
        """
        Summarize a specific date's timeline.

        Args:
            date: Date to summarize
            output_language: Output language (ko/en/auto/None)

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

        return summary

    def summarize_week(
        self,
        start_date: Optional[datetime.date] = None,
        output_language: Optional[str] = None,
    ) -> str:
        """
        Summarize a week's timeline.

        Args:
            start_date: Start of week (Monday). If None, uses current week.
            output_language: Output language (ko/en/auto/None)

        Returns:
            Summary text

        Raises:
            FileNotFoundError: If no timeline files found for the week
        """
        # Get week start (Monday)
        if start_date is None:
            today = datetime.now().date()
            start_date = today - timedelta(days=today.weekday())

        # Collect week's timeline
        week_content = []
        for i in range(7):
            date = start_date + timedelta(days=i)
            dt = datetime.combine(date, datetime.min.time())
            timeline_file = self.timeline.get_timeline_file(dt)

            if timeline_file.exists():
                content = timeline_file.read_text(encoding="utf-8")
                if content.strip():
                    week_content.append(f"## {date.isoformat()}\n\n{content}")

        if not week_content:
            raise FileNotFoundError(
                f"No timeline entries found for week starting {start_date}"
            )

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

        return summary

    def summarize_range(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        output_language: Optional[str] = None,
    ) -> str:
        """
        Summarize a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            output_language: Output language (ko/en/auto/None)

        Returns:
            Summary text

        Raises:
            FileNotFoundError: If no timeline files found in range
            ValueError: If date range is invalid
        """
        if end_date < start_date:
            raise ValueError(f"Invalid date range: {start_date} to {end_date}")

        # Collect range timeline
        range_content = []
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

            current_date += timedelta(days=1)

        if not range_content:
            raise FileNotFoundError(
                f"No timeline entries found between {start_date} and {end_date}"
            )

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

        return summary
