# freight-quote-agent — Project CLAUDE.md

Extends `/Users/bobmoses/.claude/CLAUDE.md`. Project rules win on conflicts.

## Project Overview

- **Name:** freight-quote-agent
- **Type:** AI agent / backend service
- **Primary language:** Python 3.11+
- **Purpose:** Automates freight quote retrieval and comparison using Claude as the reasoning engine.

## Language-specific Defaults

- Use `python-dotenv` for env loading at the boundary only (entry points / tests).
- Pydantic models for all external data shapes (API responses, user input).
- `httpx` for all HTTP calls (async-capable, consistent with agentic patterns).
- No global mutable state. Pass context explicitly.

## Tests

- Location: `tests/`
- Runner: `pytest`
- Run all: `pytest`
- Run single file: `pytest tests/test_foo.py`
- No mocking of live HTTP unless test is explicitly marked `@pytest.mark.unit`.

## Lint / Format

- No formatter enforced yet — match surrounding style (4-space indent, double quotes).
- Add linter config in a future sprint if complexity warrants it.

## Domain Conventions

- A "quote" is a structured response from a freight carrier API containing price, transit time, and carrier ID.
- Agent tools are defined in `src/tools/`. Each tool is a single-responsibility callable.
- Prompts live in `src/prompts/`. Never inline multi-line prompts in agent logic.

## CI/CD

- No CI configured yet. Do not push without explicit user confirmation.
- Branch: `main` is the only branch until sprint 2.

## .state/ Convention

Follows global standard. `.state/` is gitignored. Orchestrator owns `context.md` and `session.log`.
