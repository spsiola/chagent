# Antigravity Rules for Chagent Project

## 1. Initializing Context (Vibe Coding)
When you start a new conversation or session in this repository, **YOUR FIRST ACTION** must be to read the following file to restore your context about what this project is and what we are doing:
- `docs/STATE.md` (Contains current project state)
- `docs/CHANGELOG.md` (Contains detailed recent changes)

Whenever you are asked to design a new feature or debug an architectural issue, consult:
- `docs/ARCHITECTURE.md` (Contains technical design decisions)
- `docs/ROADMAP.md` (Contains future plans)

## 2. Python & Development Rules
- Use modern Python 3.12+ features (type hinting, async/await).
- Manage dependencies and virtual environments with `uv`. (Do not use pip directly).
- Execution should always be done via `uv run chagent ...`.
- Keep the agent logic modular: separate LLM client (`agent.py`), tool execution, and MCP communication (`mcp_integration.py`).
- Use `pydantic` for configuration management and data validation.
- Standard tools should be pure Python functions with clear docstrings for the LLM to understand.

## 3. Web & Frontend Rules
- The UI is designed to be "Premium" (Dark mode, glassmorphism, smooth animations).
- Use Vanilla CSS and Vanilla JS. Avoid frameworks like React or Tailwind unless explicitly requested.
- Maintain the current clean structure in `src/chagent/static/` (`index.html`, `styles.css`, `app.js`).

## 4. Documentation & Changelog Rules
- All changes must be tracked formally in `docs/CHANGELOG.md`.
- `docs/CHANGELOG.md` is strictly **append-only** (newer versions at the top). Do not edit or rewrite the history of older versions.
- A new version entry should only be added when making a version commit. Describe changes in more detail than a standard git commit message.
