#!/usr/bin/env bash
set -euo pipefail
API="${API:-http://localhost:8000/api/v1}"
echo "Health"; curl -sf "$API/health" | head -c 200; echo
echo "Security headers via root"; curl -sI http://localhost:8000/ | tr -d '\r' | egrep -i 'x-frame|content-security|x-content-type' || true
