#!/bin/bash
set -e

# ----------------------------------------------------
# ROUTER — the entry point for ALL GitHub webhook events.
#
# This script is called by the "webhook" tool running
# on EC2 via systemd. The webhook tool listens on port
# 9000 and when GitHub sends an HTTP POST, it calls
# this script with 2 arguments:
#
#   $1 = X-GitHub-Event header
#        This tells us WHAT happened:
#        "push"         = someone pushed/merged code
#        "pull_request" = someone opened/updated a PR
#
#   $2 = raw JSON payload from GitHub
#        Contains all the details: branch names, commit
#        hashes, changed files, PR info, etc.
#
# The router's job:
#   1. Figure out the event type (push or pull_request)
#   2. Figure out which files changed (billing or weight)
#   3. Call the right test script
#
# TWO-TIER CI:
#   PR targeting weight/billing  → run unit+integration
#                                   for that service only
#   PR targeting staging         → run E2E + frontend build
#   Push to staging (PR merged)  → run deploy
# ----------------------------------------------------

# ----------------------------------------------------
# AUTO-SYNC SCRIPTS FROM BARE REPO
# Every time the webhook fires, pull the latest scripts
# from the devops branch in the bare repo. This means
# you NEVER have to manually copy scripts to EC2 again.
# Router.sh is the only file that needs a one-time copy.
# ----------------------------------------------------
BARE_REPO="/home/ubuntu/opt/gan-shmuel.git"
SCRIPTS_DIR="/home/ubuntu/opt/scripts"
git --git-dir="$BARE_REPO" fetch origin devops:devops 2>/dev/null || true
git --git-dir="$BARE_REPO" archive devops -- devops/scripts/ 2>/dev/null \
  | tar -xf - --strip-components=2 -C "$SCRIPTS_DIR" 2>/dev/null || true
chmod +x "$SCRIPTS_DIR"/*.sh 2>/dev/null || true

EVENT="$1"
PAYLOAD="$2"
LOGFILE="/home/ubuntu/opt/scripts/.logs/router.log"

mkdir -p /home/ubuntu/opt/scripts/.logs
touch "$LOGFILE"

log() {
    local msg="$1"
    local ts
    ts=$(date +'%Y-%m-%d_%H-%M-%S')
    echo "[$ts] $msg" >> "$LOGFILE"
}

fail() {
    local msg="$1"
    echo "ERROR: $msg"
    log "[ERROR] $msg"
    exit 1
}

send_slack() {
    local text="$1"
    curl -s -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"$text\"}" \
      "${SLACK_URL:-}" > /dev/null 2>&1 || true
}

log "========================================"
log "[INFO] Router triggered — event=$EVENT"
# v2 — full pipeline test

# ----------------------------------------------------
# Save the JSON payload to a temp file so we can parse
# it with jq. We clean it up before exiting.
# ----------------------------------------------------
TMP=$(mktemp)
printf '%s' "$PAYLOAD" > "$TMP"

# ----------------------------------------------------
# PULL REQUEST EVENT
# Fires when someone opens a new PR or pushes new
# commits to an existing PR. Routes based on the
# target (base) branch:
#   weight/billing → test-single-service.sh (unit+integration)
#   frontend       → test-single-service.sh (build check only)
#   staging        → test-weight-and-billing-and-frontend.sh
#                    (E2E + frontend build)
# The test script runs in the background (&) so the
# webhook tool can return 200 to GitHub immediately
# instead of making GitHub wait for all tests to finish.
# ----------------------------------------------------
if [ "$EVENT" = "pull_request" ]; then

    # Extract PR details from the JSON payload
    ACTION=$(jq -r '.action' "$TMP")
    PR_NUM=$(jq -r '.number' "$TMP")
    PR_BRANCH=$(jq -r '.pull_request.head.ref' "$TMP")
    BASE_BRANCH=$(jq -r '.pull_request.base.ref' "$TMP")
    COMMIT_SHA=$(jq -r '.pull_request.head.sha' "$TMP")

    log "[INFO] PR #$PR_NUM: action=$ACTION, branch=$PR_BRANCH -> $BASE_BRANCH, sha=$COMMIT_SHA"

    # Slack notify on closed (merged or not)
    if [ "$ACTION" = "closed" ]; then
        MERGED=$(jq -r '.pull_request.merged' "$TMP")
        if [ "$MERGED" = "true" ]; then
            send_slack ":merged: PR #$PR_NUM merged: $PR_BRANCH → $BASE_BRANCH"
        else
            send_slack ":no_entry_sign: PR #$PR_NUM closed (not merged): $PR_BRANCH → $BASE_BRANCH"
        fi
        log "[INFO] Ignoring PR action: $ACTION"
        rm -f "$TMP"
        exit 0
    fi

    # Slack notify on reopened
    if [ "$ACTION" = "reopened" ]; then
        send_slack ":recycle: PR #$PR_NUM reopened: $PR_BRANCH → $BASE_BRANCH"
    fi

    # Only run CI for opened, reopened, or synchronize.
    # Ignore everything else: labeled, assigned, etc.
    if [ "$ACTION" != "opened" ] && [ "$ACTION" != "reopened" ] && [ "$ACTION" != "synchronize" ]; then
        log "[INFO] Ignoring PR action: $ACTION"
        rm -f "$TMP"
        exit 0
    fi

    # Export COMMIT_SHA so the test scripts can post
    # GitHub commit status (green checkmark / red X)
    export COMMIT_SHA

    # ----------------------------------------------------
    # TWO-TIER ROUTING
    # Route based on which branch the PR targets:
    #   weight/billing  → test-single-service.sh (fast,
    #                     unit+integration for that service)
    #   frontend        → test-single-service.sh (build
    #                     check only — no tests exist)
    #   staging         → test-weight-and-billing-and-frontend.sh
    #                     (E2E + frontend build only — unit+
    #                     integration already passed on the
    #                     service branch)
    #   anything else   → ignore
    # ----------------------------------------------------
    case "$BASE_BRANCH" in
        weight)
            log "[INFO] PR targets weight — running weight unit+integration tests"
            send_slack ":test_tube: PR #$PR_NUM → weight — running unit+integration tests"
            /home/ubuntu/opt/scripts/test-single-service.sh weight &
            ;;
        billing)
            log "[INFO] PR targets billing — running billing unit+integration tests"
            send_slack ":test_tube: PR #$PR_NUM → billing — running unit+integration tests"
            /home/ubuntu/opt/scripts/test-single-service.sh billing &
            ;;
        frontend)
            # Frontend has no tests — just verify the Docker image builds.
            log "[INFO] PR targets frontend — running frontend build check"
            send_slack ":test_tube: PR #$PR_NUM → frontend — running build check"
            /home/ubuntu/opt/scripts/test-single-service.sh frontend &
            ;;
        staging)
            log "[INFO] PR targets staging — running E2E + frontend build"
            send_slack ":rocket: PR #$PR_NUM → staging — running E2E + frontend build"
            /home/ubuntu/opt/scripts/test-weight-and-billing-and-frontend.sh &
            ;;
        *)
            log "[INFO] PR targets $BASE_BRANCH — not a CI branch. Ignoring."
            ;;
    esac

    rm -f "$TMP"
    exit 0
fi

# ----------------------------------------------------
# PUSH EVENT
# Fires when code is pushed to a branch. For us, this
# happens when a PR is merged into staging. GitHub
# treats a merge as a push. We check which files
# changed in the push commits and route to deploy.
# (deploy.sh will be created in a later step)
# ----------------------------------------------------
if [ "$EVENT" = "push" ]; then

    # Check which branch was pushed to
    REF=$(jq -r '.ref' "$TMP")

    # We only care about pushes to staging.
    # Pushes to any other branch are ignored.
    if [ "$REF" != "refs/heads/staging" ]; then
        log "[INFO] Push to $REF, not staging. Ignoring."
        rm -f "$TMP"
        exit 0
    fi

    COMMIT_SHA=$(jq -r '.after' "$TMP")
    log "[INFO] Push to staging detected, sha=$COMMIT_SHA"
    send_slack ":package: Push to staging detected — checking for deploy"

    # ----------------------------------------------------
    # DETECT WHICH FILES CHANGED
    # For push events, the payload includes the list of
    # commits with their added/modified/removed files.
    # We extract all of them and deduplicate.
    # ----------------------------------------------------
    CHANGED_FILES=$(jq -r '
      [ .commits[]? | (.added[]?, .modified[]?, .removed[]?) ] | unique[]?
    ' "$TMP")

    log "[INFO] Changed files in push:"
    while IFS= read -r file; do
        [ -n "$file" ] && log "  - $file"
    done <<< "$CHANGED_FILES"

    # ----------------------------------------------------
    # DECIDE WHETHER TO DEPLOY
    # Any change to billing/, weight/, frontend/,
    # compose files, or devops/ triggers a full deploy.
    # ----------------------------------------------------
    RUN_DEPLOY=false

    while IFS= read -r file; do
        case "$file" in
            billing/* | weight/* | frontend/* | compose* | devops/*)
                RUN_DEPLOY=true
                ;;
        esac
    done <<< "$CHANGED_FILES"

    log "[INFO] Routing decision: run_deploy=$RUN_DEPLOY"

    export COMMIT_SHA

    # ----------------------------------------------------
    # TRIGGER DEPLOY
    # deploy.sh handles: build, deploy to production,
    # smoke test, rollback if needed, push staging->main.
    # Runs in background so webhook returns 200 to GitHub
    # immediately.
    # ----------------------------------------------------
    if [ "$RUN_DEPLOY" = true ]; then
        log "[INFO] Running deploy mode"
        /home/ubuntu/opt/scripts/deploy.sh &
    else
        log "[INFO] No relevant changes. Skipping deploy."
    fi

    rm -f "$TMP"
    exit 0
fi

# ----------------------------------------------------
# UNKNOWN EVENT
# GitHub can send many event types (issues, comments,
# releases, etc.). We don't care about any of them.
# Log it and move on.
# ----------------------------------------------------
log "[INFO] Unknown event type: $EVENT. Ignoring."
rm -f "$TMP"
exit 0
