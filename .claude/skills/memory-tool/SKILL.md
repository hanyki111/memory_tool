---
name: memory-tool
description: Automates memory_tool workflows requiring judgment: suggest recording after completing features (decide what/when), search and analyze past work (find + interpret), manage session context (check + refresh). Use for complex workflows, not simple timeline views or direct searches.
---

# Memory Tool Integration

This Skill enables natural integration with the memory_tool system for timeline-based knowledge capture and retrieval.

## Instructions

### 1. When to Record (Use `m` command)

**IMPORTANT PRINCIPLE: Do NOT interrupt workflow with recording. Record at natural breakpoints or when explicitly requested.**

Record to timeline in these situations:

**A. Explicit user requests (IMMEDIATE):**
- User says "기록해줘", "record this", "save this", "타임라인에 추가"
- User says "write this down", "remember this"
- Action: Record immediately as requested

**B. After natural breakpoints (SUGGEST, don't interrupt):**

Record suggestion is appropriate AFTER completing these actions:
- ✅ After writing/editing files (files saved)
- ✅ After running code/tests (execution complete, results shown)
- ✅ After completing a feature (implementation done, tested)
- ✅ After fixing a bug (verified working)
- ✅ After major refactoring (code modified, working)

**Natural breakpoint pattern:**
```
[Complete the work first]
→ Show results to user
→ THEN suggest: "Shall I record this?"
```

**What to record at breakpoints:**
- Important decisions made during work: "Decision: PostgreSQL chosen for relational data"
- Milestones completed: "Feature complete: User authentication"
- Bugs fixed: "Fixed memory leak in worker threads"
- Significant refactors: "Refactored error handling to centralized middleware"

**How to suggest recording:**
```
"I've completed [task]. Shall I record this milestone/decision?
- [Brief summary of what was done]"
```

**Recording guidelines:**
- Keep messages concise (focus on "what" and "why", not "how")
- Use present/past tense, not future plans
- Include context for decisions: "Decision: X chosen because Y"
- Show the command to user for transparency

**Do NOT record during:**
- ❌ Middle of conversation (wait for natural breakpoint)
- ❌ While user is still describing requirements
- ❌ During exploratory discussions
- ❌ Trivial conversations or questions
- ❌ Temporary explorations
- ❌ Implementation details (unless specifically requested)

**Do NOT suggest recording for:**
- Trivial changes
- Work in progress
- Your own responses (only user's decisions/milestones)

### 2. When to Search (Use `ms` command)

Search timeline/knowledge when user:

**A. Explicitly asks to search:**
- "검색해줘", "search for", "find", "look up"
- "이전에 뭐했지?", "what did we do about...?"

**B. Asks about past work:**
- "How did we implement X?"
- "What did we decide about Y?"
- "Show me an example of Z"
- Mentions "last time", "before", "previously"

**How to search:**
```bash
# Local project only
ms "query"

# Include knowledge base
ms --with-kb "query"

# All projects
ms --all "query"
```

**Search workflow:**
1. Run search first (don't guess)
2. Show relevant findings to user
3. Answer based on actual results
4. If no results, suggest broader search (--with-kb or --all)

### 3. Context Management (Use `mcontext` command)

Update project context when:

**A. Session starts:**
- Check if `.claude/memory-context.md` exists and is recent (< 1 hour)
- If stale or missing, suggest: "Let me update the context first"
- Run `mcontext` to refresh

**B. After multiple recordings (if auto_update disabled):**
- After 3+ timeline entries without context update
- Before answering questions about current project state

**How to update:**
```bash
mcontext
```

**Note:** If `config.yaml` has `context.auto_update: true`, context updates automatically after `m` command. Don't run `mcontext` manually in this case.

### 4. Timeline Analysis (Complex queries requiring interpretation)

**Use Skill when user needs analysis/interpretation:**
- "오늘 중요한 결정만 요약해줘" → mtoday + filter + summarize
- "이번 주 작업 중 X 관련만 보여줘" → mweek + filter

**DON'T use Skill for simple timeline views:**
- "오늘 뭐했지?" → Use tool directly: `python -m memory_tool today`
- "이번 주 타임라인" → Use tool directly: `python -m memory_tool week`

Simple timeline display is a one-off task requiring minimal context. The Skill is only needed when interpretation, filtering, or analysis is required.

### 5. Batch Recording (After Work Complete)

If multiple items need recording after completing work:

**Step 1:** Complete the work first (implement, test, verify)

**Step 2:** At natural breakpoint, suggest recording
```
"I've completed [task]. Should I record these items?
- [Item 1]
- [Item 2]
- [Item 3]"
```

**Step 3:** If user agrees, record each
```bash
m "Decision: TypeScript for frontend - type safety"
m "Decision: PostgreSQL for database - relational data"
m "Decision: Docker for deployment - consistency"
```

**Step 4:** Confirm
```
✓ Recorded 3 decisions to timeline
```

**Important:** Do NOT interrupt work to suggest recording. Wait for natural completion point.

### 6. Error Handling

If command fails:
```
⚠ Recording failed: .memory/ not initialized
Run 'minit' to initialize the project first.
```

Handle gracefully:
- Explain the error
- Suggest solution (e.g., "Run minit to initialize")
- Ask if user wants to try again or skip

### 7. Response Format

**When recording:**
```
m "Feature complete: User authentication with JWT"
✓ Recorded: User authentication completed
```

**When searching:**
```
Searching for "authentication"...

Found 2 entries:
- 2025-11-12: Decision: JWT for auth tokens
- 2025-11-10: Started OAuth implementation

Based on these entries, we're using JWT tokens for authentication...
```

**When updating context:**
```
mcontext
✓ Context updated with latest timeline and module status
```

## Examples

### Example 1: Explicit Recording Request

**User:** "기록해줘: We decided to use Redis for caching"

**Claude Response:**
```
m "Decision: Redis for caching - persistence and scalability"

✓ Recorded to timeline
```

### Example 2: Recording After Natural Breakpoint

**Conversation:**
```
User: "Add JWT authentication to the API"
Claude: [implements authentication, writes files, tests]
Claude: "I've implemented JWT authentication. The API now requires
         Bearer tokens for protected endpoints. Tests are passing.

         Shall I record this milestone?
         - Feature complete: JWT authentication"

User: "Yes"
Claude:
m "Feature complete: JWT authentication with Bearer tokens"

✓ Recorded to timeline
```

**Note:** Recording suggested AFTER work is complete, not during implementation.

### Example 3: Search Before Answering

**User:** "How did we handle errors in our last project?"

**Claude Response:**
```
Let me check our previous work:

ms --all "error handling"

Found 3 results:
- project-api (2025-11-10): Centralized error middleware
- project-api (2025-11-08): Custom error classes
- project-web (2025-10-15): Try-catch with logging

Based on these, we used centralized error middleware with custom error classes. Would you like to follow the same pattern?
```

### Example 4: Session Start

**User:** "Hi, let's continue working on the API"

**Claude Response:**
```
Welcome back! Let me check the latest context:

mcontext

✓ Context updated

I can see from the timeline:
- Yesterday: OAuth implementation started
- Active modules: auth-system, api-layer
- Last decision: Using Passport.js for OAuth

Ready to continue with OAuth integration?
```

### Example 5: Multiple Decisions After Work Complete

**Conversation:**
```
User: "Let's use PostgreSQL, Redis, and Docker"
Claude: [discusses trade-offs, helps with setup]
Claude: "I've helped you set up the configuration files.

         Should I record these technology decisions?
         - PostgreSQL for database
         - Redis for caching
         - Docker for deployment"

User: "Yes, record them"
Claude:
m "Decision: PostgreSQL for relational data and complex queries"
m "Decision: Redis for caching and session storage"
m "Decision: Docker for consistent deployment across environments"

✓ Recorded 3 decisions to timeline
```

**Note:** Batch recording offered after discussion and setup are complete.

### Example 6: Batch Recording

**User:** "We've decided to use TypeScript, PostgreSQL, and Docker"

**Claude Response:**
```
I'll record these 3 decisions:

m "Decision: TypeScript for type safety and better IDE support"
m "Decision: PostgreSQL for relational data needs"
m "Decision: Docker for consistent deployment"

✓ Recorded 3 decisions to timeline
```

### Example 7: Don't Over-Record (Negative Example)

**User:** "What's the weather today?"

**Claude Response:**
```
I don't have access to real-time weather data, but you can check weather.com or your local weather service.
```

**Note:** Does NOT offer to record this trivial conversation.

### Example 8: Search with No Results

**User:** "Find information about GraphQL"

**Claude Response:**
```
ms "GraphQL"

No results found in local project.

Would you like me to search in your knowledge base (--with-kb) or across all projects (--all)?
```

## Configuration Awareness

Check `config.yaml` settings:

- **auto_update: true**: Context updates automatically after `m`, don't run `mcontext` manually
- **auto_update: false**: Suggest `mcontext` after multiple recordings
- **recent_days: N**: Context includes last N days of timeline

## Best Practices

1. **Don't Interrupt Workflow:** Complete work first, suggest recording at natural breakpoints
2. **Be Transparent:** Always show the command you're running
3. **Be Selective:** Record important items only, not everything
4. **Be Concise:** Keep timeline messages short and clear
5. **Search First:** When user asks about past work, search before answering
6. **Be Helpful:** Suggest searches when context might help
7. **Be Respectful:** Ask before batch recording multiple items
8. **Be Contextual:** Use timeline/module info to provide better answers
9. **Respect User Focus:** If user is in flow state, defer recording until they pause

## Testing

After implementing this Skill, test with scenarios from `TEST_SCENARIOS.md`:
- Explicit recording requests
- Decision detection
- Search functionality
- Session start/end
- Batch recording
- Over-recording prevention
- Error handling
