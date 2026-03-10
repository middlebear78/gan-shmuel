#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

docker compose -f "$SCRIPT_DIR/docker-compose.dev.yml" up --build -d

echo ""
echo "Frontend: http://localhost:8082"
echo "Weight:   http://localhost:8080"
echo "Billing:  http://localhost:8081"
