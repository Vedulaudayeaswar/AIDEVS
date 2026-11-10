# Contributing to AIDevs

Thanks for helping! Small, focused pull requests are easiest to review.

## Setup
Follow **Run locally** in the [README](README.md). You need your own free Groq API key only to exercise AI features;
all automated tests run without one (they use a deterministic fake model client).

## Before opening a PR
```bash
cd backend
pip install -r requirements-dev.txt
ruff check .                 # lint + security rules
python -m pytest -q          # backend tests
cd ..
npx eslint src --max-warnings=0
CI=true npx react-scripts test --watchAll=false
CI=true npm run build
```
CI runs the same checks plus PostgreSQL tests, `alembic check`, dependency audits and gitleaks.

## Guidelines
- **Schema changes:** edit `backend/models.py`, then `python manage.py makemigration "message"`. Review the generated
  file: new `NOT NULL` columns need a `server_default` so existing databases upgrade in place. Never delete user data
  in a migration.
- **AI features:** agents must return JSON validated by a function in `agents/studio/*` or `services/schema.py`.
  Never apply unvalidated model output; mutate projects only inside a job with a snapshot first.
- **Security:** every new project-scoped route must call `get_owned_project`. Never log secrets, tokens or passwords.
- **Real-model tests:** `GROQ_API_KEY=… RUN_REAL_AI=1 python -m pytest tests/real_ai -v -s` (uses your quota).
- Use conventional, descriptive commit messages. Do not commit `.env` files or build output.

By contributing you agree your work is licensed under the MIT License and to follow the
[Code of Conduct](CODE_OF_CONDUCT.md).
