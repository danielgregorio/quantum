#!/bin/bash
#
# Quantum Rollback Script
# Usage: ./rollback.sh [slot]
#

set -e

SLOT=${1:-$(cat /var/www/quantum-app/current_slot 2>/dev/null || echo "blue")}
DEPLOY_PATH="/var/www/quantum-app"
SLOT_PATH="$DEPLOY_PATH/$SLOT"
BACKUP_PATH="${SLOT_PATH}.bak"

echo "=========================================="
echo "Quantum Rollback Script"
echo "=========================================="
echo "Rolling back slot: $SLOT"
echo "=========================================="

# Check backup exists
if [ ! -d "$BACKUP_PATH" ]; then
    echo "Error: No backup found at $BACKUP_PATH"
    echo "Available backups:"
    ls -la "$DEPLOY_PATH"/*.bak 2>/dev/null || echo "  None"
    exit 1
fi

# Stop current instance
echo "Stopping quantum-$SLOT..."
sudo systemctl stop "quantum-$SLOT" || true

# Restore backup
echo "Restoring backup..."
sudo rm -rf "$SLOT_PATH"
sudo mv "$BACKUP_PATH" "$SLOT_PATH"

# Restart service
echo "Starting quantum-$SLOT..."
sudo systemctl start "quantum-$SLOT"

# Health check
echo "Running health check..."
sleep 5

PORT=$([ "$SLOT" == "blue" ] && echo "8080" || echo "8081")
STATUS=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$PORT/health" 2>/dev/null || echo "000")

if [ "$STATUS" == "200" ]; then
    echo "=========================================="
    echo "Rollback successful!"
    echo "=========================================="
else
    echo "=========================================="
    echo "Warning: Health check returned $STATUS"
    echo "Manual intervention may be required."
    echo "=========================================="
    exit 1
fi
