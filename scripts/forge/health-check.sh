#!/bin/bash
#
# Quantum Health Check Script
# Usage: ./health-check.sh [port] [max_attempts]
#

PORT=${1:-8080}
MAX_ATTEMPTS=${2:-10}
SLEEP_INTERVAL=3

echo "=========================================="
echo "Quantum Health Check"
echo "=========================================="
echo "Port: $PORT"
echo "Max attempts: $MAX_ATTEMPTS"
echo "=========================================="

for i in $(seq 1 $MAX_ATTEMPTS); do
    echo "Attempt $i/$MAX_ATTEMPTS..."

    # Check HTTP status
    STATUS=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT/health" 2>/dev/null || echo "000")

    if [ "$STATUS" == "200" ]; then
        echo "=========================================="
        echo "Health check PASSED!"
        echo "=========================================="

        # Additional checks
        echo "Checking response time..."
        RESPONSE_TIME=$(curl -s -o /dev/null -w '%{time_total}' "http://localhost:$PORT/health")
        echo "Response time: ${RESPONSE_TIME}s"

        if (( $(echo "$RESPONSE_TIME > 5" | bc -l) )); then
            echo "Warning: Response time is slow (>5s)"
        fi

        exit 0
    fi

    echo "Status: $STATUS (expected 200)"
    sleep $SLEEP_INTERVAL
done

echo "=========================================="
echo "Health check FAILED!"
echo "=========================================="
exit 1
