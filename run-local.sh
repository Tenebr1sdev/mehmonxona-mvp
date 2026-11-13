#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo "Xato: Python 3 topilmadi. Python 3.10 yoki yangirog‘ini o‘rnating."
  exit 1
fi
if [ ! -d .venv ]; then
  python3 -m venv .venv || {
    echo "Virtual muhit yaralmadi. Debian/Parrot OS’da python3-venv paketini o‘rnating:"
    echo "sudo apt update && sudo apt install python3-venv python3-pip"
    exit 1
  }
fi
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export DATABASE_URL="${DATABASE_URL:-sqlite:///./hotel-local.db}"
export SECRET_KEY="${SECRET_KEY:-local-development-secret-change-before-sharing}"
export ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
export ADMIN_PASSWORD="${ADMIN_PASSWORD:-Admin123!}"
export DEMO_PASSWORD="${DEMO_PASSWORD:-Demo123!}"
export UPLOAD_DIR="${UPLOAD_DIR:-./uploads}"
python -m alembic upgrade head
python -m app.seed
exec python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
