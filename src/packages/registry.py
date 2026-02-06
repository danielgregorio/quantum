"""
Quantum Package Registry

Local registry for storing and managing installed packages.

Registry structure:
    ~/.quantum/
    ├── packages/
    │   ├── my-component/
    │   │   ├── 1.0.0/         # Version directory
    │   │   │   ├── quantum.yaml
    │   │   │   ├── src/
    │   │   │   └── ...
    │   │   └── 1.0.1/
    │   └── other-package/
    ├── registry.json          # Package index
    └── config.yaml            # User config
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .manifest import PackageManifest, ManifestError


class RegistryError(Exception):
    """Error in package registry operations."""
    pass


class PackageRegistry:
    """
    Local package registry manager.

    Handles:
    - Package installation/removal
    - Version management
    - Package index maintenance
    - Package search
    """

    def __init__(self, registry_path: Optional[Path] = None):
        """Initialize registry at given path or default ~/.quantum."""
        if registry_path is None:
            # Default to ~/.quantum/
            home = Path.home()
            registry_path = home / '.quantum'

        self.registry_path = Path(registry_path)
        self.packages_path = self.registry_path / 'packages'
        self.index_path = self.registry_path / 'registry.json'

        # Ensure directories exist
        self._init_registry()

    def _init_registry(self) -> None:
        """Initialize registry directories and files."""
        self.registry_path.mkdir(parents=True, exist_ok=True)
        self.packages_path.mkdir(exist_ok=True)

        if not self.index_path.exists():
            self._save_index({})

    def _load_index(self) -> Dict[str, Any]:
        """Load registry index."""
        try:
            with open(self.index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_index(self, index: Dict[str, Any]) -> None:
        """Save registry index."""
        with open(self.index_path, 'w', encoding='utf-8') as f:
            json.dump(index, f, indent=2)

    def install_package(
        self,
        source_path: Path,
        manifest: Optional[PackageManifest] = None
    ) -> PackageManifest:
        """
        Install a package from source directory.

        Args:
            source_path: Path to package directory (with quantum.yaml)
            manifest: Pre-loaded manifest (optional)

        Returns:
            Installed package manifest
        """
        source_path = Path(source_path)

        # Load manifest if not provided
        if manifest is None:
            manifest_path = source_path / 'quantum.yaml'
            if not manifest_path.exists():
                raise RegistryError(f"No quantum.yaml found in {source_path}")
            manifest = PackageManifest.load(manifest_path)

        package_name = manifest.name
        version = manifest.version

        # Create package version directory
        version_dir = self.packages_path / package_name / version
        if version_dir.exists():
            # Remove existing version
            shutil.rmtree(version_dir)

        version_dir.mkdir(parents=True)

        # Copy package contents
        for item in source_path.iterdir():
            if item.name.startswith('.'):
                continue  # Skip hidden files

            dest = version_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)

        # Update registry index
        index = self._load_index()
        if package_name not in index:
            index[package_name] = {
                'versions': {},
                'latest': None,
                'installed_at': None,
            }

        index[package_name]['versions'][version] = {
            'path': str(version_dir),
            'installed_at': datetime.now().isoformat(),
            'description': manifest.description,
            'author': manifest.author,
            'keywords': manifest.keywords,
        }
        index[package_name]['latest'] = version
        index[package_name]['installed_at'] = datetime.now().isoformat()

        self._save_index(index)

        # Update manifest path
        manifest._path = version_dir

        return manifest

    def remove_package(
        self,
        package_name: str,
        version: Optional[str] = None
    ) -> bool:
        """
        Remove a package or specific version.

        Args:
            package_name: Name of package to remove
            version: Specific version to remove (None = all versions)

        Returns:
            True if removed, False if not found
        """
        index = self._load_index()

        if package_name not in index:
            return False

        package_dir = self.packages_path / package_name

        if version:
            # Remove specific version
            version_dir = package_dir / version
            if version_dir.exists():
                shutil.rmtree(version_dir)

            if version in index[package_name]['versions']:
                del index[package_name]['versions'][version]

            # Update latest version
            remaining_versions = list(index[package_name]['versions'].keys())
            if remaining_versions:
                # Sort by version and get highest
                remaining_versions.sort(key=self._version_key, reverse=True)
                index[package_name]['latest'] = remaining_versions[0]
            else:
                # No versions left, remove package entirely
                del index[package_name]
                if package_dir.exists():
                    shutil.rmtree(package_dir)
        else:
            # Remove all versions
            if package_dir.exists():
                shutil.rmtree(package_dir)
            del index[package_name]

        self._save_index(index)
        return True

    def get_package(
        self,
        package_name: str,
        version: Optional[str] = None
    ) -> Optional[PackageManifest]:
        """
        Get installed package manifest.

        Args:
            package_name: Package name
            version: Specific version (None = latest)

        Returns:
            Package manifest or None if not found
        """
        index = self._load_index()

        if package_name not in index:
            return None

        pkg_info = index[package_name]

        if version is None:
            version = pkg_info.get('latest')

        if not version or version not in pkg_info['versions']:
            return None

        version_info = pkg_info['versions'][version]
        version_dir = Path(version_info['path'])

        manifest_path = version_dir / 'quantum.yaml'
        if not manifest_path.exists():
            return None

        try:
            return PackageManifest.load(manifest_path)
        except ManifestError:
            return None

    def get_package_path(
        self,
        package_name: str,
        version: Optional[str] = None
    ) -> Optional[Path]:
        """
        Get path to installed package directory.

        Args:
            package_name: Package name
            version: Specific version (None = latest)

        Returns:
            Path to package directory or None
        """
        index = self._load_index()

        if package_name not in index:
            return None

        pkg_info = index[package_name]

        if version is None:
            version = pkg_info.get('latest')

        if not version or version not in pkg_info['versions']:
            return None

        version_info = pkg_info['versions'][version]
        return Path(version_info['path'])

    def list_packages(self) -> List[Dict[str, Any]]:
        """
        List all installed packages.

        Returns:
            List of package info dictionaries
        """
        index = self._load_index()
        packages = []

        for name, info in index.items():
            pkg = {
                'name': name,
                'latest': info.get('latest'),
                'versions': list(info.get('versions', {}).keys()),
                'installed_at': info.get('installed_at'),
            }

            # Get description from latest version
            if info.get('latest') and info['latest'] in info.get('versions', {}):
                version_info = info['versions'][info['latest']]
                pkg['description'] = version_info.get('description', '')
                pkg['author'] = version_info.get('author', '')
                pkg['keywords'] = version_info.get('keywords', [])

            packages.append(pkg)

        return packages

    def search_packages(self, query: str) -> List[Dict[str, Any]]:
        """
        Search installed packages by name or keywords.

        Args:
            query: Search query

        Returns:
            List of matching package info dictionaries
        """
        query = query.lower()
        packages = self.list_packages()
        results = []

        for pkg in packages:
            # Match by name
            if query in pkg['name'].lower():
                results.append(pkg)
                continue

            # Match by keywords
            keywords = pkg.get('keywords', [])
            if any(query in kw.lower() for kw in keywords):
                results.append(pkg)
                continue

            # Match by description
            description = pkg.get('description', '')
            if query in description.lower():
                results.append(pkg)

        return results

    def has_package(self, package_name: str, version: Optional[str] = None) -> bool:
        """Check if package is installed."""
        index = self._load_index()

        if package_name not in index:
            return False

        if version:
            return version in index[package_name].get('versions', {})

        return True

    def get_all_versions(self, package_name: str) -> List[str]:
        """Get all installed versions of a package."""
        index = self._load_index()

        if package_name not in index:
            return []

        versions = list(index[package_name].get('versions', {}).keys())
        versions.sort(key=self._version_key, reverse=True)
        return versions

    @staticmethod
    def _version_key(version: str) -> tuple:
        """Convert version string to sortable tuple."""
        # Remove prerelease suffix for comparison
        base_version = version.split('-')[0]
        try:
            parts = [int(p) for p in base_version.split('.')]
            # Pad to 3 parts
            while len(parts) < 3:
                parts.append(0)
            return tuple(parts)
        except ValueError:
            return (0, 0, 0)


class RemoteRegistry:
    """
    Remote package registry client.

    TODO: Implement when remote registry server is available.
    For now, packages are shared via local paths or git URLs.
    """

    def __init__(self, registry_url: str = "https://packages.quantum.dev"):
        self.registry_url = registry_url

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search remote registry."""
        # TODO: Implement HTTP search
        raise NotImplementedError("Remote registry not yet implemented")

    def download(self, package_name: str, version: Optional[str] = None) -> Path:
        """Download package from remote registry."""
        # TODO: Implement HTTP download
        raise NotImplementedError("Remote registry not yet implemented")

    def publish(self, manifest: PackageManifest, archive_path: Path) -> bool:
        """Publish package to remote registry."""
        # TODO: Implement HTTP publish
        raise NotImplementedError("Remote registry not yet implemented")
