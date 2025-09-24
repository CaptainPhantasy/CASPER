#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)
cd "$SCRIPT_DIR"

export PORT=8742
export CASPER_OUTPUT_DIR=".casper/generated"

echo "Starting CASPER Prime API on :$PORT"
PY_CMD="uvicorn core.server:app --host 0.0.0.0 --port $PORT"

($PY_CMD &)
API_PID=$!

echo "Starting Dashboard on :9318"
cd dashboard
npm run dev &
UI_PID=$!

cd ..
echo "API PID: $API_PID, UI PID: $UI_PID"
echo "Logs: API in terminal, UI in Vite output"
echo "Dashboard: http://localhost:9318"
echo "API: http://localhost:8742"

cleanup() {
  echo "Shutting down..."
  kill $API_PID $UI_PID 2>/dev/null || true
}
trap cleanup EXIT INT TERM

wait

