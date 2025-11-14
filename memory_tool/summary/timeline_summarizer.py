"""Timeline summarization functionality."""

from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Literal
from ..llm.client import LLMClient
from ..llm.prompts import TIMELINE_SUMMARY_PROMPT
from ..core.timeline import Timeline


class TimelineSummarizer:
    """Summarize timeline entries using LLM."""

    def __init__(self, llm_client: Optional[LLMClient] = None):
        """
        Initialize timeline summarizer.

        Args:
            llm_client: LLM client (optional, creates one if not provided)
        """
        self.llm_client = llm_client or LLMClient()
        self.timeline = Timeline(Path.cwd() / ".memory" / "timeline")

    def summarize_today(self) -> str:
        """
        Summarize today's timeline.

        Returns:
            Summary text

        Raises:
            FileNotFoundError: If today's timeline doesn't exist
            ValueError: If timeline is empty
        """
        today = datetime.now().date()
        return self.summarize_date(today)

    def summarize_date(self, date: datetime.date) -> str:
        """
        Summarize a specific date's timeline.

        Args:
            date: Date to summarize

        Returns:
            Summary text

        Raises:
            FileNotFoundError: If timeline file doesn't exist
            ValueError: If timeline is empty
        """
        # Get timeline file path
        year_month = date.strftime("%Y-%m")
        day = date.strftime("%d")
        timeline_file = self.timeline.root / year_month / f"{day}.md"

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

        # Generate summary
        summary = self.llm_client.summarize(
            content=full_content,
            system_prompt=TIMELINE_SUMMARY_PROMPT,
        )

        return summary

    def summarize_week(
        self,
        start_date: Optional[datetime.date] = None,
    ) -> str:
        """
        Summarize a week's timeline.

        Args:
            start_date: Start of week (Monday). If None, uses current week.

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
            year_month = date.strftime("%Y-%m")
            day = date.strftime("%d")
            timeline_file = self.timeline.root / year_month / f"{day}.md"

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

        # Generate summary
        summary = self.llm_client.summarize(
            content=full_content,
            system_prompt=TIMELINE_SUMMARY_PROMPT,
        )

        return summary

    def summarize_range(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> str:
        """
        Summarize a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

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
            year_month = current_date.strftime("%Y-%m")
            day = current_date.strftime("%d")
            timeline_file = self.timeline.root / year_month / f"{day}.md"

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

        # Generate summary
        summary = self.llm_client.summarize(
            content=full_content,
            system_prompt=TIMELINE_SUMMARY_PROMPT,
        )

        return summary
