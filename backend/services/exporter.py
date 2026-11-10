"""Assemble the downloadable full-stack project (React + Flask + tests + deploy)."""
import io
import json
import mimetypes
import re
import zipfile

from services.compiler import compose_page
from services.export_backend import backend_files
from services.export_frontend import frontend_files
from services.schema import sanitize_subtree, sanitize_tree

ASSET_RE = re.compile(r"/api/assets/([0-9a-f]{32})")


def project_snapshot(project, pages, entities):
    return {
        "name": project.name, "description": project.description, "spec": project.spec,
        "tokens": project.tokens, "layout": project.layout,
        "pages": [{"name": p.name, "route": p.route, "position": p.position, "tree": p.tree, "seo": p.seo}
                  for p in pages],
        "entities": [{"name": e.name, "label": e.label, "fields": e.fields, "permissions": e.permissions,
                      "sample_data": e.sample_data} for e in entities],
    }


def readme(name, entities, pages):
    entity_list = "\n".join(f"- **{e['label']}** (`{e['name']}`)" for e in entities) or "- (none)"
    page_list = "\n".join(f"- `{p['route']}` — {p['name']}" for p in pages)
    return f"""# {name}

Full-stack application generated with **AIDevs 2.0**.

* `frontend/` — React 18 + Vite single-page app
* `backend/` — Flask + SQLAlchemy REST API with JWT auth
* `API.md` — endpoint reference

## Pages
{page_list}

## Data models
{entity_list}

## Run locally

### 1. Backend (Python 3.10+)
```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\activate   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit JWT_SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
python seed.py                # creates the admin user + sample data
python app.py                 # http://localhost:5000
```

### 2. Frontend (Node 18+)
```bash
cd frontend
npm install
cp .env.example .env          # VITE_API_URL=http://localhost:5000
npm run dev                   # http://localhost:5173
```

### Tests
```bash
cd backend && pytest
```

### Docker
```bash
JWT_SECRET_KEY=$(python -c "import secrets;print(secrets.token_urlsafe(48))") docker compose up --build
```

## Database
SQLite by default (`DATABASE_URL=sqlite:///app.db`). For production set `DATABASE_URL` to PostgreSQL.
Tables are created automatically on start; reference DDL lives in `backend/migrations/`.

## Admin access
Register (or seed) with the email in `ADMIN_EMAIL` to get the `admin` role, which is required for
admin-only operations listed in `API.md`.

## Deploy
`render.yaml` deploys the API, the static frontend and a PostgreSQL database on Render. Set
`VITE_API_URL` on the static site to the API URL and `CORS_ORIGINS` on the API to the site URL.

## Editing in AIDevs
`aidevs.project.json` contains the full design source (pages, design tokens, data models) and
`aidevs.sourcemap.json` maps every visual element id to the component file and CSS class that renders it.
"""


DOCKER_COMPOSE = """services:
  api:
    build: ./backend
    environment:
      JWT_SECRET_KEY: ${JWT_SECRET_KEY:?set JWT_SECRET_KEY}
      DATABASE_URL: postgresql://app:app@db:5432/app
      CORS_ORIGINS: http://localhost:5173
      ADMIN_EMAIL: ${ADMIN_EMAIL:-admin@example.com}
    ports: ["5000:5000"]
    depends_on: [db]
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    volumes: [dbdata:/var/lib/postgresql/data]
volumes:
  dbdata:
"""


def render_yaml(slug):
    return f"""services:
  - type: web
    name: {slug}-api
    runtime: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn -w 2 -b 0.0.0.0:$PORT "app:create_app()"
    healthCheckPath: /api/health
    envVars:
      - key: JWT_SECRET_KEY
        generateValue: true
      - key: DATABASE_URL
        fromDatabase:
          name: {slug}-db
          property: connectionString
      - key: CORS_ORIGINS
        sync: false
      - key: ADMIN_EMAIL
        sync: false
  - type: web
    name: {slug}-web
    runtime: static
    rootDir: frontend
    buildCommand: npm install && npm run build
    staticPublishPath: dist
    routes:
      - type: rewrite
        source: /*
        destination: /index.html
    envVars:
      - key: VITE_API_URL
        sync: false
databases:
  - name: {slug}-db
    plan: free
"""


def build_export(project, pages, entities, assets):
    """Return (zip_bytes, file_list). `assets` maps asset id -> Asset row."""
    asset_map = {}
    for asset_id, asset in assets.items():
        ext = mimetypes.guess_extension(asset.content_type) or ".bin"
        asset_map[f"/api/assets/{asset_id}"] = f"/assets/{asset_id}{ext}"

    # Defense in depth: never compile anything that has not passed the sanitizer.
    page_dicts = [{"name": p.name, "route": p.route, "tree": sanitize_tree(compose_page({}, p.tree))[0],
                   "seo": p.seo or {}} for p in pages]
    layout = {k: sanitize_subtree(v)[0] for k, v in (project.layout or {}).items()
              if k in ("header", "footer") and isinstance(v, dict)}
    entity_dicts = [{"name": e.name, "label": e.label, "fields": e.fields, "permissions": e.permissions,
                     "sample_data": e.sample_data or []} for e in entities]
    project_dict = {"name": project.name, "description": project.description, "layout": layout}
    slug = re.sub(r"[^a-z0-9-]+", "-", project.name.lower()).strip("-")[:40] or "aidevs-app"

    files, sourcemap = frontend_files(project_dict, page_dicts, entity_dicts, project.tokens, asset_map)
    files.update(backend_files(project.name, entity_dicts))
    files["README.md"] = readme(project.name, entity_dicts, page_dicts)
    files["docker-compose.yml"] = DOCKER_COMPOSE
    files["render.yaml"] = render_yaml(slug)
    files[".gitignore"] = "node_modules/\ndist/\n.env\n__pycache__/\n*.db\n.venv/\n"
    files["aidevs.sourcemap.json"] = json.dumps(sourcemap, indent=2)
    files["aidevs.project.json"] = json.dumps(project_snapshot(project, pages, entities), indent=2,
                                              ensure_ascii=False)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in sorted(files.items()):
            zf.writestr(f"{slug}/{path}", content)
        for asset_id, asset in assets.items():
            zf.writestr(f"{slug}/frontend/public{asset_map[f'/api/assets/{asset_id}']}", asset.data)
    return buffer.getvalue(), sorted(files.keys()), files


def referenced_asset_ids(project, pages):
    blob = json.dumps([project.layout, [p.tree for p in pages]])
    return set(ASSET_RE.findall(blob))
