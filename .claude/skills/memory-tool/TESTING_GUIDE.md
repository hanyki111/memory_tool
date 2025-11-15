# Claude Skill Testing Guide

**목적:** 새 세션에서 memory-tool Skill이 올바르게 작동하는지 검증

---

## 사전 준비

### 1. 환경 확인

```bash
# memory_tool 설치 확인
python -m memory_tool --help

# .memory/ 초기화 확인
ls .memory/config.yaml

# Skill 파일 존재 확인
ls .claude/skills/memory-tool/SKILL.md
```

### 2. config.yaml 설정

테스트용 권장 설정:
```yaml
context:
  auto_update: true  # 자동 컨텍스트 업데이트
  recent_days: 3

timeline:
  granularity: medium
```

---

## 테스트 절차

### Phase 1: Skill 로드 확인

**1. Claude Code 완전 재시작**
- 현재 세션 종료
- Claude Code 재시작
- 이 프로젝트 열기

**2. Skill 로드 확인 대화**

```
You: "Hi, can you see the memory-tool skill?"

Expected: Claude should acknowledge the skill exists
```

**3. 간단한 기능 테스트**

```
You: "기록해줘: Test message for skill verification"

Expected:
- Claude runs: m "Test message for skill verification"
- Shows: ✓ Recorded to timeline
- Auto-updates context (if enabled)
```

**확인 방법:**
```bash
# Timeline에 기록되었는지 확인
tail -n 3 .memory/timeline/2025-11/14.md
```

---

## Phase 2: 주요 시나리오 테스트

### Test 1: 명시적 기록 요청 ⭐

**Input:**
```
You: "기록해줘: We decided to use Redis for caching"
```

**Expected:**
```
Claude:
m "We decided to use Redis for caching"

✓ Recorded to timeline
```

**Verify:**
```bash
grep -i "redis" .memory/timeline/2025-11/14.md
```

**Result:** ✅ Pass / ❌ Fail

---

### Test 2: 자연스러운 중단점 후 기록 ⭐⭐⭐

**Input:**
```
You: "Create a simple function that adds two numbers and test it"
```

**Expected Claude Behavior:**
1. Creates function
2. Creates test
3. Runs test
4. **AFTER showing results**, suggests:
   ```
   "I've created and tested the add function. Tests passing.

    Shall I record this milestone?
    - Feature complete: Add function with tests"
   ```

**Critical Check:**
- ❌ Does NOT suggest recording DURING implementation
- ✅ Suggests recording AFTER completion

**Verify:**
If you say "yes":
```bash
grep -i "add function" .memory/timeline/2025-11/14.md
```

**Result:** ✅ Pass / ❌ Fail

---

### Test 3: 검색 기능 ⭐

**Setup:** Ensure timeline has "Redis" entry from Test 1

**Input:**
```
You: "What did we decide about caching?"
```

**Expected Claude Behavior:**
1. Recognizes need to search
2. Runs: `ms "caching"` or `ms "Redis"`
3. Shows search results
4. Answers based on findings: "Based on the timeline, we decided to use Redis..."

**Critical Check:**
- ✅ Searches BEFORE answering
- ❌ Does NOT guess/hallucinate

**Result:** ✅ Pass / ❌ Fail

---

### Test 4: 세션 시작 컨텍스트 ⭐

**New Session Required:** Restart Claude Code

**Input:**
```
You: "Hi, what have I been working on recently?"
```

**Expected Claude Behavior:**
1. Checks if context is fresh
2. If stale: "Let me update the context first" → runs `mcontext`
3. Reads `.claude/memory-context.md`
4. Answers with: "Based on recent timeline: [summary of work]"

**Critical Check:**
- ✅ Uses memory-context.md
- ✅ Provides accurate summary from timeline

**Result:** ✅ Pass / ❌ Fail

---

### Test 5: Over-Recording 방지 (Negative Test) ⭐

**Input:**
```
You: "What's the weather today?"
```

**Expected Claude Behavior:**
- Answers the question (or says can't access weather)
- ❌ Does NOT offer to record
- ❌ No timeline entry created

**Verify:**
```bash
grep -i "weather" .memory/timeline/2025-11/14.md
# Should return empty
```

**Result:** ✅ Pass / ❌ Fail

---

### Test 6: 배치 기록 (작업 완료 후) ⭐

**Input:**
```
You: "We've decided on three things:
1. TypeScript for frontend
2. PostgreSQL for database
3. Docker for deployment

Please set up initial config files for these."
```

**Expected Claude Behavior:**
1. Creates config files
2. **AFTER completion**, suggests:
   ```
   "I've created the configuration files.

    Should I record these technology decisions?
    - TypeScript for frontend
    - PostgreSQL for database
    - Docker for deployment"
   ```

**If you say "yes":**
```
m "Decision: TypeScript for frontend - type safety"
m "Decision: PostgreSQL for database - relational data"
m "Decision: Docker for deployment - consistency"

✓ Recorded 3 decisions
```

**Critical Check:**
- ✅ Suggests recording AFTER work complete
- ❌ Does NOT interrupt during work

**Result:** ✅ Pass / ❌ Fail

---

### Test 7: 오늘 작업 보기 ⭐

**Input:**
```
You: "오늘 뭐했는지 보여줘"
or
You: "Show me what I did today"
```

**Expected:**
```
Claude runs: mtoday
[Shows today's timeline entries]
```

**Result:** ✅ Pass / ❌ Fail

---

### Test 8: 에러 핸들링 ⭐

**Setup:** Temporarily rename `.memory/` to `.memory_backup/`

**Input:**
```
You: "기록해줘: Test error handling"
```

**Expected:**
```
m "Test error handling"

⚠ Recording failed: .memory/ not found
Run 'minit' to initialize the project first.
```

**Critical Check:**
- ✅ Graceful error message
- ✅ Suggests solution
- ❌ Does NOT crash

**Cleanup:**
```bash
mv .memory_backup .memory
```

**Result:** ✅ Pass / ❌ Fail

---

## Phase 3: Edge Cases

### Test 9: 대화 중 기록 제안 안 함

**Input:**
```
You: "I'm thinking about using Redis or Memcached for caching.
     What do you think?"
```

**Expected:**
- Claude discusses pros/cons
- Provides recommendation
- ❌ Does NOT suggest recording (still discussing, no decision made)

**Then:**
```
You: "Good points. Let's go with Redis then."
```

**Expected:**
- Claude acknowledges
- ❌ STILL does NOT suggest recording (just a decision, no work done)

**Then:**
```
You: "Can you help me set up Redis configuration?"
```

**Expected:**
- Claude creates config
- **AFTER config created**, suggests recording

**Result:** ✅ Pass / ❌ Fail

---

### Test 10: Flow State 존중

**Input:**
```
You: "I need to implement these 5 features quickly:
1. User login
2. Password reset
3. Email verification
4. Profile update
5. Account deletion

Let's start with login."
```

**Expected:**
- Claude helps implement all 5 features
- ❌ Does NOT interrupt between features
- ✅ At the END, suggests batch recording all 5

**Result:** ✅ Pass / ❌ Fail

---

## 테스트 결과 기록

### Test Summary Template

```markdown
## Test Run: 2025-11-14

**Environment:**
- OS: Windows 11
- Python: 3.11
- memory_tool: Phase 1
- Claude Code: [version]

**Results:**
| Test | Description | Result | Notes |
|------|-------------|--------|-------|
| 1 | 명시적 기록 | ✅ / ❌ | |
| 2 | 자연스러운 중단점 | ✅ / ❌ | |
| 3 | 검색 기능 | ✅ / ❌ | |
| 4 | 세션 시작 컨텍스트 | ✅ / ❌ | |
| 5 | Over-recording 방지 | ✅ / ❌ | |
| 6 | 배치 기록 | ✅ / ❌ | |
| 7 | 오늘 작업 보기 | ✅ / ❌ | |
| 8 | 에러 핸들링 | ✅ / ❌ | |
| 9 | 대화 중 제안 안 함 | ✅ / ❌ | |
| 10 | Flow State 존중 | ✅ / ❌ | |

**Pass Rate:** X/10 (X%)

**Issues Found:**
1. [Issue description]
2. [Issue description]

**Observations:**
- [Any observations about Skill behavior]
- [User experience notes]
- [Performance notes]
```

---

## 성공 기준

### Minimum Viable (최소 합격):
- ✅ 명시적 기록 작동 (Test 1)
- ✅ 검색 작동 (Test 3)
- ✅ Over-recording 방지 (Test 5)
- ✅ 에러 핸들링 (Test 8)

**Pass Rate:** 4/10 (40%)

### Good (양호):
- 위 4개 +
- ✅ 자연스러운 중단점 (Test 2)
- ✅ 배치 기록 (Test 6)
- ✅ 오늘 작업 보기 (Test 7)

**Pass Rate:** 7/10 (70%)

### Excellent (우수):
- 위 7개 +
- ✅ 세션 시작 컨텍스트 (Test 4)
- ✅ 대화 중 제안 안 함 (Test 9)
- ✅ Flow State 존중 (Test 10)

**Pass Rate:** 10/10 (100%)

---

## 문제 발견 시

### 1. Skill이 로드되지 않음
```bash
# Skill 경로 확인
ls -la .claude/skills/memory-tool/SKILL.md

# YAML frontmatter 확인
head -n 5 .claude/skills/memory-tool/SKILL.md

# Claude Code 재시작
```

### 2. 명령어가 실행되지 않음
```bash
# PATH 확인
which python
python -m memory_tool --help

# 수동 실행 테스트
python -m memory_tool record "Manual test"
```

### 3. 너무 자주 기록 제안
→ SKILL.md의 "Do NOT interrupt workflow" 원칙 재확인
→ decisions.md #22 참고

### 4. 전혀 기록 제안 안 함
→ description의 트리거 키워드 확인
→ "record", "save", "기록" 등의 명시적 요청 테스트

---

## 다음 단계

### 테스트 통과 시:
- ✅ Phase 1 완전 검증 완료
- 실제 프로젝트에 적용 가능
- Phase 2 계획 시작

### 문제 발견 시:
- Issue 문서화 (.memory/timeline/에 기록!)
- SKILL.md 수정
- 재테스트

---

## Tips

1. **한 번에 하나씩:** 각 테스트를 독립적으로 실행
2. **Timeline 확인:** 매 테스트 후 timeline 파일 확인
3. **로그 관찰:** Claude의 응답 패턴 관찰
4. **피드백 기록:** 불편한 점이나 개선 아이디어를 timeline에 기록

---

**마지막 체크리스트:**
- [ ] Claude Code 완전 재시작
- [ ] .memory/ 초기화됨
- [ ] config.yaml 설정 확인
- [ ] Skill 파일 존재 확인
- [ ] 테스트 결과 기록 준비

**Ready? 새 세션에서 "Hi"로 시작하세요!** 🚀
