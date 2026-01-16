# Quantum Admin - Makefile
# Simplified commands for common operations

.PHONY: help install install-quick install-dev start stop restart status logs shell test clean build-exe docker-up docker-down

# Colors
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo ""
	@echo "$(CYAN)Quantum Admin - Available Commands$(NC)"
	@echo "$(YELLOW)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""

# Installation
install: ## Run interactive installer
	@echo "$(CYAN)→ Launching interactive installer...$(NC)"
	@python3 install.py

install-quick: ## Quick install with defaults (SQLite, dev mode)
	@echo "$(CYAN)→ Quick installation...$(NC)"
	@cd quantum_admin && python3 -m pip install -r requirements.txt --quiet
	@echo "DATABASE_URL=sqlite:///quantum_admin.db" > .env
	@echo "JWT_SECRET_KEY=$$(openssl rand -hex 32)" >> .env
	@echo "ADMIN_USERNAME=admin" >> .env
	@echo "ADMIN_PASSWORD=admin123" >> .env
	@echo "REDIS_ENABLED=false" >> .env
	@echo "$(GREEN)✓ Quick installation complete!$(NC)"
	@echo ""
	@echo "Run 'make start' to launch the server"

install-dev: ## Install for development (with testing tools)
	@echo "$(CYAN)→ Installing development dependencies...$(NC)"
	@cd quantum_admin && python3 -m pip install -r requirements.txt
	@python3 -m pip install pytest pytest-cov pytest-asyncio black flake8 mypy
	@echo "$(GREEN)✓ Development environment ready!$(NC)"

# Server Management
start: ## Start Quantum Admin server
	@echo "$(CYAN)→ Starting Quantum Admin...$(NC)"
	@python3 quantum-cli.py start

start-dev: ## Start server with hot-reload (development)
	@echo "$(CYAN)→ Starting Quantum Admin (dev mode)...$(NC)"
	@python3 quantum-cli.py start --reload

stop: ## Stop Quantum Admin server
	@echo "$(CYAN)→ Stopping Quantum Admin...$(NC)"
	@python3 quantum-cli.py stop

restart: ## Restart Quantum Admin server
	@echo "$(CYAN)→ Restarting Quantum Admin...$(NC)"
	@python3 quantum-cli.py restart

status: ## Show server status
	@python3 quantum-cli.py status

logs: ## View server logs
	@python3 quantum-cli.py logs

logs-follow: ## Follow server logs (tail -f)
	@python3 quantum-cli.py logs --follow

# Development
shell: ## Open interactive Python shell with Quantum context
	@python3 quantum-cli.py shell

test: ## Run test suite
	@echo "$(CYAN)→ Running tests...$(NC)"
	@python3 quantum-cli.py test

test-cov: ## Run tests with coverage report
	@echo "$(CYAN)→ Running tests with coverage...$(NC)"
	@cd quantum_admin && pytest tests/ --cov=backend --cov-report=html --cov-report=term
	@echo ""
	@echo "$(GREEN)✓ Coverage report generated at quantum_admin/htmlcov/index.html$(NC)"

migrate: ## Run database migrations
	@echo "$(CYAN)→ Running migrations...$(NC)"
	@python3 quantum-cli.py migrate

# Docker
docker-up: ## Start Docker Compose stack
	@echo "$(CYAN)→ Starting Docker stack...$(NC)"
	@docker-compose up -d
	@echo "$(GREEN)✓ Docker stack started!$(NC)"
	@docker-compose ps

docker-down: ## Stop Docker Compose stack
	@echo "$(CYAN)→ Stopping Docker stack...$(NC)"
	@docker-compose down

docker-logs: ## View Docker container logs
	@docker-compose logs -f

docker-ps: ## Show running containers
	@docker-compose ps

# Build
build-exe: ## Build Windows executable (setup.exe)
	@echo "$(CYAN)→ Building Windows executable...$(NC)"
	@python3 build-exe.py

# Cleanup
clean: ## Clean build artifacts and cache
	@echo "$(CYAN)→ Cleaning...$(NC)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@rm -rf build/ dist/ *.spec 2>/dev/null || true
	@rm -f quantum.pid 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete!$(NC)"

clean-all: clean ## Clean everything including database and logs
	@echo "$(CYAN)→ Deep cleaning...$(NC)"
	@rm -f quantum_admin.db quantum_admin.log .env 2>/dev/null || true
	@echo "$(GREEN)✓ Deep cleanup complete!$(NC)"

# Info
info: ## Show system and project info
	@echo ""
	@echo "$(CYAN)Quantum Admin - System Information$(NC)"
	@echo "$(YELLOW)═══════════════════════════════════════════════════════════$(NC)"
	@echo ""
	@echo "Python Version:"
	@python3 --version
	@echo ""
	@echo "Docker Version:"
	@docker --version 2>/dev/null || echo "  Not installed"
	@echo ""
	@echo "Git Version:"
	@git --version 2>/dev/null || echo "  Not installed"
	@echo ""
	@echo "Project Location:"
	@pwd
	@echo ""

# Database & Schema
schema: ## Inspect database schema
	@echo "$(CYAN)→ Inspecting database schema...$(NC)"
	@python3 quantum-cli.py schema

schema-models: ## Generate SQLAlchemy models from database
	@echo "$(CYAN)→ Generating models from database...$(NC)"
	@cd quantum_admin/backend && python3 -c "from schema_inspector import inspect_database; inspector = inspect_database('sqlite:///../../quantum_admin.db'); print(inspector.generate_sqlalchemy_models())" > generated_models.py
	@echo "$(GREEN)✓ Models generated at quantum_admin/backend/generated_models.py$(NC)"

migration-create: ## Create new migration (usage: make migration-create MSG="your message")
	@echo "$(CYAN)→ Creating migration...$(NC)"
	@cd quantum_admin/backend && alembic revision --autogenerate -m "$(MSG)"

migration-upgrade: ## Run all pending migrations
	@echo "$(CYAN)→ Running migrations...$(NC)"
	@cd quantum_admin/backend && alembic upgrade head

migration-downgrade: ## Rollback last migration
	@echo "$(CYAN)→ Rolling back migration...$(NC)"
	@cd quantum_admin/backend && alembic downgrade -1

migration-history: ## Show migration history
	@cd quantum_admin/backend && alembic history

# Quick aliases
i: install ## Alias for 'install'
s: start ## Alias for 'start'
t: test ## Alias for 'test'
c: clean ## Alias for 'clean'
m: migrate ## Alias for 'migrate'

# Default target
.DEFAULT_GOAL := help
