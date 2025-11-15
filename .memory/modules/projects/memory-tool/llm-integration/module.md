# Module: projects/memory-tool/llm-integration

**Created:** 2025-11-15
**Tags:** llm, ai, summarization, embeddings, anthropic, ollama

## Purpose

AI-powered features using Large Language Models: Timeline/module summarization, semantic embeddings for search, AI-based connection suggestions, and intelligent tagging. Supports both cloud (Anthropic) and local (Ollama) providers.

## Scope

**Included:**
- **Timeline Summarization**: Day/week/range summaries with context
- **Module Summarization**: Module status and progress summaries
- **Conversation Summarization**: Infrastructure for future use
- **Semantic Embeddings**: Vector generation for similarity search
- **AI Suggestions**: Connection recommendations, auto-tagging
- **Dual Providers**: Anthropic API (cloud) + Ollama (local)
- **Context Management**: Project context injection, token management
- **Multi-language**: Korean/English output support
- **CLI**: `summary` command, AI flags in other commands

**Provider Support:**
- **Anthropic**: claude-3-5-sonnet-20241022 (high quality)
- **Ollama**: qwen2.5:7b (local, free, offline)

**Excluded:**
- Timeline storage → [[projects/memory-tool/core-system]]
- Search ranking → [[projects/memory-tool/search-system]]
- Module graph logic → [[projects/memory-tool/module-system]]
- UI presentation → [[projects/memory-tool/ui-system]]

## Architecture

**Summarization Pipeline:**
1. Content gathering (timeline entries, decisions, module state)
2. Context injection (project overview, recent decisions)
3. Prompt building (dynamic, language-aware)
4. LLM call (with retry/fallback)
5. Output formatting (markdown, categories)

**Embedding Generation:**
- Model: `all-MiniLM-L6-v2` (sentence-transformers)
- Batch processing: 10-50x speedup
- Incremental updates: Only new/changed content
- Caching: Persistent embeddings database

**AI Suggestions:**
- Content similarity analysis
- Connection pattern detection
- Tag extraction and recommendation
- Confidence scoring

**Context Management:**
- Smart context injection (minimal for today, full for week)
- Token limit enforcement (configurable)
- Language detection (Korean/English character ratio)

**Related Decisions:**
- Decision #26: Dual provider support
- Decision #27: Local-first with Ollama
- Decision #28: Timeline summarization strategy
- Decision #29: Archive automation

## Related Modules

- [[projects/memory-tool/search-system]] - Provides embeddings
- [[projects/memory-tool/module-system]] - Gets AI suggestions
- [[projects/memory-tool/core-system]] - Summarizes timeline
- [[projects/memory-tool/ui-system]] - Displays summaries
