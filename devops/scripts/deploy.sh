#!/bin/bash
set -e

# ----------------------------------------------------
# Deployer for production
# Spins up ALL services together (weight + billing + frontend)
# using compose.yaml + compose.prod.yaml, waits for them to be
# healthy
# ----------------------------------------------------

SLACK_URL="${SLACK_URL:?SLACK_URL is not set}"
STAGING_DIR="/home/ubuntu/opt/staging"
SCRIPTS_DIR="/home/ubuntu/opt/scripts"
COMPOSE_CMD="docker compose -f compose.yaml -f compose.prod.yaml"
LOGDIR="/home/ubuntu/opt/scripts/.logs"
LOGFILE="$LOGDIR/prod-$(date +'%Y%m%d-%H%M%S').log"

mkdir -p "$LOGDIR"

# ----------------------------------------------------
# LOAD SERVICE URLs FROM .env FILES
# The URLs are defined in the .env files inside each
# service folder on the EC2 (billing/.env-prod, weight/.env-prod).
# We source them so the script uses whatever is configured
# there — no hardcoded URLs anywhere.
# ----------------------------------------------------

[ -f "$STAGING_DIR/billing/.env-prod" ] && . "$STAGING_DIR/billing/.env-prod"
[ -f "$STAGING_DIR/weight/.env-prod" ] && . "$STAGING_DIR/weight/.env-prod"

BILLING_URL="${BILLING_URL_PROD:?BILLING_URL_PROD is not set in billing/.env}"
WEIGHT_URL="${WEIGHT_URL_PROD:?WEIGHT_URL_PROD is not set in billing/.env}"

log() {
    local msg="$1"
    local ts
    ts=$(date '+%d/%m/%Y_%H:%M:%S')
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
# If the deploy fails at ANY point, this tears down all
# production containers so nothing is left in a broken
# state. Only runs on failure — on success we disable
# the trap so containers keep running (it's production).
# ----------------------------------------------------
DEPLOY_SUCCESS=false
cleanup() {
    if [ "$DEPLOY_SUCCESS" = false ]; then
        log "[INFO] Trap triggered — tearing down failed deploy..."
        cd "$STAGING_DIR" && $COMPOSE_CMD down -v --remove-orphans 2>/dev/null || true
        log "[INFO] Cleanup complete"
    fi
}
trap cleanup EXIT

fail() {
    local msg="$1"
    echo "ERROR: $msg"
    log "[ERROR] $msg"
    send_slack "❌ Deployment failed: $msg"
    # send email notification on deploy failure
    python3 "$SCRIPTS_DIR/send_email.py" --event deploy --status fail --details "$msg" || true
    exit 1
}

log "[INFO] === Deployment started ==="

cd "$STAGING_DIR" || fail "Cannot cd to $STAGING_DIR"

# ----------------------------------------------------
# START ALL SERVICES
# compose.yaml + compose.prod.yaml spins up:
#   - weight-db + weight-app (port 8080)
#   - billing-db + billing-app (port 8081)
#   - frontend (port 8083)
# All on the same Docker network so services can call
# each other internally via hostname.
# ----------------------------------------------------
$COMPOSE_CMD up --build -d || fail "production deploy compose up failed"

# ----------------------------------------------------
# WAIT FOR SERVICES TO BE HEALTHY
# Poll each service's /health endpoint every 2 seconds.
# Timeout after 90 seconds (45 attempts x 2 seconds).
# Both must be up before we run tests.
# ----------------------------------------------------
log "[INFO] Waiting for weight service ($WEIGHT_URL)..."
for i in {1..45}; do
    curl -sf "$WEIGHT_URL/health" > /dev/null 2>&1 && break
    [ "$i" -eq 45 ] && fail "deploy weight not healthy in 90s"
    sleep 2
done
log "[INFO] Weight service is healthy"

log "[INFO] Waiting for billing service ($BILLING_URL)..."
for i in {1..45}; do
    curl -sf "$BILLING_URL/health" > /dev/null 2>&1 && break
    [ "$i" -eq 45 ] && fail "deploy billing not healthy in 90s"
    sleep 2
done
log "[INFO] Billing service is healthy"

# ----------------------------------------------------
# FRONTEND HEALTH CHECK
# Frontend has no /health endpoint — check root / which
# serves index.html and returns 200.
# ----------------------------------------------------
FRONTEND_URL="${FRONTEND_URL_PROD:-http://localhost:8083}"
log "[INFO] Waiting for frontend service ($FRONTEND_URL)..."
for i in {1..45}; do
    curl -sf "$FRONTEND_URL/" > /dev/null 2>&1 && break
    [ "$i" -eq 45 ] && fail "deploy frontend not healthy in 90s"
    sleep 2
done
log "[INFO] Frontend service is healthy"

# ----------------------------------------------------
# DEPLOY SUCCESS
# All services are up and healthy. Mark success so the
# cleanup trap does NOT tear down the containers.
# ----------------------------------------------------
DEPLOY_SUCCESS=true
log "[SUCCESS] === Deployment complete — all services healthy ==="

# ----------------------------------------------------
# PUSH STAGING → MAIN
# After a successful deploy, main must mirror production
# exactly. This pushes staging to main so they stay in
# sync. The code has already been:
#   1. Tested by CI (unit + integration + e2e)
#   2. Approved by devops on the PR
#   3. Merged to staging
#   4. Deployed and health-checked in production
# So there's no reason to gate this again.
#
# IMPORTANT: main has branch protection enabled. The
# GITHUB_TOKEN used on EC2 must be added to the bypass
# list in GitHub repo settings (Settings → Rules →
# Rulesets) so this push is allowed. Everyone else
# still needs a PR + approval to push to main.
# ----------------------------------------------------
cd "$STAGING_DIR" || fail "Cannot cd to $STAGING_DIR"
log "[INFO] Pushing staging → main..."
git push origin staging:main || fail "Failed to push staging to main"
log "[SUCCESS] main branch updated to match production"

send_slack "✅ Deployment complete — weight, billing, frontend all healthy. main branch updated."
# send email notification on deploy success
python3 "$SCRIPTS_DIR/send_email.py" --event deploy --status pass || true