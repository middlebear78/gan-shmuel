#!/bin/bash
set -e

COMPOSE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$COMPOSE_DIR"

echo "=== Building and starting containers ==="
docker compose up -d --build

echo ""
echo "=== Waiting for billing-app to be ready ==="
for i in $(seq 1 30); do
    if docker compose exec billing-app python -c "print('ready')" &>/dev/null; then
        echo "billing-app is up."
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "ERROR: billing-app failed to start within 30 seconds."
        docker compose logs
        docker compose down -v
        exit 1
    fi
    sleep 1
done

echo ""
echo "=== Running pytest inside billing-app container ==="
docker compose exec billing-app pytest tests/ -v
TEST_EXIT_CODE=$?

echo ""
echo "=== Tearing down containers ==="
docker compose down -v

if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo "All tests passed."
else
    echo "Some tests failed (exit code: $TEST_EXIT_CODE)."
fi

exit $TEST_EXIT_CODE
