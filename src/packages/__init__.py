"""
Quantum Package Manager

Package management system for sharing Quantum components.

Features:
- Package manifest handling (quantum.yaml)
- Local package registry (~/.quantum/packages/)
- Dependency resolution with version constraints
- Install, remove, list, search operations
- CLI integration (quantum pkg ...)
"""

from .manifest import PackageManifest, ManifestError
from .registry import PackageRegistry, RegistryError
from .resolver import DependencyResolver, ResolutionError
from .manager import PackageManager, PackageError

__all__ = [
    'PackageManifest',
    'ManifestError',
    'PackageRegistry',
    'RegistryError',
    'DependencyResolver',
    'ResolutionError',
    'PackageManager',
    'PackageError',
]
