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
from memory_tool.utils.paths import base_dir_for_root, get_project_root


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
        "get_config_guide": {
            "description": "Get configuration guide for config.yaml settings",
            "args": {
                "section": "Config section: 'all', 'notion', 'timeline', 'search', 'llm', 'help', or specific key path"
            },
            "examples": ["get_config_guide(section='notion')", "get_config_guide(section='all')", "get_config_guide(section='notion.sync.timeline')"]
        },
        "get_usage_guide": {
            "description": "Get comprehensive usage guide for Memory Tool features (tags, wiki links, search modes, etc.)",
            "args": {
                "topic": "Topic to get guide for: 'all', 'tags', 'search', 'timeline', 'modules', 'plans', 'ai', 'notion', 'config'"
            },
            "examples": ["get_usage_guide(topic='tags')", "get_usage_guide(topic='all')", "get_usage_guide(topic='search')"]
        },
    }

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize Memory Agent.

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
- "설정/config/config.yaml/어떻게 설정" → get_config_guide(section="...")
- "notion 설정/notion sync 설정" → get_config_guide(section="notion.sync")

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

    def _tool_get_config_guide(self, section: str = "all") -> str:
        """Get configuration guide for config.yaml settings.

        Args:
            section: Config section name or 'all' for complete guide
        """
        # Configuration documentation
        CONFIG_GUIDE = {
            "overview": """# config.yaml 설정 가이드

config.yaml 파일은 .memory/ 디렉토리에 위치하며, Memory Tool의 모든 설정을 관리합니다.

## 주요 섹션
- timeline: 타임라인 기록 설정
- context: Claude Code 컨텍스트 설정
- search: 검색 설정
- llm: AI/LLM 제공자 설정
- help: 도움말 언어 설정
- notion: Notion 동기화 설정

각 섹션에 대한 상세 정보는 해당 섹션을 질문하세요.""",

            "timeline": """# timeline 설정

```yaml
timeline:
  auto_record: false      # 자동 기록 활성화 여부
  granularity: medium     # 기록 상세도: low, medium, high
  warn_old_days: 365      # N일 이전 기록 시 경고
```

## 옵션 설명
- **auto_record**: true 시 특정 이벤트에 자동 기록
- **granularity**: 기록 상세 수준
  - low: 간단한 기록만
  - medium: 기본 (권장)
  - high: 상세 기록
- **warn_old_days**: 오래된 날짜에 기록 시 경고 표시""",

            "context": """# context 설정

```yaml
context:
  auto_update: false      # 기록 시 컨텍스트 자동 업데이트
  recent_days: 3          # 컨텍스트에 포함할 최근 일수
```

## 옵션 설명
- **auto_update**: true 시 `m` 명령 후 자동으로 `mcontext` 실행
- **recent_days**: memory-context.md에 포함할 최근 타임라인 일수""",

            "search": """# search 설정

```yaml
search:
  default_scope: local    # 기본 검색 범위: local, kb, all
  include_archived: false # 아카이브 포함 여부
  max_file_size: 1048576  # 검색할 최대 파일 크기 (bytes)
  exclude_patterns: []    # 검색 제외 패턴
```

## 옵션 설명
- **default_scope**: 검색 범위
  - local: .memory/ 내부만
  - kb: 지식 베이스만
  - all: 모두
- **include_archived**: true 시 archive/ 폴더도 검색
- **max_file_size**: 이 크기보다 큰 파일은 검색 제외
- **exclude_patterns**: 검색 제외할 glob 패턴 목록""",

            "llm": """# llm 설정

```yaml
llm:
  provider: anthropic     # 기본 제공자: anthropic, ollama, claude-cli, gemini-cli
  ollama_host: "http://localhost:11434"
  ollama_model: "llama3.2"
  anthropic_api_key: null # 또는 환경변수 ANTHROPIC_API_KEY 사용
  anthropic_model: "claude-3-5-sonnet-20241022"
  max_tokens: 4096
  temperature: 0.7
```

## 제공자별 설정
1. **claude-cli** (권장): Claude Code 환경에서 자동 사용
2. **gemini-cli**: Gemini CLI 사용
3. **anthropic**: API 키 필요
4. **ollama**: 로컬 LLM (Ollama 서버 필요)

## 환경변수
- ANTHROPIC_API_KEY: Anthropic API 키
- GOOGLE_API_KEY: Gemini API 키""",

            "help": """# help 설정

```yaml
help:
  language: en            # 도움말 언어: en, ko
```

## 옵션 설명
- **language**: mhelp 명령어의 기본 출력 언어
  - en: 영어 (기본값)
  - ko: 한국어

## 언어 변경 방법
```bash
mconfig set help.language ko    # 한국어로 변경
mhelp --set-lang ko             # 동일한 효과
```""",

            "notion": """# notion 설정

Notion 연동을 위한 설정입니다.

```yaml
notion:
  mode: default           # 인증 모드: default, pat
  api_key: null          # Notion API 키 (또는 NOTION_API_KEY 환경변수)
  default_page_id: null  # 기본 페이지 ID (레거시)

  # PAT 모드 (Personal Access Token)
  pat:
    token: null          # PAT 토큰
    default_page_id: null

  # 동기화 설정
  sync:
    # 모듈 동기화
    module:
      enabled: false
      root_page_id: null    # 모듈 동기화 루트 페이지
      targets: []           # 동기화할 모듈 경로 목록
      exclude_patterns: []  # 제외할 패턴
      conflict_resolution: last-write-wins

    # 타임라인 동기화
    timeline:
      enabled: false
      root_page_id: null    # 타임라인 루트 페이지
      bidirectional: false  # 양방향 동기화
      sync_days: 30         # 동기화할 일수

    # 플랜 동기화
    plan:
      enabled: false
      root_page_id: null    # 플랜 루트 페이지
      daily: true           # 일간 플랜 동기화
      weekly: true          # 주간 플랜 동기화
      monthly: true         # 월간 플랜 동기화
```""",

            "notion.sync": """# notion.sync 상세 설정

## 모듈 동기화 (notion.sync.module)
```yaml
notion:
  sync:
    module:
      enabled: true
      root_page_id: "abc123..."  # Notion 페이지 ID
      targets:                    # 동기화할 모듈
        - "projects/memory-tool"
        - "concepts"
      exclude_patterns:
        - "*.tmp"
        - "archive/*"
      conflict_resolution: last-write-wins  # 또는 local-wins, notion-wins
```

## 타임라인 동기화 (notion.sync.timeline)
```yaml
notion:
  sync:
    timeline:
      enabled: true
      root_page_id: "def456..."  # 타임라인 루트 페이지
      bidirectional: true        # Notion에서 수정 시 로컬에도 반영
      sync_days: 30              # 최근 30일 동기화
```

## 플랜 동기화 (notion.sync.plan)
```yaml
notion:
  sync:
    plan:
      enabled: true
      root_page_id: "ghi789..."  # 플랜 루트 페이지
      daily: true
      weekly: true
      monthly: true
```

## 페이지 ID 찾는 방법
1. Notion에서 페이지 열기
2. 우측 상단 "..." → "Copy link"
3. URL에서 마지막 32자가 페이지 ID
   예: notion.so/My-Page-**abc123def456...**""",

            "notion.sync.module": """# 모듈 동기화 설정 (notion.sync.module)

```yaml
notion:
  sync:
    module:
      enabled: true              # 모듈 동기화 활성화
      root_page_id: "페이지ID"   # Notion 루트 페이지
      targets:                   # 동기화 대상 모듈
        - "projects/memory-tool"
        - "projects/memory-tool/core-system"
        - "concepts"
      exclude_patterns:          # 제외할 파일 패턴
        - "*.tmp"
        - "archive/*"
      conflict_resolution: last-write-wins
```

## conflict_resolution 옵션
- **last-write-wins**: 가장 최근 수정된 것이 우선 (기본값)
- **local-wins**: 로컬 파일이 항상 우선
- **notion-wins**: Notion이 항상 우선

## 사용 예시
```bash
nsync --module            # 모듈 동기화 실행
nsync --module --push     # 로컬 → Notion
nsync --module --pull     # Notion → 로컬
```""",

            "notion.sync.timeline": """# 타임라인 동기화 설정 (notion.sync.timeline)

```yaml
notion:
  sync:
    timeline:
      enabled: true              # 타임라인 동기화 활성화
      root_page_id: "페이지ID"   # Notion 타임라인 루트 페이지
      bidirectional: true        # 양방향 동기화 활성화
      sync_days: 30              # 최근 30일 동기화
```

## 옵션 설명
- **enabled**: true로 설정 시 타임라인 동기화 활성화
- **root_page_id**: Notion에서 타임라인을 저장할 페이지 ID
- **bidirectional**: true 시 Notion에서 수정한 내용도 로컬에 반영
- **sync_days**: 동기화할 최근 일수 (기본 30일)

## 사용 예시
```bash
nsync --timeline          # 타임라인 동기화
nm "기록 내용"            # Notion에 직접 기록 (동기화 포함)
nwatch --timeline-only    # 타임라인 변경 감시
```""",

            "notion.sync.plan": """# 플랜 동기화 설정 (notion.sync.plan)

```yaml
notion:
  sync:
    plan:
      enabled: true              # 플랜 동기화 활성화
      root_page_id: "페이지ID"   # Notion 플랜 루트 페이지
      daily: true                # 일간 플랜 동기화
      weekly: true               # 주간 플랜 동기화
      monthly: true              # 월간 플랜 동기화
```

## 페이지 구조
Notion에 다음 구조로 페이지가 생성됩니다:
```
Plans (root_page_id)
├── 📅 Daily Plans/
│   └── 2026-01/
│       ├── 21
│       └── 22
├── 📆 Weekly Plans/
│   └── 2026/
│       ├── W04
│       └── W05
└── 📆 Monthly Plans/
    └── 2026/
        └── 01
```

## 사용 예시
```bash
nsync --plan              # 플랜 동기화
np "작업 내용"            # Notion 플랜에 직접 추가
np "작업" --weekly        # 주간 플랜에 추가
nwatch --plans-only       # 플랜 변경 감시
```""",

            "summary": """# summary 설정

```yaml
summary:
  default_language: ko    # 요약 언어: ko, en, auto
```

## 옵션 설명
- **default_language**: msummary 명령의 출력 언어
  - ko: 한국어
  - en: 영어
  - auto: 입력 내용에 따라 자동 선택""",

            "modules": """# modules 설정

```yaml
modules:
  auto_update_current: false  # current.md 자동 업데이트
```

## 옵션 설명
- **auto_update_current**: true 시 모듈 관련 기록 후 current.md 자동 업데이트""",
        }

        section = section.lower().strip()

        # Handle 'all' - return overview
        if section == "all":
            overview = CONFIG_GUIDE["overview"]
            # Also include section list
            sections = "\n\n## 사용 가능한 섹션\n"
            for key in sorted(CONFIG_GUIDE.keys()):
                if key != "overview":
                    sections += f"- {key}\n"
            return overview + sections

        # Try exact match first
        if section in CONFIG_GUIDE:
            return CONFIG_GUIDE[section]

        # Try partial match (e.g., "notion.sync" matches "notion.sync.module")
        matches = [k for k in CONFIG_GUIDE.keys() if section in k or k in section]
        if matches:
            # Return most specific match
            best_match = max(matches, key=len)
            return CONFIG_GUIDE[best_match]

        # If not found, return overview with suggestion
        return f"""설정 섹션 '{section}'을 찾을 수 없습니다.

사용 가능한 섹션:
- all (전체 개요)
- timeline
- context
- search
- llm
- help
- summary
- modules
- notion
- notion.sync
- notion.sync.module
- notion.sync.timeline
- notion.sync.plan

예: get_config_guide(section='notion.sync.timeline')"""

    def _tool_get_usage_guide(self, topic: str = "all") -> str:
        """Get comprehensive usage guide for Memory Tool features.

        Args:
            topic: Topic to get guide for ('all', 'tags', 'search', etc.)
        """
        content = None

        # Try to read from package data first
        try:
            import importlib.resources
            if hasattr(importlib.resources, 'files'):
                # Python 3.9+
                data_path = importlib.resources.files('memory_tool') / 'data' / 'USAGE.md'
                if data_path.is_file():
                    content = data_path.read_text(encoding='utf-8')
        except Exception:
            pass

        # Fallback to .memory/docs/USAGE.md
        if content is None:
            usage_file = self.memory_path / "docs" / "USAGE.md"
            if usage_file.exists():
                try:
                    content = usage_file.read_text(encoding="utf-8")
                except Exception:
                    pass

        # If no content found, return fallback
        if content is None:
            return """USAGE.md not found. Run 'mhelp --guide' for advanced features guide.

Key features:
1. Tags: m "message" --tags bug,auth (then search with ms "query" --tag auth)
2. Wiki Links: [[module-name]] to connect modules
3. Search Modes: --hybrid, --semantic, --boost-recent
4. Plans: mplan daily/weekly for task management
5. AI: mask "question" to ask about your memory

For detailed help, run 'mhelp --guide' or 'mhelp <command>'."""

        # If topic is 'all', return full content
        if topic.lower() == "all":
            return content

        # Extract relevant section based on topic
        topic_map = {
            "tags": "## 12. Tags System",
            "tag": "## 12. Tags System",
            "search": "## 2. Search",
            "timeline": "## 1. Timeline Recording",
            "record": "## 1. Timeline Recording",
            "modules": "## 4. Modules",
            "module": "## 4. Modules",
            "plans": "## 5. Plans",
            "plan": "## 5. Plans",
            "ai": "## 6. AI Features",
            "ask": "## 6. AI Features",
            "mask": "## 6. AI Features",
            "notion": "## 10. Notion Integration",
            "config": "## 9. Configuration",
            "wiki": "## 4. Modules",  # Wiki links are in modules section
            "archive": "## 13. Archive System",
            "context": "## 8. Context Generation",
            "summary": "## 7. Summarization",
        }

        section_header = topic_map.get(topic.lower())
        if section_header:
            # Find section and extract until next ## header
            start_idx = content.find(section_header)
            if start_idx != -1:
                # Find next section or end of file
                next_section = content.find("\n## ", start_idx + len(section_header))
                if next_section != -1:
                    section_content = content[start_idx:next_section].strip()
                else:
                    section_content = content[start_idx:].strip()
                return section_content

        # If topic not found, return available topics
        return f"""Topic '{topic}' not found in usage guide.

Available topics:
- all: Complete guide
- tags: Tag system for categorization
- search: Search features and modes
- timeline: Timeline recording
- modules: Module organization
- plans: Daily/weekly plans
- ai/mask: AI question answering
- notion: Notion integration
- config: Configuration settings
- archive: Archive system
- wiki: Wiki links

Example: get_usage_guide(topic='tags')"""

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
            elif tool_name == "get_config_guide":
                result = self._tool_get_config_guide(args.get("section", "all"))
            elif tool_name == "get_usage_guide":
                result = self._tool_get_usage_guide(args.get("topic", "all"))
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
