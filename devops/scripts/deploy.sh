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
# ROLLBACK SUPPORT
# Before building new images, we tag the current running
# images as :prev. If the deploy fails (health checks
# don't pass), we don't just tear everything down and
# leave production dead — we roll back to the previous
# working images instead.
#
# The app images are built by compose and named after
# the project directory (staging) + service name:
#   staging-weight-app, staging-billing-app, staging-frontend
# DB images are pulled (mysql, mariadb), not built, so
# they don't change between deploys.
#
# On first-ever deploy there are no previous images —
# in that case a failed deploy just tears down.
# ----------------------------------------------------
ROLLBACK_AVAILABLE=false
if docker image inspect staging-weight-app:latest > /dev/null 2>&1; then
    log "[INFO] Tagging current images as :prev for rollback..."
    docker tag staging-weight-app:latest staging-weight-app:prev
    docker tag staging-billing-app:latest staging-billing-app:prev
    docker tag staging-frontend:latest staging-frontend:prev
    ROLLBACK_AVAILABLE=true
    log "[INFO] Rollback images saved"
fi

# ----------------------------------------------------
# GUARANTEED CLEANUP (trap)
# If the deploy fails at ANY point, this function runs
# automatically on exit. Two scenarios:
#   - Previous images exist → roll back to them so
#     production stays up with the last working version
#   - No previous images (first deploy) → tear down,
#     nothing to roll back to
# Only runs on failure — on success the containers
# keep running (it's production).
# ----------------------------------------------------
DEPLOY_SUCCESS=false
cleanup() {
    if [ "$DEPLOY_SUCCESS" = true ]; then
        return 0
    fi

    if [ "$ROLLBACK_AVAILABLE" = true ]; then
        log "[INFO] Deploy failed — rolling back to previous images..."
        cd "$STAGING_DIR"
        # stop the broken containers (no -v, keep DB volumes)
        $COMPOSE_CMD down --remove-orphans 2>/dev/null || true
        # restore the previous working images
        docker tag staging-weight-app:prev staging-weight-app:latest
        docker tag staging-billing-app:prev staging-billing-app:latest
        docker tag staging-frontend:prev staging-frontend:latest
        # bring up with the old images (--no-build skips rebuild)
        $COMPOSE_CMD up -d --no-build 2>/dev/null || true
        log "[INFO] Rollback complete — previous version restored"
        send_slack "⚠️ Deploy failed — rolled back to previous working version"
    else
        log "[INFO] No previous images — tearing down failed deploy..."
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
# PULL LATEST CODE FROM STAGING
# The staging directory on EC2 may be stale if previous
# deploys or manual work left it behind. We always pull
# the latest code from origin/staging before building
# so Docker gets the newest source files.
#
# chown is needed because Docker sometimes creates files
# as root (__pycache__, .pyc) which block git reset.
# ----------------------------------------------------
log "[INFO] Pulling latest code from origin/staging..."
git fetch origin || fail "git fetch failed"
sudo chown -R ubuntu:ubuntu "$STAGING_DIR" 2>/dev/null || true
git reset --hard origin/staging || fail "git reset to origin/staging failed"
log "[INFO] Code updated to latest staging"

# ----------------------------------------------------
# BUILD AND START ALL SERVICES
# compose.yaml + compose.prod.yaml spins up:
#   - weight-db + weight-app (port 8080)
#   - billing-db + billing-app (port 8081)
#   - frontend (port 8083)
# All on the same Docker network so services can call
# each other internally via hostname.
# If this fails, the cleanup trap rolls back to the
# previous images automatically.
# ----------------------------------------------------
$COMPOSE_CMD up --build -d || fail "production deploy compose up failed"

# ----------------------------------------------------
# WAIT FOR SERVICES TO BE HEALTHY
# Poll each service's /health endpoint every 2 seconds.
# Timeout after 180 seconds (90 attempts x 2 seconds).
# Both must be up before we run tests.
# ----------------------------------------------------
log "[INFO] Waiting for weight service ($WEIGHT_URL)..."
for i in {1..90}; do
    curl -sf "$WEIGHT_URL/health" > /dev/null 2>&1 && break
    [ "$i" -eq 90 ] && fail "deploy weight not healthy in 180s"
    sleep 2
done
log "[INFO] Weight service is healthy"

log "[INFO] Waiting for billing service ($BILLING_URL)..."
for i in {1..90}; do
    curl -sf "$BILLING_URL/health" > /dev/null 2>&1 && break
    [ "$i" -eq 90 ] && fail "deploy billing not healthy in 180s"
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
for i in {1..90}; do
    curl -sf "$FRONTEND_URL/" > /dev/null 2>&1 && break
    [ "$i" -eq 90 ] && fail "deploy frontend not healthy in 180s"
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
# CREATE PR: STAGING → MAIN
# After a successful deploy, create a PR to sync main
# with staging. Devops reviews and approves it. This
# respects main's branch protection rules.
# The code has already been:
#   1. Tested by CI (unit + integration + e2e)
#   2. Approved by devops on the PR
#   3. Merged to staging
#   4. Deployed and health-checked in production
# The PR won't trigger CI because the router ignores
# PRs targeting main.
# ----------------------------------------------------
GITHUB_REPO="middlebear78/gan-shmuel"
log "[INFO] Creating PR: staging → main..."
PR_URL=$(curl -s -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/$GITHUB_REPO/pulls" \
  -d '{"title":"Deploy: sync staging → main","head":"staging","base":"main","body":"Auto-created by deploy script after successful production deployment."}' \
  | jq -r '.html_url // .message') || true

if [ "$PR_URL" != "null" ] && [ -n "$PR_URL" ]; then
    log "[SUCCESS] PR created: $PR_URL"
else
    log "[WARN] Could not create PR (may already exist)"
fi

send_slack "✅ Deployment complete — all services healthy. PR created: staging → main"
# send email notification on deploy success
python3 "$SCRIPTS_DIR/send_email.py" --event deploy --status pass || true