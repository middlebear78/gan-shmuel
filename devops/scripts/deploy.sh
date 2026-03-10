#!/bin/bash
set -e

# ----------------------------------------------------
# Deployer for production
# Spins up ALL services together (weight + billing)
# using docker-compose.prod.yml, waits for them to be
# healthy
# ----------------------------------------------------

SLACK_URL="${SLACK_URL:?SLACK_URL is not set}"
STAGING_DIR="/home/ubuntu/opt/staging"
PROD_COMPOSE="docker-compose.prod.yml"
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
[ -f "$STAGING_DIR/billing/.env-prod" ] && . "$STAGING_DIR/weight/.env-prod"
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

fail() {
    local msg="$1"
    echo "ERROR: $msg"
    log "[ERROR] $msg"
    send_slack "❌ Deployment failed: $msg"
    exit 1
}

log "[INFO] === Deployment started ==="

cd "$STAGING_DIR" || fail "Cannot cd to $STAGING_DIR"

# ----------------------------------------------------
# START ALL SERVICES
# docker-compose.prod.yml spins up:
#   - weight-db + weight-app (port 8080)
#   - billing-db + billing-app (port 8081)
# All on the same Docker network so billing can call
# weight internally via hostname.
# ----------------------------------------------------
docker compose -f "$PROD_COMPOSE" up --build -d || fail "production deploy compose up failed"

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