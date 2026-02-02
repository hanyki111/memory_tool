"""Bilingual help text system for CLI commands.

This module provides language-aware help texts that can be used with Typer's
help system. The language preference is read from config.yaml (help.language).
"""

from pathlib import Path
from typing import Optional, Dict, Callable
import functools

# Cache for language preference
_language_cache: Optional[str] = None


def get_help_language() -> str:
    """Get help language from config.yaml.

    Returns:
        Language code ('en' or 'ko'), defaults to 'en'
    """
    global _language_cache

    if _language_cache is not None:
        return _language_cache

    try:
        from memory_tool.utils.config import Config
        cfg = Config()
        _language_cache = cfg.get("help.language", "en")
        return _language_cache
    except Exception:
        return "en"


def clear_language_cache():
    """Clear the language cache (for testing or config reload)."""
    global _language_cache
    _language_cache = None


def get_text(en: str, ko: str) -> str:
    """Get text in the configured language.

    Args:
        en: English text
        ko: Korean text

    Returns:
        Text in the configured language
    """
    lang = get_help_language()
    return ko if lang == "ko" else en


# =============================================================================
# Help texts for all commands
# =============================================================================

HELP_TEXTS = {
    # -------------------------------------------------------------------------
    # Core Commands
    # -------------------------------------------------------------------------
    "record": {
        "short": {
            "en": "Record entry to timeline",
            "ko": "타임라인에 기록 추가",
        },
        "long": {
            "en": """Record an entry to the timeline.

Records a timestamped entry to your timeline. The entry is automatically
organized by date and can include optional tags for categorization.

Examples:
    m "Started working on feature X"
    m "Fixed bug in login" --tags bug,login
    m "Meeting with team" --date 2026-01-20
    m "Review completed" --time 14:30
""",
            "ko": """타임라인에 항목을 기록합니다.

타임스탬프가 포함된 항목을 타임라인에 기록합니다. 항목은 자동으로
날짜별로 정리되며, 분류를 위한 태그를 선택적으로 포함할 수 있습니다.

예시:
    m "기능 X 작업 시작"
    m "로그인 버그 수정" --tags bug,login
    m "팀 미팅" --date 2026-01-20
    m "리뷰 완료" --time 14:30
""",
        },
        "options": {
            "message": {
                "en": "The message to record",
                "ko": "기록할 메시지",
            },
            "tags": {
                "en": "Comma-separated tags for categorization",
                "ko": "쉼표로 구분된 분류 태그",
            },
            "date": {
                "en": "Record date (YYYY-MM-DD), defaults to today",
                "ko": "기록 날짜 (YYYY-MM-DD), 기본값은 오늘",
            },
            "time": {
                "en": "Record time (HH:MM), defaults to current time",
                "ko": "기록 시간 (HH:MM), 기본값은 현재 시간",
            },
        },
    },

    # -------------------------------------------------------------------------
    # Timeline Commands
    # -------------------------------------------------------------------------
    "today": {
        "short": {
            "en": "Show today's timeline entries",
            "ko": "오늘의 타임라인 항목 보기",
        },
        "long": {
            "en": """Display all timeline entries for today.

Shows all entries recorded on the current date, sorted by time.
Use --edit to open the timeline file in your default editor.

Examples:
    mtoday           # Show today's entries
    mtoday --edit    # Edit today's timeline file
""",
            "ko": """오늘의 모든 타임라인 항목을 표시합니다.

현재 날짜에 기록된 모든 항목을 시간순으로 표시합니다.
--edit 옵션으로 기본 편집기에서 타임라인 파일을 열 수 있습니다.

예시:
    mtoday           # 오늘 항목 보기
    mtoday --edit    # 오늘 타임라인 파일 편집
""",
        },
    },

    "week": {
        "short": {
            "en": "Show this week's timeline",
            "ko": "이번 주 타임라인 보기",
        },
        "long": {
            "en": """Display timeline entries for the current week.

Shows all entries from Monday to today (or Sunday if viewing past weeks).
Entries are grouped by date for easy scanning.

Examples:
    mweek                    # Show this week
    mweek --offset -1        # Show last week
""",
            "ko": """이번 주의 타임라인 항목을 표시합니다.

월요일부터 오늘(또는 과거 주를 볼 때는 일요일)까지의 모든 항목을 표시합니다.
항목은 날짜별로 그룹화되어 쉽게 확인할 수 있습니다.

예시:
    mweek                    # 이번 주 보기
    mweek --offset -1        # 지난 주 보기
""",
        },
    },

    "month": {
        "short": {
            "en": "Show this month's timeline",
            "ko": "이번 달 타임라인 보기",
        },
        "long": {
            "en": """Display timeline entries for the current month.

Shows all entries from the 1st to today (or end of month for past months).

Examples:
    mmonth                   # Show this month
    mmonth --offset -1       # Show last month
    mmonth --year 2025 --month 12   # Show December 2025
""",
            "ko": """이번 달의 타임라인 항목을 표시합니다.

1일부터 오늘(또는 과거 달의 경우 말일)까지의 모든 항목을 표시합니다.

예시:
    mmonth                   # 이번 달 보기
    mmonth --offset -1       # 지난 달 보기
    mmonth --year 2025 --month 12   # 2025년 12월 보기
""",
        },
    },

    # -------------------------------------------------------------------------
    # Search Commands
    # -------------------------------------------------------------------------
    "tags": {
        "short": {
            "en": "List tags used in .memory",
            "ko": ".memory에서 사용된 태그 목록",
        },
        "long": {
            "en": """List all tags used in your .memory files.

Shows tags with usage counts from timeline, modules, and plans.
By default, only searches timeline files.

Output includes a visual bar chart showing relative usage frequency.

Examples:
    mtags                              # Timeline tags (default)
    mtags --all                        # All file types
    mtags --type timeline --type modules  # Multiple types
    mtags --sort alpha                 # Sort alphabetically
    mtags --min-count 3                # Tags used 3+ times
""",
            "ko": """.memory 파일에서 사용된 모든 태그를 나열합니다.

타임라인, 모듈, 플랜에서 사용 횟수와 함께 태그를 표시합니다.
기본값으로 타임라인 파일만 검색합니다.

출력에는 상대적 사용 빈도를 보여주는 시각적 막대 차트가 포함됩니다.

예시:
    mtags                              # 타임라인 태그 (기본값)
    mtags --all                        # 모든 파일 타입
    mtags --type timeline --type modules  # 여러 타입
    mtags --sort alpha                 # 알파벳순 정렬
    mtags --min-count 3                # 3회 이상 사용된 태그만
""",
        },
        "options": {
            "type": {
                "en": "File types to search: timeline, modules, plans (can use multiple)",
                "ko": "검색할 파일 타입: timeline, modules, plans (다중 사용 가능)",
            },
            "all": {
                "en": "Search all file types",
                "ko": "모든 파일 타입 검색",
            },
            "sort": {
                "en": "Sort by: count (default), alpha",
                "ko": "정렬 방식: count (기본값), alpha",
            },
            "min_count": {
                "en": "Minimum usage count to display",
                "ko": "표시할 최소 사용 횟수",
            },
        },
    },

    "search": {
        "short": {
            "en": "Search timeline and modules",
            "ko": "타임라인 및 모듈 검색",
        },
        "long": {
            "en": """Search through timeline entries and module documents.

Supports keyword search (default), semantic search (--semantic),
and hybrid search (--hybrid) that combines both approaches.

Tag search:
  - Use #hashtag directly in query: ms "#bug"
  - Multiple tags: ms "#bug #urgent"
  - Tag + keyword: ms "login #auth"
  - Tag-only filter: ms --tag-only bug
  - Keyword + tag filter: ms "error" --tag auth

Search scopes:
  - local: Search only in .memory/ directory (default)
  - kb: Search in knowledge base
  - all: Search both local and knowledge base

Examples:
    ms "bug fix"                    # Keyword search
    ms "#bug"                       # Search by tag
    ms "#bug #urgent"               # Multiple tags
    ms "login" --tag auth           # Keyword + tag filter
    ms "authentication" --semantic  # Semantic search
    ms "login" --hybrid             # Hybrid search
    ms "api" --with-kb              # Include KB
    ms "refactor" --date this-week  # This week only
""",
            "ko": """타임라인 항목과 모듈 문서를 검색합니다.

키워드 검색(기본), 시맨틱 검색(--semantic),
그리고 두 가지를 결합한 하이브리드 검색(--hybrid)을 지원합니다.

태그 검색:
  - 쿼리에 #해시태그 직접 사용: ms "#버그"
  - 여러 태그: ms "#버그 #긴급"
  - 태그 + 키워드: ms "로그인 #인증"
  - 태그만 필터: ms --tag-only 버그
  - 키워드 + 태그 필터: ms "에러" --tag 인증

검색 범위:
  - local: .memory/ 디렉토리만 검색 (기본값)
  - kb: 지식 베이스에서 검색
  - all: 로컬과 지식 베이스 모두 검색

예시:
    ms "버그 수정"                   # 키워드 검색
    ms "#버그"                       # 태그로 검색
    ms "#버그 #긴급"                 # 여러 태그
    ms "로그인" --tag 인증           # 키워드 + 태그 필터
    ms "인증 문제" --semantic        # 시맨틱 검색
    ms "로그인" --hybrid             # 하이브리드 검색
    ms "api" --with-kb               # KB 포함
    ms "리팩토링" --date this-week   # 이번 주만
""",
        },
    },

    # -------------------------------------------------------------------------
    # Module Commands
    # -------------------------------------------------------------------------
    "module": {
        "short": {
            "en": "Manage modules and connections",
            "ko": "모듈 및 연결 관리",
        },
        "long": {
            "en": """Manage knowledge modules and their connections.

Modules are the spatial organization of your knowledge, complementing
the timeline's temporal organization. Each module contains:
  - current.md: Current state and ongoing work
  - decisions.md: Important decisions and rationale
  - archive/: Historical records

Subcommands:
  list      - List all modules
  show      - Display module details
  create    - Create new module
  edit      - Edit module files
  connect   - Create connections between modules

Examples:
    mmodule list                           # List all modules
    mmodule show projects/memory-tool      # Show module details
    mmodule create projects/new-feature    # Create module
    mmodule edit projects/memory-tool --current  # Edit current.md
""",
            "ko": """지식 모듈과 연결을 관리합니다.

모듈은 지식의 공간적 조직으로, 타임라인의 시간적 조직을 보완합니다.
각 모듈에는 다음이 포함됩니다:
  - current.md: 현재 상태와 진행 중인 작업
  - decisions.md: 중요한 결정 사항과 근거
  - archive/: 과거 기록

하위 명령어:
  list      - 모든 모듈 나열
  show      - 모듈 상세 정보 표시
  create    - 새 모듈 생성
  edit      - 모듈 파일 편집
  connect   - 모듈 간 연결 생성

예시:
    mmodule list                           # 모든 모듈 나열
    mmodule show projects/memory-tool      # 모듈 상세 정보 보기
    mmodule create projects/new-feature    # 모듈 생성
    mmodule edit projects/memory-tool --current  # current.md 편집
""",
        },
    },

    "context": {
        "short": {
            "en": "Build Claude Code context file",
            "ko": "Claude Code 컨텍스트 파일 생성",
        },
        "long": {
            "en": """Generate context file for Claude Code integration.

Creates .claude/memory-context.md containing:
  - Recent timeline entries
  - Active plans and tasks
  - Module status overview
  - Document health warnings

This file helps Claude Code understand your project's current state.

Examples:
    mcontext                    # Generate context file
    mcontext --days 7           # Include last 7 days
    mcontext --no-timeline      # Skip timeline section
""",
            "ko": """Claude Code 연동을 위한 컨텍스트 파일을 생성합니다.

.claude/memory-context.md 파일에 다음 내용이 포함됩니다:
  - 최근 타임라인 항목
  - 활성 계획 및 작업
  - 모듈 상태 개요
  - 문서 상태 경고

이 파일은 Claude Code가 프로젝트의 현재 상태를 이해하는 데 도움이 됩니다.

예시:
    mcontext                    # 컨텍스트 파일 생성
    mcontext --days 7           # 최근 7일 포함
    mcontext --no-timeline      # 타임라인 섹션 제외
""",
        },
    },

    # -------------------------------------------------------------------------
    # Planning Commands
    # -------------------------------------------------------------------------
    "plan": {
        "short": {
            "en": "Manage plans and tasks",
            "ko": "계획 및 작업 관리",
        },
        "long": {
            "en": """Manage daily, weekly, and monthly plans.

Plans help you organize tasks and track progress. Each plan type has
specific focus:
  - daily: Today's specific tasks
  - weekly: Week's goals and priorities
  - monthly: Month's objectives and milestones

Subcommands:
  daily [show/edit/carryover/yesterday]   - Daily plan operations
  weekly [show/edit/carryover/lastweek]   - Weekly plan operations
  monthly [show/edit]                      - Monthly plan operations

Examples:
    mplan daily                    # Show today's plan
    mplan daily edit               # Edit today's plan
    mplan daily carryover          # Move incomplete tasks from yesterday
    mplan weekly                   # Show this week's plan
    mplan weekly lastweek          # Show last week's plan
""",
            "ko": """일간, 주간, 월간 계획을 관리합니다.

계획은 작업을 조직하고 진행 상황을 추적하는 데 도움이 됩니다.
각 계획 유형의 초점:
  - daily: 오늘의 구체적인 작업
  - weekly: 이번 주의 목표와 우선순위
  - monthly: 이번 달의 목표와 마일스톤

하위 명령어:
  daily [show/edit/carryover/yesterday]   - 일일 계획 작업
  weekly [show/edit/carryover/lastweek]   - 주간 계획 작업
  monthly [show/edit]                      - 월간 계획 작업

예시:
    mplan daily                    # 오늘 계획 보기
    mplan daily edit               # 오늘 계획 편집
    mplan daily carryover          # 어제 미완료 작업 이관
    mplan weekly                   # 이번 주 계획 보기
    mplan weekly lastweek          # 지난 주 계획 보기
""",
        },
    },

    # -------------------------------------------------------------------------
    # AI/LLM Commands
    # -------------------------------------------------------------------------
    "ask": {
        "short": {
            "en": "Ask questions about your memory (RAG)",
            "ko": "메모리 기반 질문 (RAG)",
        },
        "long": {
            "en": """Ask questions about your memory using AI.

Uses Retrieval-Augmented Generation (RAG) to answer questions based on
your timeline, modules, and plans. The AI agent can:
  - Search your timeline and modules
  - Retrieve relevant context
  - Synthesize comprehensive answers

Requires LLM configuration in config.yaml.

Examples:
    mask "What did I work on last week?"
    mask "What decisions were made about authentication?"
    mask "Summarize recent bug fixes"
    mask "What are my current priorities?" --verbose
""",
            "ko": """AI를 사용하여 메모리에 대해 질문합니다.

검색 증강 생성(RAG)을 사용하여 타임라인, 모듈, 계획을 기반으로
질문에 답변합니다. AI 에이전트가 할 수 있는 일:
  - 타임라인과 모듈 검색
  - 관련 컨텍스트 검색
  - 종합적인 답변 생성

config.yaml에 LLM 설정이 필요합니다.

예시:
    mask "지난 주에 무슨 작업을 했나요?"
    mask "인증 관련 어떤 결정을 내렸나요?"
    mask "최근 버그 수정 요약해 주세요"
    mask "현재 우선순위가 뭔가요?" --verbose
""",
        },
    },

    # -------------------------------------------------------------------------
    # Notion Commands
    # -------------------------------------------------------------------------
    "nsync": {
        "short": {
            "en": "Sync with Notion",
            "ko": "노션과 동기화",
        },
        "long": {
            "en": """Synchronize local memory with Notion.

Syncs modules, timeline, and plans between local .memory/ and Notion.
Supports bidirectional sync with conflict resolution.

Requires Notion configuration in config.yaml.

Sync targets:
  --module      Sync modules only
  --timeline    Sync timeline only
  --plan        Sync plans only

Examples:
    nsync                          # Sync everything
    nsync --push                   # Push local to Notion
    nsync --pull                   # Pull from Notion to local
    nsync --module --push          # Push modules only
    nsync --plan --daily           # Sync daily plans only
    nsync --dry-run                # Preview without changes
""",
            "ko": """로컬 메모리를 노션과 동기화합니다.

.memory/의 모듈, 타임라인, 계획을 노션과 동기화합니다.
충돌 해결과 함께 양방향 동기화를 지원합니다.

config.yaml에 노션 설정이 필요합니다.

동기화 대상:
  --module      모듈만 동기화
  --timeline    타임라인만 동기화
  --plan        계획만 동기화

예시:
    nsync                          # 전체 동기화
    nsync --push                   # 로컬에서 노션으로 푸시
    nsync --pull                   # 노션에서 로컬로 풀
    nsync --module --push          # 모듈만 푸시
    nsync --plan --daily           # 일일 계획만 동기화
    nsync --dry-run                # 변경 없이 미리보기
""",
        },
    },

    # -------------------------------------------------------------------------
    # System Commands
    # -------------------------------------------------------------------------
    "init": {
        "short": {
            "en": "Initialize .memory/ structure",
            "ko": ".memory/ 구조 초기화",
        },
        "long": {
            "en": """Initialize Memory Tool in the current directory.

Creates the .memory/ directory structure with:
  - timeline/: Time-based entries
  - modules/: Knowledge modules
  - plans/: Daily, weekly, monthly plans
  - config.yaml: Configuration file
  - docs/: Documentation templates

Also creates .claude/ directory for Claude Code integration.

Examples:
    minit                          # Initialize in current directory
    minit --force                  # Reinitialize (overwrites)
    minit --kb /path/to/kb         # Set knowledge base path
    minit --update-docs            # Update documentation templates
""",
            "ko": """현재 디렉토리에 Memory Tool을 초기화합니다.

다음 구조의 .memory/ 디렉토리를 생성합니다:
  - timeline/: 시간 기반 항목
  - modules/: 지식 모듈
  - plans/: 일간, 주간, 월간 계획
  - config.yaml: 설정 파일
  - docs/: 문서 템플릿

Claude Code 연동을 위한 .claude/ 디렉토리도 생성합니다.

예시:
    minit                          # 현재 디렉토리에 초기화
    minit --force                  # 재초기화 (덮어쓰기)
    minit --kb /path/to/kb         # 지식 베이스 경로 설정
    minit --update-docs            # 문서 템플릿 업데이트
""",
        },
    },

    "config": {
        "short": {
            "en": "Manage config.yaml settings",
            "ko": "config.yaml 설정 관리",
        },
        "long": {
            "en": """View and modify config.yaml settings.

Configuration file controls behavior of Memory Tool including:
  - Timeline settings (auto-record, granularity)
  - Search settings (scope, max file size)
  - LLM settings (provider, model, API key)
  - Notion integration settings
  - Help language preference

Actions:
  list    Show all configuration values
  get     Get a specific configuration value
  set     Set a configuration value

Examples:
    mconfig list                       # Show all settings
    mconfig get help.language          # Get help language
    mconfig set help.language ko       # Set help language to Korean
    mconfig set llm.provider ollama    # Set LLM provider
    mconfig set search.max_file_size 2097152  # Set max file size to 2MB
""",
            "ko": """config.yaml 설정을 확인하고 수정합니다.

설정 파일은 Memory Tool의 동작을 제어합니다:
  - 타임라인 설정 (자동 기록, 세분화)
  - 검색 설정 (범위, 최대 파일 크기)
  - LLM 설정 (제공자, 모델, API 키)
  - 노션 연동 설정
  - 도움말 언어 설정

작업:
  list    모든 설정 값 표시
  get     특정 설정 값 가져오기
  set     설정 값 변경

예시:
    mconfig list                       # 모든 설정 보기
    mconfig get help.language          # 도움말 언어 가져오기
    mconfig set help.language ko       # 도움말 언어를 한국어로 설정
    mconfig set llm.provider ollama    # LLM 제공자 설정
    mconfig set search.max_file_size 2097152  # 최대 파일 크기 2MB로 설정
""",
        },
    },

    "alias": {
        "short": {
            "en": "Manage command aliases",
            "ko": "명령어 별칭 관리",
        },
        "long": {
            "en": """Install and manage command aliases.

Aliases provide short commands for common operations:
  m      -> record (add timeline entry)
  ms     -> search (search memory)
  mtoday -> today (show today's timeline)
  etc.

Installation options:
  - Batch files (Windows default)
  - PowerShell profile functions
  - Bash/Zsh profile functions

Examples:
    malias list                    # Show all aliases
    malias list --lang ko          # Show with Korean descriptions
    malias install                 # Install batch files
    malias install --powershell    # Install to PowerShell profile
    malias install --bash          # Install to Bash profile
    malias uninstall               # Remove aliases
""",
            "ko": """명령어 별칭을 설치하고 관리합니다.

별칭은 자주 사용하는 작업에 대한 짧은 명령어를 제공합니다:
  m      -> record (타임라인 항목 추가)
  ms     -> search (메모리 검색)
  mtoday -> today (오늘 타임라인 보기)
  등.

설치 옵션:
  - 배치 파일 (Windows 기본)
  - PowerShell 프로필 함수
  - Bash/Zsh 프로필 함수

예시:
    malias list                    # 모든 별칭 보기
    malias list --lang ko          # 한국어 설명으로 보기
    malias install                 # 배치 파일 설치
    malias install --powershell    # PowerShell 프로필에 설치
    malias install --bash          # Bash 프로필에 설치
    malias uninstall               # 별칭 제거
""",
        },
    },
}


def get_command_help(command: str, help_type: str = "short") -> str:
    """Get help text for a command.

    Args:
        command: Command name (e.g., "record", "search")
        help_type: Type of help ("short" or "long")

    Returns:
        Help text in configured language
    """
    lang = get_help_language()

    if command not in HELP_TEXTS:
        return ""

    cmd_help = HELP_TEXTS[command]

    if help_type not in cmd_help:
        return ""

    help_dict = cmd_help[help_type]
    return help_dict.get(lang, help_dict.get("en", ""))


def get_option_help(command: str, option: str) -> str:
    """Get help text for a command option.

    Args:
        command: Command name
        option: Option name

    Returns:
        Option help text in configured language
    """
    lang = get_help_language()

    if command not in HELP_TEXTS:
        return ""

    options = HELP_TEXTS[command].get("options", {})

    if option not in options:
        return ""

    opt_help = options[option]
    return opt_help.get(lang, opt_help.get("en", ""))
