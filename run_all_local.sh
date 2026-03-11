#!/bin/bash
docker compose -f docker-compose.dev.yml up --build -d

echo ""
echo "Frontend: http://localhost:8082"
echo "Weight:   http://localhost:8080"
echo "Billing:  http://localhost:8081"
