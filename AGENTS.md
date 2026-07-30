# AGENTS.md — HealthCore Digital

Rules for any AI agent working in this repository.

## Session start — required reads (in order)

Before making changes, read:

1. [`memory-bank/projectBrief.md`](memory-bank/projectBrief.md)
2. [`memory-bank/productContext.md`](memory-bank/productContext.md)
3. [`memory-bank/techContext.md`](memory-bank/techContext.md)
4. [`memory-bank/progress.md`](memory-bank/progress.md)
5. [`memory-bank/systemPatterns.md`](memory-bank/systemPatterns.md) when changing architecture or folder layout
6. Relevant scoped rules under [`.agents/rules/`](.agents/rules/) for the paths you will touch

## Mandatory delivery workflow (before every commit)

Follow these steps **in order**. Do not skip.

1. **Confirm context** — Memory-bank files above were read this session; apply matching `.agents/rules/` for edited paths.
2. **Implement in allowed paths only** — Leave protected paths untouched unless the user gave explicit instruction to change them.
3. **Verify** — Run [`skills/pre-delivery-verification`](skills/pre-delivery-verification/SKILL.md). Acceptance criteria must pass (typecheck for UI work; Milestone 2 output visible in the DOM for backoffice analytics).
4. **Update progress** — If milestone or deliverable status changed, update [`memory-bank/progress.md`](memory-bank/progress.md).
5. **Commit** — Only after verification passes; use a clear message focused on why.

## Folders and files agents MUST NOT modify without explicit instruction

| Path | Reason |
|------|--------|
| `CONTEXT-healthcore.md` | Canonical company briefing |
| `CONTEXT.md` | Template / programme placeholder |
| `src/types/**` | Milestone 2 domain models & sample data — **import only** |
| `src/utils/**` | Milestone 2 business logic — **import only** |
| `uis/index.html` | Milestone 1 archive |
| `uis/application.html` | Milestone 1 archive |
| `uis/validation.js` | Milestone 1 archive |
| `.env`, `.env.*`, credentials files | Secrets |
| `.git/` | Version control internals |

## Where to put new work

| Kind of work | Location |
|--------------|----------|
| Public website | `uis/website/` |
| Internal app | `uis/backoffice/` |
| HTTP APIs | `services/` only |
| Agent rules | `.agents/rules/` |
| Agent skills | `skills/<skill-name>/` |
| Persistent context | `memory-bank/` |

## Skill for recurring delivery checks

Use **`skills/pre-delivery-verification`** before every commit that changes UI, agent scaffolding, or docs that affect delivery status.
