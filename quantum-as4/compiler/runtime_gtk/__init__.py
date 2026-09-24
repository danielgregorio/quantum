"""
GTK Runtime Package - Desktop equivalent of web runtime

Provides GTK-based rendering of MXML applications for native desktop support.
"""

from .reactive_runtime_gtk import GTKReactiveRuntime, ReactiveObject, run_gtk_app
from .components_gtk import *

__all__ = ['GTKReactiveRuntime', 'ReactiveObject', 'run_gtk_app']
