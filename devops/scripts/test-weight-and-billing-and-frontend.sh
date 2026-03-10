#!/bin/bash
set -e

# ----------------------------------------------------
# TEST PIPELINE — weight + billing + frontend
#
# Runs on every PR targeting staging. Orchestrates:
#   1. Weight unit + integration tests (via weight/docker-compose-dev.yaml)
#   2. Billing unit + integration tests (via billing/docker-compose.yml)
#   3. Frontend build check (docker build only, no tests)
#   4. E2E cross-service tests (via run-e2e.sh)
#
# Each service's individual compose file is used for
# unit/integration tests in isolation. After those pass,
# everything is torn down and run-e2e.sh spins up the
# full stack with compose.yaml + compose.ci.yaml.
#
# Called by router.sh in the background (&) so the
# webhook returns 200 to GitHub immediately.
# ----------------------------------------------------

SLACK_URL="${SLACK_URL:?SLACK_URL is not set}"
LOGDIR="/home/ubuntu/opt/scripts/.logs"
LOGFILE="$LOGDIR/weight-and-billing-and-frontend.log"

WEIGHT_WORKDIR="/home/ubuntu/opt/staging/weight"
WEIGHT_COMPOSE="docker-compose-dev.yaml"

BILLING_WORKDIR="/home/ubuntu/opt/staging/billing"
BILLING_COMPOSE="docker-compose.yml"

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

fail() {
    local msg="$1"
    echo "ERROR: $msg"
    log "[ERROR] $msg"
    send_slack "❌ Billing+Weight test failed: $msg"
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
# GUARANTEED CLEANUP (trap)
# If the script crashes, gets killed, or fails at ANY point,
# this function runs automatically on exit.
# It tears down ALL containers (weight + billing) so nothing
# is left running and leaking resources on the EC2 instance.
# Without this, a failed build leaves orphan containers
# eating CPU, memory, and ports until someone manually kills them.
# ----------------------------------------------------
cleanup() {
    log "[INFO] Trap triggered — tearing down all containers..."
    cd "$WEIGHT_WORKDIR" && docker compose -f "$WEIGHT_COMPOSE" down -v --remove-orphans 2>/dev/null || true
    cd "$BILLING_WORKDIR" && docker compose -f "$BILLING_COMPOSE" down -v --remove-orphans 2>/dev/null || true
    log "[INFO] Cleanup complete"
}
trap cleanup EXIT

log "[INFO] Billing + Weight test started"

cd "$WEIGHT_WORKDIR" || fail "Moving to weight WORKDIR failed"
git fetch origin || fail "weight git fetch failed"
git reset --hard origin/staging || fail "weight git reset failed"

docker compose -f "$WEIGHT_COMPOSE" config || fail "weight compose config failed"
docker compose -f "$WEIGHT_COMPOSE" build || fail "weight compose build failed"
docker compose -f "$WEIGHT_COMPOSE" down -v || true
docker compose -f "$WEIGHT_COMPOSE" up -d || fail "weight compose up failed"

check_health "$WEIGHT_COMPOSE" "db" "weight db"

# ----------------------------------------------------
# WEIGHT APP HEALTH CHECK
# DB is up, but the Flask app might still be starting,
# crashing, or stuck. We curl /health inside the
# container and retry every 5s for up to 120s.
# Only after the app responds 200 do we run tests.
# ----------------------------------------------------
W_APP="$(docker compose -f "$WEIGHT_COMPOSE" ps -q app)"
[ -n "$W_APP" ] || fail "weight app container was not created"

log "[INFO] Waiting for weight app to respond on /health..."
w_app_healthy=false
for i in {1..24}; do
    if docker exec "$W_APP" curl -sf http://localhost:5000/health > /dev/null 2>&1; then
        w_app_healthy=true
        break
    fi
    sleep 5
done
[ "$w_app_healthy" = true ] || fail "weight app did not become healthy in 120s"
log "[SUCCESS] Weight app is healthy"

# ----------------------------------------------------
# RUN WEIGHT PYTEST (unit + integration)
# docker exec runs commands INSIDE the container where
# the app code and live DB connection are available.
# PIPESTATUS[0] captures docker exec's exit code
# (not tee's), so we know if pytest actually failed.
# ----------------------------------------------------
log "[INFO] Running weight unit tests..."
docker exec "$W_APP" python -m pytest tests/unit -v --tb=short 2>&1 | tee -a "$LOGFILE"
[ "${PIPESTATUS[0]}" -eq 0 ] || fail "Weight unit tests failed"
log "[SUCCESS] Weight unit tests passed"

log "[INFO] Running weight integration tests..."
docker exec "$W_APP" python -m pytest tests/integration -v --tb=short 2>&1 | tee -a "$LOGFILE"
[ "${PIPESTATUS[0]}" -eq 0 ] || fail "Weight integration tests failed"
log "[SUCCESS] Weight integration tests passed"

cd "$BILLING_WORKDIR" || fail "Moving to billing WORKDIR failed"
git fetch origin || fail "billing git fetch failed"
git reset --hard origin/staging || fail "billing git reset failed"

docker compose -f "$BILLING_COMPOSE" config || fail "billing compose config failed"
docker compose -f "$BILLING_COMPOSE" build || fail "billing compose build failed"
docker compose -f "$BILLING_COMPOSE" down -v || true
docker compose -f "$BILLING_COMPOSE" up -d || fail "billing compose up failed"

check_health "$BILLING_COMPOSE" "mysql" "billing mysql"

# ----------------------------------------------------
# BILLING APP HEALTH CHECK
# Same as weight — DB is up but Flask app might not be.
# We curl /health inside the container and retry every
# 5s for up to 120s before running tests.
# ----------------------------------------------------
B_APP="$(docker compose -f "$BILLING_COMPOSE" ps -q app)"
[ -n "$B_APP" ] || fail "billing app container was not created"

log "[INFO] Waiting for billing app to respond on /health..."
b_app_healthy=false
for i in {1..24}; do
    if docker exec "$B_APP" curl -sf http://localhost:5000/health > /dev/null 2>&1; then
        b_app_healthy=true
        break
    fi
    sleep 5
done
[ "$b_app_healthy" = true ] || fail "billing app did not become healthy in 120s"
log "[SUCCESS] Billing app is healthy"

# ----------------------------------------------------
# RUN BILLING PYTEST (unit + integration)
# Same as weight — exec into the container and run tests.
# ----------------------------------------------------
log "[INFO] Running billing unit tests..."
docker exec "$B_APP" python -m pytest tests/unit -v --tb=short 2>&1 | tee -a "$LOGFILE"
[ "${PIPESTATUS[0]}" -eq 0 ] || fail "Billing unit tests failed"
log "[SUCCESS] Billing unit tests passed"

log "[INFO] Running billing integration tests..."
docker exec "$B_APP" python -m pytest tests/integration -v --tb=short 2>&1 | tee -a "$LOGFILE"
[ "${PIPESTATUS[0]}" -eq 0 ] || fail "Billing integration tests failed"
log "[SUCCESS] Billing integration tests passed"

log "[SUCCESS] Billing + Weight unit + integration passed"

# ----------------------------------------------------
# FRONTEND BUILD CHECK
# Frontend has no tests — just verify the image builds.
# Uses the staging directory which has the full repo.
# ----------------------------------------------------
STAGING_DIR="/home/ubuntu/opt/staging"
log "[INFO] Building frontend image..."
docker build -t ci-frontend "$STAGING_DIR/frontend" || fail "Frontend build failed"
log "[SUCCESS] Frontend image built"

# ----------------------------------------------------
# TEAR DOWN INDIVIDUAL SERVICES BEFORE E2E
# The e2e script spins up its own containers using
# compose.yaml + compose.ci.yaml with different port mappings.
# We tear down the individual service containers first
# so there are no port conflicts.
# ----------------------------------------------------
cd "$WEIGHT_WORKDIR" && docker compose -f "$WEIGHT_COMPOSE" down -v || true
cd "$BILLING_WORKDIR" && docker compose -f "$BILLING_COMPOSE" down -v || true

# ----------------------------------------------------
# RUN E2E TESTS
# Calls the standalone run-e2e.sh script which spins up
# ALL services together and runs cross-service tests.
# If e2e fails, its own fail() handles Slack + cleanup.
# We check the exit code here to stop the pipeline.
# ----------------------------------------------------
log "[INFO] Handing off to e2e tests..."
/home/ubuntu/opt/scripts/run-e2e.sh || fail "E2E tests failed"

log "[SUCCESS] Billing + Weight + Frontend test passed — all unit + integration + e2e green"
send_slack "✅ Billing + Weight + Frontend test passed — all unit + integration + e2e green"
