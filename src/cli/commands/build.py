"""
Quantum CLI - Build Command

Build Quantum applications for production.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List
from datetime import datetime

import click

from cli.utils import get_console, find_project_root, find_q_files


# Available build targets
TARGETS = ['html', 'desktop', 'mobile', 'textual', 'all']


@click.command('build')
@click.option('--target', '-t', type=click.Choice(TARGETS), default='html',
              help='Build target (html, desktop, mobile, textual, all)')
@click.option('--output', '-o', type=click.Path(), default='./dist',
              help='Output directory')
@click.option('--minify', is_flag=True, default=True, help='Minify output')
@click.option('--no-minify', is_flag=True, help='Disable minification')
@click.option('--sourcemap', is_flag=True, help='Generate source maps')
@click.option('--watch', '-w', is_flag=True, help='Watch mode - rebuild on changes')
@click.option('--clean', is_flag=True, help='Clean output directory before build')
@click.option('--config', '-c', type=click.Path(), default='quantum.config.yaml',
              help='Config file path')
@click.option('--debug', is_flag=True, help='Debug mode with verbose output')
@click.option('--quiet', '-q', is_flag=True, help='Quiet mode')
def build(
    target: str,
    output: str,
    minify: bool,
    no_minify: bool,
    sourcemap: bool,
    watch: bool,
    clean: bool,
    config: str,
    debug: bool,
    quiet: bool
):
    """Build Quantum application for production.

    Compiles .q files to the specified target format.

    Examples:

        quantum build

        quantum build --target desktop

        quantum build --target all --output ./build

        quantum build --target mobile --no-minify
    """
    console = get_console(quiet=quiet)

    # Find project root
    project_root = find_project_root()
    if not project_root:
        console.error("No Quantum project found. Run from a project directory or use 'quantum new'")
        raise click.Abort()

    output_dir = Path(output)
    if not output_dir.is_absolute():
        output_dir = project_root / output

    # Resolve minify flag
    should_minify = minify and not no_minify

    console.header(
        "Building Quantum Application",
        f"Target: {target} | Output: {output_dir}"
    )

    # Clean output directory
    if clean and output_dir.exists():
        with console.spinner("Cleaning output directory..."):
            shutil.rmtree(output_dir)
        console.info(f"Cleaned: {output_dir}")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find .q files
    q_files = find_q_files(project_root)
    if not q_files:
        console.error("No .q files found in project")
        raise click.Abort()

    console.info(f"Found {len(q_files)} .q files")

    # Determine targets to build
    if target == 'all':
        targets_to_build = ['html', 'desktop', 'mobile', 'textual']
    else:
        targets_to_build = [target]

    # Build each target
    results = {}
    for build_target in targets_to_build:
        console.print()
        console.info(f"Building for target: [bold]{build_target}[/bold]")

        try:
            result = _build_target(
                project_root=project_root,
                q_files=q_files,
                target=build_target,
                output_dir=output_dir / build_target if target == 'all' else output_dir,
                minify=should_minify,
                sourcemap=sourcemap,
                debug=debug,
                console=console
            )
            results[build_target] = result
            console.success(f"Built {build_target}: {result['output_path']}")

        except Exception as e:
            console.error(f"Failed to build {build_target}: {e}")
            if debug:
                import traceback
                console.print(traceback.format_exc())
            results[build_target] = {'error': str(e)}

    # Summary
    console.print()
    successful = [t for t, r in results.items() if 'error' not in r]
    failed = [t for t, r in results.items() if 'error' in r]

    if successful:
        console.panel(
            f"[bold green]Successfully built:[/bold green] {', '.join(successful)}\n"
            f"[bold]Output:[/bold] {output_dir}",
            title="Build Complete"
        )

    if failed:
        console.warning(f"Failed targets: {', '.join(failed)}")

    # Watch mode
    if watch:
        console.print()
        console.info("Watching for changes... (Ctrl+C to stop)")
        _watch_and_rebuild(
            project_root=project_root,
            targets=targets_to_build,
            output_dir=output_dir,
            minify=should_minify,
            sourcemap=sourcemap,
            debug=debug,
            console=console,
            target=target
        )


def _build_target(
    project_root: Path,
    q_files: List[Path],
    target: str,
    output_dir: Path,
    minify: bool,
    sourcemap: bool,
    debug: bool,
    console
) -> dict:
    """Build a specific target."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from core.parser import QuantumParser
    from core.ast_nodes import ApplicationNode

    parser = QuantumParser()
    output_dir.mkdir(parents=True, exist_ok=True)

    built_files = []

    with console.progress("Building...", total=len(q_files)) as advance:
        for q_file in q_files:
            try:
                # Parse file
                ast = parser.parse_file(str(q_file))

                # Only build ApplicationNode files
                if isinstance(ast, ApplicationNode):
                    output_path = _build_application(
                        app=ast,
                        target=target,
                        output_dir=output_dir,
                        minify=minify,
                        debug=debug
                    )
                    built_files.append(output_path)

                if advance:
                    advance()

            except Exception as e:
                if debug:
                    console.warning(f"Skipping {q_file.name}: {e}")

    # Copy static assets
    assets_dir = project_root / 'assets'
    if assets_dir.exists():
        target_assets = output_dir / 'assets'
        if target_assets.exists():
            shutil.rmtree(target_assets)
        shutil.copytree(assets_dir, target_assets)
        console.info(f"Copied assets to {target_assets}")

    return {
        'target': target,
        'output_path': str(output_dir),
        'files_built': len(built_files),
        'minified': minify,
    }


def _build_application(
    app,
    target: str,
    output_dir: Path,
    minify: bool,
    debug: bool
) -> str:
    """Build an application node to target."""
    from runtime.ui_builder import UIBuilder, UIBuildError

    # Determine builder based on app type
    app_type = getattr(app, 'app_type', 'html')

    if app_type == 'game':
        from runtime.game_builder import GameBuilder
        builder = GameBuilder()
        ext = '.html'
    elif app_type == 'terminal':
        from runtime.terminal_builder import TerminalBuilder
        builder = TerminalBuilder()
        ext = '.py'
    elif app_type == 'testing':
        from runtime.testing_builder import TestingBuilder
        builder = TestingBuilder()
        ext = '.py'
    elif app_type == 'ui' or target in ('html', 'desktop', 'mobile', 'textual'):
        builder = UIBuilder()
        # Map target to extension
        ext_map = {
            'html': '.html',
            'desktop': '.py',
            'mobile': '.js',
            'textual': '.py',
        }
        ext = ext_map.get(target, '.html')
    else:
        # Default to HTML
        builder = UIBuilder()
        ext = '.html'
        target = 'html'

    # Build output
    output_file = output_dir / f"{app.app_id}{ext}"

    if hasattr(builder, 'build_to_file'):
        # UI builder with target
        if isinstance(builder, UIBuilder):
            output_path = builder.build_to_file(app, target=target, output_path=str(output_file))
        else:
            output_path = builder.build_to_file(app, output_path=str(output_file))
    else:
        # Generic builder
        code = builder.build(app)
        output_file.write_text(code, encoding='utf-8')
        output_path = str(output_file)

    # Minify if requested
    if minify and ext == '.html':
        _minify_html(output_path)
    elif minify and ext == '.js':
        _minify_js(output_path)
    elif minify and ext == '.css':
        _minify_css(output_path)

    return output_path


def _minify_html(path: str) -> None:
    """Minify HTML file."""
    try:
        import re
        content = Path(path).read_text(encoding='utf-8')

        # Basic HTML minification
        # Remove comments
        content = re.sub(r'<!--(?!\[if).*?-->', '', content, flags=re.DOTALL)
        # Remove extra whitespace between tags
        content = re.sub(r'>\s+<', '><', content)
        # Remove leading/trailing whitespace
        content = '\n'.join(line.strip() for line in content.splitlines() if line.strip())

        Path(path).write_text(content, encoding='utf-8')
    except Exception:
        pass  # Minification is optional


def _minify_js(path: str) -> None:
    """Minify JavaScript file."""
    try:
        import re
        content = Path(path).read_text(encoding='utf-8')

        # Basic JS minification
        # Remove single-line comments (but not URLs)
        content = re.sub(r'(?<!:)//.*$', '', content, flags=re.MULTILINE)
        # Remove multi-line comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Remove extra whitespace
        content = ' '.join(content.split())

        Path(path).write_text(content, encoding='utf-8')
    except Exception:
        pass


def _minify_css(path: str) -> None:
    """Minify CSS file."""
    try:
        import re
        content = Path(path).read_text(encoding='utf-8')

        # Basic CSS minification
        # Remove comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        # Remove extra whitespace
        content = re.sub(r'\s+', ' ', content)
        # Remove space around special chars
        content = re.sub(r'\s*([{};:,])\s*', r'\1', content)

        Path(path).write_text(content, encoding='utf-8')
    except Exception:
        pass


def _watch_and_rebuild(
    project_root: Path,
    targets: List[str],
    output_dir: Path,
    minify: bool,
    sourcemap: bool,
    debug: bool,
    console,
    target: str
):
    """Watch for changes and rebuild."""
    import time
    import signal

    last_mtimes = {}

    def get_file_mtimes():
        mtimes = {}
        for ext in ['.q', '.yaml', '.yml']:
            for f in project_root.rglob(f'*{ext}'):
                try:
                    mtimes[f] = f.stat().st_mtime
                except OSError:
                    pass
        return mtimes

    def signal_handler(sig, frame):
        console.print()
        console.info("Stopping watch mode...")
        raise SystemExit(0)

    signal.signal(signal.SIGINT, signal_handler)
    last_mtimes = get_file_mtimes()

    while True:
        time.sleep(1)
        current_mtimes = get_file_mtimes()

        changed = []
        for f, mtime in current_mtimes.items():
            if f not in last_mtimes or mtime > last_mtimes[f]:
                changed.append(f)

        if changed:
            console.print()
            for f in changed:
                rel_path = f.relative_to(project_root)
                console.info(f"Changed: {rel_path}")

            console.info("Rebuilding...")

            q_files = find_q_files(project_root)
            for build_target in targets:
                try:
                    _build_target(
                        project_root=project_root,
                        q_files=q_files,
                        target=build_target,
                        output_dir=output_dir / build_target if target == 'all' else output_dir,
                        minify=minify,
                        sourcemap=sourcemap,
                        debug=debug,
                        console=console
                    )
                    console.success(f"Rebuilt {build_target}")
                except Exception as e:
                    console.error(f"Failed to rebuild {build_target}: {e}")

            last_mtimes = current_mtimes
