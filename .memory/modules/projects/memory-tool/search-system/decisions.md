# Key Decisions

> **Search-related decisions for memory_tool**

---

## Recent Decisions

### 2025-11-14: SQLite 인덱싱 구현 결정 ⭐⭐⭐
**결정 #26:** 검색 성능 개선을 위한 SQLite FTS5 인덱싱 구현

**배경:**
- 현재: 파일 기반 검색 (ripgrep), 매번 전체 파일 읽기
- 문제: Timeline이 길어지면 검색 느려짐
- Phase 5 Revised 우선순위 #2

**목표:**
- 검색 속도 10-100배 개선
- 1000+ 항목에서도 sub-second 응답
- Backward compatible (기존 방식 유지)

**설계 결정:**

1. **Index 위치:** `.memory/.index.db` (hidden, gitignored)
   - 파생 데이터 (재생성 가능)
   - Git 커밋 제외
   - 사용자 직접 수정 불가

2. **SQLite FTS5 사용:**
   - Full-text search with porter tokenizer
   - Unicode61 support
   - Space-efficient (~2x text size)

3. **Backward Compatibility:**
   - SQLite 실패 시 → ripgrep fallback
   - Index 삭제되면 → 자동 재생성
   - 기존 명령어 변경 없음

4. **인덱싱 전략:**
   - `m` 명령어: 즉시 인덱싱
   - `ms` 명령어: Index 신선도 체크, 필요 시 rebuild
   - 새 명령어: `mindex` (수동 reindex)

5. **인덱싱 대상:**
   - ✅ Timeline entries
   - ✅ Decisions
   - ✅ Current state
   - ✅ Concepts
   - ❌ Archive (읽기 전용, 접근 드뭄)

**구현 범위 (4-6시간):**
- Phase 1: Core infrastructure (db/indexer.py, db/search.py)
- Phase 2: Timeline integration (auto-index)
- Phase 3: CLI commands (mindex, ms 개선)
- Phase 4: Testing & validation

**리스크 완화:**
- SQLite 없음 → ripgrep fallback
- Index 손상 → auto-rebuild
- 동시 쓰기 → write lock
- 디스크 공간 → FTS5 효율적

**성공 기준:**
- ✅ 10x 이상 속도 개선 (1000+ 항목)
- ✅ Backward compatible
- ✅ Auto-rebuild on corruption
- ✅ 기존 명령어 동작 유지

**Non-Goals:**
- ❌ Vector search 통합 (별도)
- ❌ Multi-project indexing
- ❌ Real-time index (on-command로 충분)

**효과:**
- 대용량 Timeline 검색 가능
- 사용자 경험 대폭 개선
- 실시간 피드백 가능
- 확장 가능한 아키텍처

**컨텍스트:** [[time:2025-11/14#23:05]]

---

## See Also

**Related Modules:**
- [[projects/memory-tool/core-system]] - Timeline data structures
- [[projects/memory-tool/llm-integration]] - Vector embeddings for semantic search
- [[projects/memory-tool/project-management]] - Architecture decisions

---

**Total Decisions:** 1 (search infrastructure decision)
