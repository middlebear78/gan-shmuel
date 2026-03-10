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
# TWO SCENARIOS:
#   PR opened/updated targeting staging → run tests
#   Push to staging (PR merged)         → run deploy
#     (deploy.sh doesn't exist yet — coming later)
# ----------------------------------------------------

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

log "========================================"
log "[INFO] Router triggered — event=$EVENT"

# ----------------------------------------------------
# Save the JSON payload to a temp file so we can parse
# it with jq. We clean it up before exiting.
# ----------------------------------------------------
TMP=$(mktemp)
printf '%s' "$PAYLOAD" > "$TMP"

# ----------------------------------------------------
# PULL REQUEST EVENT
# Fires when someone opens a new PR or pushes new
# commits to an existing PR. We only care about PRs
# that target the staging branch. We figure out which
# files changed by doing a git diff between the PR
# branch and staging, then call the right test script.
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

    # Only react to "opened" (new PR) or "synchronize" (new commits pushed).
    # Ignore everything else: closed, labeled, assigned, etc.
    if [ "$ACTION" != "opened" ] && [ "$ACTION" != "synchronize" ]; then
        log "[INFO] Ignoring PR action: $ACTION"
        rm -f "$TMP"
        exit 0
    fi

    # Only care about PRs targeting staging.
    # PRs to main, weight, billing, etc. are not our business.
    if [ "$BASE_BRANCH" != "staging" ]; then
        log "[INFO] PR targets $BASE_BRANCH, not staging. Ignoring."
        rm -f "$TMP"
        exit 0
    fi

    # ----------------------------------------------------
    # DETECT WHICH FILES CHANGED
    # We fetch both branches from the bare repo on EC2,
    # then git diff to see which files are different
    # between the PR branch and staging. This tells us
    # if billing/, weight/, or both were modified.
    # ----------------------------------------------------
    cd /home/ubuntu/opt/gan-shmuel.git
    git fetch origin "$PR_BRANCH" staging 2>/dev/null || true
    CHANGED=$(git diff --name-only "origin/staging...origin/$PR_BRANCH" 2>/dev/null || echo "")

    log "[INFO] Changed files in PR:"
    while IFS= read -r file; do
        [ -n "$file" ] && log "  - $file"
    done <<< "$CHANGED"

    # ----------------------------------------------------
    # DECIDE WHICH TEST SCRIPT TO RUN
    # billing changed → run billing + weight (billing depends on weight)
    # weight changed  → run weight only
    # neither changed → skip
    # ----------------------------------------------------
    RUN_BILLING=false
    RUN_WEIGHT=false

    while IFS= read -r file; do
        case "$file" in
            billing/*)
                RUN_BILLING=true
                RUN_WEIGHT=true
                ;;
            weight/*)
                RUN_WEIGHT=true
                ;;
        esac
    done <<< "$CHANGED"

    log "[INFO] Routing decision: billing=$RUN_BILLING weight=$RUN_WEIGHT"

    # Export COMMIT_SHA so the test scripts can post
    # GitHub commit status (green checkmark / red X)
    export COMMIT_SHA

    if [ "$RUN_BILLING" = true ]; then
        log "[INFO] Running billing + weight tests (TEST MODE)"
        /home/ubuntu/opt/scripts/test-billing-and-weight.sh &
    elif [ "$RUN_WEIGHT" = true ]; then
        log "[INFO] Running weight-only tests (TEST MODE)"
        /home/ubuntu/opt/scripts/test-weight.sh &
    else
        log "[INFO] No billing/weight changes in PR. Skipping."
    fi

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

    RUN_BILLING=false
    RUN_WEIGHT=false

    while IFS= read -r file; do
        case "$file" in
            billing/*)
                RUN_BILLING=true
                RUN_WEIGHT=true
                ;;
            weight/*)
                RUN_WEIGHT=true
                ;;
        esac
    done <<< "$CHANGED_FILES"

    log "[INFO] Routing decision: billing=$RUN_BILLING weight=$RUN_WEIGHT"

    export COMMIT_SHA

    # ----------------------------------------------------
    # TRIGGER DEPLOY
    # deploy.sh handles: build, deploy to production,
    # smoke test, rollback if needed, push staging->main.
    # We pass which services changed so it only deploys
    # what's needed. Runs in background so webhook
    # returns 200 to GitHub immediately.
    # (deploy.sh will be created in a later step)
    # ----------------------------------------------------
    if [ "$RUN_BILLING" = true ] || [ "$RUN_WEIGHT" = true ]; then
        log "[INFO] Running deploy mode"
        /home/ubuntu/opt/scripts/deploy.sh "$RUN_BILLING" "$RUN_WEIGHT" &
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
