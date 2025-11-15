# External Release Plan

> Complete preparation for external users and PyPI deployment

**Created:** 2025-11-15
**Status:** In Progress
**Target:** v1.0.0 Release

---

## Goals

1. **배포 준비** - PyPI에 배포 가능한 패키지 준비
2. **사용자 문서화** - 외부 사용자가 쉽게 시작할 수 있는 문서
3. **설계 문서 동기화** - 실제 구현과 설계 문서 일치

---

## Phase 1: PyPI 배포 준비 (2-3시간)

### 1.1 pyproject.toml 개선

**현재 상태:**
```toml
version = "0.1.0"
# URLs 없음
# 일부 classifiers 부족
```

**필요 작업:**
- [ ] 버전을 1.0.0으로 업그레이드
- [ ] project.urls 추가 (GitHub, Issues, Documentation)
- [ ] classifiers 추가 (Topic 등)
- [ ] long_description_content_type 명시

### 1.2 추가 파일 생성

**필요 파일:**
- [ ] `LICENSE` - MIT License 전체 텍스트
- [ ] `MANIFEST.in` - Non-Python 파일 포함
- [ ] `CHANGELOG.md` - 버전별 변경 이력
- [ ] `.pypirc` template (optional, for maintainers)

### 1.3 배포 스크립트

**필요 스크립트:**
```bash
# scripts/build.sh
# scripts/publish.sh
```

---

## Phase 2: 설치 및 빠른 시작 문서 (2-3시간)

### 2.1 INSTALLATION.md

**내용:**
1. **시스템 요구사항**
   - Python 3.10+
   - OS: Windows, macOS, Linux

2. **설치 방법**
   - PyPI: `pip install memory-tool`
   - From source: `git clone && pip install -e .`

3. **선택적 의존성**
   - Vector search: `pip install memory-tool[vector]`
   - LLM features: `pip install memory-tool[llm]`
   - TUI browser: `pip install memory-tool[tui]`
   - Shell completion: `pip install memory-tool[completion]`
   - All features: `pip install memory-tool[all]`

4. **초기 설정**
   - `minit` 명령어
   - `.memory/` 구조 설명
   - config.yaml 설정

5. **별칭 설치** (선택)
   - `malias install`
   - PowerShell 프로필 통합

### 2.2 QUICKSTART.md

**내용:**
1. **5분 시작 가이드**
   ```bash
   # 1. 설치
   pip install memory-tool

   # 2. 초기화
   minit

   # 3. 첫 기록
   m "프로젝트 시작!"

   # 4. 검색
   ms "프로젝트"

   # 5. 오늘 타임라인 보기
   mtoday
   ```

2. **핵심 개념 (3분 이해)**
   - Timeline: 시간축 (0.5초 포착)
   - Modules: 공간축 (구조화)
   - Search: 찾기
   - Context: Claude Code 통합

3. **다음 단계**
   - USER_GUIDE.md 링크
   - Tutorial 실행: `mtutorial`

---

## Phase 3: 사용자 가이드 (4-6시간)

### 3.1 USER_GUIDE.md

**구조:**

#### Part 1: Core Concepts (개념 이해)
1. **시간-공간 통합 지식 체계란?**
   - 문제: 지식 관리의 어려움
   - 해결: Time + Space 통합
   - 철학: 5 Core Principles

2. **Timeline System (시간축)**
   - 0.5초 포착 원칙
   - 자동 구조화
   - 검색과 필터링

3. **Module System (공간축)**
   - 계층적 구조
   - Wiki-style connections
   - 그래프 시각화

4. **Claude Code Integration**
   - 자동 컨텍스트 전달
   - mcontext 명령어
   - .claude/ 폴더

#### Part 2: Command Reference (명령어 상세)

**각 명령어마다:**
- 용도 (What)
- 사용법 (How)
- 옵션 설명
- 실제 예시 3-5개
- 고급 사용법
- Tips & Tricks

**명령어 목록:**
1. `m` - Timeline 기록
2. `minit` - 초기화
3. `ms` - 검색 (텍스트, 시맨틱, 하이브리드)
4. `mcontext` - Claude 컨텍스트 생성
5. `mtoday` / `mweek` - Timeline 조회
6. `mstatus` - 통계
7. `malias` - 별칭 관리
8. `msort` - Timeline 정렬
9. `module` - 모듈 관리
10. `msummary` - LLM 요약
11. `mindex` - 검색 인덱스 관리
12. `marchive` - 문서 아카이브
13. `mbrowse` - TUI 브라우저
14. `mplan` - 계획 관리
15. `mtutorial` - 대화형 튜토리얼
16. `mhooks` - Git hooks 관리

#### Part 3: Real-world Workflows (실사용 시나리오)

1. **일일 워크플로우**
   - 아침: 계획 검토
   - 작업 중: 실시간 기록
   - 저녁: 요약 및 정리

2. **프로젝트 관리**
   - 프로젝트 모듈 생성
   - 진행상황 추적
   - 결정사항 문서화

3. **연구/학습**
   - 학습 내용 기록
   - 개념 연결
   - 복습 및 검색

4. **Claude Code와 함께**
   - 자동 컨텍스트 전달
   - 개발 과정 기록
   - 리팩토링 히스토리

#### Part 4: Advanced Features (고급 기능)

1. **Vector Search & LLM**
   - 시맨틱 검색 활성화
   - Anthropic/Ollama 설정
   - 자동 요약 활용

2. **Wiki-style Connections**
   - [[module]] 링크 문법
   - 그래프 시각화
   - AI 연결 제안

3. **Module Organization**
   - 계층 vs 평면 구조
   - 분리 기준
   - 모범 사례

4. **Performance Optimization**
   - 인덱싱 전략
   - 캐싱 설정
   - 대용량 처리

#### Part 5: Configuration (설정)

1. **config.yaml 상세**
   - 모든 옵션 설명
   - 기본값
   - 예시

2. **환경별 설정**
   - 개인 프로젝트
   - 팀 프로젝트
   - 멀티 프로젝트

### 3.2 FAQ.md

**주요 질문:**

1. **일반**
   - Q: Claude Code가 없어도 사용할 수 있나요?
   - Q: 기존 프로젝트에 추가할 수 있나요?
   - Q: 데이터는 어디에 저장되나요?

2. **설치/설정**
   - Q: Python 버전 요구사항은?
   - Q: Vector search가 왜 느린가요?
   - Q: LLM API 키는 어떻게 설정하나요?

3. **사용법**
   - Q: Timeline과 Module의 차이는?
   - Q: 언제 모듈을 나눠야 하나요?
   - Q: 검색이 원하는 결과를 안 보여줘요

4. **고급**
   - Q: 여러 프로젝트를 관리하려면?
   - Q: 데이터를 백업하려면?
   - Q: 성능 최적화는?

5. **문제 해결**
   - Q: 명령어가 안 돼요
   - Q: 검색 인덱스 깨짐
   - Q: 그래프가 이상해요

### 3.3 TROUBLESHOOTING.md

**문제 카테고리:**

1. **설치 문제**
   - pip install 실패
   - 의존성 충돌
   - Python 버전 문제

2. **실행 문제**
   - 명령어 not found
   - Permission error
   - 인코딩 문제 (Windows)

3. **기능 문제**
   - 검색 결과 없음
   - 그래프 rebuild 실패
   - Context 생성 오류

4. **성능 문제**
   - 검색이 느림
   - 메모리 부족
   - 디스크 공간

---

## Phase 4: README.md 개선 (1-2시간)

### 현재 README.md 분석

**현재 구조:**
- ✅ 한글로 작성 (타겟 사용자)
- ✅ 핵심 개념 설명
- ⚠️ 개발자 관점 (dogfooding)
- ⚠️ 설치 방법 간단

**개선 방향:**

1. **상단 섹션 개선**
   ```markdown
   # memory_tool

   > 시간-공간 통합 지식 체계 (Time-Space Integrated Knowledge System)

   [![PyPI](badge)] [![Python](badge)] [![License](badge)]

   **0.5초로 포착하고, 주말에 정리하며, 평생 활용한다.**
   ```

2. **Quick Demo 추가**
   - GIF/Screenshot
   - 3-step 시작 가이드
   - Live example

3. **Features 강조**
   - ✨ 주요 기능 하이라이트
   - 🎯 Use cases
   - 💡 Why memory_tool?

4. **Installation 상세화**
   - PyPI 설치
   - 선택적 의존성
   - 검증 방법

5. **Documentation Links**
   - 📚 [User Guide](USER_GUIDE.md)
   - 🚀 [Quick Start](QUICKSTART.md)
   - ❓ [FAQ](FAQ.md)

6. **Community/Support**
   - Issues
   - Discussions
   - Contributing

7. **메타 섹션 간소화**
   - Dogfooding 언급은 유지하되 간략히
   - 개발 문서는 별도 링크

---

## Phase 5: 설계 문서 업데이트 (3-4시간)

### 5.1 시간-공간-통합-지식-체계-v2.0.md 분석

**작업 순서:**
1. 전체 문서 읽기 (2476 lines)
2. 구현과 다른 부분 식별
3. 실제 구현 내용으로 업데이트
4. 새 기능 추가 문서화

**주요 업데이트 예상 영역:**

1. **구현 세부사항**
   - CLI 명령어 (실제 구현)
   - 파일 구조 (실제 사용)
   - 설정 옵션 (config.yaml)

2. **추가된 기능**
   - Phase 5-7 기능들
   - TUI 브라우저
   - 그래프 버전 관리
   - AI 기반 제안

3. **변경된 결정사항**
   - MCP 서버 우선순위 하락
   - 모듈 분리 (6개 feature-based)
   - 실용성 우선 접근

4. **실사용 교훈**
   - Dogfooding insights
   - 모범 사례
   - 주의사항

### 5.2 업데이트 전략

**Option A: 병렬 버전**
```
시간-공간-통합-지식-체계-v2.0.md (원본 설계)
시간-공간-통합-지식-체계-v2.1-implemented.md (실제 구현)
```

**Option B: 단일 버전 업데이트**
```
시간-공간-통합-지식-체계-v2.0.md 직접 수정
+ CHANGELOG 섹션 추가 (설계 vs 구현 차이)
```

**권장: Option B** (단일 진실의 원천)

---

## Phase 6: 배포 테스트 (2-3시간)

### 6.1 로컬 빌드 테스트

```bash
# Clean build
rm -rf dist/ build/ *.egg-info

# Build
python -m build

# Check
twine check dist/*
```

### 6.2 TestPyPI 배포

```bash
# Upload to TestPyPI
twine upload --repository testpypi dist/*

# Test installation
pip install --index-url https://test.pypi.org/simple/ memory-tool
```

### 6.3 실제 설치 테스트

**환경:**
1. Windows (clean venv)
2. macOS (if available)
3. Linux (if available)

**테스트:**
- [ ] pip install 성공
- [ ] 모든 명령어 실행
- [ ] 문서 접근 가능
- [ ] 예제 동작

### 6.4 PyPI 배포 (실제)

```bash
# Final upload
twine upload dist/*

# Verify
pip install memory-tool
```

---

## Phase 7: 추가 문서 (선택, 1-2시간)

### 7.1 CONTRIBUTING.md

**내용:**
- 개발 환경 설정
- 코드 스타일 가이드
- PR 프로세스
- 테스트 작성

### 7.2 ARCHITECTURE.md

**내용:**
- 시스템 아키텍처
- 모듈 구조
- 설계 결정사항
- 확장 포인트

---

## Success Criteria

### 배포
- [ ] PyPI에 v1.0.0 배포 완료
- [ ] 신규 사용자가 `pip install` 가능
- [ ] 모든 의존성 자동 설치
- [ ] LICENSE 파일 포함

### 문서화
- [ ] INSTALLATION.md - 명확한 설치 가이드
- [ ] QUICKSTART.md - 5분 시작 가이드
- [ ] USER_GUIDE.md - 완전한 사용자 가이드
- [ ] FAQ.md - 자주 묻는 질문 15+개
- [ ] README.md - 외부 사용자 친화적
- [ ] CHANGELOG.md - 버전 히스토리

### 설계 문서
- [ ] 시간-공간-통합-지식-체계-v2.0.md 업데이트
- [ ] 구현과 설계 일치
- [ ] 새 기능 모두 문서화

### 검증
- [ ] 3개 환경에서 설치 테스트
- [ ] 모든 명령어 동작 확인
- [ ] 문서 링크 모두 유효
- [ ] 오타/오류 0개

---

## Timeline Estimate

**Total: 15-23 hours**

- Phase 1 (배포 준비): 2-3h
- Phase 2 (설치/빠른시작): 2-3h
- Phase 3 (사용자 가이드): 4-6h
- Phase 4 (README 개선): 1-2h
- Phase 5 (설계 문서): 3-4h
- Phase 6 (배포 테스트): 2-3h
- Phase 7 (추가 문서, 선택): 1-2h

**권장 진행:**
- Session 1 (6h): Phase 1-2
- Session 2 (8h): Phase 3-4
- Session 3 (6h): Phase 5-6
- Session 4 (2h): 검증 및 배포

---

## Next Steps

1. ✅ 이 계획 검토 및 승인
2. ⏳ Phase 1 시작: pyproject.toml 개선
3. ⏳ LICENSE, MANIFEST.in 작성
4. ⏳ CHANGELOG.md 초안
5. ⏳ Phase 2로 진행...

---

**Status:** Plan Complete, Ready for Approval
**Created:** 2025-11-15
**Next:** 사용자 승인 후 Phase 1 시작
