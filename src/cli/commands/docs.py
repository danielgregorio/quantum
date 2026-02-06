"""
Quantum CLI - Docs Command

Generate documentation from components.
"""

import sys
from pathlib import Path
from typing import Optional, List

import click

from cli.utils import get_console, find_project_root, find_q_files


@click.command('docs')
@click.argument('path', required=False, type=click.Path())
@click.option('--output', '-o', type=click.Path(), default='docs/api',
              help='Output directory for generated docs')
@click.option('--format', '-f', type=click.Choice(['markdown', 'html', 'json']), default='markdown',
              help='Output format')
@click.option('--serve', '-s', is_flag=True, help='Start docs server after generation')
@click.option('--port', '-p', type=int, default=5173, help='Port for docs server')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode')
def docs(
    path: Optional[str],
    output: str,
    format: str,
    serve: bool,
    port: int,
    quiet: bool
):
    """Generate documentation from Quantum components.

    Extracts component metadata, props, slots, and examples to create
    API documentation.

    Examples:

        quantum docs

        quantum docs ./components

        quantum docs --output ./api-docs --format html

        quantum docs --serve
    """
    console = get_console(quiet=quiet)

    # Find project root
    project_root = find_project_root()
    if not project_root:
        project_root = Path.cwd()

    # Determine source path
    if path:
        source_path = Path(path)
        if not source_path.is_absolute():
            source_path = project_root / path
    else:
        # Default locations for components
        for default_path in ['components', 'src/components', 'src']:
            candidate = project_root / default_path
            if candidate.exists():
                source_path = candidate
                break
        else:
            source_path = project_root

    if not source_path.exists():
        console.error(f"Source path not found: {source_path}")
        raise click.Abort()

    # Output directory
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = project_root / output

    console.header(
        "Quantum Docs Generator",
        f"Source: {source_path}\nOutput: {output_path}"
    )

    # Find .q files
    q_files = find_q_files(source_path, recursive=True)
    console.info(f"Found {len(q_files)} component(s)")

    if not q_files:
        console.warning("No .q files found")
        return

    # Generate documentation
    output_path.mkdir(parents=True, exist_ok=True)
    generated = []

    with console.progress("Generating documentation...") as progress:
        task = progress.add_task("Processing", total=len(q_files))

        for q_file in q_files:
            try:
                doc = _generate_component_doc(q_file, format)
                if doc:
                    # Write doc file
                    rel_path = q_file.relative_to(source_path) if q_file.is_relative_to(source_path) else q_file.name
                    ext = {'markdown': '.md', 'html': '.html', 'json': '.json'}[format]
                    doc_file = output_path / str(rel_path).replace('.q', ext)
                    doc_file.parent.mkdir(parents=True, exist_ok=True)
                    doc_file.write_text(doc, encoding='utf-8')
                    generated.append(doc_file)
            except Exception as e:
                console.warning(f"Failed to process {q_file.name}: {e}")

            progress.update(task, advance=1)

    # Generate index
    if generated and format == 'markdown':
        index_content = _generate_index(generated, output_path)
        index_file = output_path / 'index.md'
        index_file.write_text(index_content, encoding='utf-8')
        generated.append(index_file)

    console.success(f"Generated {len(generated)} documentation file(s)")

    # Start server if requested
    if serve:
        console.info(f"Starting docs server on http://localhost:{port}")
        _serve_docs(output_path, port)


def _generate_component_doc(file_path: Path, format: str) -> Optional[str]:
    """Generate documentation for a single component."""
    import re

    content = file_path.read_text(encoding='utf-8')

    # Extract component metadata
    component_match = re.search(r'<q:component\s+name="([^"]+)"', content)
    if not component_match:
        return None

    component_name = component_match.group(1)

    # Extract description from comment
    desc_match = re.search(r'<!--\s*@description\s+(.*?)\s*-->', content, re.DOTALL)
    description = desc_match.group(1).strip() if desc_match else "No description available."

    # Extract params
    params = []
    for match in re.finditer(
        r'<q:param\s+name="([^"]+)"(?:\s+type="([^"]+)")?(?:\s+default="([^"]+)")?(?:\s+required="([^"]+)")?[^>]*/?>',
        content
    ):
        params.append({
            'name': match.group(1),
            'type': match.group(2) or 'any',
            'default': match.group(3),
            'required': match.group(4) == 'true',
        })

    # Extract slots
    slots = []
    for match in re.finditer(r'<q:slot(?:\s+name="([^"]+)")?[^>]*/>', content):
        slot_name = match.group(1) or 'default'
        slots.append({'name': slot_name})

    # Extract example from comment
    example_match = re.search(r'<!--\s*@example\s+(.*?)\s*-->', content, re.DOTALL)
    example = example_match.group(1).strip() if example_match else None

    # Generate output
    if format == 'markdown':
        return _format_markdown(component_name, description, params, slots, example, file_path)
    elif format == 'html':
        return _format_html(component_name, description, params, slots, example, file_path)
    elif format == 'json':
        import json
        return json.dumps({
            'name': component_name,
            'description': description,
            'params': params,
            'slots': slots,
            'example': example,
            'file': str(file_path),
        }, indent=2)

    return None


def _format_markdown(name: str, description: str, params: List, slots: List, example: Optional[str], file_path: Path) -> str:
    """Format component documentation as Markdown."""
    lines = [
        f"# {name}",
        "",
        description,
        "",
    ]

    if params:
        lines.extend([
            "## Props",
            "",
            "| Name | Type | Default | Required |",
            "|------|------|---------|----------|",
        ])
        for p in params:
            default = f"`{p['default']}`" if p['default'] else "-"
            required = "Yes" if p['required'] else "No"
            lines.append(f"| `{p['name']}` | `{p['type']}` | {default} | {required} |")
        lines.append("")

    if slots:
        lines.extend([
            "## Slots",
            "",
        ])
        for s in slots:
            lines.append(f"- `{s['name']}`")
        lines.append("")

    if example:
        lines.extend([
            "## Example",
            "",
            "```xml",
            example,
            "```",
            "",
        ])

    lines.extend([
        "---",
        f"*Source: `{file_path.name}`*",
    ])

    return '\n'.join(lines)


def _format_html(name: str, description: str, params: List, slots: List, example: Optional[str], file_path: Path) -> str:
    """Format component documentation as HTML."""
    import html

    parts = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        f"<title>{html.escape(name)} - Quantum Component</title>",
        "<style>",
        "body { font-family: system-ui, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }",
        "h1 { color: #333; }",
        "table { border-collapse: collapse; width: 100%; }",
        "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
        "th { background: #f5f5f5; }",
        "code { background: #f5f5f5; padding: 2px 6px; border-radius: 3px; }",
        "pre { background: #1e1e1e; color: #d4d4d4; padding: 16px; border-radius: 6px; overflow-x: auto; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>{html.escape(name)}</h1>",
        f"<p>{html.escape(description)}</p>",
    ]

    if params:
        parts.extend([
            "<h2>Props</h2>",
            "<table>",
            "<tr><th>Name</th><th>Type</th><th>Default</th><th>Required</th></tr>",
        ])
        for p in params:
            default = f"<code>{html.escape(p['default'])}</code>" if p['default'] else "-"
            required = "Yes" if p['required'] else "No"
            parts.append(f"<tr><td><code>{html.escape(p['name'])}</code></td><td><code>{html.escape(p['type'])}</code></td><td>{default}</td><td>{required}</td></tr>")
        parts.append("</table>")

    if slots:
        parts.append("<h2>Slots</h2><ul>")
        for s in slots:
            parts.append(f"<li><code>{html.escape(s['name'])}</code></li>")
        parts.append("</ul>")

    if example:
        parts.extend([
            "<h2>Example</h2>",
            f"<pre><code>{html.escape(example)}</code></pre>",
        ])

    parts.extend([
        f"<hr><p><em>Source: <code>{html.escape(file_path.name)}</code></em></p>",
        "</body>",
        "</html>",
    ])

    return '\n'.join(parts)


def _generate_index(generated: List[Path], output_path: Path) -> str:
    """Generate index file for documentation."""
    lines = [
        "# Quantum Component API",
        "",
        "## Components",
        "",
    ]

    for doc_file in sorted(generated):
        if doc_file.name == 'index.md':
            continue
        rel_path = doc_file.relative_to(output_path)
        name = doc_file.stem
        lines.append(f"- [{name}](./{rel_path})")

    return '\n'.join(lines)


def _serve_docs(output_path: Path, port: int):
    """Start a simple HTTP server for documentation."""
    import http.server
    import socketserver
    import os

    os.chdir(output_path)

    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"Serving docs at http://localhost:{port}")
        print("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped")
