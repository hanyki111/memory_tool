---
type: module
created: 2025-11-13
status: active
---

# Memory System Module

## Purpose
Claude Code와 통합하여 작업 히스토리와 지식을 기록/관리하는 시스템

## Scope
- Timeline 기록 (시간축): 0.5초 포착
- Modules 관리 (공간축): 구조화된 컨텍스트
- Concepts 정리: 재사용 가능한 지식
- 검색: 로컬/KB/전체 범위
- Claude Code 컨텍스트 빌더

## Out of Scope
- 웹 UI (Phase 1에서는 CLI만)
- 실시간 동기화 (로컬 파일 기반)
- 다중 사용자 (단일 사용자 우선)

## Architecture
- **Python CLI**: typer 기반 명령어
- **파일 기반**: 마크다운 + YAML frontmatter
- **검색**: Phase 1 regex → Phase 2 SQLite → Phase 3 벡터
- **통합**: Claude Code Read 도구로 직접 읽기

## Tech Stack
- Python 3.10+
- typer (CLI 프레임워크)
- pathlib (파일 처리)
- PyYAML (메타데이터)
- 선택: SQLite (Phase 2), ChromaDB/FAISS (Phase 3)

## Related Modules
- [[modules/cli]] (명령어 인터페이스)
- [[modules/core]] (핵심 로직)
- [[modules/context]] (Claude 통합)
- [[modules/search]] (검색 기능)

## Philosophy
시간-공간-통합-지식-체계-v2.0.md의 5대 원칙:
1. Time First: 먼저 포착, 나중 정리
2. Lossless: 모든 것 기록, 아무것도 잃지 않음
3. Minimal Friction: 입력 최소, 정리 나중
4. Loose Coupling: 프로젝트 격리, 지식 공유
5. Local First: 기본 로컬, 확장 명시적
