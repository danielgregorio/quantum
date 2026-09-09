#!/bin/bash
# Quantum Deploy - Forge VM Setup Script
# Run this once on the forge VM to initialize the deployment infrastructure

set -e

echo "======================================"
echo "  Quantum Deploy - Forge Setup"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: Please run as root (sudo ./setup-forge.sh)"
    exit 1
fi

# Configuration
DATA_DIR="/data/quantum"
NGINX_CONF="/etc/nginx/conf.d/quantum.conf"
NETWORK_NAME="quantum-net"

echo "[1/6] Creating data directories..."
mkdir -p ${DATA_DIR}/{apps,registry,nginx}
chown -R 1000:1000 ${DATA_DIR}
echo "  Created: ${DATA_DIR}"

echo ""
echo "[2/6] Creating Docker network..."
if docker network inspect ${NETWORK_NAME} >/dev/null 2>&1; then
    echo "  Network ${NETWORK_NAME} already exists"
else
    docker network create ${NETWORK_NAME}
    echo "  Created network: ${NETWORK_NAME}"
fi

echo ""
echo "[3/6] Configuring nginx..."

# Create quantum error page
cat > /usr/share/nginx/html/quantum_error.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>Service Unavailable</title>
    <style>
        body { font-family: -apple-system, sans-serif; text-align: center; padding: 50px; }
        h1 { color: #333; }
        p { color: #666; }
        .quantum { color: #6366f1; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Service Temporarily Unavailable</h1>
    <p>The <span class="quantum">Quantum</span> application is starting up or experiencing issues.</p>
    <p>Please try again in a moment.</p>
</body>
</html>
EOF
echo "  Created error page"

# Create main quantum nginx config
cat > ${NGINX_CONF} << 'EOF'
# Quantum Deploy - Nginx Configuration
# Include all app-specific configs

# Include generated app configs
include /data/quantum/nginx/*.conf;

# Deploy API proxy
location /api/deploy {
    proxy_pass http://quantum-deploy-service:9000/api/deploy;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Allow large uploads
    client_max_body_size 100m;

    # Longer timeout for deploy operations
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
}

# Deploy API - other endpoints
location /api/apps {
    proxy_pass http://quantum-deploy-service:9000/api/apps;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
EOF
echo "  Created nginx config: ${NGINX_CONF}"

echo ""
echo "[4/6] Testing nginx configuration..."
nginx -t
echo "  Nginx config is valid"

echo ""
echo "[5/6] Reloading nginx..."
nginx -s reload || systemctl reload nginx
echo "  Nginx reloaded"

echo ""
echo "[6/6] Setting up environment..."

# Create .env file if it doesn't exist
ENV_FILE="${DATA_DIR}/.env"
if [ ! -f "${ENV_FILE}" ]; then
    # Generate random API key
    API_KEY=$(openssl rand -hex 32)
    cat > ${ENV_FILE} << EOF
# Quantum Deploy Environment
QUANTUM_API_KEY=${API_KEY}
QUANTUM_BASE_URL=https://$(hostname -f)
QUANTUM_APPS_DIR=/data/quantum/apps
QUANTUM_NGINX_DIR=/data/quantum/nginx
QUANTUM_REGISTRY_DIR=/data/quantum/registry
EOF
    chmod 600 ${ENV_FILE}
    echo "  Created .env file: ${ENV_FILE}"
    echo ""
    echo "  IMPORTANT: Your API key is: ${API_KEY}"
    echo "  Save this key - you'll need it for deployments!"
else
    echo "  .env file already exists"
fi

echo ""
echo "======================================"
echo "  Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. Start the deploy service:"
echo "     cd /path/to/quantum/deploy"
echo "     docker-compose -f docker-compose.forge.yml up -d"
echo ""
echo "  2. Verify the service is running:"
echo "     curl http://localhost:9000/health"
echo ""
echo "  3. Deploy your first app:"
echo "     quantum deploy ./my-app --name my-app --target forge"
echo ""
echo "  4. Access your app at:"
echo "     https://$(hostname -f)/my-app/"
echo ""
