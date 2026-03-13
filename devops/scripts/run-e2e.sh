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
SCRIPTS_DIR="/home/ubuntu/opt/scripts"
COMPOSE_CMD="docker compose -f compose.yaml -f compose.ci.yaml"
LOGDIR="/home/ubuntu/opt/scripts/.logs"
LOGFILE="$LOGDIR/e2e-$(date +'%Y%m%d-%H%M%S').log"

mkdir -p "$LOGDIR"

# ----------------------------------------------------
# LOAD SERVICE URLs
# URLs come from .env.webhook (loaded by systemd into
# the webhook environment). No need to source service
# .env files — those get overwritten by git reset.
# ----------------------------------------------------
BILLING_URL="${BILLING_URL_TEST:?BILLING_URL_TEST is not set — add it to .env.webhook}"
WEIGHT_URL="${WEIGHT_URL_TEST:?WEIGHT_URL_TEST is not set — add it to .env.webhook}"

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
# Tears down ALL e2e containers on exit AND removes code
# from staging directory. Preserves .env files (secrets)
# but deletes .env.example (tracked in git).
# SAFETY: Only operates on STAGING_DIR, never production.
# ----------------------------------------------------
cleanup() {
    log "[INFO] Trap triggered — tearing down e2e containers..."
    cd "$STAGING_DIR" && $COMPOSE_CMD down -v --remove-orphans 2>/dev/null || true

    # SAFETY CHECK: Only clean staging, NEVER production
    if [[ "$STAGING_DIR" != "/home/ubuntu/opt/staging" ]]; then
        log "[ERROR] STAGING_DIR is not /home/ubuntu/opt/staging — refusing to clean"
        return 1
    fi

    log "[INFO] Cleaning staging code (preserving .env files)..."

    # Backup all .env files EXCEPT .env.example
    local TEMP_ENV
    TEMP_ENV=$(mktemp -d)
    find "$STAGING_DIR" -name '.env*' ! -name '.env.example' -exec cp --parents {} "$TEMP_ENV" \; 2>/dev/null || true

    # Delete everything except .git
    find "$STAGING_DIR" -mindepth 1 -maxdepth 1 ! -name '.git' -exec rm -rf {} +

    # Restore .env files
    if [ -d "$TEMP_ENV$STAGING_DIR" ]; then
        cp -r "$TEMP_ENV$STAGING_DIR"/* "$STAGING_DIR/" 2>/dev/null || true
    fi
    rm -rf "$TEMP_ENV"

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
# container reads them via a bind mount (compose.ci.yaml
# mounts ./tests/e2e/in from $STAGING_DIR).
# We create it before docker compose so it's owned by
# the current user, not root.
# ----------------------------------------------------
mkdir -p "$STAGING_DIR/tests/e2e/in"

# ----------------------------------------------------
# TEAR DOWN ANY LEFTOVER CONTAINERS
# Single-service tests or manual runs may have left
# containers on conflicting ports (80, 8090). Kill
# them before starting E2E.
# ----------------------------------------------------
log "[INFO] Cleaning up any leftover containers..."
cd "$STAGING_DIR/weight" && docker compose -f docker-compose-dev.yaml down -v 2>/dev/null || true
cd "$STAGING_DIR/billing" && docker compose -f docker-compose.yml down -v 2>/dev/null || true
cd "$STAGING_DIR" && $COMPOSE_CMD down -v --remove-orphans 2>/dev/null || true

# ----------------------------------------------------
# FETCH FRESH CODE FROM PR BRANCH
# PR_BRANCH is exported by router.sh (e.g., "weight").
# We fetch and checkout the entire repo from that branch
# to ensure we test the actual code being merged, not
# stale leftovers from previous test runs.
# Preserves .env files (secrets) but overwrites code.
# ----------------------------------------------------
cd "$STAGING_DIR" || fail "Cannot cd to $STAGING_DIR"

if [ -n "${PR_BRANCH:-}" ]; then
    log "[INFO] Fetching fresh code from origin/$PR_BRANCH..."

    # Backup .env files (except .env.example)
    TEMP_ENV=$(mktemp -d)
    find "$STAGING_DIR" -name '.env*' ! -name '.env.example' -exec cp --parents {} "$TEMP_ENV" \; 2>/dev/null || true

    # Fetch and checkout fresh code
    git fetch origin || fail "git fetch failed"
    git checkout "origin/$PR_BRANCH" -- . || fail "git checkout origin/$PR_BRANCH failed"

    # Restore .env files
    if [ -d "$TEMP_ENV$STAGING_DIR" ]; then
        cp -r "$TEMP_ENV$STAGING_DIR"/* "$STAGING_DIR/" 2>/dev/null || true
    fi
    rm -rf "$TEMP_ENV"

    log "[INFO] Code updated from origin/$PR_BRANCH"
else
    log "[WARN] PR_BRANCH not set — using existing code in staging"
fi

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
# Tests live in the scripts dir, not the staging dir.
# E2E_IN_DIR tells the test where to write Excel files
# (must match compose.ci.yaml bind mount in $STAGING_DIR).
# PIPESTATUS[0] captures pytest's exit code (not tee's).
# ----------------------------------------------------
log "[INFO] Running e2e tests..."
BILLING_URL_TEST="$BILLING_URL" \
WEIGHT_URL_TEST="$WEIGHT_URL" \
E2E_IN_DIR="$STAGING_DIR/tests/e2e/in" \
python3 -m pytest "$SCRIPTS_DIR/tests/e2e/" -v --tb=short 2>&1 | tee -a "$LOGFILE"
E2E_EXIT=${PIPESTATUS[0]}
[ "$E2E_EXIT" -eq 0 ] || fail "E2E tests failed (exit code $E2E_EXIT)"

log "[SUCCESS] === E2E tests passed ==="
send_slack "✅ E2E tests passed"
# cleanup runs automatically via trap
