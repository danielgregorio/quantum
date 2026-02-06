"""
Quantum Package Manager

Main package manager that coordinates manifest, registry, and resolver.

Usage:
    from packages import PackageManager

    pm = PackageManager()
    pm.init('/path/to/new-package')
    pm.install('/path/to/package-source')
    pm.install_from_git('https://github.com/user/quantum-component.git')
    pm.remove('my-component')
    pm.list_packages()
    pm.search('button')
"""

import os
import shutil
import tempfile
import tarfile
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any

from .manifest import PackageManifest, ManifestError, init_package
from .registry import PackageRegistry, RegistryError
from .resolver import DependencyResolver, ResolutionError, ResolvedPackage


class PackageError(Exception):
    """General package manager error."""
    pass


class PackageManager:
    """
    Main package manager for Quantum components.

    Handles:
    - Package initialization (quantum pkg init)
    - Package publishing (quantum pkg publish)
    - Package installation (quantum pkg install)
    - Package removal (quantum pkg remove)
    - Package listing (quantum pkg list)
    - Package search (quantum pkg search)
    """

    def __init__(self, registry_path: Optional[Path] = None):
        """
        Initialize package manager.

        Args:
            registry_path: Custom registry path (default: ~/.quantum)
        """
        self.registry = PackageRegistry(registry_path)
        self.resolver = DependencyResolver(self.registry)

    def init(
        self,
        path: str,
        name: Optional[str] = None,
        description: str = "",
        author: str = "",
        license_id: str = "MIT"
    ) -> PackageManifest:
        """
        Initialize a new package in the given directory.

        Creates package structure with quantum.yaml, src/, examples/, README.md.

        Args:
            path: Directory to initialize package in
            name: Package name (default: directory name)
            description: Package description
            author: Package author
            license_id: License identifier

        Returns:
            Created package manifest
        """
        path = Path(path)

        # Check if already initialized
        manifest_path = path / 'quantum.yaml'
        if manifest_path.exists():
            raise PackageError(f"Package already initialized at {path}")

        try:
            manifest = init_package(
                path=path,
                name=name,
                description=description,
                author=author,
                license_id=license_id
            )
            return manifest
        except ManifestError as e:
            raise PackageError(f"Failed to initialize package: {e}")

    def install(
        self,
        source: str,
        version: Optional[str] = None,
        resolve_deps: bool = True
    ) -> List[PackageManifest]:
        """
        Install a package from local path or URL.

        Args:
            source: Package source (local path, git URL, or package name)
            version: Specific version to install (for registered packages)
            resolve_deps: Whether to resolve and install dependencies

        Returns:
            List of installed package manifests
        """
        installed = []
        source_path = None
        temp_dir = None

        try:
            # Determine source type
            if source.startswith('http://') or source.startswith('https://'):
                if '.git' in source or 'github.com' in source:
                    # Git URL
                    temp_dir = Path(tempfile.mkdtemp())
                    source_path = self._clone_git(source, temp_dir)
                else:
                    raise PackageError(f"Unsupported URL: {source}")
            elif os.path.exists(source):
                # Local path
                source_path = Path(source)
            else:
                # Check if it's already installed (for dependency resolution)
                if self.registry.has_package(source, version):
                    manifest = self.registry.get_package(source, version)
                    if manifest:
                        return [manifest]

                raise PackageError(
                    f"Package not found: {source}. "
                    "Provide a local path or git URL."
                )

            # Load and validate manifest
            manifest_path = source_path / 'quantum.yaml'
            if not manifest_path.exists():
                raise PackageError(f"No quantum.yaml found in {source_path}")

            try:
                manifest = PackageManifest.load(manifest_path)
            except ManifestError as e:
                raise PackageError(f"Invalid manifest: {e}")

            # Resolve and install dependencies first
            if resolve_deps and manifest.dependencies:
                for dep_name, dep_version in manifest.dependencies.items():
                    if not self.registry.has_package(dep_name):
                        raise PackageError(
                            f"Missing dependency: {dep_name}. "
                            f"Install it first: quantum pkg install <path-to-{dep_name}>"
                        )

                    # Check version constraint
                    try:
                        resolved = self.resolver.resolve(dep_name, dep_version)
                        installed.append(resolved.manifest)
                    except ResolutionError as e:
                        raise PackageError(f"Dependency resolution failed: {e}")

            # Install the main package
            try:
                installed_manifest = self.registry.install_package(source_path, manifest)
                installed.append(installed_manifest)
            except RegistryError as e:
                raise PackageError(f"Installation failed: {e}")

            return installed

        finally:
            # Clean up temp directory
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def install_from_git(self, git_url: str, ref: Optional[str] = None) -> List[PackageManifest]:
        """
        Install a package from a git repository.

        Args:
            git_url: Git repository URL
            ref: Git ref (branch, tag, commit) to checkout

        Returns:
            List of installed package manifests
        """
        temp_dir = Path(tempfile.mkdtemp())
        try:
            source_path = self._clone_git(git_url, temp_dir, ref)
            return self.install(str(source_path))
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def remove(
        self,
        package_name: str,
        version: Optional[str] = None
    ) -> bool:
        """
        Remove an installed package.

        Args:
            package_name: Name of package to remove
            version: Specific version to remove (None = all versions)

        Returns:
            True if removed, False if not found
        """
        if not self.registry.has_package(package_name, version):
            return False

        try:
            return self.registry.remove_package(package_name, version)
        except RegistryError as e:
            raise PackageError(f"Failed to remove package: {e}")

    def list_packages(self) -> List[Dict[str, Any]]:
        """
        List all installed packages.

        Returns:
            List of package info dictionaries
        """
        return self.registry.list_packages()

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Search installed packages.

        Args:
            query: Search query (matches name, keywords, description)

        Returns:
            List of matching package info dictionaries
        """
        return self.registry.search_packages(query)

    def get_package(
        self,
        package_name: str,
        version: Optional[str] = None
    ) -> Optional[PackageManifest]:
        """
        Get an installed package manifest.

        Args:
            package_name: Package name
            version: Specific version (None = latest)

        Returns:
            Package manifest or None
        """
        return self.registry.get_package(package_name, version)

    def get_package_path(
        self,
        package_name: str,
        version: Optional[str] = None
    ) -> Optional[Path]:
        """
        Get path to an installed package.

        Args:
            package_name: Package name
            version: Specific version (None = latest)

        Returns:
            Path to package directory or None
        """
        return self.registry.get_package_path(package_name, version)

    def publish(self, source_path: str) -> Path:
        """
        Create a publishable package archive.

        Creates a .tar.gz archive that can be shared or uploaded to a registry.

        Args:
            source_path: Path to package directory

        Returns:
            Path to created archive
        """
        source_path = Path(source_path)

        # Load and validate manifest
        manifest_path = source_path / 'quantum.yaml'
        if not manifest_path.exists():
            raise PackageError(f"No quantum.yaml found in {source_path}")

        try:
            manifest = PackageManifest.load(manifest_path)
        except ManifestError as e:
            raise PackageError(f"Invalid manifest: {e}")

        # Create archive
        archive_name = f"{manifest.name}-{manifest.version}.tar.gz"
        archive_path = source_path.parent / archive_name

        with tarfile.open(archive_path, 'w:gz') as tar:
            for item in source_path.iterdir():
                if item.name.startswith('.'):
                    continue  # Skip hidden files
                if item.name.endswith('.tar.gz'):
                    continue  # Skip existing archives
                tar.add(item, arcname=item.name)

        return archive_path

    def resolve_dependencies(
        self,
        package_name: str,
        version_constraint: str = '*'
    ) -> ResolvedPackage:
        """
        Resolve package dependencies.

        Args:
            package_name: Package to resolve
            version_constraint: Version constraint

        Returns:
            Resolved package with dependencies
        """
        try:
            return self.resolver.resolve(package_name, version_constraint)
        except ResolutionError as e:
            raise PackageError(f"Dependency resolution failed: {e}")

    def get_component_path(
        self,
        package_name: str,
        component_name: Optional[str] = None
    ) -> Optional[Path]:
        """
        Get path to a component file in a package.

        Args:
            package_name: Package name
            component_name: Component name (None = main component)

        Returns:
            Path to component file or None
        """
        manifest = self.get_package(package_name)
        if not manifest:
            return None

        if component_name is None:
            # Return main component
            return manifest.get_main_component_path()

        # Search for component in package
        pkg_path = self.get_package_path(package_name)
        if not pkg_path:
            return None

        # Try src/{ComponentName}.q
        component_path = pkg_path / 'src' / f'{component_name}.q'
        if component_path.exists():
            return component_path

        # Try src/{component_name}.q (lowercase)
        component_path = pkg_path / 'src' / f'{component_name.lower()}.q'
        if component_path.exists():
            return component_path

        return None

    def _clone_git(
        self,
        git_url: str,
        dest_dir: Path,
        ref: Optional[str] = None
    ) -> Path:
        """Clone a git repository."""
        try:
            cmd = ['git', 'clone', '--depth', '1']
            if ref:
                cmd.extend(['--branch', ref])
            cmd.extend([git_url, str(dest_dir / 'repo')])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                raise PackageError(f"Git clone failed: {result.stderr}")

            return dest_dir / 'repo'

        except subprocess.TimeoutExpired:
            raise PackageError("Git clone timed out")
        except FileNotFoundError:
            raise PackageError("Git not found. Please install git.")


def get_package_manager() -> PackageManager:
    """Get default package manager instance."""
    return PackageManager()
