#!/bin/sh
set -eu

term() {
  if [ -n "${WEBSITE_PID:-}" ]; then kill "$WEBSITE_PID" 2>/dev/null || true; fi
  if [ -n "${WEB_PID:-}" ]; then kill "$WEB_PID" 2>/dev/null || true; fi
}

trap term INT TERM

cd /app
npm run dev -w uis/website -- -H 0.0.0.0 -p 3000 &
WEBSITE_PID=$!
npm run dev -w uis/web -- -H 0.0.0.0 -p 3001 &
WEB_PID=$!

wait "$WEBSITE_PID" "$WEB_PID"
