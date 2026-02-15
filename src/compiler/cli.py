#!/usr/bin/env python
"""
Quantum Transpiler CLI
======================

Command-line interface for compiling Quantum files.

Usage:
    quantum compile app.q -o app.py
    quantum compile app.q --target=javascript -o app.js
    quantum compile src/ -o dist/ --watch
"""

import sys
import os
import time
import argparse
from pathlib import Path
from typing import Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from compiler.transpiler import Transpiler, CompilationResult


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog='quantum compile',
        description='Quantum Transpiler - Compile .q files to Python/JavaScript'
    )

    parser.add_argument(
        'source',
        help='Source file or directory'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output file or directory'
    )

    parser.add_argument(
        '--target',
        choices=['python', 'javascript', 'js'],
        default='python',
        help='Target language (default: python)'
    )

    parser.add_argument(
        '--watch', '-w',
        action='store_true',
        help='Watch for file changes'
    )

    parser.add_argument(
        '--optimize',
        action='store_true',
        help='Enable optimizations'
    )

    parser.add_argument(
        '--sourcemap',
        action='store_true',
        help='Generate source maps'
    )

    parser.add_argument(
        '--strict',
        action='store_true',
        help='Treat warnings as errors'
    )

    parser.add_argument(
        '--check',
        action='store_true',
        help='Check only, do not generate output'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Minimal output'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )

    return parser


def compile_file(
    source: Path,
    output: Optional[Path],
    transpiler: Transpiler,
    check_only: bool = False,
    quiet: bool = False,
    verbose: bool = False
) -> bool:
    """
    Compile a single file.

    Returns:
        True if successful
    """
    result = transpiler.compile_file(str(source))

    if not result.success:
        if not quiet:
            print(f"ERROR: {source}")
            for error in result.errors:
                print(f"  {error}")
        return False

    if check_only:
        if not quiet:
            print(f"OK: {source}")
        return True

    # Determine output path
    if output is None:
        ext = transpiler._get_generator().file_extension()
        output = source.with_suffix(ext)

    # Write output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(result.code, encoding='utf-8')

    if not quiet:
        stats = result.stats or {}
        time_ms = stats.get('compile_time_ms', 0)
        print(f"OK: {source} -> {output} ({time_ms:.1f}ms)")

    if verbose:
        print(f"  Lines: {stats.get('source_lines', 0)} -> {stats.get('output_lines', 0)}")

    # Write source map
    if result.sourcemap and transpiler.sourcemap:
        map_path = output.with_suffix(output.suffix + '.map')
        map_path.write_text(result.sourcemap, encoding='utf-8')
        if verbose:
            print(f"  Source map: {map_path}")

    # Warnings
    if result.warnings and not quiet:
        for warning in result.warnings:
            print(f"  WARNING: {warning}")

    return True


def compile_directory(
    source_dir: Path,
    output_dir: Path,
    transpiler: Transpiler,
    check_only: bool = False,
    quiet: bool = False,
    verbose: bool = False
) -> int:
    """
    Compile all .q files in a directory.

    Returns:
        Number of errors
    """
    errors = 0
    compiled = 0

    for q_file in source_dir.rglob('*.q'):
        rel_path = q_file.relative_to(source_dir)
        ext = transpiler._get_generator().file_extension()
        output_file = output_dir / rel_path.with_suffix(ext)

        if compile_file(q_file, output_file, transpiler, check_only, quiet, verbose):
            compiled += 1
        else:
            errors += 1

    if not quiet:
        print(f"\nCompiled {compiled} file(s), {errors} error(s)")

    return errors


def watch_directory(
    source_dir: Path,
    output_dir: Path,
    transpiler: Transpiler,
    quiet: bool = False,
    verbose: bool = False
):
    """Watch directory for changes and recompile."""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent
    except ImportError:
        print("ERROR: watchdog package required for --watch")
        print("  Install: pip install watchdog")
        sys.exit(1)

    class QuantumHandler(FileSystemEventHandler):
        def on_modified(self, event):
            if event.is_directory:
                return
            if event.src_path.endswith('.q'):
                self._compile(Path(event.src_path))

        def on_created(self, event):
            if event.is_directory:
                return
            if event.src_path.endswith('.q'):
                self._compile(Path(event.src_path))

        def _compile(self, q_file: Path):
            rel_path = q_file.relative_to(source_dir)
            ext = transpiler._get_generator().file_extension()
            output_file = output_dir / rel_path.with_suffix(ext)
            compile_file(q_file, output_file, transpiler, False, quiet, verbose)

    # Initial compile
    print("Initial compilation...")
    compile_directory(source_dir, output_dir, transpiler, False, quiet, verbose)

    # Start watching
    print(f"\nWatching {source_dir} for changes... (Ctrl+C to stop)")

    observer = Observer()
    observer.schedule(QuantumHandler(), str(source_dir), recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped.")

    observer.join()


def main(argv=None):
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Normalize target
    target = args.target
    if target == 'js':
        target = 'javascript'

    # Create transpiler
    transpiler = Transpiler(
        target=target,
        optimize=args.optimize,
        sourcemap=args.sourcemap,
        strict=args.strict
    )

    source = Path(args.source)

    if not source.exists():
        print(f"ERROR: Source not found: {source}")
        sys.exit(1)

    if source.is_file():
        # Single file
        output = Path(args.output) if args.output else None
        success = compile_file(
            source, output, transpiler,
            args.check, args.quiet, args.verbose
        )
        sys.exit(0 if success else 1)

    elif source.is_dir():
        # Directory
        if not args.output:
            output_dir = source.parent / (source.name + '_compiled')
        else:
            output_dir = Path(args.output)

        if args.watch:
            watch_directory(source, output_dir, transpiler, args.quiet, args.verbose)
        else:
            errors = compile_directory(
                source, output_dir, transpiler,
                args.check, args.quiet, args.verbose
            )
            sys.exit(1 if errors > 0 else 0)


if __name__ == '__main__':
    main()
