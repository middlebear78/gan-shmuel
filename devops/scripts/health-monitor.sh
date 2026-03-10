#!/bin/bash

# ----------------------------------------------------
# PRODUCTION HEALTH MONITOR
#
# Runs via cron every 5 minutes. Checks the /health
# endpoint on each production service. If any service
# is down:
#   - Logs the failure
#   - Sends Slack notification
#   - Sends email notification
#
# If all services are healthy, logs a quiet OK line.
# This way the log file always shows a full timeline
# of uptime and downtime.
#
# Cron setup (add with: crontab -e):
#   */5 * * * * /home/ubuntu/opt/scripts/health-monitor.sh
#
# Required env vars (set in crontab or /etc/environment):
#   SLACK_URL, SMTP_HOST, SMTP_PORT, SMTP_USER,
#   SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO
# ----------------------------------------------------

SCRIPTS_DIR="/home/ubuntu/opt/scripts"
LOGDIR="/home/ubuntu/opt/scripts/.logs"
LOGFILE="$LOGDIR/health-monitor.log"

mkdir -p "$LOGDIR"

# ----------------------------------------------------
# SERVICE ENDPOINTS
# Weight and billing use /health, frontend has no
# /health endpoint — check root / which serves
# index.html and returns 200.
# ----------------------------------------------------
WEIGHT_URL="${WEIGHT_URL_PROD:-http://localhost:8080}"
BILLING_URL="${BILLING_URL_PROD:-http://localhost:8081}"
FRONTEND_URL="${FRONTEND_URL_PROD:-http://localhost:8083}"

SLACK_URL="${SLACK_URL:-}"

log() {
    local msg="$1"
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$ts] $msg" >> "$LOGFILE"
}

send_slack() {
    local text="$1"
    [ -z "$SLACK_URL" ] && return 0
    curl -s -X POST -H 'Content-type: application/json' \
      --data "{\"text\":\"$text\"}" \
      "$SLACK_URL" > /dev/null
}

# ----------------------------------------------------
# CHECK EACH SERVICE
# curl -sf: silent + fail on HTTP errors.
# Timeout of 10 seconds per check so a hung service
# doesn't block the whole monitor.
# ----------------------------------------------------
FAILURES=""

# weight
if curl -sf --max-time 10 "$WEIGHT_URL/health" > /dev/null 2>&1; then
    log "[OK] Weight service is healthy ($WEIGHT_URL)"
else
    log "[DOWN] Weight service is NOT responding ($WEIGHT_URL)"
    FAILURES="${FAILURES}Weight ($WEIGHT_URL)\n"
fi

# billing
if curl -sf --max-time 10 "$BILLING_URL/health" > /dev/null 2>&1; then
    log "[OK] Billing service is healthy ($BILLING_URL)"
else
    log "[DOWN] Billing service is NOT responding ($BILLING_URL)"
    FAILURES="${FAILURES}Billing ($BILLING_URL)\n"
fi

# frontend (no /health — check root /)
if curl -sf --max-time 10 "$FRONTEND_URL/" > /dev/null 2>&1; then
    log "[OK] Frontend service is healthy ($FRONTEND_URL)"
else
    log "[DOWN] Frontend service is NOT responding ($FRONTEND_URL)"
    FAILURES="${FAILURES}Frontend ($FRONTEND_URL)\n"
fi

# ----------------------------------------------------
# SEND ALERTS IF ANY SERVICE IS DOWN
# Only notify on failure — no spam when everything
# is healthy. The log file captures the full picture.
# ----------------------------------------------------
if [ -n "$FAILURES" ]; then
    MSG="🚨 Production health check FAILED:\n${FAILURES}Check logs: $LOGFILE"
    send_slack "$MSG"
    python3 "$SCRIPTS_DIR/send_email.py" \
      --event deploy --status fail \
      --details "Health monitor: services down - $(echo -e "$FAILURES" | tr '\n' ' ')" || true
    log "[ALERT] Notifications sent for failed health check"
fi
