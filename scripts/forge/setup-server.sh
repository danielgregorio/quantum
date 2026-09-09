#!/bin/bash
#
# Quantum Server Setup Script
# Run this once on a fresh server to configure everything
#
# Usage: sudo ./setup-server.sh
#

set -e

echo "=========================================="
echo "Quantum Server Setup"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo ./setup-server.sh)"
    exit 1
fi

# Update system
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install dependencies
echo "Installing dependencies..."
apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    nginx \
    curl \
    git \
    supervisor \
    certbot \
    python3-certbot-nginx

# Create www-data user directories
echo "Setting up directories..."
mkdir -p /var/www/quantum-app/blue
mkdir -p /var/www/quantum-app/green
mkdir -p /var/www/quantum-staging
mkdir -p /var/www/previews
chown -R www-data:www-data /var/www/

# Initialize current slot
echo "blue" > /var/www/quantum-app/current_slot

# Create systemd services
echo "Creating systemd services..."

# Blue slot service
cat > /etc/systemd/system/quantum-blue.service << 'EOF'
[Unit]
Description=Quantum App (Blue Slot)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/quantum-app/blue
Environment="PATH=/var/www/quantum-app/blue/venv/bin"
ExecStart=/var/www/quantum-app/blue/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8080 \
    --timeout 120 \
    --access-logfile /var/log/quantum/blue-access.log \
    --error-logfile /var/log/quantum/blue-error.log \
    'src.runtime.web_server:create_app()'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Green slot service
cat > /etc/systemd/system/quantum-green.service << 'EOF'
[Unit]
Description=Quantum App (Green Slot)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/quantum-app/green
Environment="PATH=/var/www/quantum-app/green/venv/bin"
ExecStart=/var/www/quantum-app/green/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:8081 \
    --timeout 120 \
    --access-logfile /var/log/quantum/green-access.log \
    --error-logfile /var/log/quantum/green-error.log \
    'src.runtime.web_server:create_app()'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Staging service
cat > /etc/systemd/system/quantum-staging.service << 'EOF'
[Unit]
Description=Quantum App (Staging)
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/quantum-staging
Environment="PATH=/var/www/quantum-staging/venv/bin"
ExecStart=/var/www/quantum-staging/venv/bin/gunicorn \
    --workers 2 \
    --bind 127.0.0.1:8082 \
    --timeout 120 \
    --access-logfile /var/log/quantum/staging-access.log \
    --error-logfile /var/log/quantum/staging-error.log \
    'src.runtime.web_server:create_app()'
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Create log directory
mkdir -p /var/log/quantum
chown www-data:www-data /var/log/quantum

# Reload systemd
systemctl daemon-reload

# Setup nginx
echo "Configuring nginx..."

cat > /etc/nginx/sites-available/quantum << 'EOF'
# Quantum Production
upstream quantum-blue {
    server 127.0.0.1:8080;
}

upstream quantum-green {
    server 127.0.0.1:8081;
}

server {
    listen 80;
    server_name quantum.sargas.cloud;

    location / {
        proxy_pass http://quantum-blue;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_read_timeout 120s;
    }

    location /health {
        proxy_pass http://quantum-blue;
        proxy_set_header Host $host;
    }

    # Static files (if any)
    location /static {
        alias /var/www/quantum-app/blue/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF

cat > /etc/nginx/sites-available/quantum-staging << 'EOF'
# Quantum Staging
server {
    listen 80;
    server_name staging.quantum.sargas.cloud;

    location / {
        proxy_pass http://127.0.0.1:8082;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://127.0.0.1:8082;
        proxy_set_header Host $host;
    }
}
EOF

# Enable sites
ln -sf /etc/nginx/sites-available/quantum /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/quantum-staging /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test and reload nginx
nginx -t
systemctl reload nginx

# Setup firewall
echo "Configuring firewall..."
ufw allow OpenSSH
ufw allow 'Nginx Full'
ufw --force enable

echo "=========================================="
echo "Server setup complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Configure SSL: certbot --nginx -d quantum.sargas.cloud"
echo "2. Add GitHub deploy key to ~/.ssh/authorized_keys"
echo "3. Set up secrets in GitHub repository"
echo "4. Push to main branch to trigger first deploy"
echo ""
echo "Services:"
echo "  - quantum-blue  (port 8080)"
echo "  - quantum-green (port 8081)"
echo "  - quantum-staging (port 8082)"
echo ""
echo "Logs:"
echo "  - /var/log/quantum/"
echo "  - /var/log/nginx/"
echo "=========================================="
