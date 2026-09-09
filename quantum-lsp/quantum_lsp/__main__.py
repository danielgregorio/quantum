"""
Entry point for running quantum-lsp as a module.

Usage:
    python -m quantum_lsp --stdio
"""

from .server import main

if __name__ == "__main__":
    main()
