#!/bin/bash
set -e

# ----------------------------------------------------
# E2E TEST RUNNER (staging only — NOT production)
# Spins up ALL services together (weight + billing + frontend)
# using compose.yaml + compose.ci.yaml, waits for them to be
# healthy, then runs the cross-service e2e pytest suite.
# This tests that weight and billing can talk to each
# other over real HTTP, with real databases.
# Called by test-weight-and-billing-and-frontend.sh after unit +
# integration tests pass, or can be run standalone.
# ----------------------------------------------------

SLACK_URL="${SLACK_URL:?SLACK_URL is not set}"
STAGING_DIR="/home/ubuntu/opt/staging"
COMPOSE_CMD="docker compose -f compose.yaml -f compose.ci.yaml"
LOGDIR="/home/ubuntu/opt/scripts/.logs"
LOGFILE="$LOGDIR/e2e-$(date +'%Y%m%d-%H%M%S').log"

mkdir -p "$LOGDIR"

# ----------------------------------------------------
# LOAD SERVICE URLs FROM .env FILES
# The URLs are defined in the .env files inside each
# service folder on the EC2 (billing/.env, weight/.env).
# We source them so the script uses whatever is configured
# there — no hardcoded URLs anywhere.
# ----------------------------------------------------
[ -f "$STAGING_DIR/billing/.env" ] && . "$STAGING_DIR/billing/.env"
BILLING_URL="${BILLING_URL_TEST:?BILLING_URL_TEST is not set in billing/.env}"
WEIGHT_URL="${WEIGHT_URL_TEST:?WEIGHT_URL_TEST is not set in billing/.env}"

log() {
    local msg="$1"
    local ts
    ts=$(date +'%Y-%m-%d_%H-%M-%S')
    echo "[$ts] $msg" | tee -a "$LOGFILE"
}

send_slack() {
    local text="$1"
    curl -s -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"$text\"}" \
      "$SLACK_URL" > /dev/null
}

# ----------------------------------------------------
# GUARANTEED CLEANUP (trap)
# Tears down ALL e2e containers on exit, no matter what.
# ----------------------------------------------------
cleanup() {
    log "[INFO] Trap triggered — tearing down e2e containers..."
    cd "$STAGING_DIR" && $COMPOSE_CMD down -v --remove-orphans 2>/dev/null || true
    log "[INFO] E2E cleanup complete"
}
trap cleanup EXIT

fail() {
    local msg="$1"
    echo "ERROR: $msg"
    log "[ERROR] $msg"
    send_slack "❌ E2E test failed: $msg"
    exit 1
}

log "[INFO] === E2E test started ==="

cd "$STAGING_DIR" || fail "Cannot cd to $STAGING_DIR"

# ----------------------------------------------------
# PRE-CREATE SHARED /in DIRECTORY
# The e2e test writes Excel files here, and the billing
# container reads them via a bind mount.
# We create it before docker compose so it's owned by
# the current user, not root.
# ----------------------------------------------------
mkdir -p tests/e2e/in

# ----------------------------------------------------
# START ALL SERVICES
# compose.yaml + compose.ci.yaml spins up:
#   - weight-db + weight-app (port 80)
#   - billing-db + billing-app (port 8090)
#   - frontend (port 8085)
# All on the same Docker network so services can call
# each other internally via hostname.
# ----------------------------------------------------
$COMPOSE_CMD up --build -d || fail "e2e compose up failed"

# ----------------------------------------------------
# WAIT FOR SERVICES TO BE HEALTHY
# Poll each service's /health endpoint every 2 seconds.
# Timeout after 90 seconds (45 attempts x 2 seconds).
# Both must be up before we run tests.
# ----------------------------------------------------
log "[INFO] Waiting for weight service ($WEIGHT_URL)..."
for i in {1..45}; do
    curl -sf "$WEIGHT_URL/health" > /dev/null 2>&1 && break
    [ "$i" -eq 45 ] && fail "e2e weight not healthy in 90s"
    sleep 2
done
log "[INFO] Weight service is healthy"

log "[INFO] Waiting for billing service ($BILLING_URL)..."
for i in {1..45}; do
    curl -sf "$BILLING_URL/health" > /dev/null 2>&1 && break
    [ "$i" -eq 45 ] && fail "e2e billing not healthy in 90s"
    sleep 2
done
log "[INFO] Billing service is healthy"

# ----------------------------------------------------
# RUN E2E PYTEST
# Passes the service URLs as env vars so the test
# knows where to send HTTP requests.
# PIPESTATUS[0] captures pytest's exit code (not tee's).
# ----------------------------------------------------
log "[INFO] Running e2e tests..."
BILLING_URL_TEST="$BILLING_URL" \
WEIGHT_URL_TEST="$WEIGHT_URL" \
python3 -m pytest tests/e2e/ -v --tb=short 2>&1 | tee -a "$LOGFILE"
E2E_EXIT=${PIPESTATUS[0]}
[ "$E2E_EXIT" -eq 0 ] || fail "E2E tests failed (exit code $E2E_EXIT)"

log "[SUCCESS] === E2E tests passed ==="
send_slack "✅ E2E tests passed"
# cleanup runs automatically via trap
