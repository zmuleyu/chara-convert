#!/usr/bin/env bash
# chara-convert production smoke test.
# Hits the five public endpoints from docs/deploy/README.md §"Acceptance smoke".
# Exits 0 only if all checks pass.
#
# Usage:
#   ./scripts/smoke.sh                     # check live prod
#   ./scripts/smoke.sh --base <pages-url>  # override Pages URL (e.g. preview)
#
# Env overrides:
#   PAGES_BASE     default: https://studio.aichathub.uk/chara-convert
#   API_BASE       default: https://chara-convert-shim.fly.dev
#   BILLING_BASE   default: https://chara-convert-billing.zmuleyu.workers.dev

set -uo pipefail

PAGES_BASE="${PAGES_BASE:-https://studio.aichathub.uk/chara-convert}"
API_BASE="${API_BASE:-https://chara-convert-shim.fly.dev}"
BILLING_BASE="${BILLING_BASE:-https://chara-convert-billing.zmuleyu.workers.dev}"

while [ $# -gt 0 ]; do
  case "$1" in
    --base) PAGES_BASE="$2"; shift 2 ;;
    --api) API_BASE="$2"; shift 2 ;;
    --billing) BILLING_BASE="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

pass=0
fail=0

check_status() {
  local label="$1" url="$2" expect="${3:-200}"
  local code
  code=$(curl -sSL -o /dev/null -w '%{http_code}' --max-time 15 "$url" 2>/dev/null)
  [ -z "$code" ] && code="000"
  if [ "$code" = "$expect" ]; then
    printf '  [PASS] %-30s %s -> %s\n' "$label" "$url" "$code"
    pass=$((pass + 1))
  else
    printf '  [FAIL] %-30s %s -> %s (expected %s)\n' "$label" "$url" "$code" "$expect"
    fail=$((fail + 1))
  fi
}

check_json() {
  local label="$1" url="$2" jq_filter="$3"
  local body
  body=$(curl -sS --max-time 15 "$url" || echo "")
  if [ -z "$body" ]; then
    printf '  [FAIL] %-30s %s -> empty body\n' "$label" "$url"
    fail=$((fail + 1)); return
  fi
  if echo "$body" | jq -e "$jq_filter" >/dev/null 2>&1; then
    printf '  [PASS] %-30s %s -> %s\n' "$label" "$url" "$(echo "$body" | jq -c . | head -c 80)"
    pass=$((pass + 1))
  else
    printf '  [FAIL] %-30s %s -> bad shape (%s)\n' "$label" "$url" "$(echo "$body" | head -c 100)"
    fail=$((fail + 1))
  fi
}

echo "== chara-convert smoke =="
echo "  PAGES_BASE   $PAGES_BASE"
echo "  API_BASE     $API_BASE"
echo "  BILLING_BASE $BILLING_BASE"
echo

echo "[Pages]"
check_status "landing"   "$PAGES_BASE/"
check_status "convert"   "$PAGES_BASE/convert"
check_status "pricing"   "$PAGES_BASE/pricing"

echo
echo "[API]"
check_status "healthz"   "$API_BASE/healthz"
check_json   "platforms" "$API_BASE/api/platforms" '.sources | length > 0'

echo
echo "[Billing worker]"
check_json   "quota"     "$BILLING_BASE/api/billing/quota" '.tier and (.aiCap | type == "number")'

echo
echo "== summary: $pass pass / $fail fail =="
[ "$fail" -eq 0 ]
