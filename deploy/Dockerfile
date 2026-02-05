# Quantum App Container
# Base image for running Quantum applications
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    QUANTUM_ENV=production \
    QUANTUM_PORT=8080

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user for security
RUN useradd --create-home --shell /bin/bash quantum

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all app files (components, static, source code, etc.)
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p logs components static data && chown -R quantum:quantum /app

# Create default config if not exists
RUN if [ ! -f quantum.config.yaml ]; then \
    echo "server:" > quantum.config.yaml && \
    echo "  port: 8080" >> quantum.config.yaml && \
    echo "  host: 0.0.0.0" >> quantum.config.yaml && \
    echo "  reload: false" >> quantum.config.yaml && \
    echo "  debug: false" >> quantum.config.yaml && \
    echo "paths:" >> quantum.config.yaml && \
    echo "  components: ./components" >> quantum.config.yaml && \
    echo "  static: ./static" >> quantum.config.yaml && \
    echo "  logs: ./logs" >> quantum.config.yaml && \
    echo "defaults:" >> quantum.config.yaml && \
    echo "  component_type: pure" >> quantum.config.yaml && \
    echo "  charset: utf-8" >> quantum.config.yaml && \
    echo "  timeout: 30" >> quantum.config.yaml && \
    echo "performance:" >> quantum.config.yaml && \
    echo "  cache_templates: true" >> quantum.config.yaml && \
    echo "  cache_ttl: 300" >> quantum.config.yaml && \
    echo "security:" >> quantum.config.yaml && \
    echo "  xss_protection: true" >> quantum.config.yaml && \
    echo "logging:" >> quantum.config.yaml && \
    echo "  level: INFO" >> quantum.config.yaml && \
    echo "  console: true" >> quantum.config.yaml; \
    fi

# Switch to non-root user
USER quantum

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run with Gunicorn (use app's gunicorn.conf.py if present)
CMD ["sh", "-c", "if [ -f gunicorn.conf.py ]; then gunicorn --config gunicorn.conf.py src.runtime.wsgi:app; else gunicorn --bind 0.0.0.0:8080 --workers ${GUNICORN_WORKERS:-2} --timeout ${GUNICORN_TIMEOUT:-300} src.runtime.wsgi:app; fi"]
