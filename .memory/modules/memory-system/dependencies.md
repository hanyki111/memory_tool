# Dependencies

## Code Dependencies

### Phase 1 (MVP)
**Core:**
- `typer[all]>=0.9.0` - CLI 프레임워크
- `pyyaml>=6.0` - YAML frontmatter 파싱
- `python-dateutil>=2.8.2` - 날짜/시간 처리

**Optional:**
- `rich>=13.0.0` - 터미널 출력 포매팅 (typer[all]에 포함)
- `shellingham>=1.5.0` - Shell 감지 (typer[all]에 포함)

### Phase 2 (하드닝)
- `sqlite3` - 표준 라이브러리 (인덱싱)
- `watchdog>=3.0.0` - 파일 변경 감지 (선택)

### Phase 3 (지능화)
- `chromadb>=0.4.0` OR `faiss-cpu>=1.7.4` - 벡터 검색
- `openai>=1.0.0` OR `anthropic>=0.7.0` - 자동 요약 (선택)

## System Dependencies

### Required
- Python 3.10 이상
- PowerShell 5.1+ (Windows)
- Git (선택, 버전 관리 시)

### Optional
- ripgrep (rg) - 빠른 검색 (없으면 Python regex)
- Claude Code - 컨텍스트 자동 로딩

## Module Dependencies

### Depends On
없음 (독립 실행형 도구)

### Used By
- Claude Code (`.memory/` 파일 읽기)
- 사용자의 다른 프로젝트 (각 프로젝트에 `.memory/` 생성)

## External Services
없음 (완전 로컬, Phase 1-2)

Phase 3에서 선택적:
- OpenAI API (자동 요약)
- Anthropic API (자동 요약)

## Environment Variables

### Optional
```bash
# 개인 KB 위치 (기본: ~/memory/personal)
MEMORY_KB_ROOT=~/my-knowledge-base

# 검색 도구 (기본: 자동 감지)
MEMORY_SEARCH_TOOL=ripgrep  # or python

# 디버그 모드
MEMORY_DEBUG=1
```

## File System Requirements
- 읽기/쓰기 권한: 프로젝트 디렉토리
- 읽기 권한: KB 디렉토리 (설정 시)
- 최소 디스크 공간: 10MB (Timeline 1년분 기준)
