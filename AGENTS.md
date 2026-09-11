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
- **Cache Busting**: Whenever you modify `app.js` or `styles.css`, you MUST increment the cache-busting parameter (e.g. `?v=4` to `?v=5`) in `src/chagent/static/index.html` to prevent the browser from serving stale cached files to the user.

## 4. Documentation & Changelog Rules
- All changes must be tracked formally in `docs/CHANGELOG.md`.
- `docs/CHANGELOG.md` is strictly **append-only** (newer versions at the top). Do not edit or rewrite the history of older versions.
- A new version entry should only be added when making a version commit. Describe changes in more detail than a standard git commit message.

## 5. When Committing a Version
When a user requests to commit a new version, the following steps are strictly required: 
1. **Analyze:** View the `git diff` and review the contents of the current dialog to understand all changes made.
2. **Version Bump:** Determine the new version number (following Semantic Versioning) and update the version field in `docs/STATE.md`.
3. **Documentation:** 
   - Update `docs/CHANGELOG.md` with a detailed new version entry.
   - Ensure all high-level changes are reflected in `docs/STATE.md` and `docs/ARCHITECTURE.md`.
   - Check `docs/ROADMAP.md` and check off any completed tasks.
4. **Commit:** Stage all changes and make a Git commit with a clear, descriptive message (e.g., "Release v0.5.0: Added sandboxing security").
5. **Push:** Push the commit to the remote GitHub repository.
