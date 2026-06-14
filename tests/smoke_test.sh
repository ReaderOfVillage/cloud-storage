#!/usr/bin/env bash
# smoke_test.sh — runs after "docker compose up -d" in CI.
# Hits every endpoint once with curl and fails fast if anything looks wrong.
# Exit code 0 = all good, non-zero = pipeline should fail.

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
MAX_WAIT=30   # seconds to wait for the API to become ready

# ── colours ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; RED='\033[0;31m'; NC='\033[0m'
pass() { echo -e "${GREEN}✓ $1${NC}"; }
fail() { echo -e "${RED}✗ $1${NC}"; exit 1; }

# ── wait for API ────────────────────────────────────────────────────────────
echo "Waiting for API at $BASE_URL ..."
for i in $(seq 1 $MAX_WAIT); do
  if curl -sf "$BASE_URL/files" > /dev/null 2>&1; then
    pass "API is up (attempt $i)"
    break
  fi
  if [ "$i" -eq "$MAX_WAIT" ]; then
    fail "API did not become ready within ${MAX_WAIT}s"
  fi
  sleep 1
done

# ── GET /files — expect empty list ──────────────────────────────────────────
BODY=$(curl -sf "$BASE_URL/files")
if echo "$BODY" | grep -q '\[\]'; then
  pass "GET /files returns empty list"
else
  fail "GET /files unexpected body: $BODY"
fi

# ── POST /upload ─────────────────────────────────────────────────────────────
echo "hello smoke test" > /tmp/smoke_file.txt
UPLOAD_RESP=$(curl -sf -X POST "$BASE_URL/upload" \
  -F "file=@/tmp/smoke_file.txt;type=text/plain")

FILE_ID=$(echo "$UPLOAD_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])" 2>/dev/null || true)

if [ -z "$FILE_ID" ]; then
  fail "POST /upload did not return an id. Response: $UPLOAD_RESP"
fi
pass "POST /upload returned id: $FILE_ID"

# ── GET /files — should now have one entry ───────────────────────────────────
BODY=$(curl -sf "$BASE_URL/files")
if echo "$BODY" | grep -q "$FILE_ID"; then
  pass "GET /files contains uploaded file"
else
  fail "GET /files missing uploaded file. Body: $BODY"
fi

# ── GET /download/{id} ───────────────────────────────────────────────────────
DOWNLOADED=$(curl -sf "$BASE_URL/download/$FILE_ID")
if echo "$DOWNLOADED" | grep -q "hello smoke test"; then
  pass "GET /download/$FILE_ID returned correct content"
else
  fail "GET /download/$FILE_ID wrong content: $DOWNLOADED"
fi

# ── DELETE /files/{id} ───────────────────────────────────────────────────────
DEL_RESP=$(curl -sf -X DELETE "$BASE_URL/files/$FILE_ID")
if echo "$DEL_RESP" | grep -q "deleted"; then
  pass "DELETE /files/$FILE_ID returned status=deleted"
else
  fail "DELETE /files/$FILE_ID unexpected response: $DEL_RESP"
fi

# ── GET /metrics — Prometheus endpoint ───────────────────────────────────────
METRICS=$(curl -sf "$BASE_URL/metrics")
if echo "$METRICS" | grep -q "file_uploads_total"; then
  pass "GET /metrics contains file_uploads_total"
else
  fail "GET /metrics missing expected metric"
fi

echo ""
pass "All smoke tests passed!"