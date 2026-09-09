"""
Quantum Dependency Resolver

Resolves package dependencies with version constraints.

Supported version constraints:
- Exact: "1.0.0"
- Caret: "^1.0.0" (compatible with 1.x.x)
- Tilde: "~1.0.0" (compatible with 1.0.x)
- Range: ">=1.0.0", ">1.0.0", "<=1.0.0", "<1.0.0"
- Any: "*"
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from .manifest import PackageManifest
from .registry import PackageRegistry


class ResolutionError(Exception):
    """Error resolving package dependencies."""
    pass


@dataclass
class VersionConstraint:
    """Represents a version constraint."""
    operator: str  # exact, caret, tilde, >=, >, <=, <, any
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None

    @classmethod
    def parse(cls, constraint: str) -> 'VersionConstraint':
        """Parse version constraint string."""
        constraint = constraint.strip()

        if constraint == '*':
            return cls(operator='any', major=0, minor=0, patch=0)

        # Extract operator
        if constraint.startswith('^'):
            operator = 'caret'
            version_str = constraint[1:]
        elif constraint.startswith('~'):
            operator = 'tilde'
            version_str = constraint[1:]
        elif constraint.startswith('>='):
            operator = '>='
            version_str = constraint[2:]
        elif constraint.startswith('<='):
            operator = '<='
            version_str = constraint[2:]
        elif constraint.startswith('>'):
            operator = '>'
            version_str = constraint[1:]
        elif constraint.startswith('<'):
            operator = '<'
            version_str = constraint[1:]
        else:
            operator = 'exact'
            version_str = constraint

        # Parse version
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9.]+)?$', version_str)
        if not match:
            raise ResolutionError(f"Invalid version format: {constraint}")

        return cls(
            operator=operator,
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            prerelease=match.group(4)[1:] if match.group(4) else None
        )

    def satisfies(self, version: str) -> bool:
        """Check if a version satisfies this constraint."""
        match = re.match(r'^(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9.]+)?$', version)
        if not match:
            return False

        v_major = int(match.group(1))
        v_minor = int(match.group(2))
        v_patch = int(match.group(3))
        v_prerelease = match.group(4)[1:] if match.group(4) else None

        if self.operator == 'any':
            return True

        if self.operator == 'exact':
            return (v_major == self.major and
                    v_minor == self.minor and
                    v_patch == self.patch)

        if self.operator == 'caret':
            # ^1.2.3 means >=1.2.3 and <2.0.0 (for major > 0)
            # ^0.2.3 means >=0.2.3 and <0.3.0 (for major == 0)
            if self.major > 0:
                if v_major != self.major:
                    return False
                return self._version_tuple(v_major, v_minor, v_patch) >= \
                       self._version_tuple(self.major, self.minor, self.patch)
            else:
                if v_major != 0 or v_minor != self.minor:
                    return False
                return v_patch >= self.patch

        if self.operator == 'tilde':
            # ~1.2.3 means >=1.2.3 and <1.3.0
            if v_major != self.major or v_minor != self.minor:
                return False
            return v_patch >= self.patch

        if self.operator == '>=':
            return self._version_tuple(v_major, v_minor, v_patch) >= \
                   self._version_tuple(self.major, self.minor, self.patch)

        if self.operator == '>':
            return self._version_tuple(v_major, v_minor, v_patch) > \
                   self._version_tuple(self.major, self.minor, self.patch)

        if self.operator == '<=':
            return self._version_tuple(v_major, v_minor, v_patch) <= \
                   self._version_tuple(self.major, self.minor, self.patch)

        if self.operator == '<':
            return self._version_tuple(v_major, v_minor, v_patch) < \
                   self._version_tuple(self.major, self.minor, self.patch)

        return False

    @staticmethod
    def _version_tuple(major: int, minor: int, patch: int) -> Tuple[int, int, int]:
        return (major, minor, patch)


@dataclass
class ResolvedPackage:
    """A resolved package with specific version."""
    name: str
    version: str
    manifest: PackageManifest
    dependencies: List['ResolvedPackage']


class DependencyResolver:
    """
    Resolves package dependencies.

    Uses a simple depth-first resolution strategy with version constraints.
    """

    def __init__(self, registry: PackageRegistry):
        self.registry = registry
        self._resolution_cache: Dict[str, ResolvedPackage] = {}
        self._resolution_stack: Set[str] = set()

    def resolve(
        self,
        package_name: str,
        version_constraint: str = '*'
    ) -> ResolvedPackage:
        """
        Resolve a package and all its dependencies.

        Args:
            package_name: Package to resolve
            version_constraint: Version constraint string

        Returns:
            ResolvedPackage with all dependencies resolved

        Raises:
            ResolutionError: If resolution fails
        """
        # Check for circular dependencies
        if package_name in self._resolution_stack:
            raise ResolutionError(
                f"Circular dependency detected: {package_name}"
            )

        # Check cache
        cache_key = f"{package_name}@{version_constraint}"
        if cache_key in self._resolution_cache:
            return self._resolution_cache[cache_key]

        # Add to resolution stack
        self._resolution_stack.add(package_name)

        try:
            # Find matching version
            version = self._find_matching_version(package_name, version_constraint)
            if not version:
                raise ResolutionError(
                    f"No matching version found for {package_name} {version_constraint}"
                )

            # Get manifest
            manifest = self.registry.get_package(package_name, version)
            if not manifest:
                raise ResolutionError(
                    f"Package {package_name}@{version} not found in registry"
                )

            # Resolve dependencies recursively
            resolved_deps = []
            for dep_name, dep_constraint in manifest.dependencies.items():
                resolved_dep = self.resolve(dep_name, dep_constraint)
                resolved_deps.append(resolved_dep)

            # Create resolved package
            resolved = ResolvedPackage(
                name=package_name,
                version=version,
                manifest=manifest,
                dependencies=resolved_deps
            )

            # Cache result
            self._resolution_cache[cache_key] = resolved

            return resolved

        finally:
            # Remove from resolution stack
            self._resolution_stack.discard(package_name)

    def resolve_all(
        self,
        dependencies: Dict[str, str]
    ) -> List[ResolvedPackage]:
        """
        Resolve multiple dependencies.

        Args:
            dependencies: Dict of package name -> version constraint

        Returns:
            List of resolved packages
        """
        resolved = []
        for name, constraint in dependencies.items():
            resolved.append(self.resolve(name, constraint))
        return resolved

    def _find_matching_version(
        self,
        package_name: str,
        version_constraint: str
    ) -> Optional[str]:
        """Find the best matching version for a constraint."""
        constraint = VersionConstraint.parse(version_constraint)

        # Get all installed versions
        versions = self.registry.get_all_versions(package_name)
        if not versions:
            return None

        # Find matching versions
        matching = [v for v in versions if constraint.satisfies(v)]
        if not matching:
            return None

        # Return highest matching version (already sorted in descending order)
        return matching[0]

    def get_install_order(self, resolved: ResolvedPackage) -> List[ResolvedPackage]:
        """
        Get packages in installation order (dependencies first).

        Args:
            resolved: Resolved package with dependencies

        Returns:
            List of packages in installation order
        """
        order = []
        visited = set()

        def visit(pkg: ResolvedPackage):
            if pkg.name in visited:
                return
            visited.add(pkg.name)

            # Visit dependencies first
            for dep in pkg.dependencies:
                visit(dep)

            order.append(pkg)

        visit(resolved)
        return order

    def check_conflicts(
        self,
        packages: List[ResolvedPackage]
    ) -> List[str]:
        """
        Check for version conflicts in resolved packages.

        Args:
            packages: List of resolved packages

        Returns:
            List of conflict descriptions (empty if no conflicts)
        """
        conflicts = []
        versions: Dict[str, Set[str]] = {}

        def collect_versions(pkg: ResolvedPackage):
            if pkg.name not in versions:
                versions[pkg.name] = set()
            versions[pkg.name].add(pkg.version)

            for dep in pkg.dependencies:
                collect_versions(dep)

        for pkg in packages:
            collect_versions(pkg)

        for name, vers in versions.items():
            if len(vers) > 1:
                conflicts.append(
                    f"Conflicting versions of {name}: {', '.join(sorted(vers))}"
                )

        return conflicts

    def clear_cache(self):
        """Clear resolution cache."""
        self._resolution_cache.clear()
        self._resolution_stack.clear()
