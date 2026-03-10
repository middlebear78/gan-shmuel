#!/bin/bash
set -e



SLACK_URL="${SLACK_URL:?SLACK_URL is not set}"
WORKDIR="/home/ubuntu/opt/staging/weight"
LOGFILE="/home/ubuntu/opt/scripts/.logs/weight.log"
COMPOSE_FILE="docker-compose-dev.yaml"

mkdir -p /home/ubuntu/opt/scripts/.logs
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
    send_slack "❌ Weight test failed: $msg"
    exit 1
}

# ----------------------------------------------------
# GUARANTEED CLEANUP (trap)
# If the script crashes, gets killed, or fails at ANY point,
# this function runs automatically on exit.
# It tears down all containers so nothing is left running
# and leaking resources on the EC2 instance.
# Without this, a failed build leaves orphan containers
# eating CPU, memory, and ports until someone manually kills them.
# ----------------------------------------------------
cleanup() {
    log "[INFO] Trap triggered — tearing down containers..."
    cd "$WORKDIR" && docker compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
    log "[INFO] Cleanup complete"
}
trap cleanup EXIT

log "[INFO] Weight test started"

cd "$WORKDIR" || fail "Moving to WORKDIR failed"

git fetch origin || fail "git fetch origin failed"
git reset --hard origin/staging || fail "git reset --hard origin/staging failed"

docker compose -f "$COMPOSE_FILE" config || fail "docker compose config failed"
docker compose -f "$COMPOSE_FILE" build || fail "docker compose build failed"
docker compose -f "$COMPOSE_FILE" down -v || true
docker compose -f "$COMPOSE_FILE" up -d || fail "docker compose up failed"

DB_CONTAINER="$(docker compose -f "$COMPOSE_FILE" ps -q db)"
[ -n "$DB_CONTAINER" ] || fail "db container was not created"

healthy=false
for i in {1..12}; do
    STATUS="$(docker inspect --format='{{.State.Health.Status}}' "$DB_CONTAINER" 2>/dev/null || true)"
    if [ "$STATUS" = "healthy" ]; then
        healthy=true
        break
    fi
    sleep 5
done

[ "$healthy" = true ] || fail "weight db did not become healthy"

log "[SUCCESS] Weight DB is healthy"

# ----------------------------------------------------
# APP HEALTH CHECK
# The DB being healthy does NOT mean the app is ready.
# The Flask app could be crashing, stuck importing, or
# waiting on something else. We exec a curl inside the
# app container hitting its /health endpoint.
# We retry every 5 seconds for up to 120 seconds.
# Only after the app responds 200 do we run tests.
# ----------------------------------------------------
APP_CONTAINER="$(docker compose -f "$COMPOSE_FILE" ps -q app)"
[ -n "$APP_CONTAINER" ] || fail "app container was not created"

log "[INFO] Waiting for weight app to respond on /health..."
app_healthy=false
for i in {1..24}; do
    if docker exec "$APP_CONTAINER" curl -sf http://localhost:5000/health > /dev/null 2>&1; then
        app_healthy=true
        break
    fi
    sleep 5
done
[ "$app_healthy" = true ] || fail "weight app did not become healthy in 120s"
log "[SUCCESS] Weight app is healthy"

# ----------------------------------------------------
# RUN PYTEST (unit + integration)
# Now that containers are up and the DB is healthy,
# we exec into the running app container and run pytest.
# docker exec runs a command INSIDE the container,
# so pytest has access to the app code and the live DB.
# We get the app container ID from docker compose,
# then run unit tests first, then integration tests.
# If either fails, fail() is called which triggers
# the trap cleanup and sends a Slack notification.
# PIPESTATUS[0] captures the exit code of docker exec
# (not tee), so we know if pytest actually failed.
# ----------------------------------------------------
log "[INFO] Running weight unit tests..."
docker exec "$APP_CONTAINER" python -m pytest tests/unit -v --tb=short 2>&1 | tee -a "$LOGFILE"
[ "${PIPESTATUS[0]}" -eq 0 ] || fail "Weight unit tests failed"
log "[SUCCESS] Weight unit tests passed"

log "[INFO] Running weight integration tests..."
docker exec "$APP_CONTAINER" python -m pytest tests/integration -v --tb=short 2>&1 | tee -a "$LOGFILE"
[ "${PIPESTATUS[0]}" -eq 0 ] || fail "Weight integration tests failed"
log "[SUCCESS] Weight integration tests passed"

log "[SUCCESS] All weight tests passed"
send_slack "✅ Weight test passed — unit + integration green"
