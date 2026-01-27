---
name: mt-master-module
description: Creates project-wide overview for KB federation. Use when user requests "마스터 모듈 만들어줘", "create master module", or needs a project overview document for cross-project knowledge sharing.
---

# MT-Master-Module: Project Overview Creator

> **"One document to represent your entire project."**

This skill creates a comprehensive project overview document that serves as the entry point for understanding a project in the federated knowledge system.

## When to Use

- User explicitly requests: "마스터 모듈 만들어줘", "create master module", "프로젝트 개요 만들어줘"
- Project is mature enough to summarize
- Preparing for KB federation (multiple projects sharing knowledge)

**For publishing specific modules, use `mt-publish` instead.**

## Workflow

### Phase 1: Gather Information

**Read project context:**
```bash
cat .claude/memory-context.md
cat CLAUDE.md
mmodule tree
```

**Review key modules:**
```bash
cat .memory/modules/projects/*/current.md
cat .memory/modules/projects/*/decisions.md
```

**Check timeline for milestones:**
```bash
mweek
mtoday
```

### Phase 2: Create Master Module

**Create module structure:**
```bash
mmodule create master
```

**Required files:**
- `current.md` - Project overview (main document)
- `decisions.md` - Architectural decisions summary

### Phase 3: Write Content

**Master module template (current.md):**

```markdown
# [Project Name] - Master Module

> One-sentence project description

## Project Identity

- **Name:** [Project Name]
- **Purpose:** [Core problem being solved]
- **Started:** [Date]
- **Status:** [Active/Maintenance/Archived]

## Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Language | Python 3.10+ | Type hints, async support |
| Database | SQLite | Zero-config, portable |
| CLI | Click | Decorator-based, composable |

## Architecture Overview

[High-level architecture diagram or description]

### Key Components

1. **Component A** - [Purpose]
2. **Component B** - [Purpose]
3. **Component C** - [Purpose]

## Module Index

| Module | Purpose | Status |
|--------|---------|--------|
| core-system | Timeline and initialization | Active |
| search-system | Text and semantic search | Active |
| ui-system | CLI and TUI interfaces | Active |

## Key Decisions

| Decision | Rationale | Date |
|----------|-----------|------|
| SQLite for storage | Zero-config, portable | 2025-01 |
| BM25 for search | Fast, no dependencies | 2025-02 |

## Lessons Learned

### What Worked Well
- [Pattern or approach that succeeded]
- [Another success]

### What We'd Do Differently
- [Retrospective insight]
- [Another insight]

## Getting Started

```bash
# Installation
pip install [package]

# Basic usage
[command] "example"
```

## Related Resources

- **Documentation:** [Link or path]
- **Repository:** [Link]
- **Published Modules:** [KB paths]
```

### Phase 4: Validate

**Self-check questions:**
1. Can a new team member understand the project from this document?
2. Are all major decisions documented with rationale?
3. Is the tech stack clearly specified?
4. Are module relationships clear?

### Phase 5: Publish (Optional)

After creating the master module, optionally publish to KB:

```bash
mpublish master --tags project-overview
```

## Output Format

```
Analyzing project for master module creation...

Project: memory-tool
Status: Active
Modules found: 6

Creating master module...

Files created:
- .memory/modules/master/current.md
- .memory/modules/master/decisions.md
- .memory/modules/master/module.md

Next steps:
1. Review and customize the generated content
2. Add project-specific details
3. Optionally publish: mpublish master
```

## Best Practices

1. **Keep it high-level** - Details belong in specific modules
2. **Update regularly** - Refresh when major changes occur
3. **Link to modules** - Use [[wiki-links]] to connect to detailed modules
4. **Include "why"** - Decisions without rationale are not useful
5. **Version awareness** - Note when significant changes were made

## Example

**User:** "마스터 모듈 만들어줘"

**Response:**
```
Let me analyze your project and create a master module.

[Read project files]

Project: memory-tool
Purpose: Time-Space Integrated Knowledge System
Tech Stack: Python, SQLite, Click
Modules: 6 active modules

Creating master module...

Created:
- .memory/modules/master/current.md (project overview)
- .memory/modules/master/decisions.md (key decisions)
- .memory/modules/master/module.md (module definition)

Please review the generated content and add any missing details.

Would you like to publish this to KB?
```
