"""Agentic RAG system for memory-based Q&A.

Uses LLM as an agent that can:
1. Interpret user questions
2. Select and execute appropriate memory tools
3. Synthesize results into coherent answers
"""

import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta


@dataclass
class ToolCall:
    """Represents a tool call requested by the LLM."""
    tool: str
    args: Dict[str, Any]


@dataclass
class ToolResult:
    """Result of executing a tool."""
    tool: str
    args: Dict[str, Any]
    success: bool
    result: str
    error: Optional[str] = None


@dataclass
class AgentResult:
    """Result of an agent query."""
    question: str
    answer: str
    tool_calls: List[ToolCall]
    tool_results: List[ToolResult]
    provider: str
    timestamp: datetime


class MemoryAgent:
    """Agentic RAG system for memory-based Q&A.

    Instead of simple keyword search, this agent:
    1. Uses LLM to interpret the question
    2. LLM decides which tools to call
    3. Executes the tools and collects results
    4. LLM synthesizes final answer from results
    """

    # Available tools with descriptions
    TOOLS = {
        "get_timeline": {
            "description": "Get timeline entries for a specific date",
            "args": {
                "date": "Date string: 'today', 'yesterday', or 'YYYY-MM-DD'"
            },
            "examples": ["get_timeline(date='yesterday')", "get_timeline(date='2026-01-20')"]
        },
        "get_timeline_range": {
            "description": "Get timeline entries for a date range (recent N days)",
            "args": {
                "days": "Number of days to look back (default: 7)"
            },
            "examples": ["get_timeline_range(days=7)", "get_timeline_range(days=30)"]
        },
        "search": {
            "description": "Search memory (timeline, modules, plans) for keywords or semantically similar content",
            "args": {
                "query": "Search query string (extract key terms only)",
                "mode": "Search mode: 'keyword' (fast), 'semantic' (meaning-based), 'hybrid' (both, default)"
            },
            "examples": ["search(query='트럼프', mode='hybrid')", "search(query='CLI refactoring')", "search(query='bug fix', mode='keyword')"]
        },
        "get_plan_daily": {
            "description": "Get daily plan for a specific date",
            "args": {
                "date": "Date string: 'today', 'yesterday', or 'YYYY-MM-DD'"
            },
            "examples": ["get_plan_daily(date='today')", "get_plan_daily(date='yesterday')"]
        },
        "get_plan_weekly": {
            "description": "Get weekly plan",
            "args": {
                "week": "Week identifier: 'this', 'last', or 'W03' format"
            },
            "examples": ["get_plan_weekly(week='this')", "get_plan_weekly(week='last')"]
        },
        "get_module": {
            "description": "Get a module's current status (current.md content)",
            "args": {
                "name": "Module name (e.g., 'projects/memory-tool')"
            },
            "examples": ["get_module(name='projects/memory-tool')", "get_module(name='projects/memory-tool/core-system')"]
        },
        "list_modules": {
            "description": "List all available modules",
            "args": {},
            "examples": ["list_modules()"]
        },
        "get_help": {
            "description": "Get usage information about memory_tool commands",
            "args": {
                "command": "Command name (e.g., 'record', 'search', 'plan') or 'all' for overview"
            },
            "examples": ["get_help(command='search')", "get_help(command='all')", "get_help(command='plan')"]
        },
    }

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize Memory Agent.

        Args:
            base_path: Base path for project. Defaults to current directory.
        """
        if base_path is None:
            base_path = Path.cwd()
        self.base_path = Path(base_path)
        self.memory_path = self.base_path / ".memory"

        # Load config
        from memory_tool.utils.config import Config
        self.config = Config()

    def _get_tools_description(self) -> str:
        """Generate tools description for LLM prompt."""
        lines = ["Available tools:\n"]

        for tool_name, tool_info in self.TOOLS.items():
            lines.append(f"- {tool_name}: {tool_info['description']}")
            if tool_info['args']:
                args_str = ", ".join(f"{k}={v}" for k, v in tool_info['args'].items())
                lines.append(f"  Args: {args_str}")
            lines.append(f"  Examples: {', '.join(tool_info['examples'])}")
            lines.append("")

        return "\n".join(lines)

    def _build_tool_selection_prompt(self, question: str) -> str:
        """Build prompt for LLM to select tools."""
        today = date.today().isoformat()

        return f"""You are a Memory Tool agent. Select tools to answer the user's question.

Today: {today}

{self._get_tools_description()}

Question: {question}

IMPORTANT: You MUST output ONLY a JSON block. No explanations before or after.

```json
{{
  "reasoning": "why these tools",
  "tool_calls": [
    {{"tool": "tool_name", "args": {{"key": "value"}}}}
  ]
}}
```

Tool Selection Rules:
- "어제/yesterday" → get_timeline(date="yesterday")
- "오늘/today" → get_timeline(date="today")
- "지난주/last week" → get_plan_weekly(week="last") or get_timeline_range(days=7)
- "최근/recently" → get_timeline_range(days=7)
- "모듈/module + 이름" → get_module(name="...")
- "찾아/검색/search + 키워드" → search(query="키워드만", mode="hybrid")
- "모든 모듈/list modules" → list_modules()
- "사용법/help/어떻게 사용/how to use" → get_help(command="...")
- "명령어 목록/command list" → get_help(command="all")

CRITICAL: For search tool:
1. Extract ONLY the search keyword, not the full question
2. Use mode="hybrid" (default) for best results (combines keyword + semantic)
3. Use mode="keyword" for exact matches only
4. Use mode="semantic" for meaning-based search

Example: "트럼프 관련 내용 찾아줘" → search(query="트럼프", mode="hybrid")

Output ONLY the JSON:"""

    def _build_answer_prompt(
        self,
        question: str,
        tool_results: List[ToolResult]
    ) -> str:
        """Build prompt for LLM to synthesize final answer."""
        # Format tool results
        results_text = []
        for tr in tool_results:
            if tr.success:
                results_text.append(f"[{tr.tool}({tr.args})]\n{tr.result}")
            else:
                results_text.append(f"[{tr.tool}({tr.args})] Error: {tr.error}")

        results_section = "\n\n---\n\n".join(results_text)

        return f"""Based on the following information from the memory system, answer the user's question.

Question: {question}

Information gathered:

{results_section}

---

Rules:
1. Answer based ONLY on the information provided above
2. If the information doesn't contain the answer, say so
3. Be concise and direct
4. Mention specific dates, files, or sources when relevant
5. Use the same language as the question (Korean or English)"""

    def _parse_tool_calls(self, llm_response: str) -> List[ToolCall]:
        """Parse LLM response to extract tool calls."""
        tool_calls = []

        # Try multiple patterns to extract JSON
        json_str = None

        # Pattern 1: ```json ... ```
        json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)

        # Pattern 2: ``` ... ``` (without json marker)
        if not json_str:
            json_match = re.search(r'```\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)

        # Pattern 3: Raw JSON with tool_calls
        if not json_str:
            json_match = re.search(r'(\{[^{}]*"tool_calls"[^{}]*\[[^\]]*\][^{}]*\})', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)

        # Pattern 4: Any JSON object
        if not json_str:
            json_match = re.search(r'(\{.*\})', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)

        if not json_str:
            return tool_calls

        # Clean up common issues
        json_str = json_str.strip()
        # Fix trailing commas (common LLM mistake)
        json_str = re.sub(r',\s*([}\]])', r'\1', json_str)

        try:
            data = json.loads(json_str)
            for tc in data.get("tool_calls", []):
                tool_name = tc.get("tool", "")
                tool_args = tc.get("args", {})
                if tool_name:  # Only add if tool name exists
                    tool_calls.append(ToolCall(tool=tool_name, args=tool_args))
        except json.JSONDecodeError as e:
            # Try to salvage partial matches
            pass

        return tool_calls

    def _extract_search_keywords(self, question: str) -> str:
        """Extract meaningful keywords from question for search fallback."""
        # Common words to remove (Korean and English)
        stop_words = {
            # Korean
            "무엇", "뭐", "언제", "어디", "누가", "왜", "어떻게", "어떤",
            "해줘", "해주세요", "알려줘", "알려주세요", "찾아줘", "찾아주세요",
            "정리해줘", "정리해주세요", "요약해줘", "요약해주세요",
            "관련", "관계", "관한", "대한", "대해", "내용", "정보",
            "은", "는", "이", "가", "을", "를", "의", "에", "에서",
            "으로", "로", "와", "과", "하고", "그리고", "또는", "된",
            "있는", "없는", "하는", "한", "할", "했", "있", "없",
            "모듈", "파일", "문서",
            # English
            "what", "when", "where", "who", "why", "how", "which",
            "please", "find", "search", "show", "tell", "me", "about",
            "related", "content", "information", "the", "a", "an",
            "is", "are", "was", "were", "do", "does", "did", "can",
        }

        # Split and filter
        words = re.split(r'[\s,?.!;:]+', question.lower())
        keywords = [w.strip() for w in words if w.strip() and w.strip() not in stop_words and len(w.strip()) > 1]

        # Return first few meaningful keywords
        return " ".join(keywords[:3]) if keywords else question[:20]

    def _parse_date(self, date_str: str) -> date:
        """Parse date string to date object."""
        date_str = date_str.lower().strip()
        today = date.today()

        if date_str in ("today", "오늘"):
            return today
        elif date_str in ("yesterday", "어제"):
            return today - timedelta(days=1)
        else:
            # Try to parse YYYY-MM-DD
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                return today

    def _parse_week(self, week_str: str) -> date:
        """Parse week string to a date in that week."""
        week_str = week_str.lower().strip()
        today = date.today()

        if week_str in ("this", "이번주"):
            return today
        elif week_str in ("last", "lastweek", "지난주"):
            return today - timedelta(days=7)
        elif week_str.startswith("w"):
            # Parse W03 format
            try:
                week_num = int(week_str[1:])
                # Get first day of that week in current year
                jan1 = date(today.year, 1, 1)
                return jan1 + timedelta(weeks=week_num - 1)
            except ValueError:
                return today
        return today

    # ========================================
    # Tool Implementation Methods
    # ========================================

    def _tool_get_timeline(self, date_str: str = "today") -> str:
        """Get timeline for a specific date."""
        target_date = self._parse_date(date_str)

        # Build timeline file path
        timeline_path = (
            self.memory_path / "timeline" / "daily" /
            target_date.strftime("%Y-%m") /
            f"{target_date.day:02d}.md"
        )

        if not timeline_path.exists():
            return f"No timeline found for {target_date.isoformat()}"

        content = timeline_path.read_text(encoding="utf-8")
        return f"Timeline for {target_date.isoformat()}:\n\n{content}"

    def _tool_get_timeline_range(self, days: int = 7) -> str:
        """Get timeline for recent N days."""
        results = []
        today = date.today()

        for i in range(days):
            target_date = today - timedelta(days=i)
            timeline_path = (
                self.memory_path / "timeline" / "daily" /
                target_date.strftime("%Y-%m") /
                f"{target_date.day:02d}.md"
            )

            if timeline_path.exists():
                content = timeline_path.read_text(encoding="utf-8")
                # Skip header line if present
                lines = content.strip().split("\n")
                entries = [l for l in lines if l.startswith("- ")]
                if entries:
                    results.append(f"### {target_date.isoformat()}\n" + "\n".join(entries))

        if not results:
            return f"No timeline entries found in the last {days} days"

        return "\n\n".join(results)

    def _tool_search(self, query: str, mode: str = "hybrid") -> str:
        """Search memory for keywords or semantically similar content.

        Args:
            query: Search query string
            mode: 'keyword', 'semantic', or 'hybrid' (default)
        """
        from memory_tool.core.search import MemorySearcher, SearchResult
        from pathlib import Path

        searcher = MemorySearcher(self.base_path)
        output = []

        # Try hybrid search first (if mode is hybrid or semantic)
        if mode in ("hybrid", "semantic"):
            try:
                from memory_tool.core.vector_search import VectorSearcher, VECTOR_SEARCH_AVAILABLE

                if VECTOR_SEARCH_AVAILABLE:
                    vector_searcher = VectorSearcher(self.base_path)
                    semantic_results = vector_searcher.semantic_search(
                        query,
                        top_k=10,
                        threshold=0.3
                    )

                    if semantic_results:
                        for r in semantic_results[:7]:
                            rel_path = Path(r['file']).relative_to(self.base_path) if self.base_path in Path(r['file']).parents else r['file']
                            score = r.get('similarity', 0)
                            output.append(f"[{rel_path}:{r['line']}] (score: {score:.2f})\n{r['content'].strip()}")

                        if mode == "semantic":
                            if output:
                                return f"Semantic search results for '{query}':\n\n" + "\n\n---\n\n".join(output)
                            return f"No semantic results found for '{query}'"
            except Exception as e:
                # Fall back to keyword search if vector search fails
                if mode == "semantic":
                    return f"Semantic search not available: {e}. Try mode='keyword'."

        # Keyword search (for keyword mode or hybrid mode)
        if mode in ("keyword", "hybrid"):
            try:
                results = searcher.search(
                    query=query,
                    scope="local",
                    context_lines=2,
                    max_results=10,
                )

                keyword_output = []
                for source, source_results in results.items():
                    for r in source_results[:5]:
                        try:
                            rel_path = r.file_path.relative_to(self.base_path)
                        except ValueError:
                            rel_path = r.file_path
                        keyword_output.append(f"[{rel_path}:{r.line_number}]\n{r.match_context.strip()}")

                # For hybrid, combine results (avoiding duplicates)
                if mode == "hybrid":
                    seen_content = set()
                    combined = []

                    # Add semantic results first (usually more relevant)
                    for item in output:
                        content_key = item[:100]
                        if content_key not in seen_content:
                            seen_content.add(content_key)
                            combined.append(item)

                    # Add keyword results
                    for item in keyword_output:
                        content_key = item[:100]
                        if content_key not in seen_content:
                            seen_content.add(content_key)
                            combined.append(item)

                    output = combined[:12]
                else:
                    output = keyword_output

            except Exception as e:
                if not output:  # No semantic results either
                    return f"Search failed: {e}"

        if not output:
            return f"No results found for '{query}'"

        mode_label = {"keyword": "Keyword", "semantic": "Semantic", "hybrid": "Hybrid"}
        return f"{mode_label.get(mode, 'Search')} results for '{query}':\n\n" + "\n\n---\n\n".join(output[:10])

    def _tool_get_plan_daily(self, date_str: str = "today") -> str:
        """Get daily plan for a specific date."""
        target_date = self._parse_date(date_str)

        plan_path = (
            self.memory_path / "plans" / "daily" /
            target_date.strftime("%Y-%m") /
            f"{target_date.day:02d}.md"
        )

        if not plan_path.exists():
            return f"No daily plan found for {target_date.isoformat()}"

        content = plan_path.read_text(encoding="utf-8")
        return f"Daily plan for {target_date.isoformat()}:\n\n{content}"

    def _tool_get_plan_weekly(self, week: str = "this") -> str:
        """Get weekly plan."""
        target_date = self._parse_week(week)

        # Get ISO week number
        year, week_num, _ = target_date.isocalendar()

        plan_path = (
            self.memory_path / "plans" / "weekly" /
            str(year) / f"W{week_num:02d}.md"
        )

        if not plan_path.exists():
            return f"No weekly plan found for {year}-W{week_num:02d}"

        content = plan_path.read_text(encoding="utf-8")
        return f"Weekly plan for {year}-W{week_num:02d}:\n\n{content}"

    def _tool_get_module(self, name: str) -> str:
        """Get module's current.md content."""
        module_path = self.memory_path / "modules" / name / "current.md"

        if not module_path.exists():
            # Try without leading path
            module_path = self.memory_path / "modules" / name.lstrip("/") / "current.md"

        if not module_path.exists():
            return f"Module not found: {name}"

        content = module_path.read_text(encoding="utf-8")

        # Truncate if too long
        if len(content) > 3000:
            content = content[:3000] + "\n\n[... truncated ...]"

        return f"Module '{name}' current status:\n\n{content}"

    def _tool_list_modules(self) -> str:
        """List all available modules."""
        modules_path = self.memory_path / "modules"

        if not modules_path.exists():
            return "No modules directory found"

        modules = []
        for current_md in modules_path.rglob("current.md"):
            rel_path = current_md.parent.relative_to(modules_path)
            modules.append(str(rel_path))

        if not modules:
            return "No modules found"

        return "Available modules:\n" + "\n".join(f"- {m}" for m in sorted(modules))

    def _tool_get_help(self, command: str = "all") -> str:
        """Get usage information about memory_tool commands.

        Args:
            command: Command name or 'all' for overview
        """
        from memory_tool.commands.help import HELP_CONTENT, COMMAND_CATEGORIES

        # Get language from config
        try:
            lang = self.config.get("help.language", "en")
        except Exception:
            lang = "en"

        if command.lower() == "all":
            # Return overview of all commands
            categories = COMMAND_CATEGORIES.get(lang, COMMAND_CATEGORIES["en"])
            lines = ["Memory Tool Commands Overview:\n"]

            for cat_key, (cat_name, commands) in categories.items():
                lines.append(f"\n## {cat_name}")
                for cmd in commands:
                    if cmd in HELP_CONTENT:
                        help_data = HELP_CONTENT[cmd].get(lang, HELP_CONTENT[cmd]["en"])
                        lines.append(f"- {help_data['name']}: {help_data['summary']}")

            lines.append("\n\nFor detailed help on a specific command, ask about that command.")
            return "\n".join(lines)

        # Normalize command name
        cmd_map = {
            "m": "record", "기": "record",
            "ms": "search", "검": "search",
            "mask": "ask", "질문": "ask",
            "mtoday": "today", "오늘": "today",
            "mplan": "plan",
            "mweek": "week", "mmonth": "month",
            "mdays": "days", "msort": "sort",
            "mmodule": "module", "marchive": "archive",
            "mcontext": "context", "mmap": "map",
            "msummary": "summary", "mproviders": "providers",
            "minit": "init", "mstatus": "status",
            "mtutorial": "tutorial", "mhelp": "help",
            "malias": "alias", "mconfig": "config",
            "mhooks": "hooks", "mcompletion": "completion",
            "mbrowse": "browse", "mcheck": "check",
        }
        cmd = cmd_map.get(command.lower(), command.lower())

        if cmd not in HELP_CONTENT:
            return f"No detailed help found for '{command}'. Use get_help(command='all') for command overview."

        help_data = HELP_CONTENT[cmd].get(lang, HELP_CONTENT[cmd]["en"])

        # Format help content
        lines = [
            f"# {help_data['name']}",
            f"{help_data['summary']}\n",
            "## Description",
            help_data['description'].strip(),
            "\n## Examples",
        ]
        for example in help_data.get('examples', []):
            lines.append(f"  {example}")

        if help_data.get('options'):
            lines.append("\n## Options")
            for opt_name, opt_desc in help_data['options']:
                lines.append(f"  {opt_name}: {opt_desc}")

        return "\n".join(lines)

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call."""
        tool_name = tool_call.tool
        args = tool_call.args

        try:
            if tool_name == "get_timeline":
                result = self._tool_get_timeline(args.get("date", "today"))
            elif tool_name == "get_timeline_range":
                result = self._tool_get_timeline_range(args.get("days", 7))
            elif tool_name == "search":
                result = self._tool_search(
                    args.get("query", ""),
                    mode=args.get("mode", "hybrid")
                )
            elif tool_name == "get_plan_daily":
                result = self._tool_get_plan_daily(args.get("date", "today"))
            elif tool_name == "get_plan_weekly":
                result = self._tool_get_plan_weekly(args.get("week", "this"))
            elif tool_name == "get_module":
                result = self._tool_get_module(args.get("name", ""))
            elif tool_name == "list_modules":
                result = self._tool_list_modules()
            elif tool_name == "get_help":
                result = self._tool_get_help(args.get("command", "all"))
            else:
                return ToolResult(
                    tool=tool_name,
                    args=args,
                    success=False,
                    result="",
                    error=f"Unknown tool: {tool_name}"
                )

            return ToolResult(
                tool=tool_name,
                args=args,
                success=True,
                result=result
            )

        except Exception as e:
            return ToolResult(
                tool=tool_name,
                args=args,
                success=False,
                result="",
                error=str(e)
            )

    def ask(
        self,
        question: str,
        provider: Optional[str] = None,
        verbose: bool = False,
    ) -> AgentResult:
        """Ask a question using the agentic approach.

        Args:
            question: Natural language question
            provider: LLM provider override
            verbose: If True, print intermediate steps

        Returns:
            AgentResult with answer and tool call details
        """
        from memory_tool.llm.client import LLMClient

        # Check LLM availability
        if not LLMClient.check_availability(provider):
            available = LLMClient.list_available_providers()
            if available:
                raise RuntimeError(
                    f"LLM provider not available. Available: {', '.join(available)}"
                )
            else:
                raise RuntimeError("No LLM providers available.")

        llm = LLMClient(provider=provider)
        actual_provider = provider or LLMClient.get_provider()

        # Step 1: LLM interprets question and selects tools
        if verbose:
            print("[Step 1] Analyzing question and selecting tools...")

        tool_selection_prompt = self._build_tool_selection_prompt(question)
        tool_selection_response = llm.generate(
            prompt=tool_selection_prompt,
            system_prompt="You are a helpful assistant that selects appropriate tools. Output only valid JSON.",
        )

        if verbose:
            print(f"  LLM response: {tool_selection_response[:200]}...")

        # Parse tool calls
        tool_calls = self._parse_tool_calls(tool_selection_response)

        if verbose:
            print(f"  Selected tools: {[tc.tool for tc in tool_calls]}")

        # Step 2: Execute tools
        if verbose:
            print("[Step 2] Executing tools...")

        tool_results = []
        for tc in tool_calls:
            if verbose:
                print(f"  Executing {tc.tool}({tc.args})...")
            result = self._execute_tool(tc)
            tool_results.append(result)
            if verbose:
                status = "OK" if result.success else f"Error: {result.error}"
                print(f"    -> {status}")

        # If no tools were called, fall back to search with extracted keywords
        if not tool_results:
            if verbose:
                print("  No tools selected, falling back to keyword search...")
            # Extract keywords from question (remove common words)
            keywords = self._extract_search_keywords(question)
            if verbose:
                print(f"  Extracted keywords: {keywords}")
            fallback_tc = ToolCall(tool="search", args={"query": keywords})
            tool_results.append(self._execute_tool(fallback_tc))

        # Step 3: LLM synthesizes answer
        if verbose:
            print("[Step 3] Synthesizing answer...")

        answer_prompt = self._build_answer_prompt(question, tool_results)
        answer = llm.generate(
            prompt=answer_prompt,
            system_prompt="You are a helpful assistant. Answer questions based on the provided information.",
        )

        return AgentResult(
            question=question,
            answer=answer,
            tool_calls=tool_calls,
            tool_results=tool_results,
            provider=actual_provider,
            timestamp=datetime.now(),
        )
