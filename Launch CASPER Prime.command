#!/bin/bash
# macOS double-click launcher for CASPER Prime

set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR/casper-prime" || {
  echo "Could not find casper-prime directory next to this launcher.";
  exit 1;
}

# Activate venv if present
if [ -f "venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
fi

export PORT=8742
export CASPER_OUTPUT_DIR=".casper/generated"

echo "🔧 Ensuring dependencies are installed..."
if ! python3 -c "import fastapi" >/dev/null 2>&1; then
  echo "📦 Installing Python dependencies..."
  pip3 install -r requirements.txt || pip install -r requirements.txt
fi

if [ ! -d "dashboard/node_modules" ]; then
  echo "📦 Installing dashboard dependencies..."
  (cd dashboard && npm install)
fi

echo "🚀 Launching CASPER Prime (API :$PORT, Dashboard :9318)"

# Open the dashboard in the default browser shortly after startup
(sleep 3; open "http://localhost:9318") &

exec bash start_all.sh

