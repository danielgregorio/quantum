#!/bin/bash
#
# Quantum Forge Deploy Script
# Usage: ./deploy.sh [blue|green] [package.tar.gz]
#

set -e

SLOT=${1:-blue}
PACKAGE=${2:-/tmp/quantum-app.tar.gz}
DEPLOY_PATH="/var/www/quantum-app"
SLOT_PATH="$DEPLOY_PATH/$SLOT"

echo "=========================================="
echo "Quantum Deploy Script"
echo "=========================================="
echo "Slot: $SLOT"
echo "Package: $PACKAGE"
echo "Deploy path: $SLOT_PATH"
echo "=========================================="

# Validate slot
if [[ "$SLOT" != "blue" && "$SLOT" != "green" ]]; then
    echo "Error: Invalid slot. Use 'blue' or 'green'"
    exit 1
fi

# Check package exists
if [ ! -f "$PACKAGE" ]; then
    echo "Error: Package not found: $PACKAGE"
    exit 1
fi

# Backup current deployment
if [ -d "$SLOT_PATH" ]; then
    echo "Backing up current deployment..."
    sudo rm -rf "${SLOT_PATH}.bak"
    sudo mv "$SLOT_PATH" "${SLOT_PATH}.bak"
fi

# Extract new deployment
echo "Extracting package..."
sudo mkdir -p "$SLOT_PATH"
sudo tar -xzf "$PACKAGE" -C "$SLOT_PATH"
sudo chown -R www-data:www-data "$SLOT_PATH"

# Setup virtual environment
echo "Setting up virtual environment..."
cd "$SLOT_PATH"
sudo -u www-data python3 -m venv venv
sudo -u www-data ./venv/bin/pip install --upgrade pip
sudo -u www-data ./venv/bin/pip install -e ".[db]"

# Copy environment file if exists
if [ -f "$DEPLOY_PATH/.env" ]; then
    echo "Copying environment file..."
    sudo cp "$DEPLOY_PATH/.env" "$SLOT_PATH/.env"
    sudo chown www-data:www-data "$SLOT_PATH/.env"
fi

# Start the new instance
echo "Starting quantum-$SLOT service..."
sudo systemctl start "quantum-$SLOT"

echo "=========================================="
echo "Deployment to $SLOT completed!"
echo "Run health check before switching traffic."
echo "=========================================="
