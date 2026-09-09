"""
CLI Runtime Package - Terminal/Console version of MXML runtime

Provides text-based CLI rendering of MXML applications.
"""

from .reactive_runtime_cli import CLIReactiveRuntime, ReactiveObject, run_cli_app
from .components_cli import *

__all__ = ['CLIReactiveRuntime', 'ReactiveObject', 'run_cli_app']
