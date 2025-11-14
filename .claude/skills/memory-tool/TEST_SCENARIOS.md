# Memory Tool Skill - Test Scenarios

Test cases to verify the skill works correctly with Claude Code.

---

## Test Environment

**Setup:**
1. Project with `.memory/` initialized
2. config.yaml with `auto_update: true`
3. Claude Code running with skill loaded

---

## Test Case 1: Explicit Recording Request

**User Input:**
```
"기록해줘: OAuth 구현 완료"
```

**Expected Claude Behavior:**
1. Recognizes recording request
2. Runs: `m "OAuth 구현 완료"`
3. Shows confirmation: "✓ Recorded to timeline"
4. Context auto-updates (if auto_update enabled)

**Verification:**
```bash
# Check timeline
tail -n 5 .memory/timeline/2025-11/14.md

# Check context updated
cat .claude/memory-context.md | head -n 3
```

---

## Test Case 2: Decision Recording

**User Input:**
```
"Let's use TypeScript for this project instead of JavaScript"
```

**Expected Claude Behavior:**
1. Detects decision
2. Offers to record: "I'll record this decision..."
3. Runs: `m "Decision: TypeScript chosen over JavaScript for type safety"`
4. Shows confirmation

**Verification:**
```bash
grep "TypeScript" .memory/timeline/2025-11/14.md
```

---

## Test Case 3: Search Request

**User Input:**
```
"What did we decide about database?"
```

**Expected Claude Behavior:**
1. Recognizes need to search
2. Runs: `ms "database"`
3. Shows search results
4. Answers based on findings: "Based on [date], we decided..."

**Verification:**
- Claude should cite specific dates/entries
- Should not hallucinate information

---

## Test Case 4: Session Start

**User Input:**
```
[New conversation starts]
"Hi, let's continue working on the API"
```

**Expected Claude Behavior:**
1. Checks if context is fresh
2. If stale, suggests: "Let me update context first"
3. Runs: `mcontext`
4. Reads `.claude/memory-context.md`
5. Responds with: "I see from recent work... [summary]"

**Verification:**
```bash
# Check context was updated recently
ls -l .claude/memory-context.md
```

---

## Test Case 5: Session End Summary

**User Input:**
```
"That's all for today!"
```

**Expected Claude Behavior:**
1. Offers to record summary
2. Runs: `m "Session complete: [concise summary of work]"`
3. Shows: "✓ Recorded"
4. Optionally suggests: "You can review with: mtoday"

**Verification:**
```bash
# Last line should be session summary
tail -n 1 .memory/timeline/2025-11/14.md
```

---

## Test Case 6: Milestone Completion

**User Input:**
```
"Great, the authentication feature is working now!"
```

**Expected Claude Behavior:**
1. Detects milestone completion
2. Offers: "Shall I record this milestone?"
3. If agreed, runs: `m "Feature complete: Authentication system"`
4. Shows confirmation

**Verification:**
```bash
grep -i "authentication" .memory/timeline/2025-11/14.md
```

---

## Test Case 7: Multiple Decisions (Batch)

**User Input:**
```
"We've decided:
1. Use PostgreSQL
2. Deploy on AWS
3. Use Docker containers"
```

**Expected Claude Behavior:**
1. Detects multiple decisions
2. Asks: "Should I record these 3 decisions?"
3. If yes, runs:
   ```
   m "Decision: PostgreSQL for database"
   m "Decision: AWS for deployment"
   m "Decision: Docker containers for consistency"
   ```
4. Shows: "✓ Recorded 3 decisions"

**Verification:**
```bash
# Should have 3 entries
grep -c "Decision:" .memory/timeline/2025-11/14.md
```

---

## Test Case 8: Don't Over-Record (Negative Test)

**User Input:**
```
"What's the weather today?"
```

**Expected Claude Behavior:**
1. Answers the question
2. Does NOT offer to record
3. No timeline entry created

**Verification:**
```bash
# Timeline should not have "weather" entry
grep -i "weather" .memory/timeline/2025-11/14.md
# Should return empty
```

---

## Test Case 9: Search in Knowledge Base

**User Input:**
```
"How did I handle errors in my other projects?"
```

**Expected Claude Behavior:**
1. Recognizes cross-project question
2. Runs: `ms --all "error handling"`
3. Shows results from multiple projects (if any)
4. Answers based on findings

**Verification:**
- Should search beyond current project
- Should show results from other projects (if KB exists)

---

## Test Case 10: Today's Summary

**User Input:**
```
"Show me what we did today"
```

**Expected Claude Behavior:**
1. Runs: `mtoday`
2. Displays today's timeline entries
3. Optionally summarizes key items

**Verification:**
```bash
# Manually run to compare
python -m memory_tool today
```

---

## Test Case 11: Context Auto-Update (Config Test)

**Setup:**
```yaml
# .memory/config.yaml
context:
  auto_update: true
```

**User Input:**
```
m "Test entry"
```

**Expected Behavior:**
1. Records to timeline
2. Automatically runs `mcontext`
3. Shows: "✓ Context updated"

**Verification:**
```bash
# Check timestamp of context file
ls -l .claude/memory-context.md
# Should be very recent (< 1 min)
```

---

## Test Case 12: Manual Context Update (Config Test)

**Setup:**
```yaml
# .memory/config.yaml
context:
  auto_update: false
```

**User Input:**
```
m "Test entry 1"
m "Test entry 2"
m "Test entry 3"
```

**Expected Behavior:**
1. Records all 3 entries
2. Does NOT auto-update context
3. After multiple entries, suggests: "Should I update the context?"

**Verification:**
```bash
# Context should be old
ls -l .claude/memory-context.md
# Manually update
mcontext
```

---

## Test Case 13: Error Handling

**User Input:**
```
[In directory without .memory/]
"Record this: test"
```

**Expected Claude Behavior:**
1. Runs: `m "test"`
2. Gets error: ".memory/ not found"
3. Shows: "⚠ Recording failed: .memory/ not initialized"
4. Suggests: "Run 'minit' to initialize"

**Verification:**
- Should handle error gracefully
- Should not crash
- Should provide helpful message

---

## Test Case 14: Regex Search

**User Input:**
```
"Find all TODO comments"
```

**Expected Claude Behavior:**
1. Runs: `ms "TODO|FIXME"`
2. Shows all matching entries
3. Summarizes findings

**Verification:**
```bash
# Manual comparison
python -m memory_tool search "TODO|FIXME"
```

---

## Test Case 15: Week Summary

**User Input:**
```
"What did I accomplish this week?"
```

**Expected Claude Behavior:**
1. Runs: `mweek`
2. Displays this week's entries (Mon-Today)
3. Summarizes key accomplishments

**Verification:**
```bash
# Manual run
python -m memory_tool week
```

---

## Regression Tests

### After Code Changes

Run all test cases to ensure:
- Recording still works
- Search still works
- Context updates correctly
- No new errors introduced

### After Config Changes

Test with different config.yaml settings:
- auto_update: true/false
- recent_days: 1, 3, 7
- granularity: low, medium, high

---

## Performance Tests

### Large Timeline

**Setup:** Timeline with 1000+ entries

**Test:** Search performance
```
ms "specific keyword"
```

**Expected:** Results in < 2 seconds

### Multiple Projects

**Setup:** 5+ projects with .memory/

**Test:** Cross-project search
```
ms --all "common pattern"
```

**Expected:** Results in < 5 seconds

---

## Edge Cases

### Edge Case 1: Empty Timeline

**Setup:** Just initialized, no entries

**Test:** `mtoday`

**Expected:** "No entries for today"

### Edge Case 2: No Search Results

**Test:** `ms "nonexistent_keyword_xyz"`

**Expected:**
- "No results found"
- Offer to expand search: "--with-kb or --all?"

### Edge Case 3: Very Long Message

**Test:** `m "Very long message with 500+ characters..."`

**Expected:**
- Should record successfully
- Should warn if > 200 chars? (optional)

---

## Success Criteria

✅ All 15 main test cases pass
✅ Error handling works gracefully
✅ No crashes or unexpected behavior
✅ Performance acceptable (< 2s for common operations)
✅ Context stays synchronized
✅ Recording is selective (not over-recording)

---

## Test Log Template

```markdown
## Test Run: [Date]

**Environment:**
- OS: Windows/Mac/Linux
- Python: 3.x
- memory_tool: v0.1.0
- Claude Code: [version]

**Results:**
- Test 1: ✅ / ❌
- Test 2: ✅ / ❌
- Test 3: ✅ / ❌
...

**Issues Found:**
1. [Issue description]
2. [Issue description]

**Notes:**
[Any observations]
```

---

**Last Updated:** 2025-11-14
