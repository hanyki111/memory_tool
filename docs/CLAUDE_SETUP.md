# CLAUDE.md Setup Guide

This guide explains how to set up `CLAUDE.md` for your project to provide context to Claude Code.

---

## What is CLAUDE.md?

`CLAUDE.md` is a project-specific instruction file that Claude Code reads when starting a new session. It provides:

- **Project Overview** - What the project is about
- **Current Status** - What's being worked on
- **Important Context** - Key files, decisions, and guidelines
- **Workflow Instructions** - How to work with this project

**Key Benefits:**
- Claude understands your project immediately
- Consistent behavior across sessions
- Automatic context from memory_tool integration
- Custom guidelines for your project

---

## Setup Instructions

### 1. Copy the Template

```bash
# From your project root
cp CLAUDE.md.template CLAUDE.md
```

### 2. Customize CLAUDE.md

Edit `CLAUDE.md` and fill in:

#### Project Overview
```markdown
**Name:** My Awesome Project
**Purpose:** A web application for task management
**Current Phase:** Active Development
```

#### Current Status
```markdown
**Active Work:**
- Implementing user authentication
- Building task API endpoints

**Recent Changes:**
- Migrated database to PostgreSQL
- Added JWT authentication

**Next Steps:**
- Complete task CRUD operations
- Add real-time notifications
```

#### Important Files
```markdown
**Project Documentation:**
- `docs/API.md` - API endpoint documentation
- `docs/ARCHITECTURE.md` - System architecture
- `config/database.yml` - Database configuration

**Module Structure:**
- `.memory/modules/auth-system/` - Authentication implementation
- `.memory/modules/task-api/` - Task management API
```

#### Project-Specific Guidelines
```markdown
**Coding Standards:**
- Use TypeScript strict mode
- Write unit tests for all services
- Follow RESTful API conventions

**Testing Requirements:**
- All features must have unit tests
- Integration tests for API endpoints
- Maintain >80% code coverage
```

### 3. Add to .gitignore

`CLAUDE.md` is personal and project-specific. Add it to `.gitignore`:

```bash
echo "CLAUDE.md" >> .gitignore
```

**Why exclude from git?**
- Contains your personal workflow preferences
- Status updates are temporal
- Each developer may have different focus areas
- Prevents merge conflicts

### 4. Keep It Updated

Update `CLAUDE.md` regularly:

**When to update:**
- Starting a new feature
- Making architectural decisions
- Changing project focus
- After major milestones

**Quick updates:**
```bash
# After recording work
m "Completed user authentication feature"
mcontext  # Updates .claude/memory-context.md automatically

# Then update CLAUDE.md "Current Status" section manually
```

---

## Integration with memory_tool

memory_tool automatically maintains `.claude/memory-context.md` with:
- Recent timeline entries (last 3 days by default)
- Active module states
- Current work context

**Workflow:**
1. Work on your project
2. Record progress: `m "description"`
3. Generate context: `mcontext`
4. Start Claude Code session
5. Claude reads both `CLAUDE.md` and `.claude/memory-context.md`

**CLAUDE.md vs memory-context.md:**

| File | Purpose | Updates | In Git? |
|------|---------|---------|---------|
| `CLAUDE.md` | Project guidelines, static context | Manual | No |
| `.claude/memory-context.md` | Recent timeline, auto-generated | Automatic (`mcontext`) | Optional |

---

## Examples

### Example 1: Web Application

```markdown
# For Claude Code 🤖

## 🎯 Project Overview

**Name:** TaskFlow Web App
**Purpose:** Real-time collaborative task management
**Tech Stack:** React, Node.js, PostgreSQL, Redis

## 📍 Current Status

**Active Work:**
- Phase 2: Real-time features (WebSocket integration)
- Implementing task notifications
- Adding team collaboration features

**Recent Decisions:**
- Use Socket.io for WebSocket (Decision #12)
- Redis for pub/sub messaging
- Optimistic UI updates for better UX

**Next Steps:**
- Complete notification system
- Add team invite feature
- Performance testing

## 🔄 Workflow Guidelines

**Before Coding:**
1. Check `.claude/memory-context.md` for recent work
2. Search past decisions: `ms "decision" --from 2025-11-01`
3. Review module docs: `.memory/modules/realtime-system/`

**After Coding:**
1. Record work: `m "Added WebSocket connection manager"`
2. Update module docs if architecture changed
3. Run tests: `npm test`
4. Update context: `mcontext`

## 📚 Important Files

**Architecture:**
- `docs/ARCHITECTURE.md` - System design
- `.memory/modules/realtime-system/` - WebSocket implementation
- `.memory/modules/auth-system/` - JWT authentication

**Configuration:**
- `config/socket.ts` - Socket.io configuration
- `config/redis.ts` - Redis pub/sub setup

## 🧭 Coding Standards

- TypeScript strict mode required
- Unit tests for all services (Jest)
- Integration tests for API endpoints (Supertest)
- Real-time features must handle disconnections
- Use optimistic updates for better UX
```

### Example 2: Python CLI Tool

```markdown
# For Claude Code 🤖

## 🎯 Project Overview

**Name:** data-processor
**Purpose:** CLI tool for processing and transforming large datasets
**Tech Stack:** Python 3.10+, Click, Pandas, DuckDB

## 📍 Current Status

**Active Work:**
- Adding streaming support for large files (>1GB)
- Implementing parallel processing
- Optimizing memory usage

**Recent Changes:**
- Migrated from CSV to Parquet for better performance
- Added DuckDB for SQL queries on datasets
- Implemented progress bars with rich

**Next Steps:**
- Add S3 input/output support
- Implement data validation rules
- Write comprehensive test suite

## 🔄 Workflow Guidelines

**Testing:**
- All features must have unit tests (pytest)
- Use fixtures for sample datasets
- Test with large files (>100MB) for performance

**Documentation:**
- Update CLI help text for new commands
- Add examples to README
- Document performance characteristics

## 📚 Important Files

**Core Modules:**
- `src/processor/streaming.py` - Streaming data processor
- `src/processor/parallel.py` - Parallel processing engine
- `src/storage/` - I/O adapters (CSV, Parquet, DuckDB)

**Configuration:**
- `config.yaml` - Default processing options
- `.memory/modules/processing-engine/` - Implementation docs

## 🧭 Development Principles

- Memory efficiency first (streaming over loading)
- Fail fast with clear error messages
- Progress feedback for long operations
- Support both CLI and Python API usage
```

### Example 3: Research Project

```markdown
# For Claude Code 🤖

## 🎯 Project Overview

**Name:** ML Model Experiments
**Purpose:** Research project testing different ML architectures
**Current Focus:** Transformer models for time-series forecasting

## 📍 Current Status

**Active Experiments:**
- Experiment #15: Attention mechanism variations
- Comparing LSTM vs Transformer performance
- Hyperparameter tuning for production model

**Recent Findings:**
- Transformers outperform LSTM by 12% (RMSE)
- Self-attention on 24-hour windows works best
- Positional encoding critical for time-series

**Next Steps:**
- Test with real production data
- Implement model ensemble
- Optimize inference speed

## 🔄 Research Workflow

**Experiment Process:**
1. Define hypothesis: `m "Experiment #16: Testing multi-head attention with 8 heads"`
2. Run experiment: `python train.py --config exp16.yaml`
3. Record results: `m "Exp #16 results: RMSE 0.145, 8% improvement"`
4. Document in module: `.memory/modules/experiments/exp16-results.md`

**Analysis:**
- Compare with baselines: `ms "baseline RMSE" --with-kb`
- Review past decisions: `ms "decision.*architecture"`

## 📚 Important Files

**Experiments:**
- `experiments/` - All experiment configs and results
- `.memory/modules/experiments/` - Detailed analysis

**Models:**
- `models/transformer.py` - Transformer implementation
- `models/lstm.py` - LSTM baseline
- `config/hyperparameters.yaml` - Tuning parameters

## 🧭 Research Guidelines

- Always compare against baseline
- Record negative results (important!)
- Document hyperparameters fully
- Version control all experiment configs
- Statistical significance testing required
```

---

## Tips & Best Practices

### 1. Keep It Concise

- Focus on actionable information
- Update "Current Status" frequently
- Archive old status to timeline: `m "Completed Phase 1"`

### 2. Link to Deeper Context

Don't duplicate what's in modules:
```markdown
**Authentication System:**
See `.memory/modules/auth-system/current.md` for implementation details
```

### 3. Use memory_tool Commands

Include relevant commands for Claude:
```markdown
**Common Tasks:**
- Find authentication code: `ms "JWT" --type modules`
- Review API decisions: `ms "API design" --with-kb`
- Check recent work: `mtoday`
```

### 4. Project-Specific Conventions

Document your conventions:
```markdown
**Naming Conventions:**
- Components: PascalCase (e.g., `TaskList.tsx`)
- Utilities: camelCase (e.g., `formatDate.ts`)
- Tests: `*.test.ts` or `*.spec.ts`

**Branch Strategy:**
- `main` - production
- `develop` - active development
- `feature/*` - new features
```

### 5. Update After Major Changes

After architectural changes:
```bash
# Record the change
m "Migrated from REST to GraphQL API"

# Update CLAUDE.md
# - Update tech stack
# - Update important files
# - Update workflow guidelines

# Regenerate context
mcontext
```

---

## Troubleshooting

### Claude Not Using CLAUDE.md?

**Check:**
1. File is named exactly `CLAUDE.md` (case-sensitive)
2. File is in project root directory
3. Claude Code is started from project root

### CLAUDE.md vs .claude/guidelines.md?

**Different purposes:**

- **CLAUDE.md** - Project-specific, what to work on
- **.claude/guidelines.md** - How to think and approach problems

Both are read by Claude Code. Use both for best results.

### Should I Commit CLAUDE.md to Git?

**Generally no:**
- It's personal workflow context
- Changes frequently
- Can cause merge conflicts

**Exception:** Team wants shared project overview
- Commit a generic version
- Each developer customizes locally
- Add to `.git/info/exclude` instead of `.gitignore`

---

## Integration with Other Tools

### VSCode

Add to `.vscode/settings.json`:
```json
{
  "files.associations": {
    "CLAUDE.md": "markdown"
  }
}
```

### Pre-commit Hook

Auto-update context before commits:
```bash
# .git/hooks/pre-commit
#!/bin/bash
mcontext
git add .claude/memory-context.md
```

### CI/CD

Generate context in CI for documentation:
```yaml
# .github/workflows/docs.yml
- name: Generate Memory Context
  run: |
    pip install memory-tool
    mcontext --output docs/current-context.md
```

---

## Advanced Usage

### Multiple Claude Code Profiles

Different profiles for different work modes:

```bash
# Development mode
cp CLAUDE.md.dev CLAUDE.md

# Review mode
cp CLAUDE.md.review CLAUDE.md

# Debugging mode
cp CLAUDE.md.debug CLAUDE.md
```

### Template Variables

Use placeholders for automation:
```markdown
**Last Context Update:** {{DATE}}
**Active Branch:** {{GIT_BRANCH}}
**Latest Commit:** {{GIT_COMMIT}}
```

Generate with script:
```bash
#!/bin/bash
DATE=$(date +"%Y-%m-%d %H:%M")
BRANCH=$(git branch --show-current)
COMMIT=$(git rev-parse --short HEAD)

sed -e "s/{{DATE}}/$DATE/" \
    -e "s/{{GIT_BRANCH}}/$BRANCH/" \
    -e "s/{{GIT_COMMIT}}/$COMMIT/" \
    CLAUDE.md.template > CLAUDE.md
```

---

## Summary

1. **Copy template:** `cp CLAUDE.md.template CLAUDE.md`
2. **Customize** with your project info
3. **Add to .gitignore:** `echo "CLAUDE.md" >> .gitignore`
4. **Update regularly** as project evolves
5. **Use with mcontext** for automatic timeline integration

**Result:** Claude Code understands your project context immediately and works more effectively with your codebase.

---

For more information:
- [USER_GUIDE.md](USER_GUIDE.md) - Complete memory_tool guide
- [QUICKSTART.md](QUICKSTART.md) - Get started in 5 minutes
- [FAQ.md](FAQ.md) - Common questions
