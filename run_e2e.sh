#!/usr/bin/env bash
# ---------------------------------------------------------------
# E2E test runner
#
# 1. Builds and starts both services (billing + weight) with Docker Compose
# 2. Waits for them to be healthy
# 3. Runs the E2E pytest suite against the live services
# 4. Tears everything down when done (pass --keep to skip teardown)
# ---------------------------------------------------------------

set -euo pipefail

# directory where this script lives (project root)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# docker compose file for the E2E environment
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.e2e.yml"

# the ports we expose for the E2E services (must match docker-compose.e2e.yml)
BILLING_URL="http://localhost:8090"
WEIGHT_URL="http://localhost:80"

# check if user passed --keep to skip teardown
KEEP_RUNNING=false
if [[ "${1:-}" == "--keep" ]]; then
    KEEP_RUNNING=true
fi

# cleanup function — runs on exit unless --keep was passed
cleanup() {
    if [ "$KEEP_RUNNING" = false ]; then
        echo ""
        echo "==> Tearing down E2E containers..."
        docker compose -f "$COMPOSE_FILE" down -v --remove-orphans
    else
        echo ""
        echo "==> Containers left running (--keep). Tear down manually with:"
        echo "    docker compose -f $COMPOSE_FILE down -v"
    fi
}

# register the cleanup function to run on script exit
trap cleanup EXIT

# pre-create the shared /in directory so Docker doesn't create it as root
mkdir -p "$SCRIPT_DIR/tests/e2e/in"

echo "==> Building and starting E2E services..."
docker compose -f "$COMPOSE_FILE" up --build -d

echo "==> Waiting for services to become healthy..."

# wait_for_service: polls a URL until it returns 200 or times out
wait_for_service() {
    local url="$1"
    local name="$2"
    local timeout="${3:-90}"
    local elapsed=0

    while [ $elapsed -lt $timeout ]; do
        # try to hit the health endpoint
        if curl -sf "$url/health" > /dev/null 2>&1; then
            echo "    $name is up ($url)"
            return 0
        fi
        # not ready yet — wait and retry
        sleep 2
        elapsed=$((elapsed + 2))
    done

    # timed out
    echo "ERROR: $name at $url did not become healthy within ${timeout}s"
    echo "==> Container logs:"
    docker compose -f "$COMPOSE_FILE" logs
    exit 1
}

# wait for both services
wait_for_service "$WEIGHT_URL"  "Weight service"  90
wait_for_service "$BILLING_URL" "Billing service" 90

echo ""
echo "==> Running E2E tests..."

# run pytest with the service URLs passed as env vars
BILLING_URL_TEST="$BILLING_URL" \
WEIGHT_URL_TEST="$WEIGHT_URL" \
python3 -m pytest "$SCRIPT_DIR/tests/e2e/" -v --tb=short

echo ""
echo "==> E2E tests passed!"
