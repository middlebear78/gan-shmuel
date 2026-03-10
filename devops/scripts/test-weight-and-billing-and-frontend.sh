#!/bin/bash
set -e

# ----------------------------------------------------
# STAGING CI — E2E + frontend build
#
# Runs on PRs targeting staging (after unit+integration
# tests already passed on the service branches). This
# script only runs:
#   1. E2E cross-service tests (via run-e2e.sh)
#   2. Frontend build check (docker build only, no tests)
#
# Unit and integration tests are NOT run here — they
# run earlier via test-single-service.sh when PRs
# target the weight or billing branches.
#
# Called by router.sh in the background (&) so the
# webhook returns 200 to GitHub immediately.
# ----------------------------------------------------

SLACK_URL="${SLACK_URL:?SLACK_URL is not set}"
LOGDIR="/home/ubuntu/opt/scripts/.logs"
LOGFILE="$LOGDIR/weight-and-billing-and-frontend.log"
SCRIPTS_DIR="/home/ubuntu/opt/scripts"
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
# Posts a status (success/failure) to the GitHub API
# for the commit that triggered this CI run. This is
# what makes the green checkmark or red X appear on the
# PR page. Without this, GitHub has no way to know if
# CI passed — which means branch protection rules
# (require status checks to pass before merging) won't
# work. The COMMIT_SHA is exported by router.sh before
# calling this script. GITHUB_TOKEN must be set on EC2
# with repo:status permission.
# ----------------------------------------------------
GITHUB_REPO="middlebear78/gan-shmuel"

set_commit_status() {
    local state="$1"       # "success", "failure", or "pending"
    local description="$2" # short text shown on the PR

    # skip if COMMIT_SHA or GITHUB_TOKEN are missing
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

fail() {
    local msg="$1"
    echo "ERROR: $msg"
    log "[ERROR] $msg"
    send_slack "❌ Staging CI failed: $msg"
    # send email notification on CI failure
    python3 "$SCRIPTS_DIR/send_email.py" --event ci --status fail --details "$msg" || true
    # set red X on the PR so GitHub blocks the merge
    set_commit_status "failure" "$msg"
    exit 1
}

log "[INFO] Staging CI started (E2E + frontend build)"
# set yellow dot on the PR so reviewers know CI is running
set_commit_status "pending" "Staging CI running (E2E + frontend)..."

# ----------------------------------------------------
# RUN E2E TESTS
# Calls the standalone run-e2e.sh script which spins up
# ALL services together and runs cross-service tests.
# If e2e fails, its own fail() handles Slack + cleanup.
# We check the exit code here to stop the pipeline.
# Run this BEFORE frontend build — no point building
# frontend if e2e fails.
# ----------------------------------------------------
log "[INFO] Handing off to e2e tests..."
/home/ubuntu/opt/scripts/run-e2e.sh || fail "E2E tests failed"

# ----------------------------------------------------
# FRONTEND BUILD CHECK
# Frontend has no tests — just verify the image builds.
# Uses the staging directory which has the full repo.
# ----------------------------------------------------
log "[INFO] Building frontend image..."
docker build -t ci-frontend "$STAGING_DIR/frontend" || fail "Frontend build failed"
log "[SUCCESS] Frontend image built"

log "[SUCCESS] Staging CI passed — E2E + frontend build green"
send_slack "✅ Staging CI passed — E2E + frontend build green"
# send email notification on CI success
python3 "$SCRIPTS_DIR/send_email.py" --event ci --status pass || true
# set green checkmark on the PR so GitHub allows the merge
set_commit_status "success" "All tests passed"
