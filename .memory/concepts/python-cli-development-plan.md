---
type: concept
domain: development
tags: [python, cli, architecture, roadmap]
created: 2025-11-13
timeline_refs:
  - [[time:2025-11/13#23:20]]
---

# Python CLI Development Plan

## 프로젝트 구조

```
memory_tool/
  README.md
  pyproject.toml           # Poetry 또는 setuptools
  setup.py                 # 설치 스크립트

  memory_tool/             # 메인 패키지
    __init__.py
    __main__.py            # python -m memory_tool 진입점
    cli.py                 # Typer CLI 정의

    core/                  # 핵심 로직
      __init__.py
      timeline.py          # Timeline 관리
      module.py            # Module 관리
      concept.py           # Concept 관리
      memory.py            # Memory 클래스 (통합)

    context/               # Claude 통합
      __init__.py
      builder.py           # 컨텍스트 빌더
      formatter.py         # 마크다운 포매터

    search/                # 검색
      __init__.py
      searcher.py          # 검색 엔진

    utils/                 # 유틸리티
      __init__.py
      fs.py                # 파일 시스템
      time.py              # 시간 처리
      yaml.py              # YAML 파싱

  tests/                   # 테스트
    __init__.py
    test_timeline.py
    test_search.py
    test_context.py

  .memory/                 # 이 프로젝트 자체의 메모리
    timeline/
    modules/
    concepts/
```

## Phase 1 개발 순서 (Week 1-2)

### Day 1-3: 프로젝트 설정 ✅
- [x] pyproject.toml 작성
- [x] 기본 패키지 구조 생성
- [x] typer + rich 설치
- [x] CLI 프레임워크 구축

### Day 4-6: minit 명령어 ✅
- [x] core/init.py: MemoryInitializer 클래스
- [x] 디렉토리 생성 로직
- [x] config.yaml 생성
- [x] README.md 생성
- [x] kb.lock 지원
- [x] cli.py: minit 명령어 추가

### Day 7-8: m 명령어 (Timeline 기록) ✅
- [x] core/timeline.py: Timeline 클래스
- [x] 시간 파싱 및 검증
- [x] 미래 차단, 과거 경고
- [x] cli.py: m 명령어 추가
- [x] 전체 시나리오 테스트

### Day 9: ms 명령어 (검색) ✅
- [x] core/search.py: MemorySearcher 클래스
- [x] 파일 기반 recursive 검색
- [x] regex 패턴 지원
- [x] 스코프 처리 (local/kb/all)
- [x] context 표시 및 옵션
- [x] Windows 이모지 처리

### Day 10: mcontext (핵심!) ✅
- [x] context/builder.py: ContextBuilder 클래스
- [x] Timeline 최근 N일 링크
- [x] 모듈 current.md 수집
- [x] .claude/memory-context.md 생성
- [x] config.yaml 연동
- [x] cli.py: mcontext 명령어

### Phase 1 Extended: malias ✅
- [x] utils/alias.py: AliasManager 클래스
- [x] 배치 파일 생성 (Windows)
- [x] PowerShell 프로필 지원 ⭐
- [x] install/uninstall/list 명령어
- [x] PATH 안내 및 확인

### Phase 1 Bonus: 추가 명령어 ✅
- [x] mtoday: 오늘 timeline 표시
- [x] mweek: 이번 주 timeline 표시
- [x] mstatus: 프로젝트 통계
- [x] Timeline.get_today(), get_week()
- [x] 통계 수집 로직
- [ ] 테스트 작성

### Day 13-14: 통합 및 문서화
- [ ] README.md 작성
- [ ] 설치 가이드
- [ ] 사용 예시
- [ ] PowerShell 래퍼 작성
- [ ] Claude Code 통합 가이드

## 핵심 클래스 설계

### Memory 클래스
```python
class Memory:
    """메인 인터페이스"""

    def __init__(self, root: Path | None = None):
        """
        root이 None이면 현재 디렉토리에서 .memory/ 찾기
        """
        self.root = root or self._find_memory_root()
        self.timeline = Timeline(self.root / "timeline")
        self.modules = ModuleManager(self.root / "modules")
        self.concepts = ConceptManager(self.root / "concepts")

    def record(self, message: str) -> None:
        """Timeline에 기록"""

    def search(self, query: str, scope: str = "local") -> SearchResults:
        """검색"""

    def build_context(self, days: int = 7) -> Context:
        """컨텍스트 빌드"""
```

### Timeline 클래스
```python
class Timeline:
    """Timeline 관리"""

    def __init__(self, root: Path):
        self.root = root

    def append(self, message: str, timestamp: datetime | None = None) -> Path:
        """
        오늘 파일에 추가
        Returns: 파일 경로
        """

    def get_recent(self, days: int = 7) -> list[TimelineEntry]:
        """최근 N일 엔트리 반환"""

    def get_date(self, date: datetime) -> list[TimelineEntry]:
        """특정 날짜 엔트리"""
```

### ContextBuilder 클래스
```python
class ContextBuilder:
    """Claude용 컨텍스트 빌더"""

    def __init__(self, memory: Memory):
        self.memory = memory

    def build(
        self,
        days: int = 7,
        include_modules: bool = True,
        include_concepts: bool = True,
    ) -> Context:
        """컨텍스트 빌드"""

    def to_markdown(self, context: Context) -> str:
        """마크다운 변환"""
```

### Searcher 클래스
```python
class Searcher:
    """검색 엔진"""

    def __init__(self, memory: Memory, kb_root: Path | None = None):
        self.memory = memory
        self.kb_root = kb_root

    def search(
        self,
        query: str,
        scope: Literal["local", "kb", "all"] = "local",
    ) -> SearchResults:
        """검색 실행"""

    def _use_ripgrep(self) -> bool:
        """ripgrep 사용 가능 여부"""
```

## 테스트 전략

### Unit Tests
```python
def test_timeline_append():
    """Timeline 추가 테스트"""

def test_search_local():
    """로컬 검색 테스트"""

def test_context_build():
    """컨텍스트 빌드 테스트"""
```

### Integration Tests
```python
def test_full_workflow():
    """전체 워크플로우: minit → m → ms → mcontext"""
```

### Fixture
```python
@pytest.fixture
def temp_memory(tmp_path):
    """임시 .memory/ 생성"""
    memory_root = tmp_path / ".memory"
    # 구조 생성
    return Memory(memory_root)
```

## 설치 및 배포

### Development
```bash
# Poetry 사용
poetry install

# 개발 모드
pip install -e .

# 실행
python -m memory_tool m "테스트"
memory m "테스트"  # alias
```

### PowerShell Integration
```powershell
# Microsoft.PowerShell_profile.ps1

function m {
    param([string]$message)
    python -m memory_tool record $message
}

function ms {
    param(
        [string]$query,
        [switch]$WithKB,
        [switch]$All
    )
    $scope = if ($All) { "all" } elseif ($WithKB) { "kb" } else { "local" }
    python -m memory_tool search $query --scope $scope
}

function minit {
    python -m memory_tool init
}

function mcontext {
    python -m memory_tool context
}

function mstatus {
    python -m memory_tool status
}

function mtoday {
    python -m memory_tool today
}

function mweek {
    python -m memory_tool week
}
```

### Production (나중에)
```bash
# PyPI 배포
poetry build
poetry publish

# 설치
pip install memory-tool
```

## 성능 고려사항

### Phase 1 (충분)
- 파일 수: ~100개 (3개월 Timeline)
- 검색 시간: <1초 (ripgrep)
- 컨텍스트 빌드: <500ms

### Phase 2 (최적화 필요 시점)
- 파일 수: >1000개 (2년+)
- 검색 시간: >2초
- → SQLite 인덱싱 도입

## 에러 처리

```python
class MemoryError(Exception):
    """Base exception"""

class MemoryNotFoundError(MemoryError):
    """`.memory/` not found"""

class MemoryAlreadyExistsError(MemoryError):
    """Already initialized"""
```

## Logging

```python
import logging

logger = logging.getLogger("memory_tool")

# DEBUG 모드
if os.getenv("MEMORY_DEBUG"):
    logger.setLevel(logging.DEBUG)
```

## Phase 1 완료 현황 ✅

**2025-11-14 완료:**
- ✅ 8개 명령어 작동: m, minit, ms, mcontext, malias, mtoday, mweek, mstatus
- ✅ PowerShell 프로필 완벽 지원
- ✅ 템플릿 시스템 (CLAUDE.md.template)
- ✅ Windows 이모지 처리
- ✅ 18개 주요 결정 문서화
- ✅ Full dogfooding (프로젝트 자체를 .memory/로 기록)

**성과:**
- 0.5초 포착 달성 (malias 덕분)
- Claude Code 통합 준비 완료
- 모든 Windows 터미널 지원

---

## Phase 2 계획 (Next)

### 1. config.yaml 고급 기능
- [ ] auto_record: m 실행 시 자동 기록
- [ ] auto_update: timeline 기록 시 mcontext 자동 실행
- [ ] granularity 설정 (low/medium/high)
- [ ] 검색 필터 및 제외 패턴
- [ ] 설정 검증 및 마이그레이션

### 2. Claude Skill / MCP 통합 ⭐
- [ ] MCP 서버 아키텍처 연구
- [ ] Claude가 직접 m, ms, mcontext 호출
- [ ] 규칙 기반 자동화 (대화 중 자동 기록)
- [ ] 자연어 → 명령어 변환
- [ ] memory-tool MCP 서버 구현

### 3. 추가 도구
- [ ] msort: Timeline 시간순 재정렬
- [ ] mmodule: 모듈 관리 (create, update, archive)
- [ ] 고급 검색 (날짜 범위, 필터, 정렬)
- [ ] mweekly: 주간 요약 (Phase 2+)

### 4. 최적화 (필요 시)
- [ ] SQLite 인덱싱 (파일 수 > 1000)
- [ ] 검색 성능 개선
- [ ] 캐싱 전략

### 5. 테스트 및 문서화
- [ ] pytest 테스트 스위트
- [ ] 통합 테스트
- [ ] 사용자 가이드
- [ ] API 문서

---

## Next Steps

**Immediate:**
1. Phase 2 계획 세부화
2. MCP 서버 프로토타입 (우선순위)
3. config.yaml 고급 기능

**Later:**
1. 실사용 피드백 수집
2. 성능 측정 및 최적화
3. PyPI 배포 준비
