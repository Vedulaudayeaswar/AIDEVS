## What & why

## How was it tested?
- [ ] `ruff check .` and `python -m pytest -q` (backend)
- [ ] `npx eslint src --max-warnings=0`, frontend tests and `CI=true npm run build`
- [ ] New migration reviewed (server defaults, no data loss) — if models changed
- [ ] New project routes call `get_owned_project`; no secrets/tokens logged

## Screenshots (UI changes)
