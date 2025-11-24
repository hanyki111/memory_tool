# .memory Documentation

Welcome to your memory_tool project! This directory contains essential documentation for organizing your knowledge.

## Quick Start

**Core Concept:** memory_tool uses two axes:
- **Time Axis:** `.memory/timeline/` - Capture thoughts instantly
- **Space Axis:** `.memory/modules/` - Organize into structured modules

**Basic Commands:**
```bash
# Record to timeline (0.5 seconds)
m "Your thought or decision"

# Search timeline
ms "search query"

# View today's entries
mtoday

# Create a module
module create projects/my-project

# Build Claude Code context
mcontext
```

## Documentation Files

**Quick Reference:**
- `QUICK-REFERENCE-MODULE-ORGANIZATION.md` - Fast decision guide for module operations

**Comprehensive Guide:**
- `MODULE-ORGANIZATION-PRINCIPLES.md` - Complete module organization principles

## Module Organization

**When to create a module:**
- New project or major feature (>500 lines expected)
- Independent concern (different topic/lifecycle)
- Reusable component

**When to split a module:**
- `current.md` > 300 lines
- More than 20 decisions
- More than 3 distinct topics

**Quick Decision:**
```
Small enhancement (<100 lines)  → Add to existing module
New feature (>500 lines)        → Create new module
Unrelated topic                 → Create new module
Part of existing project        → Create child module
```

## Best Practices

**Timeline Recording:**
- Capture first, organize later (0.5-second principle)
- Record everything, lose nothing
- Use `m "message"` frequently

**Module Organization:**
- Single responsibility per module
- Clear parent-child hierarchy
- Wiki-style [[connections]] between modules

**Documentation:**
- Keep `current.md` under 300 lines
- Archive old decisions regularly
- Use `mcontext` to update Claude Code context

## Need Help?

**Full Documentation:**
- See `MODULE-ORGANIZATION-PRINCIPLES.md` for detailed guidelines
- See `QUICK-REFERENCE-MODULE-ORGANIZATION.md` for quick decisions

**Commands:**
```bash
# Get help
python -m memory_tool --help

# Module management
module create <name>
module list
module tree
module archive <name>

# Search
ms "query"
ms --semantic "query"
ms --after 2025-11-01 "query"

# Context
mcontext               # Update Claude Code context
mtoday                 # Today's timeline
mweek                  # This week's timeline
```

---

**Philosophy:** "Capture in 0.5 seconds, organize on weekends, use for life."
