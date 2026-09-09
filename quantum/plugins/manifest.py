"""
Quantum Plugin Manifest Parser

Parses quantum-plugin.yaml manifest files that define plugin metadata,
tag handlers, hooks, and other plugin configuration.
"""

import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


class ManifestError(Exception):
    """Error parsing or validating plugin manifest"""
    pass


@dataclass
class TagDefinition:
    """Defines a custom tag provided by a plugin"""
    prefix: str           # e.g., "my" for <my:tag>
    handler: str          # Module path: "src.tags:MyTagHandler"
    tags: List[str] = field(default_factory=list)  # Optional: specific tags, empty = all

    def __post_init__(self):
        if not self.prefix:
            raise ManifestError("Tag definition requires 'prefix'")
        if not self.handler:
            raise ManifestError("Tag definition requires 'handler'")


@dataclass
class HookDefinition:
    """Defines a lifecycle hook registration"""
    hook_type: str        # before_parse, after_parse, before_render, after_render, etc.
    handler: str          # Module path: "src.hooks:on_before_render"
    priority: int = 100   # Lower = earlier execution

    def __post_init__(self):
        valid_hooks = [
            'before_parse', 'after_parse',
            'before_render', 'after_render',
            'before_execute', 'after_execute',
            'on_error', 'on_init', 'on_shutdown'
        ]
        if self.hook_type not in valid_hooks:
            raise ManifestError(f"Invalid hook type: {self.hook_type}. Valid: {valid_hooks}")


@dataclass
class AdapterDefinition:
    """Defines a custom adapter (e.g., for different output targets)"""
    name: str             # e.g., "my-adapter"
    handler: str          # Module path: "src.adapters:MyAdapter"
    target: str = "html"  # Target type: html, textual, desktop, etc.


@dataclass
class CLICommandDefinition:
    """Defines a custom CLI command"""
    name: str             # Command name: "my-command"
    handler: str          # Module path: "src.cli:my_command"
    help: str = ""        # Help text
    aliases: List[str] = field(default_factory=list)


@dataclass
class ASTNodeDefinition:
    """Defines a custom AST node type"""
    name: str             # Node class name: "MyCustomNode"
    handler: str          # Module path: "src.nodes:MyCustomNode"
    base: str = "QuantumNode"  # Base class


@dataclass
class PluginManifest:
    """
    Complete plugin manifest from quantum-plugin.yaml

    Example manifest:
    ```yaml
    name: my-plugin
    version: 1.0.0
    quantum: ">=1.0.0"
    description: My custom plugin
    author: Developer Name

    tags:
      - prefix: "my"
        handler: "src.tags:MyTagHandler"
        tags:
          - custom-tag
          - another-tag

    hooks:
      - hook_type: before_render
        handler: "src.hooks:on_before_render"
        priority: 50

    adapters:
      - name: custom-adapter
        handler: "src.adapters:CustomAdapter"
        target: html

    cli:
      - name: generate
        handler: "src.cli:generate_cmd"
        help: "Generate custom files"

    nodes:
      - name: CustomNode
        handler: "src.nodes:CustomNode"

    dependencies:
      - other-plugin>=1.0.0
    ```
    """
    name: str
    version: str
    quantum_version: str = ">=1.0.0"
    description: str = ""
    author: str = ""
    license: str = ""
    homepage: str = ""
    repository: str = ""

    # Plugin components
    tags: List[TagDefinition] = field(default_factory=list)
    hooks: List[HookDefinition] = field(default_factory=list)
    adapters: List[AdapterDefinition] = field(default_factory=list)
    cli_commands: List[CLICommandDefinition] = field(default_factory=list)
    nodes: List[ASTNodeDefinition] = field(default_factory=list)

    # Dependencies
    dependencies: List[str] = field(default_factory=list)

    # Source directory (set during loading)
    source_path: Optional[Path] = None

    @classmethod
    def from_file(cls, manifest_path) -> 'PluginManifest':
        """Load manifest from yaml file"""
        if isinstance(manifest_path, str):
            manifest_path = Path(manifest_path)
        if not manifest_path.exists():
            raise ManifestError(f"Manifest file not found: {manifest_path}")

        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ManifestError(f"Invalid YAML in manifest: {e}")

        if not data:
            raise ManifestError("Empty manifest file")

        return cls.from_dict(data, manifest_path.parent)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], source_path: Path = None) -> 'PluginManifest':
        """Create manifest from dictionary"""
        # Validate required fields
        if 'name' not in data:
            raise ManifestError("Manifest requires 'name' field")
        if 'version' not in data:
            raise ManifestError("Manifest requires 'version' field")

        # Parse tags
        tags = []
        for tag_data in data.get('tags', []):
            if isinstance(tag_data, dict):
                tags.append(TagDefinition(
                    prefix=tag_data.get('prefix', ''),
                    handler=tag_data.get('handler', ''),
                    tags=tag_data.get('tags', [])
                ))

        # Parse hooks
        hooks = []
        for hook_data in data.get('hooks', []):
            if isinstance(hook_data, dict):
                # Support both formats:
                # - hook_type: before_render
                #   handler: "src.hooks:fn"
                # - before_render: "src.hooks:fn"
                hook_type = hook_data.get('hook_type')
                handler = hook_data.get('handler')
                priority = hook_data.get('priority', 100)

                # Alternative format
                if not hook_type:
                    for ht in ['before_parse', 'after_parse', 'before_render',
                               'after_render', 'before_execute', 'after_execute',
                               'on_error', 'on_init', 'on_shutdown']:
                        if ht in hook_data:
                            hook_type = ht
                            handler = hook_data[ht]
                            break

                if hook_type and handler:
                    hooks.append(HookDefinition(
                        hook_type=hook_type,
                        handler=handler,
                        priority=priority
                    ))

        # Parse adapters
        adapters = []
        for adapter_data in data.get('adapters', []):
            if isinstance(adapter_data, dict):
                adapters.append(AdapterDefinition(
                    name=adapter_data.get('name', ''),
                    handler=adapter_data.get('handler', ''),
                    target=adapter_data.get('target', 'html')
                ))

        # Parse CLI commands
        cli_commands = []
        for cli_data in data.get('cli', []):
            if isinstance(cli_data, dict):
                cli_commands.append(CLICommandDefinition(
                    name=cli_data.get('name', ''),
                    handler=cli_data.get('handler', ''),
                    help=cli_data.get('help', ''),
                    aliases=cli_data.get('aliases', [])
                ))

        # Parse AST nodes
        nodes = []
        for node_data in data.get('nodes', []):
            if isinstance(node_data, dict):
                nodes.append(ASTNodeDefinition(
                    name=node_data.get('name', ''),
                    handler=node_data.get('handler', ''),
                    base=node_data.get('base', 'QuantumNode')
                ))

        return cls(
            name=data['name'],
            version=data['version'],
            quantum_version=data.get('quantum', '>=1.0.0'),
            description=data.get('description', ''),
            author=data.get('author', ''),
            license=data.get('license', ''),
            homepage=data.get('homepage', ''),
            repository=data.get('repository', ''),
            tags=tags,
            hooks=hooks,
            adapters=adapters,
            cli_commands=cli_commands,
            nodes=nodes,
            dependencies=data.get('dependencies', []),
            source_path=source_path
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to dictionary"""
        result = {
            'name': self.name,
            'version': self.version,
            'quantum': self.quantum_version,
        }

        if self.description:
            result['description'] = self.description
        if self.author:
            result['author'] = self.author
        if self.license:
            result['license'] = self.license

        if self.tags:
            result['tags'] = [
                {'prefix': t.prefix, 'handler': t.handler, 'tags': t.tags}
                for t in self.tags
            ]

        if self.hooks:
            result['hooks'] = [
                {'hook_type': h.hook_type, 'handler': h.handler, 'priority': h.priority}
                for h in self.hooks
            ]

        if self.adapters:
            result['adapters'] = [
                {'name': a.name, 'handler': a.handler, 'target': a.target}
                for a in self.adapters
            ]

        if self.cli_commands:
            result['cli'] = [
                {'name': c.name, 'handler': c.handler, 'help': c.help, 'aliases': c.aliases}
                for c in self.cli_commands
            ]

        if self.nodes:
            result['nodes'] = [
                {'name': n.name, 'handler': n.handler, 'base': n.base}
                for n in self.nodes
            ]

        if self.dependencies:
            result['dependencies'] = self.dependencies

        return result

    def validate(self) -> List[str]:
        """Validate manifest and return list of errors"""
        errors = []

        # Name validation
        if not self.name:
            errors.append("Plugin name is required")
        elif not self.name.replace('-', '').replace('_', '').isalnum():
            errors.append(f"Invalid plugin name: {self.name}")

        # Version validation
        if not self.version:
            errors.append("Plugin version is required")

        # Tag validation
        for tag in self.tags:
            if not tag.prefix:
                errors.append("Tag prefix is required")
            if not tag.handler:
                errors.append(f"Handler is required for tag prefix '{tag.prefix}'")

        # Hook validation
        for hook in self.hooks:
            if not hook.handler:
                errors.append(f"Handler is required for hook '{hook.hook_type}'")

        return errors

    def __repr__(self):
        return f"<PluginManifest {self.name}@{self.version}>"
