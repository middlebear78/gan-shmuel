#!/bin/bash
set -e

# ----------------------------------------------------
# TEST SINGLE SERVICE — unit + integration tests
#
# Generic script that tests ONE service in isolation.
# Takes the service name as $1 (weight or billing).
# Used by router.sh when a PR targets a service branch
# (not staging).
#
# weight:   compose up weight/docker-compose-dev.yaml,
#           health check DB + app, docker exec pytest
#           unit + integration, cleanup.
#
# billing:  compose up billing/docker-compose.yml,
#           health check DB + app, docker exec pytest
#           unit + integration, cleanup.
#
# Called by router.sh in the background (&) so the
# webhook returns 200 to GitHub immediately.
# ----------------------------------------------------

SERVICE="${1:?Usage: test-single-service.sh <weight|billing>}"

SLACK_URL="${SLACK_URL:?SLACK_URL is not set}"
SCRIPTS_DIR="/home/ubuntu/opt/scripts"
LOGDIR="/home/ubuntu/opt/scripts/.logs"
LOGFILE="$LOGDIR/test-${SERVICE}-$(date +'%Y%m%d-%H%M%S').log"
STAGING_DIR="/home/ubuntu/opt/staging"

mkdir -p "$LOGDIR"
touch "$LOGFILE"

log() {
    local msg="$1"
    local ts
    ts=$(date +'%Y-%m-%d_%H-%M-%S')
    echo "[$ts] $msg" >> "$LOGFILE"
}

send_slack() {
    local text="$1"
    curl -s -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"$text\"}" \
      "$SLACK_URL" > /dev/null
}

# ----------------------------------------------------
# GITHUB COMMIT STATUS
# Posts a status (success/failure/pending) to the GitHub
# API for the commit that triggered this CI run. This
# makes the green checkmark or red X appear on the PR.
# COMMIT_SHA is exported by router.sh before calling
# this script. GITHUB_TOKEN must be set on EC2 with
# repo:status permission.
# ----------------------------------------------------
GITHUB_REPO="middlebear78/gan-shmuel"

set_commit_status() {
    local state="$1"       # "success", "failure", or "pending"
    local description="$2" # short text shown on the PR

    if [ -z "${COMMIT_SHA:-}" ] || [ -z "${GITHUB_TOKEN:-}" ]; then
        log "[WARN] COMMIT_SHA or GITHUB_TOKEN not set — skipping commit status"
        return 0
    fi

    curl -s -X POST \
      -H "Authorization: token $GITHUB_TOKEN" \
      -H "Accept: application/vnd.github.v3+json" \
      "https://api.github.com/repos/$GITHUB_REPO/statuses/$COMMIT_SHA" \
      -d "{\"state\":\"$state\",\"description\":\"$description\",\"context\":\"ci/gan-shmuel\"}" \
      > /dev/null 2>&1 || true
}

# ----------------------------------------------------
# SEND EMAIL NOTIFICATION
# Wraps the send_email.py script with error swallowing.
# ----------------------------------------------------
send_email() {
    local status="$1"
    local details="${2:-}"
    if [ -n "$details" ]; then
        python3 "$SCRIPTS_DIR/send_email.py" --event ci --status "$status" --details "$details" || true
    else
        python3 "$SCRIPTS_DIR/send_email.py" --event ci --status "$status" || true
    fi
}

fail() {
    local msg="$1"
    echo "ERROR: $msg"
    log "[ERROR] $msg"
    send_slack ":x: ${SERVICE} test failed: $msg"
    send_email "fail" "$msg"
    set_commit_status "failure" "$msg"
    exit 1
}

check_health() {
    local compose_file="$1"
    local service_name="$2"
    local label="$3"

    local container_id
    container_id="$(docker compose -f "$compose_file" ps -q "$service_name")"
    [ -n "$container_id" ] || fail "$label container was not created"

    local healthy=false
    for i in {1..12}; do
        local status
        status="$(docker inspect --format='{{.State.Health.Status}}' "$container_id" 2>/dev/null || true)"
        if [ "$status" = "healthy" ]; then
            healthy=true
            break
        fi
        sleep 5
    done

    [ "$healthy" = true ] || fail "$label did not become healthy"
    log "[SUCCESS] $label is healthy"
}

# ----------------------------------------------------
# TEST WEIGHT
# Compose up weight's dev compose file, health check
# DB + Flask app, run unit + integration tests inside
# the container, then cleanup via trap.
# ----------------------------------------------------
test_weight() {
    local WORKDIR="$STAGING_DIR/weight"
    local COMPOSE_FILE="docker-compose-dev.yaml"

    cleanup() {
        log "[INFO] Trap triggered — tearing down weight containers..."
        cd "$WORKDIR" && docker compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
        log "[INFO] Weight cleanup complete"
    }
    trap cleanup EXIT

    cd "$WORKDIR" || fail "Moving to weight WORKDIR failed"
    git fetch origin || fail "weight git fetch failed"
    git reset --hard "origin/$SERVICE" || fail "weight git reset failed"

    docker compose -f "$COMPOSE_FILE" config || fail "weight compose config failed"
    docker compose -f "$COMPOSE_FILE" build || fail "weight compose build failed"
    docker compose -f "$COMPOSE_FILE" down -v || true
    docker compose -f "$COMPOSE_FILE" up -d || fail "weight compose up failed"

    check_health "$COMPOSE_FILE" "db" "weight db"

    local W_APP
    W_APP="$(docker compose -f "$COMPOSE_FILE" ps -q app)"
    [ -n "$W_APP" ] || fail "weight app container was not created"

    log "[INFO] Waiting for weight app to respond on /health..."
    local w_app_healthy=false
    for i in {1..24}; do
        if docker exec "$W_APP" curl -sf http://localhost:5000/health > /dev/null 2>&1; then
            w_app_healthy=true
            break
        fi
        sleep 5
    done
    [ "$w_app_healthy" = true ] || fail "weight app did not become healthy in 120s"
    log "[SUCCESS] Weight app is healthy"

    log "[INFO] Running weight unit tests..."
    docker exec "$W_APP" python -m pytest tests/unit -v --tb=short 2>&1 | tee -a "$LOGFILE"
    [ "${PIPESTATUS[0]}" -eq 0 ] || fail "Weight unit tests failed"
    log "[SUCCESS] Weight unit tests passed"

    log "[INFO] Running weight integration tests..."
    docker exec "$W_APP" python -m pytest tests/integration -v --tb=short 2>&1 | tee -a "$LOGFILE"
    [ "${PIPESTATUS[0]}" -eq 0 ] || fail "Weight integration tests failed"
    log "[SUCCESS] Weight integration tests passed"
}

# ----------------------------------------------------
# TEST BILLING
# Compose up billing's compose file, health check
# DB + Flask app, run unit + integration tests inside
# the container, then cleanup via trap.
# ----------------------------------------------------
test_billing() {
    local WORKDIR="$STAGING_DIR/billing"
    local COMPOSE_FILE="docker-compose.yml"

    cleanup() {
        log "[INFO] Trap triggered — tearing down billing containers..."
        cd "$WORKDIR" && docker compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
        log "[INFO] Billing cleanup complete"
    }
    trap cleanup EXIT

    cd "$WORKDIR" || fail "Moving to billing WORKDIR failed"
    git fetch origin || fail "billing git fetch failed"
    git reset --hard "origin/$SERVICE" || fail "billing git reset failed"

    docker compose -f "$COMPOSE_FILE" config || fail "billing compose config failed"
    docker compose -f "$COMPOSE_FILE" build || fail "billing compose build failed"
    docker compose -f "$COMPOSE_FILE" down -v || true
    docker compose -f "$COMPOSE_FILE" up -d || fail "billing compose up failed"

    check_health "$COMPOSE_FILE" "mysql" "billing mysql"

    local B_APP
    B_APP="$(docker compose -f "$COMPOSE_FILE" ps -q app)"
    [ -n "$B_APP" ] || fail "billing app container was not created"

    log "[INFO] Waiting for billing app to respond on /health..."
    local b_app_healthy=false
    for i in {1..24}; do
        if docker exec "$B_APP" curl -sf http://localhost:5000/health > /dev/null 2>&1; then
            b_app_healthy=true
            break
        fi
        sleep 5
    done
    [ "$b_app_healthy" = true ] || fail "billing app did not become healthy in 120s"
    log "[SUCCESS] Billing app is healthy"

    log "[INFO] Running billing unit tests..."
    docker exec "$B_APP" python -m pytest tests/unit -v --tb=short 2>&1 | tee -a "$LOGFILE"
    [ "${PIPESTATUS[0]}" -eq 0 ] || fail "Billing unit tests failed"
    log "[SUCCESS] Billing unit tests passed"

    log "[INFO] Running billing integration tests..."
    docker exec "$B_APP" python -m pytest tests/integration -v --tb=short 2>&1 | tee -a "$LOGFILE"
    [ "${PIPESTATUS[0]}" -eq 0 ] || fail "Billing integration tests failed"
    log "[SUCCESS] Billing integration tests passed"
}

# ====================================================
# MAIN — dispatch to the right test function
# ====================================================

log "[INFO] === Single-service test started: $SERVICE ==="
set_commit_status "pending" "CI running: $SERVICE tests..."

case "$SERVICE" in
    weight)
        test_weight
        ;;
    billing)
        test_billing
        ;;
    *)
        fail "Unknown service: $SERVICE (expected weight or billing)"
        ;;
esac

log "[SUCCESS] === $SERVICE tests passed ==="
send_slack ":white_check_mark: ${SERVICE} tests passed — unit + integration green"
send_email "pass"
set_commit_status "success" "$SERVICE tests passed"
