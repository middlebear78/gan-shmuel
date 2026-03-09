#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────
# run_tests.sh — Automated test runner for the Weight team
#
# Usage: ./run_tests.sh  (run from the weight/ directory)
# ─────────────────────────────────────────────────────────
set -e

COMPOSE_FILE="docker-compose-dev.yaml"
APP_SERVICE="app"

# ── Pre-flight checks ──
if [[ ! -f "$COMPOSE_FILE" ]]; then
    echo "ERROR: $COMPOSE_FILE not found."
    echo "Make sure you run this script from the weight/ directory."
    exit 1
fi

if [[ ! -f ".env" ]]; then
    echo "ERROR: .env file not found."
    echo "Copy .env.example to .env and fill in the values first."
    exit 1
fi

echo "========================================"
echo "  Weight Team — Test Runner"
echo "========================================"

# ── Step 1: Tear down existing containers + volumes ──
echo ""
echo "[1/3] Tearing down existing containers..."
docker compose -f "$COMPOSE_FILE" down -v 2>/dev/null || true

# ── Step 2: Build and start services, wait for healthy ──
echo ""
echo "[2/3] Building and starting services..."
docker compose -f "$COMPOSE_FILE" up --build --wait -d

# ── Step 3: Run pytest inside the app container ──
echo ""
echo "[3/3] Running tests..."
echo "----------------------------------------"

set +e
docker compose -f "$COMPOSE_FILE" exec -T "$APP_SERVICE" pytest tests/ -v --color=yes
TEST_EXIT_CODE=$?
set -e

echo "----------------------------------------"

# ── Clean up based on results ──
if [[ $TEST_EXIT_CODE -eq 0 ]]; then
    echo ""
    echo "Tearing down containers..."
    docker compose -f "$COMPOSE_FILE" down -v
else
    echo ""
    echo "Leaving containers running so you can debug."
    echo "To get inside the app container:"
    echo ""
    echo "  docker compose -f $COMPOSE_FILE exec $APP_SERVICE bash"
    echo ""
    echo "From there you can run specific tests:"
    echo ""
    echo "  pytest tests/integration/test_post_weight.py -v"
    echo ""
    echo "When you're done, tear down with:"
    echo ""
    echo "  docker compose -f $COMPOSE_FILE down -v"
fi

exit $TEST_EXIT_CODE