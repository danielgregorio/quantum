"""
Quantum Package Manifest Handler

Handles parsing and validation of quantum.yaml package manifests.

Package structure:
    my-component/
    ├── quantum.yaml         # Package manifest
    ├── src/
    │   └── MyComponent.q    # Component file
    ├── examples/
    │   └── demo.q
    └── README.md
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    import yaml
except ImportError:
    yaml = None


class ManifestError(Exception):
    """Error parsing or validating package manifest."""
    pass


@dataclass
class PackageManifest:
    """
    Represents a quantum.yaml package manifest.

    Attributes:
        name: Package name (lowercase, alphanumeric, hyphens allowed)
        version: Semantic version (e.g., "1.0.0")
        description: Package description
        author: Package author
        license: License identifier (e.g., "MIT", "Apache-2.0")
        main: Main component file path (relative to package root)
        dependencies: Dict of package name -> version constraint
        keywords: List of keywords for search
        repository: Optional repository URL
        homepage: Optional homepage URL
        exports: List of exported component names
    """
    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = "MIT"
    main: str = "src/index.q"
    dependencies: Dict[str, str] = field(default_factory=dict)
    keywords: List[str] = field(default_factory=list)
    repository: Optional[str] = None
    homepage: Optional[str] = None
    exports: List[str] = field(default_factory=list)

    # Internal
    _path: Optional[Path] = None

    @classmethod
    def load(cls, manifest_path: Path) -> 'PackageManifest':
        """Load manifest from quantum.yaml file."""
        if yaml is None:
            raise ManifestError("PyYAML not installed. Install with: pip install pyyaml")

        if not manifest_path.exists():
            raise ManifestError(f"Manifest not found: {manifest_path}")

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ManifestError(f"Invalid YAML in manifest: {e}")

        if not data:
            raise ManifestError("Empty manifest file")

        # Validate required fields
        if 'name' not in data:
            raise ManifestError("Package name is required")
        if 'version' not in data:
            raise ManifestError("Package version is required")

        # Validate name format
        name = data['name']
        if not cls._validate_name(name):
            raise ManifestError(
                f"Invalid package name: {name}. "
                "Names must be lowercase, alphanumeric with hyphens allowed."
            )

        # Validate version format
        version = data['version']
        if not cls._validate_version(version):
            raise ManifestError(
                f"Invalid version: {version}. "
                "Use semantic versioning (e.g., 1.0.0)"
            )

        # Parse dependencies
        dependencies = {}
        if 'dependencies' in data and data['dependencies']:
            for dep_name, dep_version in data['dependencies'].items():
                if not cls._validate_name(dep_name):
                    raise ManifestError(f"Invalid dependency name: {dep_name}")
                if not cls._validate_version_constraint(dep_version):
                    raise ManifestError(f"Invalid version constraint for {dep_name}: {dep_version}")
                dependencies[dep_name] = dep_version

        manifest = cls(
            name=name,
            version=str(version),
            description=data.get('description', ''),
            author=data.get('author', ''),
            license=data.get('license', 'MIT'),
            main=data.get('main', 'src/index.q'),
            dependencies=dependencies,
            keywords=data.get('keywords', []) or [],
            repository=data.get('repository'),
            homepage=data.get('homepage'),
            exports=data.get('exports', []) or [],
        )
        manifest._path = manifest_path.parent

        return manifest

    @staticmethod
    def _validate_name(name: str) -> bool:
        """Validate package name format."""
        if not name:
            return False
        # lowercase, alphanumeric, hyphens allowed, must start with letter
        pattern = r'^[a-z][a-z0-9-]*$'
        return bool(re.match(pattern, name))

    @staticmethod
    def _validate_version(version: str) -> bool:
        """Validate semantic version format."""
        if not version:
            return False
        # Basic semver: major.minor.patch with optional prerelease
        pattern = r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$'
        return bool(re.match(pattern, str(version)))

    @staticmethod
    def _validate_version_constraint(constraint: str) -> bool:
        """Validate version constraint format."""
        if not constraint:
            return False
        # Support: exact, ^, ~, >=, >, <=, <, or ranges
        patterns = [
            r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$',  # exact: 1.0.0
            r'^\^?\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$',  # caret: ^1.0.0
            r'^~\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$',  # tilde: ~1.0.0
            r'^[><]=?\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$',  # comparison: >=1.0.0
            r'^\*$',  # any version
        ]
        return any(re.match(p, str(constraint)) for p in patterns)

    def save(self, path: Optional[Path] = None) -> None:
        """Save manifest to quantum.yaml file."""
        if yaml is None:
            raise ManifestError("PyYAML not installed. Install with: pip install pyyaml")

        target_path = path or (self._path / 'quantum.yaml' if self._path else None)
        if not target_path:
            raise ManifestError("No path specified for saving manifest")

        if isinstance(target_path, Path) and target_path.is_dir():
            target_path = target_path / 'quantum.yaml'

        data = {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'license': self.license,
            'main': self.main,
        }

        if self.dependencies:
            data['dependencies'] = self.dependencies

        if self.keywords:
            data['keywords'] = self.keywords

        if self.repository:
            data['repository'] = self.repository

        if self.homepage:
            data['homepage'] = self.homepage

        if self.exports:
            data['exports'] = self.exports

        with open(target_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary."""
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description,
            'author': self.author,
            'license': self.license,
            'main': self.main,
            'dependencies': self.dependencies,
            'keywords': self.keywords,
            'repository': self.repository,
            'homepage': self.homepage,
            'exports': self.exports,
        }

    def get_main_component_path(self) -> Path:
        """Get absolute path to main component file."""
        if not self._path:
            raise ManifestError("Package path not set")
        return self._path / self.main

    def get_component_paths(self) -> List[Path]:
        """Get all component (.q) files in the package."""
        if not self._path:
            raise ManifestError("Package path not set")

        components = []
        src_dir = self._path / 'src'
        if src_dir.exists():
            for qfile in src_dir.rglob('*.q'):
                components.append(qfile)

        # Also check root if main is at root level
        main_path = self.get_main_component_path()
        if main_path.exists() and main_path not in components:
            components.append(main_path)

        return components


def init_package(
    path: Path,
    name: Optional[str] = None,
    description: str = "",
    author: str = "",
    license_id: str = "MIT"
) -> PackageManifest:
    """
    Initialize a new package in the given directory.

    Creates:
    - quantum.yaml manifest
    - src/ directory with index.q
    - examples/ directory
    - README.md
    """
    if yaml is None:
        raise ManifestError("PyYAML not installed. Install with: pip install pyyaml")

    path = Path(path)

    # Use directory name as package name if not provided
    if not name:
        name = path.name.lower().replace('_', '-').replace(' ', '-')
        # Remove invalid characters
        name = re.sub(r'[^a-z0-9-]', '', name)
        if not name or not name[0].isalpha():
            name = 'my-component'

    # Create directories
    path.mkdir(parents=True, exist_ok=True)
    (path / 'src').mkdir(exist_ok=True)
    (path / 'examples').mkdir(exist_ok=True)

    # Create manifest
    manifest = PackageManifest(
        name=name,
        version='1.0.0',
        description=description,
        author=author,
        license=license_id,
        main='src/index.q',
    )
    manifest._path = path
    manifest.save()

    # Create main component file
    component_name = ''.join(word.capitalize() for word in name.split('-'))
    main_content = f'''<q:component name="{component_name}">
  <!-- Component parameters -->
  <q:param name="title" type="string" default="{component_name}" />

  <!-- Component template -->
  <div class="{name}">
    <h1>{{title}}</h1>
    <q:slot />
  </div>
</q:component>
'''

    with open(path / 'src' / 'index.q', 'w', encoding='utf-8') as f:
        f.write(main_content)

    # Create example file
    example_content = f'''<q:component name="Demo">
  <q:import component="{component_name}" from="../src" />

  <{component_name} title="Hello World">
    <p>This is a demo of the {name} component.</p>
  </{component_name}>
</q:component>
'''

    with open(path / 'examples' / 'demo.q', 'w', encoding='utf-8') as f:
        f.write(example_content)

    # Create README
    readme_content = f'''# {name}

{description or 'A Quantum component package.'}

## Installation

```bash
quantum pkg install {name}
```

## Usage

```xml
<q:import component="{component_name}" from="{name}" />

<{component_name} title="Example">
  <p>Content goes here</p>
</{component_name}>
```

## License

{license_id}
'''

    with open(path / 'README.md', 'w', encoding='utf-8') as f:
        f.write(readme_content)

    return manifest
