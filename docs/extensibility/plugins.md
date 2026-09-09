# Plugin System

Quantum's plugin system allows you to extend the framework with custom tags, AST nodes, adapters, CLI commands, and lifecycle hooks. Plugins are self-contained packages that can be shared and reused across projects.

## Plugin Structure

A Quantum plugin follows this directory structure:

```
my-plugin/
├── quantum-plugin.yaml    # Plugin manifest (required)
├── src/
│   ├── __init__.py
│   ├── tags.py            # Tag handlers
│   ├── nodes.py           # Custom AST nodes
│   ├── hooks.py           # Lifecycle hooks
│   ├── adapters.py        # Output adapters
│   └── cli.py             # CLI commands
├── tests/
│   └── test_plugin.py
└── README.md
```

## Plugin Manifest

The `quantum-plugin.yaml` file defines your plugin's metadata and components:

```yaml
name: my-awesome-plugin
version: 1.0.0
quantum: ">=1.0.0"
description: My custom plugin for Quantum Framework
author: Your Name
license: MIT
homepage: https://github.com/you/my-plugin
repository: https://github.com/you/my-plugin.git

# Custom tags (new XML prefixes)
tags:
  - prefix: "my"
    handler: "src.tags:MyTagHandler"
    tags:
      - custom-tag
      - another-tag

# Lifecycle hooks
hooks:
  - hook_type: before_render
    handler: "src.hooks:on_before_render"
    priority: 50

  - hook_type: after_execute
    handler: "src.hooks:on_after_execute"
    priority: 100

# Custom adapters (output targets)
adapters:
  - name: pdf-adapter
    handler: "src.adapters:PdfAdapter"
    target: html

# CLI commands
cli:
  - name: generate
    handler: "src.cli:generate_command"
    help: "Generate custom files from templates"
    aliases:
      - gen
      - g

# Custom AST nodes
nodes:
  - name: MyCustomNode
    handler: "src.nodes:MyCustomNode"
    base: QuantumNode

# Dependencies on other plugins
dependencies:
  - other-plugin>=1.0.0
```

### Required Fields

| Field | Description |
|-------|-------------|
| `name` | Plugin name (lowercase, alphanumeric with hyphens) |
| `version` | Semantic version (e.g., "1.0.0") |

### Optional Fields

| Field | Description | Default |
|-------|-------------|---------|
| `quantum` | Required Quantum version constraint | `>=1.0.0` |
| `description` | Plugin description | `""` |
| `author` | Plugin author | `""` |
| `license` | License identifier | `""` |
| `homepage` | Homepage URL | `""` |
| `repository` | Repository URL | `""` |

## Creating a Plugin

### Step 1: Create the Plugin Directory

```bash
mkdir my-plugin
cd my-plugin
mkdir src tests
```

### Step 2: Create the Manifest

Create `quantum-plugin.yaml`:

```yaml
name: my-chart-plugin
version: 1.0.0
quantum: ">=1.0.0"
description: Custom chart components for Quantum
author: Your Name

tags:
  - prefix: "chart"
    handler: "src.tags:ChartTagHandler"
```

### Step 3: Implement the Tag Handler

Create `src/tags.py`:

```python
"""
Custom chart tag handler for Quantum.
"""

from typing import Dict, Any, List, Optional
from core.ast_nodes import QuantumNode


class ChartNode(QuantumNode):
    """AST node for <chart:*> tags."""

    def __init__(self, tag_name: str):
        self.tag_name = tag_name
        self.chart_type: str = "bar"
        self.data: Optional[str] = None
        self.title: Optional[str] = None
        self.width: str = "100%"
        self.height: str = "300px"
        self.children: List[QuantumNode] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": f"chart_{self.tag_name}",
            "chart_type": self.chart_type,
            "data": self.data,
            "title": self.title,
            "width": self.width,
            "height": self.height,
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.data:
            errors.append(f"chart:{self.tag_name} requires 'data' attribute")
        return errors


class ChartTagHandler:
    """
    Handler for <chart:*> custom tags.

    Supports:
      - <chart:bar data="{salesData}" title="Sales" />
      - <chart:line data="{trends}" />
      - <chart:pie data="{distribution}" />
    """

    prefix = "chart"

    def can_handle(self, tag_name: str) -> bool:
        """Check if this handler can process the tag."""
        return tag_name in ("bar", "line", "pie", "doughnut", "radar")

    def parse(self, tag_name: str, attrs: Dict[str, str], children: List) -> ChartNode:
        """Parse the tag and return an AST node."""
        node = ChartNode(tag_name)
        node.chart_type = tag_name
        node.data = attrs.get("data")
        node.title = attrs.get("title")
        node.width = attrs.get("width", "100%")
        node.height = attrs.get("height", "300px")
        return node

    def render_html(self, node: ChartNode, context: Dict) -> str:
        """Render the node to HTML."""
        return f'''
        <div class="chart-container" style="width: {node.width}; height: {node.height};">
            <canvas id="chart-{id(node)}"
                    data-chart-type="{node.chart_type}"
                    data-chart-data="{node.data}"
                    data-chart-title="{node.title or ''}">
            </canvas>
        </div>
        '''

    def execute(self, node: ChartNode, context: Dict) -> Any:
        """Execute the node (for server-side processing)."""
        # Return data for the chart
        return {
            "type": node.chart_type,
            "data": context.get(node.data.strip("{}")) if node.data else [],
            "title": node.title,
        }
```

### Step 4: Create `__init__.py`

Create `src/__init__.py`:

```python
"""My Chart Plugin for Quantum Framework."""

from .tags import ChartTagHandler, ChartNode

__all__ = ["ChartTagHandler", "ChartNode"]
```

## Tag Handlers

Tag handlers process custom XML tags and convert them to AST nodes and output.

### Tag Handler Interface

```python
class TagHandler:
    """Base interface for tag handlers."""

    prefix: str = ""  # Tag prefix (e.g., "my" for <my:tag>)

    def can_handle(self, tag_name: str) -> bool:
        """Return True if this handler can process the given tag name."""
        pass

    def parse(self, tag_name: str, attrs: Dict[str, str], children: List) -> QuantumNode:
        """Parse the tag and return an AST node."""
        pass

    def render_html(self, node: QuantumNode, context: Dict) -> str:
        """Render the AST node to HTML output."""
        pass

    def render_textual(self, node: QuantumNode, context: Dict) -> str:
        """Render the AST node for terminal (Textual TUI)."""
        pass

    def execute(self, node: QuantumNode, context: Dict) -> Any:
        """Execute the node (for server-side logic)."""
        pass
```

### Example: Multiple Tags

```python
class UIKitTagHandler:
    """Handler for a UI component library."""

    prefix = "kit"

    SUPPORTED_TAGS = {
        "card": CardNode,
        "button": ButtonNode,
        "input": InputNode,
        "modal": ModalNode,
    }

    def can_handle(self, tag_name: str) -> bool:
        return tag_name in self.SUPPORTED_TAGS

    def parse(self, tag_name: str, attrs: Dict[str, str], children: List) -> QuantumNode:
        node_class = self.SUPPORTED_TAGS[tag_name]
        node = node_class()

        # Copy attributes
        for key, value in attrs.items():
            if hasattr(node, key):
                setattr(node, key, value)

        # Add children
        for child in children:
            if hasattr(node, 'add_child'):
                node.add_child(child)

        return node
```

## Lifecycle Hooks

Hooks allow you to intercept and modify Quantum's processing at various stages.

### Available Hook Types

| Hook Type | Description | Context Data |
|-----------|-------------|--------------|
| `on_init` | Plugin initialized | `plugin` info |
| `on_shutdown` | Plugin being unloaded | `plugin` info |
| `before_parse` | Before parsing XML | `source`, `path` |
| `after_parse` | After parsing, before execution | `ast`, `path` |
| `before_execute` | Before executing component | `component`, `context` |
| `after_execute` | After execution | `component`, `result` |
| `before_render` | Before rendering output | `ast`, `target` |
| `after_render` | After rendering | `output`, `target` |
| `on_error` | When an error occurs | `error`, `context` |

### Hook Priority

Lower priority numbers execute first. Default is 100.

```yaml
hooks:
  - hook_type: before_render
    handler: "src.hooks:high_priority_hook"
    priority: 10   # Runs first

  - hook_type: before_render
    handler: "src.hooks:low_priority_hook"
    priority: 200  # Runs later
```

### Implementing Hooks

```python
"""
Lifecycle hooks for my plugin.
"""

from plugins.hooks import HookContext


def on_before_render(ctx: HookContext):
    """
    Called before rendering output.

    Args:
        ctx: Hook context with data about the render operation.
             - ctx.data['ast']: The AST to be rendered
             - ctx.data['target']: Output target (html, textual, etc.)
    """
    ast = ctx.data.get('ast')
    target = ctx.data.get('target')

    # Example: Add analytics tracking to all pages
    if target == 'html' and ast:
        inject_analytics(ast)

    # Modify context data if needed
    ctx.data['custom_data'] = 'injected by hook'


def on_after_execute(ctx: HookContext):
    """Called after component execution."""
    result = ctx.data.get('result')

    # Log execution metrics
    print(f"Component executed with result: {result}")


def on_error(ctx: HookContext):
    """Called when an error occurs."""
    error = ctx.data.get('error')

    # Custom error handling or logging
    log_error_to_service(error)


def inject_analytics(ast):
    """Helper to inject analytics script."""
    # Implementation here
    pass


def log_error_to_service(error):
    """Helper to log errors externally."""
    # Implementation here
    pass
```

## Custom AST Nodes

Create custom AST node types for your tags.

```python
"""
Custom AST nodes for my plugin.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from core.ast_nodes import QuantumNode


@dataclass
class MyCustomNode(QuantumNode):
    """
    Custom AST node for <my:custom> tag.

    Attributes:
        name: Node identifier
        value: Node value
        children: Child nodes
    """
    name: str = ""
    value: Optional[str] = None
    mode: str = "default"
    children: List[QuantumNode] = field(default_factory=list)

    def add_child(self, child: QuantumNode):
        self.children.append(child)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "my_custom",
            "name": self.name,
            "value": self.value,
            "mode": self.mode,
            "children_count": len(self.children),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.name:
            errors.append("MyCustomNode requires 'name' attribute")
        if self.mode not in ("default", "advanced", "simple"):
            errors.append(f"Invalid mode: {self.mode}")
        return errors
```

## CLI Commands from Plugins

Add custom commands to the `quantum` CLI.

```python
"""
CLI commands for my plugin.
"""

import argparse
from pathlib import Path


def generate_command(args: argparse.Namespace) -> int:
    """
    Generate custom files from templates.

    Usage: quantum generate [options]
    """
    template = args.template if hasattr(args, 'template') else 'default'
    output = args.output if hasattr(args, 'output') else '.'

    print(f"Generating from template: {template}")
    print(f"Output directory: {output}")

    # Implementation here
    create_from_template(template, output)

    print("[SUCCESS] Generation complete!")
    return 0


def create_from_template(template: str, output: str):
    """Create files from template."""
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)

    # Create files based on template
    # ...
```

Register in manifest:

```yaml
cli:
  - name: generate
    handler: "src.cli:generate_command"
    help: "Generate custom files from templates"
    aliases:
      - gen
```

Usage:

```bash
quantum generate --template=component --output=./src
# or using alias
quantum gen --template=component
```

## Loading Plugins

### Automatic Discovery

Quantum automatically discovers plugins in:

1. `./plugins/` directory in your project
2. Installed Python packages with `quantum_plugin_` prefix
3. Packages with `quantum.plugins` entry point

### Manual Loading

```python
from plugins.loader import PluginLoader

loader = PluginLoader()

# Load a single plugin
loader.load_plugin('./plugins/my-plugin')

# Discover all plugins in a directory
loaded = loader.discover_plugins('./plugins')
print(f"Loaded {len(loaded)} plugins")

# List loaded plugins
for name in loader.get_loaded_plugins():
    print(f"  - {name}")
```

### Plugin in Project Configuration

In your project's `quantum.yaml`:

```yaml
plugins:
  - ./plugins/my-local-plugin
  - quantum-plugin-charts
  - github:user/quantum-plugin-ui@1.0.0
```

## Publishing Plugins

### As a Python Package

1. Create `setup.py` or `pyproject.toml`:

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="quantum-plugin-charts",
    version="1.0.0",
    packages=find_packages(),
    install_requires=["quantum-framework>=1.0.0"],
    entry_points={
        "quantum.plugins": [
            "charts=quantum_plugin_charts:register",
        ],
    },
)
```

2. Include manifest function:

```python
# quantum_plugin_charts/__init__.py

def get_manifest():
    """Return plugin manifest as dictionary."""
    return {
        "name": "charts",
        "version": "1.0.0",
        "tags": [
            {"prefix": "chart", "handler": "quantum_plugin_charts.tags:ChartHandler"}
        ],
    }


def register():
    """Register the plugin."""
    from .tags import ChartHandler
    return ChartHandler
```

3. Publish to PyPI:

```bash
pip install build twine
python -m build
twine upload dist/*
```

### As a Git Repository

Users can install directly from Git:

```bash
quantum plugin install github:user/my-plugin
```

## Example: Complete Plugin

Here's a complete example of a plugin that adds `<report:*>` tags for generating reports.

### Directory Structure

```
quantum-plugin-reports/
├── quantum-plugin.yaml
├── src/
│   ├── __init__.py
│   ├── tags.py
│   ├── nodes.py
│   └── generators.py
├── templates/
│   └── report.html
└── tests/
    └── test_reports.py
```

### quantum-plugin.yaml

```yaml
name: quantum-plugin-reports
version: 1.0.0
quantum: ">=1.0.0"
description: Report generation plugin for Quantum
author: Your Name

tags:
  - prefix: "report"
    handler: "src.tags:ReportTagHandler"

hooks:
  - hook_type: after_execute
    handler: "src.hooks:collect_report_data"
    priority: 50

cli:
  - name: report
    handler: "src.cli:report_command"
    help: "Generate reports from Quantum components"
```

### src/tags.py

```python
from typing import Dict, Any, List
from .nodes import ReportNode, ReportSectionNode, ReportChartNode


class ReportTagHandler:
    """Handler for <report:*> tags."""

    prefix = "report"

    def can_handle(self, tag_name: str) -> bool:
        return tag_name in ("document", "section", "chart", "table", "summary")

    def parse(self, tag_name: str, attrs: Dict[str, str], children: List) -> Any:
        if tag_name == "document":
            node = ReportNode()
            node.title = attrs.get("title", "Report")
            node.format = attrs.get("format", "html")
        elif tag_name == "section":
            node = ReportSectionNode()
            node.title = attrs.get("title", "")
        elif tag_name == "chart":
            node = ReportChartNode()
            node.chart_type = attrs.get("type", "bar")
            node.data = attrs.get("data")

        for child in children:
            if hasattr(node, 'add_child'):
                node.add_child(child)

        return node

    def render_html(self, node: Any, context: Dict) -> str:
        if isinstance(node, ReportNode):
            return self._render_document(node, context)
        elif isinstance(node, ReportSectionNode):
            return self._render_section(node, context)
        elif isinstance(node, ReportChartNode):
            return self._render_chart(node, context)

    def _render_document(self, node: ReportNode, context: Dict) -> str:
        children_html = "".join(
            self.render_html(child, context) for child in node.children
        )
        return f'''
        <div class="report">
            <h1>{node.title}</h1>
            {children_html}
        </div>
        '''

    def _render_section(self, node: ReportSectionNode, context: Dict) -> str:
        children_html = "".join(
            self.render_html(child, context) for child in node.children
        )
        return f'''
        <section class="report-section">
            <h2>{node.title}</h2>
            {children_html}
        </section>
        '''

    def _render_chart(self, node: ReportChartNode, context: Dict) -> str:
        return f'''
        <div class="report-chart" data-type="{node.chart_type}" data-source="{node.data}">
        </div>
        '''
```

### Usage

```xml
<q:component name="SalesReport">
    <report:document title="Q4 Sales Report" format="html">
        <report:section title="Overview">
            <p>This report covers Q4 2025 sales performance.</p>
        </report:section>

        <report:section title="Sales by Region">
            <report:chart type="bar" data="{salesByRegion}" />
        </report:section>

        <report:section title="Top Products">
            <report:table source="{topProducts}" />
        </report:section>
    </report:document>
</q:component>
```

## Best Practices

1. **Namespace your tags** - Use a unique prefix to avoid conflicts
2. **Validate thoroughly** - Implement `validate()` in your AST nodes
3. **Document your plugin** - Include README with examples
4. **Test extensively** - Write tests for parsing, execution, and rendering
5. **Handle errors gracefully** - Use the `on_error` hook for custom error handling
6. **Version your plugin** - Follow semantic versioning
7. **Minimize dependencies** - Keep external dependencies minimal

## Related Documentation

- [Package Manager](/extensibility/packages) - Share and install packages
- [Custom Components](/guide/components) - Create reusable components
- [Tags Reference](/api/tags-reference) - Built-in tags reference
