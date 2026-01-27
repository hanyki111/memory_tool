---
name: mt-publish
description: Refines project module knowledge and publishes to central KB. Use when user requests "KB에 발행해줘", "publish to KB", "모듈 발행해줘", or wants to share a specific module across projects.
---

# MT-Publish: Module Publisher

> **"Execution should be isolated, but Knowledge must be federated."**

This skill helps refine a specific module's knowledge into reusable, context-independent artifacts and publish them to the central Knowledge Base.

## When to Use

- User explicitly requests: "KB에 발행해줘", "publish to KB", "모듈 발행해줘"
- User wants to share a specific module's learnings
- Module is mature and worth preserving

**For project-wide overview, use `mt-master-module` instead.**

## Workflow

### Phase 1: Analyze (분석)

**Review target module:**
```bash
cat .memory/modules/<path>/current.md
cat .memory/modules/<path>/decisions.md
cat .memory/modules/<path>/module.md
```

**Identify publishable content:**
- Core patterns and architectures
- Reusable solutions
- Key decisions with rationale

### Phase 2: Refine (정제)

**De-contextualization:**
- Remove project-specific paths, variable names
- Generalize code examples
- Make dependencies explicit

**Before (project-specific):**
```python
from myproject.auth import JWTHandler
db = connect("postgres://myproject:pass@localhost/mydb")
```

**After (generalized):**
```python
# Requires: pyjwt, psycopg2
from auth_module import JWTHandler  # Your JWT implementation
db = connect(DATABASE_URL)  # Set via environment variable
```

**Add explicit dependencies:**
```markdown
## Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Required packages: pyjwt, psycopg2
```

### Phase 3: Validate (검증)

**Self-check question:**
> "이 문서만 보고, 빈 프로젝트에서 해당 기능을 구현할 수 있는가?"

If missing information, add:
- Environment variables needed
- Database schema
- External service setup
- Configuration files

### Phase 4: Publish (발행)

**Preview first:**
```bash
mpublish <module-name> --dry-run
```

**Publish with metadata:**
```bash
mpublish <module-name> --tags auth,security,jwt
```

**Verify:**
```bash
mimport --list
```

## Output Format

```
Analyzing module: auth-system

Key artifacts found:
- JWT authentication pattern
- Role-based access control
- Session management

Refinement needed:
- Remove hardcoded secrets
- Generalize database schema
- Add environment variable docs

Ready to publish?
[Preview] mpublish auth-system --dry-run
```

## Best Practices

1. **Don't publish raw code** - Only refined, documented knowledge
2. **Include "why"** - Decisions without rationale are not knowledge
3. **Make it standalone** - Reader shouldn't need project context
4. **Version awareness** - Note library/framework versions
5. **Test instructions** - Ensure steps are reproducible

## Error Handling

**KB not configured:**
```
KB path not set. Configure with:
mconfig set kb.path ~/your/kb/path
```

**Module not found:**
```
Module 'xxx' not found. Available modules:
mmodule tree
```

## Example

**User:** "search-system 모듈 KB에 발행해줘"

**Response:**
```
Let me analyze the search-system module for publishing.

[Read module files]

Found:
- Hybrid search (text + semantic)
- BM25 ranking algorithm
- SQLite FTS5 indexing

Refinements needed:
- Generalize database paths
- Document embedding model requirements
- Add performance tuning notes

Preview:
mpublish search-system --tags search,fts5,hybrid --dry-run

Proceed with publishing?
```
