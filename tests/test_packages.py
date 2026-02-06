"""
Tests for Quantum Package Manager

Tests:
- Package manifest parsing and validation
- Package registry operations
- Dependency resolver
- Package manager operations
"""

import pytest
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from packages.manifest import (
    PackageManifest,
    ManifestError,
    init_package,
)
from packages.registry import (
    PackageRegistry,
    RegistryError,
)
from packages.resolver import (
    DependencyResolver,
    ResolutionError,
    VersionConstraint,
    ResolvedPackage,
)
from packages.manager import (
    PackageManager,
    PackageError,
)


# ============================================
# Package Manifest Tests
# ============================================

class TestPackageManifest:
    """Test PackageManifest parsing and validation."""

    def test_manifest_validation_name_format(self):
        """Test package name format validation."""
        # Valid names
        assert PackageManifest._validate_name('my-package') is True
        assert PackageManifest._validate_name('mypackage') is True
        assert PackageManifest._validate_name('my-package-123') is True

        # Invalid names
        assert PackageManifest._validate_name('') is False
        assert PackageManifest._validate_name('MyPackage') is False  # uppercase
        assert PackageManifest._validate_name('123-package') is False  # starts with number
        assert PackageManifest._validate_name('my_package') is False  # underscore

    def test_manifest_validation_version_format(self):
        """Test semantic version format validation."""
        # Valid versions
        assert PackageManifest._validate_version('1.0.0') is True
        assert PackageManifest._validate_version('0.1.0') is True
        assert PackageManifest._validate_version('10.20.30') is True
        assert PackageManifest._validate_version('1.0.0-alpha') is True
        assert PackageManifest._validate_version('1.0.0-beta.1') is True

        # Invalid versions
        assert PackageManifest._validate_version('') is False
        assert PackageManifest._validate_version('1.0') is False
        assert PackageManifest._validate_version('v1.0.0') is False
        assert PackageManifest._validate_version('1.0.0.0') is False

    def test_manifest_validation_constraint_format(self):
        """Test version constraint format validation."""
        # Valid constraints
        assert PackageManifest._validate_version_constraint('1.0.0') is True
        assert PackageManifest._validate_version_constraint('^1.0.0') is True
        assert PackageManifest._validate_version_constraint('~1.0.0') is True
        assert PackageManifest._validate_version_constraint('>=1.0.0') is True
        assert PackageManifest._validate_version_constraint('>1.0.0') is True
        assert PackageManifest._validate_version_constraint('<=1.0.0') is True
        assert PackageManifest._validate_version_constraint('<1.0.0') is True
        assert PackageManifest._validate_version_constraint('*') is True

        # Invalid constraints
        assert PackageManifest._validate_version_constraint('') is False
        assert PackageManifest._validate_version_constraint('1.0') is False
        assert PackageManifest._validate_version_constraint('latest') is False

    def test_manifest_load_valid(self, tmp_path):
        """Test loading a valid manifest."""
        manifest_content = """
name: my-component
version: 1.2.3
description: A test component
author: Test Author
license: MIT
main: src/index.q
keywords:
  - ui
  - component
dependencies:
  other-package: ^1.0.0
"""
        manifest_file = tmp_path / 'quantum.yaml'
        manifest_file.write_text(manifest_content)

        manifest = PackageManifest.load(manifest_file)

        assert manifest.name == 'my-component'
        assert manifest.version == '1.2.3'
        assert manifest.description == 'A test component'
        assert manifest.author == 'Test Author'
        assert manifest.license == 'MIT'
        assert manifest.main == 'src/index.q'
        assert 'ui' in manifest.keywords
        assert 'other-package' in manifest.dependencies
        assert manifest.dependencies['other-package'] == '^1.0.0'

    def test_manifest_load_minimal(self, tmp_path):
        """Test loading a minimal manifest."""
        manifest_content = """
name: minimal
version: 0.1.0
"""
        manifest_file = tmp_path / 'quantum.yaml'
        manifest_file.write_text(manifest_content)

        manifest = PackageManifest.load(manifest_file)

        assert manifest.name == 'minimal'
        assert manifest.version == '0.1.0'
        assert manifest.description == ''
        assert manifest.license == 'MIT'  # default

    def test_manifest_load_missing_name(self, tmp_path):
        """Test loading manifest without name fails."""
        manifest_content = """
version: 1.0.0
"""
        manifest_file = tmp_path / 'quantum.yaml'
        manifest_file.write_text(manifest_content)

        with pytest.raises(ManifestError, match="name"):
            PackageManifest.load(manifest_file)

    def test_manifest_load_missing_version(self, tmp_path):
        """Test loading manifest without version fails."""
        manifest_content = """
name: no-version
"""
        manifest_file = tmp_path / 'quantum.yaml'
        manifest_file.write_text(manifest_content)

        with pytest.raises(ManifestError, match="version"):
            PackageManifest.load(manifest_file)

    def test_manifest_load_invalid_name(self, tmp_path):
        """Test loading manifest with invalid name fails."""
        manifest_content = """
name: Invalid-Name
version: 1.0.0
"""
        manifest_file = tmp_path / 'quantum.yaml'
        manifest_file.write_text(manifest_content)

        with pytest.raises(ManifestError, match="Invalid package name"):
            PackageManifest.load(manifest_file)

    def test_manifest_load_invalid_version(self, tmp_path):
        """Test loading manifest with invalid version fails."""
        manifest_content = """
name: my-package
version: not-a-version
"""
        manifest_file = tmp_path / 'quantum.yaml'
        manifest_file.write_text(manifest_content)

        with pytest.raises(ManifestError, match="Invalid version"):
            PackageManifest.load(manifest_file)

    def test_manifest_load_not_found(self):
        """Test loading non-existent manifest fails."""
        with pytest.raises(ManifestError, match="not found"):
            PackageManifest.load(Path('/nonexistent/quantum.yaml'))

    def test_manifest_to_dict(self):
        """Test manifest serialization."""
        manifest = PackageManifest(
            name='test-pkg',
            version='1.0.0',
            description='Test',
            author='Author',
            dependencies={'dep': '^1.0.0'}
        )
        d = manifest.to_dict()

        assert d['name'] == 'test-pkg'
        assert d['version'] == '1.0.0'
        assert d['description'] == 'Test'
        assert d['dependencies'] == {'dep': '^1.0.0'}

    def test_manifest_save(self, tmp_path):
        """Test saving manifest to file."""
        manifest = PackageManifest(
            name='save-test',
            version='2.0.0',
            description='Save test'
        )
        manifest._path = tmp_path

        manifest.save()

        saved_file = tmp_path / 'quantum.yaml'
        assert saved_file.exists()

        # Load and verify
        loaded = PackageManifest.load(saved_file)
        assert loaded.name == 'save-test'
        assert loaded.version == '2.0.0'


# ============================================
# Init Package Tests
# ============================================

class TestInitPackage:
    """Test package initialization."""

    def test_init_package_basic(self, tmp_path):
        """Test basic package initialization."""
        pkg_dir = tmp_path / 'new-package'
        manifest = init_package(pkg_dir)

        assert pkg_dir.exists()
        assert (pkg_dir / 'quantum.yaml').exists()
        assert (pkg_dir / 'src').exists()
        assert (pkg_dir / 'examples').exists()
        assert (pkg_dir / 'README.md').exists()
        assert (pkg_dir / 'src' / 'index.q').exists()

        assert manifest.name == 'new-package'
        assert manifest.version == '1.0.0'

    def test_init_package_with_options(self, tmp_path):
        """Test package initialization with options."""
        pkg_dir = tmp_path / 'custom-package'
        manifest = init_package(
            pkg_dir,
            name='custom-name',
            description='Custom description',
            author='Test Author',
            license_id='Apache-2.0'
        )

        assert manifest.name == 'custom-name'
        assert manifest.description == 'Custom description'
        assert manifest.author == 'Test Author'
        assert manifest.license == 'Apache-2.0'


# ============================================
# Version Constraint Tests
# ============================================

class TestVersionConstraint:
    """Test version constraint parsing and matching."""

    def test_parse_exact(self):
        """Test parsing exact version."""
        c = VersionConstraint.parse('1.2.3')
        assert c.operator == 'exact'
        assert c.major == 1
        assert c.minor == 2
        assert c.patch == 3

    def test_parse_caret(self):
        """Test parsing caret constraint."""
        c = VersionConstraint.parse('^1.2.3')
        assert c.operator == 'caret'
        assert c.major == 1

    def test_parse_tilde(self):
        """Test parsing tilde constraint."""
        c = VersionConstraint.parse('~1.2.3')
        assert c.operator == 'tilde'

    def test_parse_gte(self):
        """Test parsing >= constraint."""
        c = VersionConstraint.parse('>=1.0.0')
        assert c.operator == '>='

    def test_parse_gt(self):
        """Test parsing > constraint."""
        c = VersionConstraint.parse('>1.0.0')
        assert c.operator == '>'

    def test_parse_lte(self):
        """Test parsing <= constraint."""
        c = VersionConstraint.parse('<=1.0.0')
        assert c.operator == '<='

    def test_parse_lt(self):
        """Test parsing < constraint."""
        c = VersionConstraint.parse('<1.0.0')
        assert c.operator == '<'

    def test_parse_any(self):
        """Test parsing * constraint."""
        c = VersionConstraint.parse('*')
        assert c.operator == 'any'

    def test_parse_invalid(self):
        """Test parsing invalid constraint."""
        with pytest.raises(ResolutionError):
            VersionConstraint.parse('invalid')

    def test_satisfies_exact(self):
        """Test exact version matching."""
        c = VersionConstraint.parse('1.2.3')
        assert c.satisfies('1.2.3') is True
        assert c.satisfies('1.2.4') is False
        assert c.satisfies('1.3.3') is False

    def test_satisfies_caret(self):
        """Test caret version matching."""
        c = VersionConstraint.parse('^1.2.3')
        assert c.satisfies('1.2.3') is True
        assert c.satisfies('1.2.4') is True
        assert c.satisfies('1.9.0') is True
        assert c.satisfies('2.0.0') is False
        assert c.satisfies('1.2.2') is False

    def test_satisfies_caret_zero_major(self):
        """Test caret with zero major version."""
        c = VersionConstraint.parse('^0.2.3')
        assert c.satisfies('0.2.3') is True
        assert c.satisfies('0.2.9') is True
        assert c.satisfies('0.3.0') is False

    def test_satisfies_tilde(self):
        """Test tilde version matching."""
        c = VersionConstraint.parse('~1.2.3')
        assert c.satisfies('1.2.3') is True
        assert c.satisfies('1.2.9') is True
        assert c.satisfies('1.3.0') is False
        assert c.satisfies('2.0.0') is False

    def test_satisfies_gte(self):
        """Test >= matching."""
        c = VersionConstraint.parse('>=1.0.0')
        assert c.satisfies('1.0.0') is True
        assert c.satisfies('2.0.0') is True
        assert c.satisfies('0.9.9') is False

    def test_satisfies_gt(self):
        """Test > matching."""
        c = VersionConstraint.parse('>1.0.0')
        assert c.satisfies('1.0.1') is True
        assert c.satisfies('1.0.0') is False

    def test_satisfies_lte(self):
        """Test <= matching."""
        c = VersionConstraint.parse('<=1.0.0')
        assert c.satisfies('1.0.0') is True
        assert c.satisfies('0.9.9') is True
        assert c.satisfies('1.0.1') is False

    def test_satisfies_lt(self):
        """Test < matching."""
        c = VersionConstraint.parse('<1.0.0')
        assert c.satisfies('0.9.9') is True
        assert c.satisfies('1.0.0') is False

    def test_satisfies_any(self):
        """Test * matches any version."""
        c = VersionConstraint.parse('*')
        assert c.satisfies('0.0.1') is True
        assert c.satisfies('99.99.99') is True


# ============================================
# Package Registry Tests
# ============================================

class TestPackageRegistry:
    """Test PackageRegistry operations."""

    @pytest.fixture
    def registry(self, tmp_path):
        """Fresh registry for each test."""
        return PackageRegistry(tmp_path)

    @pytest.fixture
    def sample_package(self, tmp_path):
        """Create a sample package directory."""
        pkg_dir = tmp_path / 'sample-package'
        pkg_dir.mkdir()
        (pkg_dir / 'src').mkdir()

        manifest_content = """
name: sample-package
version: 1.0.0
description: Sample package
"""
        (pkg_dir / 'quantum.yaml').write_text(manifest_content)
        (pkg_dir / 'src' / 'index.q').write_text('<q:component name="Sample" />')

        return pkg_dir

    def test_install_package(self, registry, sample_package):
        """Test installing a package."""
        manifest = PackageManifest.load(sample_package / 'quantum.yaml')
        installed = registry.install_package(sample_package, manifest)

        assert installed.name == 'sample-package'
        assert registry.has_package('sample-package')

    def test_get_package(self, registry, sample_package):
        """Test getting installed package."""
        manifest = PackageManifest.load(sample_package / 'quantum.yaml')
        registry.install_package(sample_package, manifest)

        retrieved = registry.get_package('sample-package')
        assert retrieved is not None
        assert retrieved.name == 'sample-package'

    def test_get_package_not_found(self, registry):
        """Test getting non-existent package."""
        result = registry.get_package('nonexistent')
        assert result is None

    def test_remove_package(self, registry, sample_package):
        """Test removing a package."""
        manifest = PackageManifest.load(sample_package / 'quantum.yaml')
        registry.install_package(sample_package, manifest)

        result = registry.remove_package('sample-package')
        assert result is True
        assert not registry.has_package('sample-package')

    def test_remove_package_not_found(self, registry):
        """Test removing non-existent package."""
        result = registry.remove_package('nonexistent')
        assert result is False

    def test_list_packages(self, registry, sample_package):
        """Test listing packages."""
        manifest = PackageManifest.load(sample_package / 'quantum.yaml')
        registry.install_package(sample_package, manifest)

        packages = registry.list_packages()
        assert len(packages) == 1
        assert packages[0]['name'] == 'sample-package'

    def test_search_packages(self, registry, sample_package):
        """Test searching packages."""
        manifest = PackageManifest.load(sample_package / 'quantum.yaml')
        registry.install_package(sample_package, manifest)

        results = registry.search_packages('sample')
        assert len(results) == 1

        results = registry.search_packages('nonexistent')
        assert len(results) == 0

    def test_has_package(self, registry, sample_package):
        """Test checking if package exists."""
        assert registry.has_package('sample-package') is False

        manifest = PackageManifest.load(sample_package / 'quantum.yaml')
        registry.install_package(sample_package, manifest)

        assert registry.has_package('sample-package') is True

    def test_get_all_versions(self, registry, tmp_path):
        """Test getting all versions of a package."""
        # Create and install v1.0.0
        pkg1 = tmp_path / 'pkg-v1'
        pkg1.mkdir()
        (pkg1 / 'quantum.yaml').write_text('name: multi-version\nversion: 1.0.0')
        manifest1 = PackageManifest.load(pkg1 / 'quantum.yaml')
        registry.install_package(pkg1, manifest1)

        # Create and install v1.1.0
        pkg2 = tmp_path / 'pkg-v2'
        pkg2.mkdir()
        (pkg2 / 'quantum.yaml').write_text('name: multi-version\nversion: 1.1.0')
        manifest2 = PackageManifest.load(pkg2 / 'quantum.yaml')
        registry.install_package(pkg2, manifest2)

        versions = registry.get_all_versions('multi-version')
        assert '1.0.0' in versions
        assert '1.1.0' in versions

    def test_get_package_path(self, registry, sample_package):
        """Test getting package installation path."""
        manifest = PackageManifest.load(sample_package / 'quantum.yaml')
        registry.install_package(sample_package, manifest)

        path = registry.get_package_path('sample-package')
        assert path is not None
        assert path.exists()


# ============================================
# Dependency Resolver Tests
# ============================================

class TestDependencyResolver:
    """Test DependencyResolver operations."""

    @pytest.fixture
    def registry(self, tmp_path):
        """Fresh registry for resolver."""
        return PackageRegistry(tmp_path)

    @pytest.fixture
    def resolver(self, registry):
        """Fresh resolver for each test."""
        return DependencyResolver(registry)

    def test_resolve_simple(self, resolver, registry, tmp_path):
        """Test resolving a simple package."""
        # Install a package first
        pkg_dir = tmp_path / 'simple-pkg'
        pkg_dir.mkdir()
        (pkg_dir / 'quantum.yaml').write_text('name: simple-pkg\nversion: 1.0.0')
        manifest = PackageManifest.load(pkg_dir / 'quantum.yaml')
        registry.install_package(pkg_dir, manifest)

        resolved = resolver.resolve('simple-pkg', '*')
        assert resolved.name == 'simple-pkg'
        assert resolved.version == '1.0.0'

    def test_resolve_not_found(self, resolver):
        """Test resolving non-existent package."""
        with pytest.raises(ResolutionError, match="No matching version found"):
            resolver.resolve('nonexistent', '*')

    def test_resolve_version_constraint(self, resolver, registry, tmp_path):
        """Test resolving with version constraint."""
        # Install v1.0.0
        pkg1 = tmp_path / 'pkg-v1'
        pkg1.mkdir()
        (pkg1 / 'quantum.yaml').write_text('name: versioned\nversion: 1.0.0')
        registry.install_package(pkg1, PackageManifest.load(pkg1 / 'quantum.yaml'))

        # Install v2.0.0
        pkg2 = tmp_path / 'pkg-v2'
        pkg2.mkdir()
        (pkg2 / 'quantum.yaml').write_text('name: versioned\nversion: 2.0.0')
        registry.install_package(pkg2, PackageManifest.load(pkg2 / 'quantum.yaml'))

        # Resolve with constraint
        resolved = resolver.resolve('versioned', '^1.0.0')
        assert resolved.version == '1.0.0'

        resolved = resolver.resolve('versioned', '>=2.0.0')
        assert resolved.version == '2.0.0'

    def test_resolve_no_matching_version(self, resolver, registry, tmp_path):
        """Test resolving with no matching version."""
        pkg = tmp_path / 'old-pkg'
        pkg.mkdir()
        (pkg / 'quantum.yaml').write_text('name: old-pkg\nversion: 0.5.0')
        registry.install_package(pkg, PackageManifest.load(pkg / 'quantum.yaml'))

        with pytest.raises(ResolutionError, match="No matching version"):
            resolver.resolve('old-pkg', '>=1.0.0')

    def test_get_install_order(self, resolver, registry, tmp_path):
        """Test getting installation order."""
        # Create package with dependency
        dep_dir = tmp_path / 'dep-pkg'
        dep_dir.mkdir()
        (dep_dir / 'quantum.yaml').write_text('name: dep-pkg\nversion: 1.0.0')
        registry.install_package(dep_dir, PackageManifest.load(dep_dir / 'quantum.yaml'))

        main_dir = tmp_path / 'main-pkg'
        main_dir.mkdir()
        (main_dir / 'quantum.yaml').write_text('name: main-pkg\nversion: 1.0.0\ndependencies:\n  dep-pkg: "*"')
        registry.install_package(main_dir, PackageManifest.load(main_dir / 'quantum.yaml'))

        resolved = resolver.resolve('main-pkg', '*')
        order = resolver.get_install_order(resolved)

        # Dependencies should come before main package
        names = [p.name for p in order]
        assert names.index('dep-pkg') < names.index('main-pkg')

    def test_check_conflicts(self, resolver):
        """Test checking for version conflicts."""
        # Create resolved packages with same name but different versions
        pkg1 = ResolvedPackage('conflict-pkg', '1.0.0', MagicMock(), [])
        pkg2 = ResolvedPackage('conflict-pkg', '2.0.0', MagicMock(), [])

        conflicts = resolver.check_conflicts([pkg1, pkg2])
        assert len(conflicts) > 0
        assert 'conflict-pkg' in conflicts[0]

    def test_clear_cache(self, resolver):
        """Test clearing resolver cache."""
        resolver._resolution_cache['test'] = 'value'
        resolver.clear_cache()
        assert len(resolver._resolution_cache) == 0


# ============================================
# Package Manager Tests
# ============================================

class TestPackageManager:
    """Test PackageManager operations."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Fresh package manager for each test."""
        return PackageManager(registry_path=tmp_path)

    def test_init_package(self, manager, tmp_path):
        """Test initializing a new package."""
        pkg_dir = tmp_path / 'new-package'
        manifest = manager.init(str(pkg_dir))

        assert pkg_dir.exists()
        assert manifest.name == 'new-package'

    def test_init_package_already_exists(self, manager, tmp_path):
        """Test init fails if package exists."""
        pkg_dir = tmp_path / 'existing'
        pkg_dir.mkdir()
        (pkg_dir / 'quantum.yaml').write_text('name: existing\nversion: 1.0.0')

        with pytest.raises(PackageError, match="already initialized"):
            manager.init(str(pkg_dir))

    def test_install_from_path(self, manager, tmp_path):
        """Test installing from local path."""
        # Create source package
        src_dir = tmp_path / 'source'
        src_dir.mkdir()
        (src_dir / 'quantum.yaml').write_text('name: local-pkg\nversion: 1.0.0')
        (src_dir / 'src').mkdir()
        (src_dir / 'src' / 'index.q').write_text('<q:component name="Local" />')

        installed = manager.install(str(src_dir))
        assert len(installed) == 1
        assert installed[0].name == 'local-pkg'

    def test_install_not_found(self, manager):
        """Test install with invalid path."""
        with pytest.raises(PackageError, match="not found"):
            manager.install('nonexistent-package')

    def test_install_no_manifest(self, manager, tmp_path):
        """Test install fails without manifest."""
        pkg_dir = tmp_path / 'no-manifest'
        pkg_dir.mkdir()

        with pytest.raises(PackageError, match="quantum.yaml"):
            manager.install(str(pkg_dir))

    def test_remove_package(self, manager, tmp_path):
        """Test removing a package."""
        # Install first
        src_dir = tmp_path / 'to-remove'
        src_dir.mkdir()
        (src_dir / 'quantum.yaml').write_text('name: remove-pkg\nversion: 1.0.0')
        manager.install(str(src_dir))

        result = manager.remove('remove-pkg')
        assert result is True

    def test_remove_not_found(self, manager):
        """Test removing non-existent package."""
        result = manager.remove('nonexistent')
        assert result is False

    def test_list_packages(self, manager, tmp_path):
        """Test listing packages."""
        # Install a package
        src_dir = tmp_path / 'list-test'
        src_dir.mkdir()
        (src_dir / 'quantum.yaml').write_text('name: list-test\nversion: 1.0.0')
        manager.install(str(src_dir))

        packages = manager.list_packages()
        assert len(packages) >= 1
        assert any(p['name'] == 'list-test' for p in packages)

    def test_search_packages(self, manager, tmp_path):
        """Test searching packages."""
        # Install a package
        src_dir = tmp_path / 'search-test'
        src_dir.mkdir()
        (src_dir / 'quantum.yaml').write_text('name: search-test\nversion: 1.0.0\nkeywords:\n  - button\n  - ui')
        manager.install(str(src_dir))

        results = manager.search('button')
        assert len(results) >= 1

    def test_get_package(self, manager, tmp_path):
        """Test getting a package."""
        # Install first
        src_dir = tmp_path / 'get-test'
        src_dir.mkdir()
        (src_dir / 'quantum.yaml').write_text('name: get-test\nversion: 1.0.0')
        manager.install(str(src_dir))

        pkg = manager.get_package('get-test')
        assert pkg is not None
        assert pkg.name == 'get-test'

    def test_get_package_path(self, manager, tmp_path):
        """Test getting package installation path."""
        # Install first
        src_dir = tmp_path / 'path-test'
        src_dir.mkdir()
        (src_dir / 'quantum.yaml').write_text('name: path-test\nversion: 1.0.0')
        manager.install(str(src_dir))

        path = manager.get_package_path('path-test')
        assert path is not None
        assert path.exists()

    def test_publish_package(self, manager, tmp_path):
        """Test creating publishable archive."""
        # Create package
        src_dir = tmp_path / 'publish-test'
        src_dir.mkdir()
        (src_dir / 'quantum.yaml').write_text('name: publish-test\nversion: 1.0.0')
        (src_dir / 'src').mkdir()
        (src_dir / 'src' / 'index.q').write_text('<q:component name="Publish" />')

        archive_path = manager.publish(str(src_dir))

        assert archive_path.exists()
        assert archive_path.name == 'publish-test-1.0.0.tar.gz'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
