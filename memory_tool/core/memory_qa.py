"""Memory-based Q&A with RAG (Retrieval Augmented Generation).

Allows natural language questions about the memory content.
Uses search to find relevant context, then LLM to generate answers.
"""

import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from memory_tool.utils.paths import base_dir_for_root, get_project_root


@dataclass
class QAContext:
    """Context gathered for answering a question."""
    source: str  # File path or source identifier
    content: str  # Relevant content
    relevance: float  # Relevance score (0-1)
    date: Optional[datetime] = None  # For timeline entries


@dataclass
class QAResult:
    """Result of a Q&A query."""
    question: str
    answer: str
    contexts: List[QAContext]
    provider: str  # LLM provider used
    timestamp: datetime


class MemoryQA:
    """Memory-based Q&A system using RAG."""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize Memory Q&A.

        Args:
            base_path: Base path for project. Defaults to current directory.
        """
        if base_path is None:
            base_path = get_project_root()
        self.base_path = Path(base_path)
        self.memory_path = base_dir_for_root(self.base_path)

        # Load config
        from memory_tool.utils.config import Config
        self.config = Config()

        # Initialize searcher
        from memory_tool.core.search import MemorySearcher
        self.searcher = MemorySearcher(base_path)

        # Get QA settings
        self.max_context_tokens = self.config.get("llm.max_context_tokens", 2000)
        self.output_language = self.config.get("llm.output_language", "auto")

    def _extract_keywords(self, question: str) -> List[str]:
        """Extract search keywords from natural language question.

        Args:
            question: Natural language question

        Returns:
            List of keywords for searching
        """
        # Remove common question words
        stop_words = {
            # English
            "what", "when", "where", "who", "why", "how", "which",
            "is", "are", "was", "were", "do", "does", "did",
            "can", "could", "will", "would", "should",
            "the", "a", "an", "of", "in", "on", "at", "to", "for",
            "and", "or", "but", "not", "with", "about", "from",
            "this", "that", "these", "those", "it", "its",
            "i", "you", "we", "they", "he", "she", "my", "your",
            # Korean
            "무엇", "언제", "어디", "누가", "왜", "어떻게", "어떤",
            "입니까", "있습니까", "했습니까", "인가요", "일까요",
            "은", "는", "이", "가", "을", "를", "의", "에", "에서",
            "으로", "로", "와", "과", "하고", "그리고", "또는",
            "이것", "저것", "그것", "이런", "저런", "그런",
            "나", "저", "우리", "너", "당신", "그", "그녀",
        }

        # Tokenize
        # For Korean, simple space split; for English, also split on punctuation
        words = re.split(r'[\s,?.!;:]+', question.lower())

        # Filter
        keywords = []
        for word in words:
            word = word.strip()
            if word and word not in stop_words and len(word) > 1:
                keywords.append(word)

        return keywords

    def _search_timeline(
        self,
        keywords: List[str],
        days: int = 30,
        max_results: int = 10,
    ) -> List[QAContext]:
        """Search timeline for relevant entries.

        Args:
            keywords: Keywords to search
            days: Number of days to search back
            max_results: Maximum results per keyword

        Returns:
            List of relevant contexts
        """
        contexts = []
        seen_content = set()

        # Calculate date range
        from datetime import date
        end_date = date.today()
        start_date = end_date - timedelta(days=days)

        for keyword in keywords:
            try:
                results = self.searcher.search(
                    query=keyword,
                    scope="local",
                    context_lines=2,
                    max_results=max_results,
                    from_date=start_date,
                    to_date=end_date,
                )

                for source, source_results in results.items():
                    for result in source_results:
                        # Deduplicate by content
                        content_key = result.line_content.strip()[:50]
                        if content_key in seen_content:
                            continue
                        seen_content.add(content_key)

                        # Extract date from path if available
                        entry_date = None
                        try:
                            rel_path = str(result.file_path)
                            if "timeline" in rel_path:
                                # Parse from path like .../2026-01/21.md
                                match = re.search(r'(\d{4}-\d{2})[/\\](\d{1,2})\.md', rel_path)
                                if match:
                                    year_month = match.group(1)
                                    day = match.group(2).zfill(2)
                                    entry_date = datetime.strptime(f"{year_month}-{day}", "%Y-%m-%d")
                        except Exception:
                            pass

                        contexts.append(QAContext(
                            source=str(result.file_path.relative_to(self.base_path)),
                            content=result.match_context,
                            relevance=0.8,  # Default relevance for keyword match
                            date=entry_date,
                        ))
            except Exception:
                continue

        # Sort by date (most recent first)
        contexts.sort(key=lambda x: x.date or datetime.min, reverse=True)

        return contexts[:max_results * 2]  # Allow some extra after dedup

    def _search_modules(
        self,
        keywords: List[str],
        max_results: int = 10,
    ) -> List[QAContext]:
        """Search modules for relevant content.

        Args:
            keywords: Keywords to search
            max_results: Maximum results per keyword

        Returns:
            List of relevant contexts
        """
        contexts = []
        seen_content = set()

        for keyword in keywords:
            try:
                results = self.searcher.search(
                    query=keyword,
                    scope="local",
                    context_lines=3,
                    max_results=max_results,
                )

                for source, source_results in results.items():
                    for result in source_results:
                        # Only include module files
                        rel_path = str(result.file_path)
                        if "modules" not in rel_path:
                            continue

                        # Deduplicate
                        content_key = result.line_content.strip()[:50]
                        if content_key in seen_content:
                            continue
                        seen_content.add(content_key)

                        contexts.append(QAContext(
                            source=str(result.file_path.relative_to(self.base_path)),
                            content=result.match_context,
                            relevance=0.7,
                        ))
            except Exception:
                continue

        return contexts[:max_results]

    def _search_plans(
        self,
        keywords: List[str],
        max_results: int = 5,
    ) -> List[QAContext]:
        """Search plans for relevant content.

        Args:
            keywords: Keywords to search
            max_results: Maximum results

        Returns:
            List of relevant contexts
        """
        contexts = []
        seen_content = set()

        for keyword in keywords:
            try:
                results = self.searcher.search(
                    query=keyword,
                    scope="local",
                    context_lines=2,
                    max_results=max_results,
                )

                for source, source_results in results.items():
                    for result in source_results:
                        rel_path = str(result.file_path)
                        if "plans" not in rel_path:
                            continue

                        content_key = result.line_content.strip()[:50]
                        if content_key in seen_content:
                            continue
                        seen_content.add(content_key)

                        contexts.append(QAContext(
                            source=str(result.file_path.relative_to(self.base_path)),
                            content=result.match_context,
                            relevance=0.75,
                        ))
            except Exception:
                continue

        return contexts[:max_results]

    def _build_context_prompt(self, contexts: List[QAContext]) -> str:
        """Build context section for LLM prompt.

        Args:
            contexts: List of relevant contexts

        Returns:
            Formatted context string
        """
        if not contexts:
            return "No relevant context found in memory."

        lines = ["Here is relevant information from the memory system:\n"]

        for i, ctx in enumerate(contexts, 1):
            lines.append(f"--- Context {i} ({ctx.source}) ---")
            if ctx.date:
                lines.append(f"Date: {ctx.date.strftime('%Y-%m-%d')}")
            lines.append(ctx.content.strip())
            lines.append("")

        return "\n".join(lines)

    def _truncate_context(self, context: str, max_chars: int = 8000) -> str:
        """Truncate context to fit within token limits.

        Args:
            context: Full context string
            max_chars: Maximum characters (rough estimate: 4 chars per token)

        Returns:
            Truncated context
        """
        if len(context) <= max_chars:
            return context

        # Truncate with indicator
        return context[:max_chars] + "\n\n[Context truncated due to length...]"

    def ask(
        self,
        question: str,
        search_timeline: bool = True,
        search_modules: bool = True,
        search_plans: bool = True,
        timeline_days: int = 30,
        max_context_items: int = 15,
        provider: Optional[str] = None,
    ) -> QAResult:
        """Ask a question about the memory content.

        Args:
            question: Natural language question
            search_timeline: Whether to search timeline
            search_modules: Whether to search modules
            search_plans: Whether to search plans
            timeline_days: Days of timeline to search
            max_context_items: Maximum context items to include
            provider: LLM provider override (optional)

        Returns:
            QAResult with answer and contexts

        Raises:
            RuntimeError: If LLM is not available
        """
        from memory_tool.llm.client import LLMClient

        # Check LLM availability
        if not LLMClient.check_availability(provider):
            available = LLMClient.list_available_providers()
            if available:
                raise RuntimeError(
                    f"LLM provider not available. Available providers: {', '.join(available)}"
                )
            else:
                raise RuntimeError(
                    "No LLM providers available. Configure one in config.yaml or install CLI tools."
                )

        # Extract keywords
        keywords = self._extract_keywords(question)

        if not keywords:
            # If no keywords extracted, use the whole question
            keywords = [question]

        # Gather context from different sources
        all_contexts = []

        if search_timeline:
            timeline_contexts = self._search_timeline(
                keywords, days=timeline_days, max_results=max_context_items // 2
            )
            all_contexts.extend(timeline_contexts)

        if search_modules:
            module_contexts = self._search_modules(
                keywords, max_results=max_context_items // 3
            )
            all_contexts.extend(module_contexts)

        if search_plans:
            plan_contexts = self._search_plans(
                keywords, max_results=max_context_items // 4
            )
            all_contexts.extend(plan_contexts)

        # Sort by relevance and limit
        all_contexts.sort(key=lambda x: x.relevance, reverse=True)
        all_contexts = all_contexts[:max_context_items]

        # Build context prompt
        context_text = self._build_context_prompt(all_contexts)
        context_text = self._truncate_context(context_text)

        # Build system prompt
        if self.output_language == "ko":
            system_prompt = """당신은 Memory Tool의 지식 기반 어시스턴트입니다.
사용자의 질문에 대해 제공된 컨텍스트를 기반으로 정확하고 유용한 답변을 제공하세요.

규칙:
1. 제공된 컨텍스트 정보만을 기반으로 답변하세요.
2. 컨텍스트에 답이 없으면 "관련 정보를 찾을 수 없습니다"라고 말하세요.
3. 답변은 간결하고 명확하게 작성하세요.
4. 가능하면 출처(파일 경로, 날짜)를 언급하세요.
5. 추측하지 말고, 확실한 정보만 제공하세요."""
        else:
            system_prompt = """You are a Memory Tool knowledge assistant.
Answer the user's question based on the provided context.

Rules:
1. Base your answer only on the provided context.
2. If the answer is not in the context, say "I couldn't find relevant information."
3. Keep answers concise and clear.
4. Mention sources (file paths, dates) when possible.
5. Don't speculate; only provide information you're certain about."""

        # Build user prompt
        user_prompt = f"""{context_text}

---

Question: {question}

Please provide a helpful answer based on the context above."""

        # Call LLM
        llm = LLMClient(provider=provider)
        actual_provider = provider or LLMClient.get_provider()

        answer = llm.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
        )

        return QAResult(
            question=question,
            answer=answer,
            contexts=all_contexts,
            provider=actual_provider,
            timestamp=datetime.now(),
        )

    def ask_simple(self, question: str, provider: Optional[str] = None) -> str:
        """Simple interface - ask and get just the answer.

        Args:
            question: Natural language question
            provider: LLM provider override (optional)

        Returns:
            Answer string
        """
        result = self.ask(question, provider=provider)
        return result.answer
