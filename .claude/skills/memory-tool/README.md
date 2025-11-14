# Memory Tool Skill - Usage Guide

This directory contains the Claude Skill for memory_tool integration.

---

## What is This?

This skill teaches Claude how to use the memory_tool system during conversations. Claude will automatically:

- Record important decisions and milestones to timeline
- Search past work when you ask about previous decisions
- Maintain project context throughout sessions

---

## Setup

### 1. Ensure memory_tool is Installed

```bash
cd /path/to/memory_tool
pip install -e .
```

### 2. Initialize Project

```bash
cd /path/to/your/project
minit
```

### 3. Enable Auto-Update (Recommended)

Edit `.memory/config.yaml`:

```yaml
context:
  auto_update: true  # Automatic context refresh after recording
  recent_days: 3
```

### 4. Verify Skill is Loaded

When you start Claude Code in a project with `.claude/skills/memory-tool/`, the skill should be automatically available.

---

## How It Works

### Automatic Recording

When you make decisions or complete work, Claude will offer to record it:

```
You: "Let's use PostgreSQL for this project"
Claude: "Good choice! Let me record this decision:
         m 'Decision: PostgreSQL chosen for relational data needs'
         ✓ Recorded to timeline"
```

### Automatic Search

When you ask about past work, Claude will search first:

```
You: "What did we decide about authentication?"
Claude: "Let me check:
         ms 'authentication'
         Based on 2025-11-12 entry, we decided to use JWT..."
```

### Context Awareness

Claude starts sessions by checking recent context:

```
Claude: "Welcome back! I see from the timeline:
         - Yesterday: Started OAuth implementation
         - Active: auth-system module
         Ready to continue?"
```

---

## Usage Tips

### 1. Explicit Recording

Ask Claude to record important items:

```
"기록해줘: API 설계 완료"
"Record this: Fixed memory leak in worker thread"
"타임라인에 추가: 테스트 커버리지 90% 달성"
```

### 2. Search Past Work

Ask about previous work:

```
"이전에 에러 핸들링 어떻게 했지?"
"How did we implement caching last time?"
"Show me what we decided about database schema"
```

### 3. Review Today's Work

```
"오늘 뭐했는지 보여줘" → Claude runs: mtoday
"이번 주 작업 요약해줘" → Claude runs: mweek
```

### 4. Session Endings

```
"오늘은 여기까지!"
→ Claude: "Let me record a summary:
           m 'Session complete: [summary of work]'
           ✓ Recorded"
```

---

## Skill Behavior

### What Claude WILL Record

✅ Decisions with rationale
✅ Completed features/fixes
✅ Important discoveries
✅ Architecture choices
✅ Major milestones

### What Claude WON'T Record

❌ Trivial conversations
❌ Questions without answers
❌ Temporary explorations
❌ Implementation details (unless requested)
❌ Claude's own responses

---

## Commands Reference

Claude will use these commands naturally:

| Command | Purpose | Example |
|---------|---------|---------|
| `m "msg"` | Record to timeline | `m "OAuth implementation complete"` |
| `ms "query"` | Search local | `ms "authentication"` |
| `ms --with-kb "query"` | Search with KB | `ms --with-kb "error handling pattern"` |
| `ms --all "query"` | Search all projects | `ms --all "Redis config"` |
| `mcontext` | Update context | `mcontext` |
| `mtoday` | Show today's work | `mtoday` |
| `mweek` | Show this week | `mweek` |

---

## Configuration

Edit `.memory/config.yaml` to customize:

```yaml
context:
  auto_update: true      # Auto-refresh context after m command
  recent_days: 3         # Days to include in memory-context.md

timeline:
  granularity: medium    # low/medium/high recording frequency
  warn_old_days: 365     # Warning threshold for old dates

search:
  default_scope: local   # local/kb/all
  max_file_size: 1048576 # 1MB limit
```

---

## Troubleshooting

### Skill Not Working?

1. **Check skill exists:**
   ```bash
   ls .claude/skills/memory-tool/SKILL.md
   ```

2. **Verify memory_tool is installed:**
   ```bash
   python -m memory_tool --help
   ```

3. **Check .memory/ exists:**
   ```bash
   ls .memory/config.yaml
   ```

4. **Restart Claude Code**

### Commands Not Running?

1. **PATH issue**: Ensure Python and memory_tool are in PATH
2. **Permission issue**: Check file permissions
3. **Config issue**: Verify config.yaml is valid YAML

### Context Not Updating?

1. **Check auto_update setting:**
   ```bash
   cat .memory/config.yaml | grep auto_update
   ```

2. **Manually update:**
   ```bash
   mcontext
   ```

3. **Check .claude/ directory:**
   ```bash
   ls -la .claude/memory-context.md
   ```

---

## Examples

See `SKILL.md` for detailed examples of:
- Decision recording
- Search and answer workflows
- Session summaries
- Context checking

---

## Version History

- **1.0** (2025-11-14): Initial release
  - Rule-based automation
  - Recording, search, context integration
  - Works with memory_tool Phase 1

---

## Future Enhancements

**Phase 2:**
- LLM-based decision detection
- Automatic importance scoring
- Smart summarization

**Phase 3:**
- Semantic search integration
- Cross-project knowledge linking
- Automatic module updates

---

## Support

For issues or questions:
1. Check `SKILL.md` for detailed behavior
2. Review memory_tool documentation in project README.md
3. Check `.memory/modules/memory-system/current.md` for project status

---

**Last Updated:** 2025-11-14
**Compatible with:** memory_tool Phase 1 (v0.1.0+)
