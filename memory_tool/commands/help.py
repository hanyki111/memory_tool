"""Detailed help system with bilingual support."""

from typing import Optional
import typer
from memory_tool.commands.common import app, console


# Detailed help content (bilingual)
HELP_CONTENT = {
    # ================================================================
    # Core Commands
    # ================================================================
    "record": {
        "en": {
            "name": "m / record",
            "summary": "Record an entry to today's timeline",
            "description": """
Records a timestamped entry to today's timeline file.
The entry is automatically saved to .memory/timeline/daily/YYYY-MM/DD.md

This is the most frequently used command - capture thoughts, progress,
decisions, or any information instantly.

Tags can be added inline at the end of message (#tag) or with --tags option.
Tags are searchable with: ms "query" --tag tagname
            """,
            "examples": [
                'm "Fixed login bug in auth.py"',
                'm "Fixed auth issue #bug #auth #urgent"',
                'm "Started feature X" --tags feature,sprint-1',
                'm "Meeting notes #meeting #team"',
            ],
            "options": [
                ("--date, -d", "Record to a specific date (YYYY-MM-DD)"),
                ("--time, -t", "Override timestamp (HH:MM)"),
                ("--tags, -t", "Comma-separated tags (e.g., bug,auth,urgent)"),
            ],
        },
        "ko": {
            "name": "m / record (기)",
            "summary": "오늘 타임라인에 기록 추가",
            "description": """
타임스탬프와 함께 오늘의 타임라인 파일에 기록합니다.
기록은 자동으로 .memory/timeline/daily/YYYY-MM/DD.md에 저장됩니다.

가장 자주 사용하는 명령어입니다 - 생각, 진행 상황, 결정 사항,
또는 어떤 정보든 즉시 기록하세요.

태그는 메시지 끝에 #태그 형식으로 추가하거나 --tags 옵션으로 지정합니다.
태그 검색: ms "검색어" --tag 태그명
            """,
            "examples": [
                'm "auth.py 로그인 버그 수정"',
                'm "인증 문제 수정 #bug #auth #urgent"',
                'm "기능 X 시작" --tags feature,sprint-1',
                'm "회의 노트 #meeting #team"',
            ],
            "options": [
                ("--date, -d", "특정 날짜에 기록 (YYYY-MM-DD)"),
                ("--time, -t", "타임스탬프 직접 지정 (HH:MM)"),
                ("--tags, -t", "쉼표로 구분된 태그 (예: bug,auth,urgent)"),
            ],
        },
    },

    "search": {
        "en": {
            "name": "ms / search",
            "summary": "Search timeline and modules",
            "description": """
Searches through your memory (timeline, modules, plans) using
keyword matching, semantic search, or hybrid mode.

Supports regex patterns, date filtering, and result ranking.
            """,
            "examples": [
                'ms "bug fix"                    # Basic keyword search',
                'ms "authentication" --hybrid   # Keyword + semantic search',
                'ms "API" --date this-week      # Search this week only',
                'ms "decision" --type modules   # Search modules only',
                'ms "refactor" --boost-recent   # Boost recent results',
                'ms "#bug"                       # Search by hashtag',
                'ms "[urgent]"                   # Search by bracket tag',
            ],
            "options": [
                ("--hybrid", "Combine keyword and semantic search"),
                ("--semantic, -s", "Use semantic (meaning-based) search"),
                ("--date", "Date filter: today, yesterday, this-week, last-N-days"),
                ("--type", "File type: timeline, modules, decisions, plans"),
                ("--boost-recent", "Prioritize recent results"),
            ],
        },
        "ko": {
            "name": "ms / search (검)",
            "summary": "타임라인과 모듈 검색",
            "description": """
메모리(타임라인, 모듈, 계획) 전체를 키워드 매칭,
시맨틱 검색, 또는 하이브리드 모드로 검색합니다.

정규식 패턴, 날짜 필터링, 결과 랭킹을 지원합니다.
            """,
            "examples": [
                'ms "버그 수정"                    # 기본 키워드 검색',
                'ms "인증" --hybrid               # 키워드 + 시맨틱 검색',
                'ms "API" --date this-week       # 이번 주만 검색',
                'ms "결정" --type modules        # 모듈만 검색',
                'ms "리팩토링" --boost-recent    # 최근 결과 우선',
                'ms "#버그"                       # 해시태그로 검색',
                'ms "[긴급]"                      # 대괄호 태그로 검색',
            ],
            "options": [
                ("--hybrid", "키워드와 시맨틱 검색 결합"),
                ("--semantic, -s", "시맨틱(의미 기반) 검색 사용"),
                ("--date", "날짜 필터: today, yesterday, this-week, last-N-days"),
                ("--type", "파일 유형: timeline, modules, decisions, plans"),
                ("--boost-recent", "최근 결과 우선 표시"),
            ],
        },
    },

    "tag": {
        "en": {
            "name": "mtag / tag",
            "summary": "Tag management commands",
            "description": """
Manage tags in your .memory files. Supports listing, replacing,
deleting, and finding tags.

Without subcommand, mtag defaults to listing tags.

Subcommands:
  (none)   - List tags (same as 'list')
  list     - List tags with usage counts
  replace  - Replace a tag with another
  delete   - Delete a tag from files
  find     - Find all occurrences of a tag

Tag matching is case-insensitive but preserves original case.
Supports both [bracket tags] and #hashtags.
            """,
            "examples": [
                'mtag                               # List timeline tags (default)',
                'mtag --all                         # All file types',
                'mtag replace endfield 엔드필드      # Replace tag',
                'mtag replace "old" "new" --dry-run # Preview changes',
                'mtag delete TAG --force            # Delete tag',
                'mtag find bug                      # Find tag usage',
            ],
            "options": [
                ("(default)", "List tags with usage counts"),
                ("list", "List tags with usage counts (explicit)"),
                ("replace <old> <new>", "Replace tag with another"),
                ("delete <tag>", "Delete tag from files"),
                ("find <tag>", "Find all occurrences"),
            ],
        },
        "ko": {
            "name": "mtag / tag",
            "summary": "태그 관리 명령어",
            "description": """
.memory 파일의 태그를 관리합니다. 목록 보기, 치환,
삭제, 찾기를 지원합니다.

하위 명령어 없이 mtag만 실행하면 태그 목록을 표시합니다.

하위 명령어:
  (없음)   - 태그 목록 (list와 동일)
  list     - 태그 목록 및 사용 횟수
  replace  - 태그 치환
  delete   - 태그 삭제
  find     - 태그 사용 위치 찾기

태그 매칭은 대소문자 구분 없이 하되 원본 대소문자는 유지합니다.
[대괄호 태그]와 #해시태그를 모두 지원합니다.
            """,
            "examples": [
                'mtag                               # 타임라인 태그 (기본)',
                'mtag --all                         # 모든 파일 유형',
                'mtag replace endfield 엔드필드      # 태그 치환',
                'mtag replace "기존" "신규" --dry-run # 미리보기',
                'mtag delete TAG --force            # 태그 삭제',
                'mtag find bug                      # 태그 찾기',
            ],
            "options": [
                ("list", "태그 목록 및 사용 횟수"),
                ("replace <이전> <신규>", "태그 치환"),
                ("delete <태그>", "태그 삭제"),
                ("find <태그>", "태그 사용 위치 찾기"),
            ],
        },
    },

    "cache": {
        "en": {
            "name": "mcache / cache",
            "summary": "Manage search and Notion cache",
            "description": """
Manage search and Notion caches.

Cache locations:
  - Search: ~/.memory/.cache/search/
  - Notion: ~/.memory/.cache/notion/ (page IDs, etc.)

Default search TTL: 3600 seconds (1 hour)
            """,
            "examples": [
                'mcache                    # Show cache summary',
                'mcache --stats            # Show detailed statistics',
                'mcache --clear            # Clear search cache',
                'mcache --clear --notion   # Clear Notion cache',
                'mcache --clear --all      # Clear all caches',
                'mcache --clear-expired    # Clear only expired entries',
            ],
            "options": [
                ("--stats, -s", "Show cache statistics"),
                ("--clear, -c", "Clear cache (search by default)"),
                ("--notion, -n", "Target Notion cache"),
                ("--all, -a", "Target all caches"),
                ("--clear-expired, -e", "Clear only expired search entries"),
            ],
        },
        "ko": {
            "name": "mcache / cache",
            "summary": "검색 및 Notion 캐시 관리",
            "description": """
검색 및 Notion 캐시를 관리합니다.

캐시 위치:
  - 검색: ~/.memory/.cache/search/
  - Notion: ~/.memory/.cache/notion/ (페이지 ID 등)

검색 캐시 기본 TTL: 3600초 (1시간)
            """,
            "examples": [
                'mcache                    # 캐시 요약 표시',
                'mcache --stats            # 상세 통계 표시',
                'mcache --clear            # 검색 캐시 삭제',
                'mcache --clear --notion   # Notion 캐시 삭제',
                'mcache --clear --all      # 모든 캐시 삭제',
                'mcache --clear-expired    # 만료된 캐시만 삭제',
            ],
            "options": [
                ("--stats, -s", "캐시 통계 표시"),
                ("--clear, -c", "캐시 삭제 (기본: 검색)"),
                ("--notion, -n", "Notion 캐시 대상"),
                ("--all, -a", "모든 캐시 대상"),
                ("--clear-expired, -e", "만료된 검색 캐시만 삭제"),
            ],
        },
    },

    "ask": {
        "en": {
            "name": "mask / ask",
            "summary": "Ask questions about your memory (RAG)",
            "description": """
Uses AI to answer questions about your memory content.
The agent interprets your question, selects appropriate tools,
gathers information, and synthesizes an answer.

Available tools: get_timeline, search, get_plan, get_module, list_modules
            """,
            "examples": [
                'mask "What did I work on yesterday?"',
                'mask "What decisions were made about the database?"',
                'mask "Summarize last week\'s progress"',
                'mask "What modules are related to authentication?"',
                'mask "지난주에 무엇을 했나요?" --verbose',
            ],
            "options": [
                ("--verbose, -v", "Show agent's reasoning and tool calls"),
                ("--simple, -s", "Use simple keyword search (faster)"),
                ("--provider, -p", "LLM provider: claude-cli, gemini-cli, etc."),
            ],
        },
        "ko": {
            "name": "mask / ask (질문)",
            "summary": "메모리에 대해 AI에게 질문 (RAG)",
            "description": """
AI를 사용하여 메모리 내용에 대한 질문에 답변합니다.
에이전트가 질문을 해석하고, 적절한 도구를 선택하여
정보를 수집한 후 답변을 생성합니다.

사용 가능한 도구: get_timeline, search, get_plan, get_module, list_modules
            """,
            "examples": [
                'mask "어제 무엇을 했나요?"',
                'mask "데이터베이스 관련 결정 사항은?"',
                'mask "지난주 진행 상황 요약해줘"',
                'mask "인증 관련 모듈은 무엇이 있나요?"',
                'mask "What did I do yesterday?" --verbose',
            ],
            "options": [
                ("--verbose, -v", "에이전트의 추론 과정과 도구 호출 표시"),
                ("--simple, -s", "단순 키워드 검색 사용 (더 빠름)"),
                ("--provider, -p", "LLM 제공자: claude-cli, gemini-cli 등"),
            ],
        },
    },

    "today": {
        "en": {
            "name": "mtoday / today",
            "summary": "Show today's timeline",
            "description": "Displays all entries recorded today in chronological order.",
            "examples": [
                "mtoday                # Show today's entries",
                "mtoday --yesterday    # Show yesterday's entries",
            ],
            "options": [
                ("--yesterday", "Show yesterday instead"),
            ],
        },
        "ko": {
            "name": "mtoday / today (오늘)",
            "summary": "오늘 타임라인 보기",
            "description": "오늘 기록된 모든 항목을 시간순으로 표시합니다.",
            "examples": [
                "mtoday                # 오늘 기록 보기",
                "mtoday --yesterday    # 어제 기록 보기",
            ],
            "options": [
                ("--yesterday", "어제 기록 보기"),
            ],
        },
    },

    "plan": {
        "en": {
            "name": "mplan / plan",
            "summary": "Manage daily and weekly plans",
            "description": """
Create, view, and manage your daily and weekly plans.
Supports task tracking with checkboxes and carryover of incomplete tasks.

Smart task completion (done command):
  - Numeric index: 'done 1' completes 1st incomplete task
  - Prefix match: 'done "Wri"' matches "Write docs" if unique
  - Contains match: Fallback to substring if prefix not found
  - Shows list with indices if multiple tasks match
            """,
            "examples": [
                "mplan daily                    # Show/create today's plan",
                "mplan daily add \"Task\"         # Add task to today",
                "mplan daily done 1             # Complete 1st task by index",
                "mplan daily done \"Write\"       # Complete by prefix match",
                "mplan daily yesterday          # Show yesterday's plan",
                "mplan daily carryover          # Carry over incomplete tasks",
                "mplan weekly                   # Show/create this week's plan",
                "mplan weekly done 1            # Complete 1st goal by index",
                "mplan weekly lastweek          # Show last week's plan",
            ],
            "options": [
                ("daily", "Daily plan operations"),
                ("weekly", "Weekly plan operations"),
                ("add <task>", "Add task/goal to plan"),
                ("done <task|index>", "Mark task complete (supports index/prefix)"),
                ("carryover", "Carry over incomplete tasks"),
            ],
        },
        "ko": {
            "name": "mplan / plan",
            "summary": "일일/주간 계획 관리",
            "description": """
일일 및 주간 계획을 생성, 조회, 관리합니다.
체크박스로 작업 추적이 가능하고, 미완료 작업 이관을 지원합니다.

스마트 작업 완료 (done 명령):
  - 숫자 인덱스: 'done 1'로 첫 번째 미완료 작업 완료
  - Prefix 매칭: 'done "작"'이 "작업 완료"에 유일하게 매칭
  - Contains 매칭: Prefix 실패 시 부분 문자열 매칭
  - 다중 매칭 시 인덱스 번호 목록 표시
            """,
            "examples": [
                "mplan daily                    # 오늘 계획 보기/생성",
                "mplan daily add \"작업\"         # 오늘 계획에 작업 추가",
                "mplan daily done 1             # 인덱스로 첫 번째 작업 완료",
                "mplan daily done \"문서\"        # Prefix 매칭으로 완료",
                "mplan daily yesterday          # 어제 계획 보기",
                "mplan daily carryover          # 미완료 작업 이관",
                "mplan weekly                   # 이번 주 계획 보기/생성",
                "mplan weekly done 1            # 인덱스로 첫 번째 목표 완료",
                "mplan weekly lastweek          # 지난주 계획 보기",
            ],
            "options": [
                ("daily", "일일 계획 작업"),
                ("weekly", "주간 계획 작업"),
                ("add <task>", "작업/목표 추가"),
                ("done <task|index>", "작업 완료 (인덱스/Prefix 지원)"),
                ("carryover", "미완료 작업 이관"),
            ],
        },
    },

    "nsync": {
        "en": {
            "name": "nsync",
            "summary": "Sync with Notion",
            "description": """
Synchronize local memory content with Notion.
Supports modules, timeline, and plans synchronization.

New timeline entries are automatically inserted in time-sorted order.

Options for fixing existing out-of-order entries:
  --sort     Sort local timeline files by time
  --reorder  Reorder timeline entries within Notion daily pages
             (Note: Daily page order in months cannot be changed via API)
            """,
            "examples": [
                "nsync                     # Sync all (modules + timeline + plans)",
                "nsync --module            # Sync modules only",
                "nsync --timeline          # Sync timeline only",
                "nsync --plan              # Sync plans only",
                "nsync --push              # Push local to Notion",
                "nsync --pull              # Pull from Notion to local",
                "nsync --status            # Show sync status",
                "nsync --timeline --sort   # Sync and sort local files",
                "nsync --timeline --reorder # Reorder Notion pages by time",
            ],
            "options": [
                ("--module", "Sync modules only"),
                ("--timeline", "Sync timeline only"),
                ("--plan", "Sync plans only"),
                ("--push", "Push local changes to Notion"),
                ("--pull", "Pull changes from Notion"),
                ("--status", "Show synchronization status"),
                ("--sort", "Sort existing local timeline entries by time"),
                ("--reorder", "Reorder timeline entries in Notion daily pages"),
            ],
        },
        "ko": {
            "name": "nsync",
            "summary": "Notion과 동기화",
            "description": """
로컬 메모리 내용을 Notion과 동기화합니다.
모듈, 타임라인, 계획 동기화를 지원합니다.

신규 타임라인 항목은 자동으로 시간순으로 삽입됩니다.

기존 항목 순서 정리 옵션:
  --sort     로컬 타임라인 파일의 기존 항목 시간순 정렬
  --reorder  Notion 일별 페이지 내 타임라인 항목 재정렬
             (참고: 월별 페이지 내 일별 페이지 순서는 API로 변경 불가)
            """,
            "examples": [
                "nsync                     # 전체 동기화 (모듈 + 타임라인 + 계획)",
                "nsync --module            # 모듈만 동기화",
                "nsync --timeline          # 타임라인만 동기화",
                "nsync --plan              # 계획만 동기화",
                "nsync --push              # 로컬 -> Notion 푸시",
                "nsync --pull              # Notion -> 로컬 풀",
                "nsync --status            # 동기화 상태 확인",
                "nsync --timeline --sort   # 동기화 후 로컬 파일 정렬",
                "nsync --timeline --reorder # Notion 페이지 시간순 재정렬",
            ],
            "options": [
                ("--module", "모듈만 동기화"),
                ("--timeline", "타임라인만 동기화"),
                ("--plan", "계획만 동기화"),
                ("--push", "로컬 변경사항을 Notion에 푸시"),
                ("--pull", "Notion에서 변경사항 풀"),
                ("--status", "동기화 상태 표시"),
                ("--sort", "로컬 타임라인 기존 항목 시간순 정렬"),
                ("--reorder", "Notion 일별 페이지 내 항목 재정렬"),
            ],
        },
    },

    # ================================================================
    # Core Commands (additional)
    # ================================================================
    "init": {
        "en": {
            "name": "minit / init",
            "summary": "Initialize .memory/ structure",
            "description": """
Creates the .memory/ directory structure for a new project.
Also creates .claude/ directory for Claude Code integration.

Run this command once in your project root to start using Memory Tool.
            """,
            "examples": [
                "minit                      # Initialize in current directory",
                "minit --force              # Reinitialize (overwrites existing)",
                "minit --kb /path/to/kb     # Set knowledge base path",
                "minit --update-docs        # Update documentation templates only",
            ],
            "options": [
                ("--force, -f", "Force reinitialize (overwrites existing)"),
                ("--kb", "Path to knowledge base directory"),
                ("--update-docs", "Update documentation templates only"),
                ("--update-all", "Update all templates (creates backups)"),
            ],
        },
        "ko": {
            "name": "minit / init",
            "summary": ".memory/ 구조 초기화",
            "description": """
새 프로젝트를 위한 .memory/ 디렉토리 구조를 생성합니다.
Claude Code 연동을 위한 .claude/ 디렉토리도 생성합니다.

Memory Tool 사용을 시작하려면 프로젝트 루트에서 이 명령어를 한 번 실행하세요.
            """,
            "examples": [
                "minit                      # 현재 디렉토리에 초기화",
                "minit --force              # 재초기화 (기존 파일 덮어쓰기)",
                "minit --kb /path/to/kb     # 지식 베이스 경로 설정",
                "minit --update-docs        # 문서 템플릿만 업데이트",
            ],
            "options": [
                ("--force, -f", "강제 재초기화 (기존 파일 덮어쓰기)"),
                ("--kb", "지식 베이스 디렉토리 경로"),
                ("--update-docs", "문서 템플릿만 업데이트"),
                ("--update-all", "모든 템플릿 업데이트 (백업 생성)"),
            ],
        },
    },

    "status": {
        "en": {
            "name": "mstatus / status",
            "summary": "Show memory statistics",
            "description": """
Displays statistics about your memory content including:
- Timeline entries count and latest date
- Number of modules and concepts
- Plan progress (daily/weekly)
- Storage size
            """,
            "examples": [
                "mstatus                    # Show all statistics",
            ],
            "options": [],
        },
        "ko": {
            "name": "mstatus / status",
            "summary": "메모리 통계 보기",
            "description": """
메모리 내용에 대한 통계를 표시합니다:
- 타임라인 항목 수와 최근 날짜
- 모듈 및 개념 수
- 계획 진행 상황 (일일/주간)
- 저장소 크기
            """,
            "examples": [
                "mstatus                    # 모든 통계 보기",
            ],
            "options": [],
        },
    },

    "tutorial": {
        "en": {
            "name": "mtutorial / tutorial",
            "summary": "Interactive tutorial",
            "description": """
Step-by-step interactive tutorial to learn Memory Tool.
Covers basic commands, timeline usage, modules, and search.
            """,
            "examples": [
                "mtutorial                  # Start interactive tutorial",
                "mtutorial basics           # Show basics lesson",
                "mtutorial --list           # List all lessons",
            ],
            "options": [
                ("--list, -l", "List all available lessons"),
            ],
        },
        "ko": {
            "name": "mtutorial / tutorial",
            "summary": "대화형 튜토리얼",
            "description": """
Memory Tool을 배우기 위한 단계별 대화형 튜토리얼입니다.
기본 명령어, 타임라인 사용법, 모듈, 검색을 다룹니다.
            """,
            "examples": [
                "mtutorial                  # 대화형 튜토리얼 시작",
                "mtutorial basics           # 기초 레슨 보기",
                "mtutorial --list           # 모든 레슨 나열",
            ],
            "options": [
                ("--list, -l", "사용 가능한 모든 레슨 나열"),
            ],
        },
    },

    # ================================================================
    # Timeline (additional)
    # ================================================================
    "week": {
        "en": {
            "name": "mweek / week",
            "summary": "Show this week's timeline",
            "description": """
Displays all timeline entries from Monday to today.
Entries are grouped by date for easy scanning.
            """,
            "examples": [
                "mweek                      # Show this week's entries",
            ],
            "options": [],
        },
        "ko": {
            "name": "mweek / week (주간)",
            "summary": "이번 주 타임라인 보기",
            "description": """
월요일부터 오늘까지의 모든 타임라인 항목을 표시합니다.
날짜별로 그룹화되어 쉽게 확인할 수 있습니다.
            """,
            "examples": [
                "mweek                      # 이번 주 항목 보기",
            ],
            "options": [],
        },
    },

    "month": {
        "en": {
            "name": "mmonth / month",
            "summary": "Show this month's timeline",
            "description": """
Displays all timeline entries for the current month.
Entries are grouped by date.
            """,
            "examples": [
                "mmonth                     # Show this month's entries",
            ],
            "options": [],
        },
        "ko": {
            "name": "mmonth / month (월간)",
            "summary": "이번 달 타임라인 보기",
            "description": """
이번 달의 모든 타임라인 항목을 표시합니다.
날짜별로 그룹화됩니다.
            """,
            "examples": [
                "mmonth                     # 이번 달 항목 보기",
            ],
            "options": [],
        },
    },

    "days": {
        "en": {
            "name": "mdays / days",
            "summary": "Show last N days timeline",
            "description": """
Displays timeline entries for the last N days.
Default is 7 days if not specified.
            """,
            "examples": [
                "mdays                      # Show last 7 days",
                "mdays 3                    # Show last 3 days",
                "mdays 30                   # Show last 30 days",
            ],
            "options": [],
        },
        "ko": {
            "name": "mdays / days (일수)",
            "summary": "최근 N일 타임라인 보기",
            "description": """
최근 N일간의 타임라인 항목을 표시합니다.
지정하지 않으면 기본값은 7일입니다.
            """,
            "examples": [
                "mdays                      # 최근 7일 보기",
                "mdays 3                    # 최근 3일 보기",
                "mdays 30                   # 최근 30일 보기",
            ],
            "options": [],
        },
    },

    "day": {
        "en": {
            "name": "mday / day",
            "summary": "Show specific date's timeline",
            "description": """
Displays timeline entries for a specific date.
Supports flexible date formats:
  - YYYY-MM-DD (full date)
  - MM-DD (month-day, current year)
  - DD (day only, current month/year)
            """,
            "examples": [
                "mday 2026-01-15            # Specific date",
                "mday 01-15                 # January 15 (current year)",
                "mday 15                    # 15th of current month",
            ],
            "options": [],
        },
        "ko": {
            "name": "mday / day (날짜)",
            "summary": "특정 날짜 타임라인 보기",
            "description": """
특정 날짜의 타임라인 항목을 표시합니다.
유연한 날짜 형식 지원:
  - YYYY-MM-DD (전체 날짜)
  - MM-DD (월-일, 현재 연도)
  - DD (일만, 현재 월/연도)
            """,
            "examples": [
                "mday 2026-01-15            # 특정 날짜",
                "mday 01-15                 # 1월 15일 (현재 연도)",
                "mday 15                    # 현재 월의 15일",
            ],
            "options": [],
        },
    },

    "edit": {
        "en": {
            "name": "medit / edit",
            "summary": "Interactive timeline editor",
            "description": """
Interactive editor for editing or deleting timeline entries.
Select entries by number and modify or delete them.

Commands in editor:
  <n>      - Edit entry message
  t <n>    - Change entry time
  d <n>    - Delete entry
  s        - Save and exit
  q        - Quit without saving
  ?        - Show help
            """,
            "examples": [
                "medit                      # Edit today's timeline",
                "medit 2026-01-15           # Edit specific date",
                "medit 15                   # Edit 15th of current month",
            ],
            "options": [],
        },
        "ko": {
            "name": "medit / edit (편집)",
            "summary": "대화형 타임라인 편집기",
            "description": """
타임라인 항목을 수정하거나 삭제하는 대화형 편집기입니다.
번호로 항목을 선택하여 수정 또는 삭제할 수 있습니다.

편집기 명령어:
  <n>      - n번 항목 메시지 편집
  t <n>    - n번 항목 시간 변경
  d <n>    - n번 항목 삭제
  s        - 저장 후 종료
  q        - 저장 없이 종료
  ?        - 도움말 표시
            """,
            "examples": [
                "medit                      # 오늘 타임라인 편집",
                "medit 2026-01-15           # 특정 날짜 편집",
                "medit 15                   # 현재 월의 15일 편집",
            ],
            "options": [],
        },
    },

    "sort": {
        "en": {
            "name": "msort / sort",
            "summary": "Sort timeline entries by time",
            "description": """
Sorts timeline entries within a day by timestamp.
Useful when entries were recorded out of order.
            """,
            "examples": [
                "msort                      # Sort today's entries",
                "msort --date 2026-01-20    # Sort specific date",
                "msort --all                # Sort all timeline files",
            ],
            "options": [
                ("--date", "Specific date to sort (YYYY-MM-DD)"),
                ("--all", "Sort all timeline files"),
            ],
        },
        "ko": {
            "name": "msort / sort",
            "summary": "타임라인 시간순 정렬",
            "description": """
하루 내의 타임라인 항목을 타임스탬프 순으로 정렬합니다.
순서가 뒤바뀐 항목을 정리할 때 유용합니다.
            """,
            "examples": [
                "msort                      # 오늘 항목 정렬",
                "msort --date 2026-01-20    # 특정 날짜 정렬",
                "msort --all                # 모든 타임라인 파일 정렬",
            ],
            "options": [
                ("--date", "정렬할 특정 날짜 (YYYY-MM-DD)"),
                ("--all", "모든 타임라인 파일 정렬"),
            ],
        },
    },

    # ================================================================
    # Search (additional)
    # ================================================================
    "browse": {
        "en": {
            "name": "mbrowse / browse",
            "summary": "Interactive search browser",
            "description": """
Opens an interactive TUI (Text User Interface) for browsing
and searching your memory content.
            """,
            "examples": [
                "mbrowse                    # Open interactive browser",
            ],
            "options": [],
        },
        "ko": {
            "name": "mbrowse / browse",
            "summary": "대화형 검색 브라우저",
            "description": """
메모리 내용을 탐색하고 검색하기 위한 대화형 TUI
(텍스트 사용자 인터페이스)를 엽니다.
            """,
            "examples": [
                "mbrowse                    # 대화형 브라우저 열기",
            ],
            "options": [],
        },
    },

    "check": {
        "en": {
            "name": "mcheck / check",
            "summary": "Check wiki links and paths",
            "description": """
Validates wiki links ([[link]]) and file paths in your memory.
Reports broken links and missing files.
            """,
            "examples": [
                "mcheck                     # Check all links",
                "mcheck --module projects   # Check specific module",
            ],
            "options": [
                ("--module", "Check specific module only"),
            ],
        },
        "ko": {
            "name": "mcheck / check",
            "summary": "위키 링크 및 경로 확인",
            "description": """
메모리 내의 위키 링크 ([[link]])와 파일 경로를 검증합니다.
깨진 링크와 누락된 파일을 보고합니다.
            """,
            "examples": [
                "mcheck                     # 모든 링크 확인",
                "mcheck --module projects   # 특정 모듈만 확인",
            ],
            "options": [
                ("--module", "특정 모듈만 확인"),
            ],
        },
    },

    # ================================================================
    # Modules
    # ================================================================
    "module": {
        "en": {
            "name": "mmodule / module",
            "summary": "Manage modules",
            "description": """
Create, view, and manage knowledge modules.
Modules are the spatial organization of your knowledge.

Each module contains:
- current.md: Current state and ongoing work
- decisions.md: Important decisions and rationale
- archive/: Historical records
            """,
            "examples": [
                "mmodule list               # List all modules",
                "mmodule tree               # Tree view of modules",
                "mmodule create newproject  # Create new module",
                "mmodule graph              # Visualize connections",
            ],
            "options": [
                ("list", "List all modules"),
                ("tree", "Tree view of modules"),
                ("create", "Create new module"),
                ("graph", "Visualize connections"),
            ],
        },
        "ko": {
            "name": "mmodule / module",
            "summary": "모듈 관리",
            "description": """
지식 모듈을 생성, 조회, 관리합니다.
모듈은 지식의 공간적 조직입니다.

각 모듈에는 다음이 포함됩니다:
- current.md: 현재 상태와 진행 중인 작업
- decisions.md: 중요한 결정 사항과 근거
- archive/: 과거 기록
            """,
            "examples": [
                "mmodule list               # 모든 모듈 나열",
                "mmodule tree               # 모듈 트리 보기",
                "mmodule create newproject  # 새 모듈 생성",
                "mmodule graph              # 연결 시각화",
            ],
            "options": [
                ("list", "모든 모듈 나열"),
                ("tree", "모듈 트리 보기"),
                ("create", "새 모듈 생성"),
                ("graph", "연결 시각화"),
            ],
        },
    },

    "archive": {
        "en": {
            "name": "marchive / archive",
            "summary": "Archive old content",
            "description": """
Archive old decisions and content to keep modules clean.
Supports interactive selection of items to archive.
            """,
            "examples": [
                "marchive decisions         # Archive old decisions",
                "marchive --module myproj   # Archive specific module",
                "marchive --interactive     # Interactive selection",
                "marchive --suggest         # Show archiving suggestions",
            ],
            "options": [
                ("--module", "Target specific module"),
                ("--interactive, -i", "Interactive selection mode"),
                ("--suggest", "Show archiving suggestions"),
            ],
        },
        "ko": {
            "name": "marchive / archive",
            "summary": "오래된 콘텐츠 아카이브",
            "description": """
오래된 결정 사항과 콘텐츠를 아카이브하여 모듈을 깔끔하게 유지합니다.
아카이브할 항목의 대화형 선택을 지원합니다.
            """,
            "examples": [
                "marchive decisions         # 오래된 결정 사항 아카이브",
                "marchive --module myproj   # 특정 모듈 아카이브",
                "marchive --interactive     # 대화형 선택",
                "marchive --suggest         # 아카이브 제안 보기",
            ],
            "options": [
                ("--module", "특정 모듈 대상"),
                ("--interactive, -i", "대화형 선택 모드"),
                ("--suggest", "아카이브 제안 보기"),
            ],
        },
    },

    "context": {
        "en": {
            "name": "mcontext / context",
            "summary": "Build Claude Code context",
            "description": """
Generates .claude/memory-context.md for Claude Code integration.
Includes recent timeline, active plans, and module status.
            """,
            "examples": [
                "mcontext                   # Generate context file",
                "mcontext --days 7          # Include last 7 days",
            ],
            "options": [
                ("--days", "Number of recent days to include"),
            ],
        },
        "ko": {
            "name": "mcontext / context",
            "summary": "Claude Code 컨텍스트 생성",
            "description": """
Claude Code 연동을 위한 .claude/memory-context.md를 생성합니다.
최근 타임라인, 활성 계획, 모듈 상태가 포함됩니다.
            """,
            "examples": [
                "mcontext                   # 컨텍스트 파일 생성",
                "mcontext --days 7          # 최근 7일 포함",
            ],
            "options": [
                ("--days", "포함할 최근 일수"),
            ],
        },
    },

    "map": {
        "en": {
            "name": "mmap / map",
            "summary": "Generate code structure map",
            "description": """
Generates a map of your codebase structure.
Useful for understanding project organization.
            """,
            "examples": [
                "mmap                       # Generate code map",
                "mmap --output map.md       # Save to specific file",
            ],
            "options": [
                ("--output, -o", "Output file path"),
            ],
        },
        "ko": {
            "name": "mmap / map",
            "summary": "코드 구조 맵 생성",
            "description": """
코드베이스 구조의 맵을 생성합니다.
프로젝트 구조를 이해하는 데 유용합니다.
            """,
            "examples": [
                "mmap                       # 코드 맵 생성",
                "mmap --output map.md       # 특정 파일에 저장",
            ],
            "options": [
                ("--output, -o", "출력 파일 경로"),
            ],
        },
    },

    # ================================================================
    # Planning (additional)
    # ================================================================
    "summary": {
        "en": {
            "name": "msummary / summary",
            "summary": "Summarize timeline or module",
            "description": """
Uses LLM to generate summaries of your timeline or module content.
Supports daily, weekly, and module summaries.
            """,
            "examples": [
                "msummary                   # Summarize today",
                "msummary --week            # Summarize this week",
                "msummary --module myproj   # Summarize module",
            ],
            "options": [
                ("--week", "Summarize this week"),
                ("--module", "Summarize specific module"),
                ("--days", "Number of days to summarize"),
            ],
        },
        "ko": {
            "name": "msummary / summary",
            "summary": "타임라인 또는 모듈 요약",
            "description": """
LLM을 사용하여 타임라인이나 모듈 내용의 요약을 생성합니다.
일일, 주간, 모듈 요약을 지원합니다.
            """,
            "examples": [
                "msummary                   # 오늘 요약",
                "msummary --week            # 이번 주 요약",
                "msummary --module myproj   # 모듈 요약",
            ],
            "options": [
                ("--week", "이번 주 요약"),
                ("--module", "특정 모듈 요약"),
                ("--days", "요약할 일수"),
            ],
        },
    },

    # ================================================================
    # AI & LLM (additional)
    # ================================================================
    "providers": {
        "en": {
            "name": "mproviders / providers",
            "summary": "List LLM providers",
            "description": """
Shows available LLM providers and their status.
Checks which providers are configured and accessible.
            """,
            "examples": [
                "mproviders                 # List all providers",
            ],
            "options": [],
        },
        "ko": {
            "name": "mproviders / providers",
            "summary": "LLM 제공자 목록",
            "description": """
사용 가능한 LLM 제공자와 상태를 표시합니다.
어떤 제공자가 설정되어 있고 접근 가능한지 확인합니다.
            """,
            "examples": [
                "mproviders                 # 모든 제공자 목록",
            ],
            "options": [],
        },
    },

    # ================================================================
    # Notion (additional)
    # ================================================================
    "nm": {
        "en": {
            "name": "nm",
            "summary": "Record to Notion",
            "description": """
Records a message to Notion (similar to 'm' command but syncs to Notion).
            """,
            "examples": [
                'nm "Meeting notes"         # Record to Notion',
            ],
            "options": [],
        },
        "ko": {
            "name": "nm (노)",
            "summary": "Notion에 기록",
            "description": """
Notion에 메시지를 기록합니다 ('m' 명령어와 유사하지만 Notion에 동기화).
            """,
            "examples": [
                'nm "회의 노트"              # Notion에 기록',
            ],
            "options": [],
        },
    },

    "nadd": {
        "en": {
            "name": "nadd",
            "summary": "Add Notion page",
            "description": """
Adds a new page to Notion under specified parent.
            """,
            "examples": [
                "nadd 'Page Title'          # Add new page",
            ],
            "options": [
                ("--parent", "Parent page ID"),
            ],
        },
        "ko": {
            "name": "nadd",
            "summary": "Notion 페이지 추가",
            "description": """
지정된 상위 페이지 아래에 새 Notion 페이지를 추가합니다.
            """,
            "examples": [
                "nadd '페이지 제목'          # 새 페이지 추가",
            ],
            "options": [
                ("--parent", "상위 페이지 ID"),
            ],
        },
    },

    "ns": {
        "en": {
            "name": "ns (노올)",
            "summary": "Search Notion",
            "description": """
Searches Notion pages by title or content.
            """,
            "examples": [
                'ns "meeting"               # Search for "meeting"',
            ],
            "options": [],
        },
        "ko": {
            "name": "ns (노올)",
            "summary": "Notion 검색",
            "description": """
제목이나 내용으로 Notion 페이지를 검색합니다.
            """,
            "examples": [
                'ns "회의"                   # "회의" 검색',
            ],
            "options": [],
        },
    },

    "nt": {
        "en": {
            "name": "nt (노오)",
            "summary": "Show Notion today",
            "description": """
Shows today's entries from Notion timeline.
            """,
            "examples": [
                "nt                         # Show today's Notion entries",
            ],
            "options": [],
        },
        "ko": {
            "name": "nt (노오)",
            "summary": "Notion 오늘 보기",
            "description": """
Notion 타임라인에서 오늘 항목을 표시합니다.
            """,
            "examples": [
                "nt                         # 오늘의 Notion 항목 보기",
            ],
            "options": [],
        },
    },

    "nw": {
        "en": {
            "name": "nw (노주)",
            "summary": "Show Notion week",
            "description": """
Shows this week's entries from Notion timeline.
            """,
            "examples": [
                "nw                         # Show this week's Notion entries",
            ],
            "options": [],
        },
        "ko": {
            "name": "nw (노주)",
            "summary": "Notion 주간 보기",
            "description": """
Notion 타임라인에서 이번 주 항목을 표시합니다.
            """,
            "examples": [
                "nw                         # 이번 주 Notion 항목 보기",
            ],
            "options": [],
        },
    },

    "nsi": {
        "en": {
            "name": "nsi (노검)",
            "summary": "Search inside Notion pages",
            "description": """
Searches inside Notion page content (not just titles).
            """,
            "examples": [
                'nsi "API design"           # Search inside pages',
            ],
            "options": [],
        },
        "ko": {
            "name": "nsi (노검)",
            "summary": "Notion 페이지 내 검색",
            "description": """
Notion 페이지 내용 안에서 검색합니다 (제목뿐만 아니라).
            """,
            "examples": [
                'nsi "API 설계"             # 페이지 내부 검색',
            ],
            "options": [],
        },
    },

    "nwatch": {
        "en": {
            "name": "nwatch",
            "summary": "Watch and auto-sync with Notion (bidirectional)",
            "description": """
Watches local files for changes and automatically syncs with Notion.
Runs continuously until stopped (Ctrl+C).

Default mode: Local -> Notion (push only)
Bidirectional mode (-b): Local <-> Notion (push and pull)
  - modules: bidirectional sync
  - timeline: bidirectional sync (entries sorted by time)
  - plans: bidirectional sync

Timeline entries are automatically inserted in time-sorted order.
            """,
            "examples": [
                "nwatch                     # Watch all, Local -> Notion",
                "nwatch -b                  # Bidirectional (all)",
                "nwatch -b -i 60            # Bidirectional, poll every 60s",
                "nwatch --modules-only      # Watch modules only",
                "nwatch --timeline-only     # Watch timeline only",
                "nwatch --plans-only        # Watch plans only",
                "nwatch --dry-run           # Preview without syncing",
            ],
            "options": [
                ("--bidirectional, -b", "Enable Notion -> Local sync (polling)"),
                ("--poll-interval, -i", "Polling interval in seconds (default: 120)"),
                ("--modules-only", "Watch modules only"),
                ("--timeline-only", "Watch timeline only"),
                ("--plans-only", "Watch plans only"),
                ("--dry-run, -n", "Show what would sync without syncing"),
            ],
        },
        "ko": {
            "name": "nwatch",
            "summary": "Notion과 양방향 자동 동기화",
            "description": """
로컬 파일의 변경을 감시하고 자동으로 Notion과 동기화합니다.
중지할 때까지(Ctrl+C) 계속 실행됩니다.

기본 모드: Local -> Notion (push만)
양방향 모드 (-b): Local <-> Notion (push + pull)
  - modules: 양방향 동기화
  - timeline: 양방향 동기화 (시간순 정렬)
  - plans: 양방향 동기화

타임라인 항목은 자동으로 시간순으로 삽입됩니다.
            """,
            "examples": [
                "nwatch                     # 전체 감시, Local -> Notion",
                "nwatch -b                  # 양방향 (전체)",
                "nwatch -b -i 60            # 양방향, 60초마다 polling",
                "nwatch --modules-only      # 모듈만 감시",
                "nwatch --timeline-only     # 타임라인만 감시",
                "nwatch --plans-only        # 계획만 감시",
                "nwatch --dry-run           # 동기화 없이 미리보기",
            ],
            "options": [
                ("--bidirectional, -b", "Notion -> Local 동기화 활성화 (polling)"),
                ("--poll-interval, -i", "Polling 간격 (초, 기본값: 120)"),
                ("--modules-only", "모듈만 감시"),
                ("--timeline-only", "타임라인만 감시"),
                ("--plans-only", "계획만 감시"),
                ("--dry-run, -n", "동기화 없이 미리보기"),
            ],
        },
    },

    "np": {
        "en": {
            "name": "np (Notion Plan)",
            "summary": "Add a task to Notion plan page",
            "description": """
Adds a task (checkbox) directly to a Notion plan page.
Default is today's daily plan. Supports daily, weekly, and monthly plans.

Requires plan sync to be configured in config.yaml:
  notion.sync.plan.enabled: true
  notion.sync.plan.root_page_id: <your_page_id>
            """,
            "examples": [
                'np "Write documentation"              # Add to today\'s daily plan',
                'np "Review PR" --weekly               # Add to this week\'s weekly plan',
                'np "Complete project" --monthly       # Add to this month\'s monthly plan',
                'np "Fix bug" --date 2026-01-25        # Add to specific date',
                'np "Deploy feature" --weekly --date W05  # Add to specific week',
                'np "Task done" --done                 # Add as completed',
            ],
            "options": [
                ("--daily, -d", "Add to daily plan (default)"),
                ("--weekly, -w", "Add to weekly plan"),
                ("--monthly, -m", "Add to monthly plan"),
                ("--date", "Target date (YYYY-MM-DD, W##, or MM)"),
                ("--done, -x", "Mark task as completed"),
            ],
        },
        "ko": {
            "name": "np (노션 플랜)",
            "summary": "Notion 플랜 페이지에 작업 추가",
            "description": """
Notion 플랜 페이지에 직접 작업(체크박스)을 추가합니다.
기본값은 오늘의 일간 플랜입니다. 일간, 주간, 월간 플랜을 지원합니다.

config.yaml에 플랜 동기화가 설정되어 있어야 합니다:
  notion.sync.plan.enabled: true
  notion.sync.plan.root_page_id: <your_page_id>
            """,
            "examples": [
                'np "문서 작성"                        # 오늘 일간 플랜에 추가',
                'np "PR 검토" --weekly                 # 이번 주 주간 플랜에 추가',
                'np "프로젝트 완료" --monthly           # 이번 달 월간 플랜에 추가',
                'np "버그 수정" --date 2026-01-25      # 특정 날짜에 추가',
                'np "배포" --weekly --date W05        # 특정 주에 추가',
                'np "완료된 작업" --done               # 완료 상태로 추가',
            ],
            "options": [
                ("--daily, -d", "일간 플랜에 추가 (기본값)"),
                ("--weekly, -w", "주간 플랜에 추가"),
                ("--monthly, -m", "월간 플랜에 추가"),
                ("--date", "대상 날짜 (YYYY-MM-DD, W##, 또는 MM)"),
                ("--done, -x", "완료 상태로 추가"),
            ],
        },
    },

    # ================================================================
    # System (additional)
    # ================================================================
    "alias": {
        "en": {
            "name": "malias / alias",
            "summary": "Manage command aliases",
            "description": """
Install and manage short command aliases.
Supports batch files (Windows), PowerShell, Bash, and Zsh.
            """,
            "examples": [
                "malias list                # Show all aliases",
                "malias list --lang ko      # Show with Korean descriptions",
                "malias install             # Install batch files (Windows)",
                "malias install --powershell # Install to PowerShell",
                "malias install --bash      # Install to Bash",
            ],
            "options": [
                ("list", "Show all aliases and status"),
                ("install", "Install aliases"),
                ("uninstall", "Remove aliases"),
                ("--powershell", "Target PowerShell profile"),
                ("--bash", "Target Bash profile"),
                ("--zsh", "Target Zsh profile"),
            ],
        },
        "ko": {
            "name": "malias / alias",
            "summary": "명령어 별칭 관리",
            "description": """
짧은 명령어 별칭을 설치하고 관리합니다.
배치 파일(Windows), PowerShell, Bash, Zsh를 지원합니다.
            """,
            "examples": [
                "malias list                # 모든 별칭 보기",
                "malias list --lang ko      # 한국어 설명으로 보기",
                "malias install             # 배치 파일 설치 (Windows)",
                "malias install --powershell # PowerShell에 설치",
                "malias install --bash      # Bash에 설치",
            ],
            "options": [
                ("list", "모든 별칭과 상태 보기"),
                ("install", "별칭 설치"),
                ("uninstall", "별칭 제거"),
                ("--powershell", "PowerShell 프로필 대상"),
                ("--bash", "Bash 프로필 대상"),
                ("--zsh", "Zsh 프로필 대상"),
            ],
        },
    },

    "hooks": {
        "en": {
            "name": "mhooks / hooks",
            "summary": "Manage git hooks",
            "description": """
Install and manage git hooks for Memory Tool.
Includes document health check and graph rebuild hooks.
            """,
            "examples": [
                "mhooks list                # List installed hooks",
                "mhooks install pre-commit  # Install pre-commit hook",
                "mhooks install document-health  # Install health check",
                "mhooks uninstall pre-commit # Remove hook",
            ],
            "options": [
                ("list", "List installed hooks"),
                ("install", "Install a hook"),
                ("uninstall", "Remove a hook"),
            ],
        },
        "ko": {
            "name": "mhooks / hooks",
            "summary": "Git 훅 관리",
            "description": """
Memory Tool을 위한 git 훅을 설치하고 관리합니다.
문서 상태 확인 및 그래프 재빌드 훅이 포함됩니다.
            """,
            "examples": [
                "mhooks list                # 설치된 훅 나열",
                "mhooks install pre-commit  # pre-commit 훅 설치",
                "mhooks install document-health  # 상태 확인 훅 설치",
                "mhooks uninstall pre-commit # 훅 제거",
            ],
            "options": [
                ("list", "설치된 훅 나열"),
                ("install", "훅 설치"),
                ("uninstall", "훅 제거"),
            ],
        },
    },

    "completion": {
        "en": {
            "name": "mcompletion / completion",
            "summary": "Manage shell completions",
            "description": """
Generate and install shell completion scripts.
Supports Bash, Zsh, and PowerShell.
            """,
            "examples": [
                "mcompletion status         # Check installation status",
                "mcompletion generate bash  # Generate bash completion",
                "mcompletion install bash   # Install bash completion",
                "mcompletion uninstall bash # Remove completion",
            ],
            "options": [
                ("generate", "Generate completion script"),
                ("install", "Install completion"),
                ("uninstall", "Remove completion"),
                ("status", "Check installation status"),
            ],
        },
        "ko": {
            "name": "mcompletion / completion",
            "summary": "셸 자동완성 관리",
            "description": """
셸 자동완성 스크립트를 생성하고 설치합니다.
Bash, Zsh, PowerShell을 지원합니다.
            """,
            "examples": [
                "mcompletion status         # 설치 상태 확인",
                "mcompletion generate bash  # bash 자동완성 생성",
                "mcompletion install bash   # bash 자동완성 설치",
                "mcompletion uninstall bash # 자동완성 제거",
            ],
            "options": [
                ("generate", "자동완성 스크립트 생성"),
                ("install", "자동완성 설치"),
                ("uninstall", "자동완성 제거"),
                ("status", "설치 상태 확인"),
            ],
        },
    },

    "config": {
        "en": {
            "name": "mconfig / config",
            "summary": "Manage config.yaml settings",
            "description": """
View and modify Memory Tool configuration.
Settings include timeline, search, LLM, Notion, and help language.
            """,
            "examples": [
                "mconfig list               # Show all settings",
                "mconfig get help.language  # Get specific setting",
                "mconfig set help.language ko  # Set to Korean",
            ],
            "options": [
                ("list", "Show all settings"),
                ("get", "Get specific setting"),
                ("set", "Set a value"),
            ],
        },
        "ko": {
            "name": "mconfig / config (설정)",
            "summary": "config.yaml 설정 관리",
            "description": """
Memory Tool 설정을 확인하고 수정합니다.
타임라인, 검색, LLM, Notion, 도움말 언어 설정이 포함됩니다.
            """,
            "examples": [
                "mconfig list               # 모든 설정 보기",
                "mconfig get help.language  # 특정 설정 가져오기",
                "mconfig set help.language ko  # 한국어로 설정",
            ],
            "options": [
                ("list", "모든 설정 보기"),
                ("get", "특정 설정 가져오기"),
                ("set", "값 설정"),
            ],
        },
    },

    # ================================================================
    # Knowledge Federation
    # ================================================================
    "publish": {
        "en": {
            "name": "mpublish / publish",
            "summary": "Publish module to Knowledge Base",
            "description": """
Publishes a local module to the central Knowledge Base for cross-project sharing.

IMPORTANT: KB path must include .memory folder.
Set with: mconfig set kb.path /path/to/kb/.memory

Modules are stored at: {kb.path}/modules/Projects/{project}/{module}/
Registry key format: {project}/{module} (e.g., memory-tool/master)
            """,
            "examples": [
                "mpublish master                    # Publish master module",
                "mpublish search-system --dry-run  # Preview without publishing",
                "mpublish master --tags overview   # Publish with tags",
                "mpublish master --category Topics # Publish to Topics category",
            ],
            "options": [
                ("--dry-run, -n", "Preview without making changes"),
                ("--tags, -t", "Comma-separated tags"),
                ("--category, -c", "KB category (Projects or Topics)"),
                ("--force, -f", "Force republish even if unchanged"),
            ],
        },
        "ko": {
            "name": "mpublish / publish (발행)",
            "summary": "모듈을 Knowledge Base에 발행",
            "description": """
로컬 모듈을 중앙 Knowledge Base에 발행하여 프로젝트 간 공유합니다.

중요: KB 경로는 .memory 폴더를 포함해야 합니다.
설정: mconfig set kb.path /path/to/kb/.memory

모듈 저장 위치: {kb.path}/modules/Projects/{project}/{module}/
Registry key 형식: {project}/{module} (예: memory-tool/master)
            """,
            "examples": [
                "mpublish master                    # master 모듈 발행",
                "mpublish search-system --dry-run  # 발행 미리보기",
                "mpublish master --tags overview   # 태그와 함께 발행",
                "mpublish master --category Topics # Topics 카테고리로 발행",
            ],
            "options": [
                ("--dry-run, -n", "변경 없이 미리보기"),
                ("--tags, -t", "쉼표로 구분된 태그"),
                ("--category, -c", "KB 카테고리 (Projects 또는 Topics)"),
                ("--force, -f", "변경 없어도 강제 재발행"),
            ],
        },
    },

    "import-kb": {
        "en": {
            "name": "mimport / import-kb",
            "summary": "Import module from Knowledge Base",
            "description": """
Imports a module from the central Knowledge Base to local project.

Use --list to browse available modules.
Use --preview to view contents before importing.

KB path must include .memory folder in config.
            """,
            "examples": [
                "mimport --list                              # List KB modules",
                "mimport --list --project memory-tool       # Filter by project",
                "mimport Projects/memory-tool/master --preview  # Preview contents",
                "mimport Projects/memory-tool/master        # Import module",
                "mimport Projects/memory-tool/master --target ref/master  # Custom path",
            ],
            "options": [
                ("--list, -l", "List available KB modules"),
                ("--preview, -v", "Preview module contents"),
                ("--target, -t", "Local target path"),
                ("--category, -c", "Filter by category when listing"),
                ("--project, -p", "Filter by project when listing"),
            ],
        },
        "ko": {
            "name": "mimport / import-kb (가져오기)",
            "summary": "Knowledge Base에서 모듈 가져오기",
            "description": """
중앙 Knowledge Base에서 로컬 프로젝트로 모듈을 가져옵니다.

--list로 사용 가능한 모듈 목록 확인.
--preview로 가져오기 전 내용 미리보기.

config에서 KB 경로에 .memory 폴더가 포함되어야 합니다.
            """,
            "examples": [
                "mimport --list                              # KB 모듈 목록",
                "mimport --list --project memory-tool       # 프로젝트별 필터",
                "mimport Projects/memory-tool/master --preview  # 내용 미리보기",
                "mimport Projects/memory-tool/master        # 모듈 가져오기",
                "mimport Projects/memory-tool/master --target ref/master  # 지정 경로",
            ],
            "options": [
                ("--list, -l", "KB 모듈 목록 보기"),
                ("--preview, -v", "모듈 내용 미리보기"),
                ("--target, -t", "로컬 대상 경로"),
                ("--category, -c", "목록 필터: 카테고리별"),
                ("--project, -p", "목록 필터: 프로젝트별"),
            ],
        },
    },
}

# Command categories for listing
COMMAND_CATEGORIES = {
    "en": {
        "core": ("Core Commands", ["record", "init", "status", "tutorial"]),
        "timeline": ("Timeline", ["today", "week", "month", "days", "sort"]),
        "search": ("Search", ["search", "tag", "browse", "check", "cache"]),
        "module": ("Modules", ["module", "archive", "context", "map"]),
        "plan": ("Planning", ["plan", "summary"]),
        "llm": ("AI & LLM", ["ask", "providers"]),
        "federation": ("KB Federation", ["publish", "import-kb"]),
        "notion": ("Notion", ["nm", "nadd", "np", "ns", "nt", "nw", "nsi", "nsync", "nwatch"]),
        "system": ("System", ["alias", "config", "hooks", "completion"]),
    },
    "ko": {
        "core": ("핵심 명령어", ["record", "init", "status", "tutorial"]),
        "timeline": ("타임라인", ["today", "week", "month", "days", "sort"]),
        "search": ("검색", ["search", "tag", "browse", "check", "cache"]),
        "module": ("모듈 관리", ["module", "archive", "context", "map"]),
        "plan": ("계획", ["plan", "summary"]),
        "llm": ("AI 기능", ["ask", "providers"]),
        "federation": ("KB 연동", ["publish", "import-kb"]),
        "notion": ("노션 연동", ["nm", "nadd", "np", "ns", "nt", "nw", "nsi", "nsync", "nwatch"]),
        "system": ("시스템", ["alias", "config", "hooks", "completion"]),
    },
}


def _get_config_language() -> str:
    """Get help language from config.yaml."""
    try:
        from memory_tool.utils.config import Config
        cfg = Config()
        return cfg.get("help.language", "en")
    except Exception:
        return "en"


def _set_config_language(lang: str) -> bool:
    """Set help language in config.yaml permanently."""
    import yaml
    from pathlib import Path

    try:
        memory_path = Path.cwd() / ".memory"
        config_path = memory_path / "config.yaml"

        if not memory_path.exists():
            return False

        # Load existing config
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f) or {}
        else:
            config_data = {}

        # Set help.language
        if "help" not in config_data:
            config_data["help"] = {}
        config_data["help"]["language"] = lang

        # Write back
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)

        return True
    except Exception:
        return False


@app.command(name="help")
def show_help(
    command: Optional[str] = typer.Argument(None, help="Command name to get help for"),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Language for this invocation: en, ko"),
    set_lang: Optional[str] = typer.Option(None, "--set-lang", help="Permanently set default language: en, ko"),
    list_all: bool = typer.Option(False, "--list", help="List all commands"),
    guide: bool = typer.Option(False, "--guide", help="Show advanced features guide"),
):
    """Show detailed help for commands (mhelp).

    Language defaults to help.language setting in config.yaml.

    Examples:
        mhelp                       # Show command list
        mhelp record                # Help for record command
        mhelp search --lang ko      # Help in Korean (this time only)
        mhelp --set-lang ko         # Permanently set language to Korean
        mhelp --list                # List all commands
        mhelp --guide               # Show advanced features guide
    """
    # Use config language as default if not specified
    if lang is None:
        lang = _get_config_language()
    lang = lang.lower()
    if lang not in ("en", "ko"):
        lang = "en"

    # Handle permanent language change
    if set_lang:
        set_lang = set_lang.lower()
        if set_lang not in ("en", "ko"):
            console.print(f"[red]ERROR[/red] Invalid language: {set_lang}")
            console.print("[dim]Valid options: en, ko[/dim]")
            return

        if _set_config_language(set_lang):
            lang_name = "Korean" if set_lang == "ko" else "English"
            console.print(f"[green]OK[/green] Help language set to {lang_name} ({set_lang})")
            console.print("[dim]This affects mhelp and --help output[/dim]")
        else:
            console.print("[red]ERROR[/red] Failed to update config.yaml")
            console.print("[dim]Make sure .memory/ exists (run minit)[/dim]")
        return

    # Handle guide option
    if guide:
        _show_advanced_guide(lang)
        return

    if list_all or command is None:
        _show_command_list(lang)
    else:
        _show_command_help(command, lang)


def _show_command_list(lang: str):
    """Show list of all commands."""
    if lang == "ko":
        console.print("[bold cyan]Memory Tool 명령어 목록[/bold cyan]\n")
        console.print("상세 도움말: mhelp <명령어> --lang ko\n")
    else:
        console.print("[bold cyan]Memory Tool Commands[/bold cyan]\n")
        console.print("Detailed help: mhelp <command>\n")

    categories = COMMAND_CATEGORIES.get(lang, COMMAND_CATEGORIES["en"])

    for cat_key, (cat_name, commands) in categories.items():
        console.print(f"[bold yellow]{cat_name}[/bold yellow]")

        for cmd in commands:
            if cmd in HELP_CONTENT:
                help_data = HELP_CONTENT[cmd].get(lang, HELP_CONTENT[cmd]["en"])
                console.print(f"  {help_data['name']:20} {help_data['summary']}")
            else:
                console.print(f"  {cmd:20} (no detailed help)")

        console.print("")


def _show_advanced_guide(lang: str):
    """Show advanced features guide."""
    from rich.panel import Panel
    from rich.table import Table
    from rich import box

    if lang == "ko":
        _show_advanced_guide_ko()
    else:
        _show_advanced_guide_en()


def _show_advanced_guide_en():
    """Show advanced guide in English."""
    from rich.panel import Panel
    from rich.table import Table
    from rich import box

    console.print()
    console.print("[bold cyan]Memory Tool - Advanced Features Guide[/bold cyan]\n")

    # 1. Tags
    console.print(Panel(
        """[bold]Tags[/bold] allow categorization and filtering of timeline entries.

[bold]Usage:[/bold]
  m "Fixed login bug" --tags bug,auth,urgent
  m "Meeting notes" --tags meeting,team
  ms "bug" --tag auth         # Search with tag filter

[bold]Tag Best Practices:[/bold]
  - Use lowercase, hyphen-separated: [green]feature-request[/green], [green]bug-fix[/green]
  - Keep tags consistent across entries
  - Limit to 3-5 tags per entry for clarity""",
        title="[bold yellow]1. Tags & Categorization[/bold yellow]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    # 2. Wiki Links
    console.print(Panel(
        """[bold]Wiki Links[/bold] connect knowledge across modules using \\[\\[double brackets]].

[bold]Usage in module files:[/bold]
  See \\[\\[auth-system]] for authentication details.
  Related to \\[\\[projects/website]] and \\[\\[core/database]].

[bold]Link Resolution:[/bold]
  - \\[\\[module-name]] -> Searches all modules for match
  - \\[\\[path/to/module]] -> Direct path lookup
  - mcheck -> Validates all wiki links

[bold]Create bidirectional connections:[/bold]
  In auth-system/current.md: "Used by \\[\\[user-service]]"
  In user-service/current.md: "Depends on \\[\\[auth-system]]" """,
        title="[bold yellow]2. Wiki Links & Cross-References[/bold yellow]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    # 3. Semantic Search
    console.print(Panel(
        """[bold]Semantic Search[/bold] finds content by meaning, not just keywords.

[bold]Modes:[/bold]
  ms "authentication" --hybrid     # Best: keyword + semantic
  ms "how users log in" --semantic # Pure semantic search
  ms "login bug" --boost-recent    # Prioritize recent content

[bold]When to use:[/bold]
  -[cyan]Keyword[/cyan]: Exact terms, file names, identifiers
  -[cyan]Semantic[/cyan]: Concepts, questions, descriptions
  -[cyan]Hybrid[/cyan]: General search (recommended default)

[bold]Requires:[/bold]
  LLM provider with embedding support (Ollama, OpenAI, etc.)
  Configure in .memory/config.yaml under llm section""",
        title="[bold yellow]3. Semantic Search[/bold yellow]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    # 4. Module Structure
    console.print(Panel(
        """[bold]Module Structure[/bold] organizes knowledge spatially.

[bold]Standard Module Files:[/bold]
  module-name/
  ├── module.md       # Metadata: name, description, tags
  ├── current.md      # Current state, ongoing work
  ├── decisions.md    # Important decisions & rationale
  └── archive/        # Historical records

[bold]Best Practices:[/bold]
  -Keep current.md focused on active work
  -Move completed items to decisions.md or archive/
  -Use marchive --suggest to find archivable content

[bold]Commands:[/bold]
  mmodule create my-project --tags dev,web
  mmodule show my-project
  marchive --module my-project --interactive""",
        title="[bold yellow]4. Module Organization[/bold yellow]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    # 5. Config.yaml
    console.print(Panel(
        """[bold]config.yaml[/bold] controls Memory Tool behavior.

[bold]Key Settings:[/bold]
  help.language: ko              # Help language (en/ko)
  llm.provider: ollama           # LLM provider
  llm.ollama_model: qwen3-vl:8b  # Model for mask command
  search.default_scope: local    # Search scope
  timeline.granularity: medium   # Recording detail level

[bold]Notion Sync:[/bold]
  notion.api_key: secret_xxx
  notion.sync.enabled: true
  notion.sync.timeline.bidirectional: true

[bold]Commands:[/bold]
  mconfig list                   # Show all settings
  mconfig get llm.provider       # Get specific value
  mconfig set help.language ko   # Change setting""",
        title="[bold yellow]5. Configuration (config.yaml)[/bold yellow]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    # 6. AI/LLM Integration
    console.print(Panel(
        """[bold]AI Integration[/bold] provides intelligent features.

[bold]mask (Ask Command):[/bold]
  mask "What did I work on yesterday?"
  mask "Summarize decisions about the database"
  mask --verbose "List all auth-related modules"

[bold]msummary (Summarization):[/bold]
  msummary                    # Summarize today
  msummary --week             # Weekly summary
  msummary --module auth      # Module summary

[bold]LLM Providers:[/bold]
  -claude-cli: Uses Claude CLI
  -ollama: Local LLM (default)
  -gemini-cli: Google Gemini

Configure with: mconfig set llm.provider ollama""",
        title="[bold yellow]6. AI & LLM Features[/bold yellow]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    console.print()
    console.print("[dim]Run 'mhelp <command>' for specific command help[/dim]")
    console.print("[dim]Run 'mhelp --list' for all commands[/dim]\n")


def _show_advanced_guide_ko():
    """Show advanced guide in Korean."""
    from rich.panel import Panel
    from rich.table import Table
    from rich import box

    console.print()
    console.print("[bold cyan]Memory Tool - 고급 기능 가이드[/bold cyan]\n")

    # 1. Tags
    console.print(Panel(
        """[bold]태그[/bold]를 사용하여 타임라인 항목을 분류하고 필터링할 수 있습니다.

[bold]사용법:[/bold]
  m "로그인 버그 수정" --tags bug,auth,urgent
  m "회의 노트" --tags meeting,team
  ms "버그" --tag auth         # 태그로 필터링하여 검색

[bold]태그 작성 팁:[/bold]
  -소문자, 하이픈 구분 사용: [green]feature-request[/green], [green]bug-fix[/green]
  -항목 전체에서 일관된 태그 사용
  -명확성을 위해 항목당 3-5개 태그로 제한""",
        title="[bold yellow]1. 태그 & 분류[/bold yellow]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    # 2. Wiki Links
    console.print(Panel(
        """[bold]위키 링크[/bold]로 \\[\\[이중 괄호]]를 사용해 모듈 간 지식을 연결합니다.

[bold]모듈 파일에서 사용:[/bold]
  인증 상세 내용은 \\[\\[auth-system]] 참조.
  \\[\\[projects/website]] 및 \\[\\[core/database]]와 관련됨.

[bold]링크 해석:[/bold]
  - \\[\\[module-name]] -> 모든 모듈에서 매칭 검색
  - \\[\\[path/to/module]] -> 직접 경로 조회
  - mcheck -> 모든 위키 링크 검증

[bold]양방향 연결 생성:[/bold]
  auth-system/current.md: "\\[\\[user-service]]에서 사용됨"
  user-service/current.md: "\\[\\[auth-system]]에 의존" """,
        title="[bold yellow]2. 위키 링크 & 상호 참조[/bold yellow]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    # 3. Semantic Search
    console.print(Panel(
        """[bold]시맨틱 검색[/bold]은 키워드가 아닌 의미로 콘텐츠를 찾습니다.

[bold]모드:[/bold]
  ms "인증" --hybrid           # 최적: 키워드 + 시맨틱
  ms "사용자가 로그인하는 방법" --semantic  # 순수 시맨틱
  ms "로그인 버그" --boost-recent  # 최근 콘텐츠 우선

[bold]사용 시점:[/bold]
  -[cyan]키워드[/cyan]: 정확한 용어, 파일명, 식별자
  -[cyan]시맨틱[/cyan]: 개념, 질문, 설명
  -[cyan]하이브리드[/cyan]: 일반 검색 (권장 기본값)

[bold]요구사항:[/bold]
  임베딩 지원 LLM 제공자 (Ollama, OpenAI 등)
  .memory/config.yaml의 llm 섹션에서 설정""",
        title="[bold yellow]3. 시맨틱 검색[/bold yellow]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    # 4. Module Structure
    console.print(Panel(
        """[bold]모듈 구조[/bold]로 지식을 공간적으로 조직합니다.

[bold]표준 모듈 파일:[/bold]
  module-name/
  ├── module.md       # 메타데이터: 이름, 설명, 태그
  ├── current.md      # 현재 상태, 진행 중인 작업
  ├── decisions.md    # 중요 결정사항 & 근거
  └── archive/        # 과거 기록

[bold]모범 사례:[/bold]
  -current.md는 활성 작업에 집중
  -완료된 항목은 decisions.md 또는 archive/로 이동
  -marchive --suggest로 아카이브 가능한 콘텐츠 찾기

[bold]명령어:[/bold]
  mmodule create my-project --tags dev,web
  mmodule show my-project
  marchive --module my-project --interactive""",
        title="[bold yellow]4. 모듈 조직[/bold yellow]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    # 5. Config.yaml
    console.print(Panel(
        """[bold]config.yaml[/bold]로 Memory Tool 동작을 제어합니다.

[bold]주요 설정:[/bold]
  help.language: ko              # 도움말 언어 (en/ko)
  llm.provider: ollama           # LLM 제공자
  llm.ollama_model: qwen3-vl:8b  # mask 명령용 모델
  search.default_scope: local    # 검색 범위
  timeline.granularity: medium   # 기록 상세 수준

[bold]Notion 동기화:[/bold]
  notion.api_key: secret_xxx
  notion.sync.enabled: true
  notion.sync.timeline.bidirectional: true

[bold]명령어:[/bold]
  mconfig list                   # 모든 설정 표시
  mconfig get llm.provider       # 특정 값 조회
  mconfig set help.language ko   # 설정 변경""",
        title="[bold yellow]5. 설정 (config.yaml)[/bold yellow]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    # 6. AI/LLM Integration
    console.print(Panel(
        """[bold]AI 통합[/bold]으로 지능형 기능을 제공합니다.

[bold]mask (질문 명령):[/bold]
  mask "어제 무엇을 했나요?"
  mask "데이터베이스 관련 결정 요약해줘"
  mask --verbose "인증 관련 모듈 모두 나열해줘"

[bold]msummary (요약):[/bold]
  msummary                    # 오늘 요약
  msummary --week             # 주간 요약
  msummary --module auth      # 모듈 요약

[bold]LLM 제공자:[/bold]
  -claude-cli: Claude CLI 사용
  -ollama: 로컬 LLM (기본값)
  -gemini-cli: Google Gemini

설정: mconfig set llm.provider ollama""",
        title="[bold yellow]6. AI & LLM 기능[/bold yellow]",
        border_style="cyan",
        box=box.ROUNDED
    ))

    console.print()
    console.print("[dim]특정 명령어 도움말: mhelp <명령어>[/dim]")
    console.print("[dim]모든 명령어 목록: mhelp --list[/dim]\n")


def _show_command_help(command: str, lang: str):
    """Show detailed help for a specific command."""
    # Normalize command name
    cmd_map = {
        "m": "record", "기": "record",
        "ms": "search", "검": "search",
        "mask": "ask", "질문": "ask",
        "mtoday": "today", "오늘": "today",
        "mday": "day", "날짜": "day",
        "medit": "edit",
        "mplan": "plan",
        "mtag": "tag",
        "mcache": "cache",
    }
    cmd = cmd_map.get(command, command)

    if cmd not in HELP_CONTENT:
        if lang == "ko":
            console.print(f"[yellow]'{command}' 명령어에 대한 상세 도움말이 없습니다.[/yellow]")
            console.print(f"[dim]기본 도움말: {command} --help[/dim]")
        else:
            console.print(f"[yellow]No detailed help for '{command}'.[/yellow]")
            console.print(f"[dim]Try: {command} --help[/dim]")
        return

    help_data = HELP_CONTENT[cmd].get(lang, HELP_CONTENT[cmd]["en"])

    # Header
    console.print(f"[bold cyan]{help_data['name']}[/bold cyan]")
    console.print(f"[dim]{help_data['summary']}[/dim]\n")

    # Description
    if lang == "ko":
        console.print("[bold]설명:[/bold]")
    else:
        console.print("[bold]Description:[/bold]")
    console.print(help_data['description'].strip())
    console.print("")

    # Examples
    if lang == "ko":
        console.print("[bold]예시:[/bold]")
    else:
        console.print("[bold]Examples:[/bold]")
    for example in help_data.get('examples', []):
        console.print(f"  [green]{example}[/green]")
    console.print("")

    # Options
    if help_data.get('options'):
        if lang == "ko":
            console.print("[bold]옵션:[/bold]")
        else:
            console.print("[bold]Options:[/bold]")
        for opt_name, opt_desc in help_data['options']:
            console.print(f"  [cyan]{opt_name:20}[/cyan] {opt_desc}")
