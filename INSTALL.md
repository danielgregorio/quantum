# 🚀 Quantum Admin Installation Guide

Welcome to the **Quantum Admin** interactive installer! This guide will help you get started with the most powerful admin interface for your projects.

---

## 📋 Prerequisites

Before running the installer, ensure you have:

- **Python 3.9+** installed
- **Git** (optional, for cloning the repository)
- **Docker** (optional, for containerized services)
- **8GB RAM** minimum (16GB recommended)
- **2GB free disk space**

---

## ⚡ Quick Install

The **fastest** way to install Quantum Admin:

```bash
# Clone the repository (or download the source)
git clone https://github.com/quantum/admin.git
cd admin

# Run the interactive installer
python3 install.py
```

That's it! The installer will guide you through everything else. ✨

---

## 🎯 Installation Types

The installer offers three installation modes:

### 1️⃣ Full Installation (Recommended)

**Best for:** Production deployments

Includes:
- ✅ All features and components
- ✅ Docker services (PostgreSQL, Redis, Celery)
- ✅ Performance optimization
- ✅ WebSocket server
- ✅ Background job queue
- ✅ Caching layer

**Requirements:**
- Docker installed and running
- 16GB RAM recommended

---

### 2️⃣ Development Installation

**Best for:** Local development

Includes:
- ✅ Core admin interface
- ✅ SQLite database (no Docker required)
- ✅ Hot-reload for development
- ✅ Debug mode enabled

**Requirements:**
- Python 3.9+
- No Docker needed

---

### 3️⃣ Custom Installation

**Best for:** Advanced users

Choose exactly which components you want:
- 🔧 Select database type
- 🔧 Enable/disable Redis
- 🔧 Configure authentication
- 🔧 Choose services to install

---

## 🎨 Installer Features

The Quantum Admin installer provides:

### 📊 System Verification
- ✓ Checks Python version
- ✓ Verifies Docker installation
- ✓ Tests port availability
- ✓ Validates dependencies

### 🎯 Interactive Configuration
- Choose installation type
- Configure database settings
- Set up Redis caching
- Create admin user
- Customize environment

### 📦 Automatic Setup
- Installs Python dependencies
- Creates configuration files
- Initializes database
- Sets up services

### 🎨 Beautiful CLI
- Rich terminal UI with colors
- Progress bars and spinners
- Clear error messages
- Configuration preview

---

## 🔧 Manual Installation

If you prefer to install manually:

### 1. Install Dependencies

```bash
cd quantum_admin
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the root directory:

```bash
cp .env.example .env
nano .env
```

Edit the configuration:

```ini
# Database
DATABASE_URL=sqlite:///quantum_admin.db

# JWT Secret (generate with: openssl rand -hex 32)
JWT_SECRET_KEY=your-secret-key-here

# Admin Credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@quantum.local

# Redis (optional)
REDIS_ENABLED=false
```

### 3. Initialize Database

```bash
cd quantum_admin/backend
python main.py
```

The application will auto-create tables on first run.

### 4. Access the Interface

Open your browser:
```
http://localhost:8000/static/login.html
```

---

## 🐳 Docker Installation

For Docker deployment:

```bash
# Build the image
docker-compose build

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

Services included:
- **web**: Quantum Admin API (port 8000)
- **db**: PostgreSQL database (port 5432)
- **redis**: Redis cache (port 6379)
- **celery**: Background worker
- **celery-beat**: Scheduler

---

## 📱 Accessing Quantum Admin

After installation, access these URLs:

| Service | URL | Description |
|---------|-----|-------------|
| **Admin UI** | http://localhost:8000/static/login.html | Main admin interface |
| **API Docs** | http://localhost:8000/docs | Interactive API documentation |
| **WebSocket** | ws://localhost:8000/ws/{client_id} | Real-time updates |
| **Pipeline Editor** | http://localhost:8000/static/pipeline-editor.html | Jenkins pipeline designer |
| **DevOps Dashboard** | http://localhost:8000/static/devops.html | CI/CD management |

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

⚠️ **Remember to change the default password after first login!**

---

## 🔍 Troubleshooting

### Port Already in Use

If port 8000 is occupied:

```bash
# Find process using port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change port in .env
PORT=8080
```

### Docker Not Running

```bash
# Start Docker daemon (Linux)
sudo systemctl start docker

# Start Docker Desktop (macOS/Windows)
# Use the Docker Desktop application
```

### Database Connection Error

Check your database configuration:

```bash
# Test PostgreSQL connection
psql -h localhost -U postgres -d quantum_admin

# Test MySQL connection
mysql -h localhost -u root -p quantum_admin
```

### Permission Denied

```bash
# Make installer executable
chmod +x install.py

# Run with proper permissions
sudo python3 install.py
```

---

## 🆘 Getting Help

If you encounter issues:

1. **Check the logs:**
   ```bash
   tail -f quantum_admin/logs/app.log
   ```

2. **Run the health check:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **View installation log:**
   ```bash
   cat quantum_install.log
   ```

4. **Community Support:**
   - GitHub Issues: https://github.com/quantum/admin/issues
   - Discord: https://discord.gg/quantum
   - Docs: https://docs.quantum.com

---

## 🎯 Next Steps

After successful installation:

1. **Configure Authentication**
   - Add users and roles
   - Set up SSO/OAuth (optional)
   - Configure permissions

2. **Connect Data Sources**
   - Add databases
   - Configure containers
   - Set up monitoring

3. **Customize Interface**
   - Create components
   - Design templates
   - Build dashboards

4. **Set Up Automation**
   - Create pipelines
   - Configure webhooks
   - Schedule jobs

---

## 📚 Documentation

Full documentation available at:
- **User Guide**: https://docs.quantum.com/user-guide
- **API Reference**: https://docs.quantum.com/api
- **Architecture**: https://docs.quantum.com/architecture
- **Contributing**: https://docs.quantum.com/contributing

---

## 📝 License

Quantum Admin is released under the MIT License.

---

## 🙏 Thank You!

Thank you for choosing **Quantum Admin**! We hope you enjoy using it as much as we enjoyed building it.

If you find it useful, please:
- ⭐ Star us on GitHub
- 🐛 Report bugs and suggest features
- 💬 Join our community
- 📢 Share with others

**Happy administrating!** 🚀✨
