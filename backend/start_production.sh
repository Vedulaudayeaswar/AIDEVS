#!/usr/bin/env bash
# Production start (same command Render uses). Migrations run on boot via AUTO_MIGRATE.
set -euo pipefail
pip install -r requirements.txt
exec gunicorn -k gevent -w 1 --worker-connections 200 --timeout 180 --bind "0.0.0.0:${PORT:-5000}" "app:create_app()"
