"""
Platform-specific compilers

Each compiler takes Universal AST and generates platform-specific output:
- web.py: HTML/CSS/JavaScript
- mobile.py: React Native (future)
- desktop.py: Tauri (future)
- cli.py: Rich TUI (future)
"""

from .web import WebCompiler

__all__ = ['WebCompiler']
