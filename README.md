# claude-guardian

Self-learning project convention enforcer for Claude Code. Watches what Claude does, learns your project's patterns (naming, structure, imports, error handling), auto-generates `.claude/rules/*.md` files, and enforces them.

**Pure Python stdlib. Zero dependencies.**

## How it works

Guardian operates in three phases based on how many sessions you've had in a project:

| Phase | Sessions | Behavior |
|-------|----------|----------|
| **OBSERVE** | 1–5 | Silently collects events. No enforcement. |
| **SUGGEST** | 6–10 | Warns about convention violations but allows them. |
| **ENFORCE** | 11+ | Blocks edits that violate learned conventions. |

### What it learns

- **Naming conventions** — PascalCase, camelCase, kebab-case, snake_case per directory
- **Project structure** — where tests, components, utils live
- **Import style** — relative vs alias vs package imports, import ordering
- **Export style** — default vs named exports
- **Error handling** — try-catch vs .catch() vs Result types
- **Tooling** — test runners, package managers, linters

### How patterns become rules

A pattern is promoted to a rule only when:
- **Confidence > 85%** — at least 85% of samples follow the pattern
- **Sample size > 15** — enough data points to be meaningful

Rules are written as `.claude/rules/guardian-*.md` files with frontmatter globs for file matching. They're human-readable and editable — Guardian will never overwrite a rule you've manually edited.

## Installation

```bash
# Clone or install as a Claude Code plugin
# Then run:
bash install.sh    # Linux/macOS
# or
powershell install.ps1  # Windows
```

This creates `~/.claude/guardian/` for storing events, state, and learned patterns.

## Data storage

All data lives in `~/.claude/guardian/`:

| File | Purpose |
|------|---------|
| `events.jsonl` | Raw events (one JSON per line) |
| `state.json` | Session count, current phase |
| `patterns.json` | Learned patterns with confidence scores |

## .guardianignore

Create a `.guardianignore` file in your project root to skip enforcement on specific files. Uses glob patterns:

```
# Generated files
dist/**
build/**

# Config files
*.config.js

# Migrations
migrations/**
```

See `.guardianignore.example` for a full template.

## Cold-start scan

On the first session in a project, Guardian walks the project tree (up to 500 files) to bootstrap patterns from existing code. This means it has useful conventions learned before you even start coding.

## Architecture

```
.claude-plugin/plugin.json   — Plugin metadata
hooks/
  hooks.json                 — Hook definitions
  run_hook.sh                — Shell runner
  session_start.py           — Increment session, determine phase
  collect_edit.py            — Collect Edit/Write events (async)
  collect_bash.py            — Collect Bash events (async)
  enforce.py                 — PreToolUse enforcement (5s timeout)
  analyze.py                 — Run analyzers on Stop (async)
server/
  store.py                   — JSONL event store + JSON state
  analyzers.py               — Pattern detection (frequency counting + regex)
  rule_generator.py          — .claude/rules/ markdown generator
```

## License

MIT
