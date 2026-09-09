"""Gunicorn configuration for Quantum RAG Demo."""

bind = "0.0.0.0:8080"
workers = 2
timeout = 600  # 10 min - knowledge base embedding can be slow on first load
graceful_timeout = 600
