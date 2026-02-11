#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Example Outputs - Execute .q examples and capture their output.

This script:
1. Reads metadata JSON files from examples/_metadata/
2. For each example, parses and executes the .q file
3. Captures the return value or error
4. Updates the metadata JSON with output and sourceCode fields

Usage:
    python scripts/generate-example-outputs.py
    python scripts/generate-example-outputs.py --category state-management
    python scripts/generate-example-outputs.py --dry-run
"""

import sys
import os
import json
import signal
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from contextlib import contextmanager
from dataclasses import dataclass

# Fix imports
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.parser import QuantumParser, QuantumParseError
from runtime.component import ComponentRuntime, ComponentExecutionError

# Categories that should be skipped (need external services)
SKIP_CATEGORIES = {
    "queries",       # Needs database
    "authentication", # Needs session/auth
    "games",         # Large HTML output
    "agents",        # Needs LLM services
}

# Individual files to skip (need external resources)
SKIP_FILES = {
    # Email examples
    "test-email-basic.q",
    "test-email-html.q",
    "test-email-recipients.q",
    # HTMX/session examples
    "test-htmx-partial.q",
    "test-htmx-swap.q",
    "test-htmx-trigger.q",
    # Session/application scope
    "test-session-scope.q",
    "test-application-scope.q",
    "test-request-scope.q",
    "test-set-all-scopes.q",
    # Island/interactive examples
    "test-island-events.q",
    "test-island-interactive.q",
    # HTTP invoke examples
    "test-invoke-http-get.q",
    "test-invoke-http-post.q",
    "test-function-rest-api.q",
    # Data import (needs files)
    "test-data-csv-simple.q",
    "test-data-json-simple.q",
    "test-data-xml-simple.q",
    "test-data-transform-compute.q",
    "test-data-transform-filter.q",
    "test-data-transform-limit.q",
    "test-data-transform-sort.q",
}

# Timeout for each example execution (seconds)
EXECUTION_TIMEOUT = 5

# Maximum output length before truncation
MAX_OUTPUT_LENGTH = 500


@dataclass
class ExampleOutput:
    """Result of executing an example"""
    output: str
    output_type: str  # "text", "json", "error", "html"
    source_code: str


class TimeoutError(Exception):
    """Execution timeout"""
    pass


@contextmanager
def timeout(seconds: int):
    """Context manager for execution timeout (Unix only)"""
    def handler(signum, frame):
        raise TimeoutError(f"Execution timed out after {seconds}s")

    if os.name != 'nt':  # Unix
        old_handler = signal.signal(signal.SIGALRM, handler)
        signal.alarm(seconds)
        try:
            yield
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)
    else:  # Windows - no signal support, run without timeout
        yield


def read_source_code(file_path: Path) -> str:
    """Read the source code from a .q file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"(Could not read source: {e})"


def execute_example(file_path: Path) -> ExampleOutput:
    """Execute a .q file and capture its output"""
    source_code = read_source_code(file_path)

    try:
        # Parse the file
        parser = QuantumParser()
        ast = parser.parse_file(str(file_path))

        # Execute the component
        runtime = ComponentRuntime()

        try:
            with timeout(EXECUTION_TIMEOUT):
                result = runtime.execute_component(ast)
        except TimeoutError as e:
            return ExampleOutput(
                output=f"Timeout: {str(e)}",
                output_type="error",
                source_code=source_code
            )

        # Determine output type and format
        if result is None:
            return ExampleOutput(
                output="(no output)",
                output_type="text",
                source_code=source_code
            )

        if isinstance(result, (dict, list)):
            try:
                output = json.dumps(result, indent=2, ensure_ascii=False)
                output_type = "json"
            except (TypeError, ValueError):
                output = str(result)
                output_type = "text"
        elif isinstance(result, str):
            output = result
            # Check if it looks like HTML
            if result.strip().startswith('<') and '>' in result:
                output_type = "html"
            else:
                output_type = "text"
        else:
            output = str(result)
            output_type = "text"

        # Truncate if too long
        if len(output) > MAX_OUTPUT_LENGTH:
            output = output[:MAX_OUTPUT_LENGTH] + "\n... (truncated)"

        return ExampleOutput(
            output=output,
            output_type=output_type,
            source_code=source_code
        )

    except QuantumParseError as e:
        return ExampleOutput(
            output=f"Parse Error: {str(e)[:200]}",
            output_type="error",
            source_code=source_code
        )
    except ComponentExecutionError as e:
        return ExampleOutput(
            output=f"Execution Error: {str(e)[:200]}",
            output_type="error",
            source_code=source_code
        )
    except Exception as e:
        return ExampleOutput(
            output=f"Error: {type(e).__name__}: {str(e)[:200]}",
            output_type="error",
            source_code=source_code
        )


def process_category(category_file: Path, examples_dir: Path, dry_run: bool = False) -> Dict[str, int]:
    """Process all examples in a category"""
    stats = {"processed": 0, "skipped": 0, "errors": 0}

    try:
        with open(category_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
    except Exception as e:
        print(f"  Error reading {category_file.name}: {e}")
        return stats

    category_id = metadata.get("category", "")
    category_name = metadata.get("name", category_id)

    # Skip entire categories
    if category_id in SKIP_CATEGORIES:
        print(f"  Skipping category: {category_name} (requires external services)")
        stats["skipped"] = len(metadata.get("examples", []))
        return stats

    examples = metadata.get("examples", [])
    updated = False

    for example in examples:
        file_name = example.get("file", "")

        # Skip specific files
        if file_name in SKIP_FILES:
            print(f"    Skipping: {file_name}")
            stats["skipped"] += 1
            continue

        # Find the example file
        file_path = examples_dir / file_name
        if not file_path.exists():
            # Try subdirectory based on category
            file_path = examples_dir / category_id / file_name

        if not file_path.exists():
            print(f"    File not found: {file_name}")
            stats["errors"] += 1
            continue

        print(f"    Processing: {file_name}")

        if dry_run:
            stats["processed"] += 1
            continue

        # Execute and capture output
        result = execute_example(file_path)

        # Update metadata
        example["output"] = result.output
        example["outputType"] = result.output_type
        example["sourceCode"] = result.source_code
        updated = True

        if result.output_type == "error":
            stats["errors"] += 1
            print(f"      Error: {result.output[:50]}...")
        else:
            stats["processed"] += 1
            # Show preview of output
            preview = result.output.replace('\n', ' ')[:40]
            print(f"      Output: {preview}...")

    # Write updated metadata back
    if updated and not dry_run:
        try:
            with open(category_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            print(f"  Updated: {category_file.name}")
        except Exception as e:
            print(f"  Error writing {category_file.name}: {e}")

    return stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Generate example outputs")
    parser.add_argument("--category", "-c", help="Process only this category")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Don't write changes")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    metadata_dir = PROJECT_ROOT / "examples" / "_metadata"
    examples_dir = PROJECT_ROOT / "examples"

    if not metadata_dir.exists():
        print(f"Error: Metadata directory not found: {metadata_dir}")
        sys.exit(1)

    print("=" * 60)
    print("Quantum Example Output Generator")
    print("=" * 60)

    if args.dry_run:
        print("DRY RUN MODE - no files will be modified\n")

    total_stats = {"processed": 0, "skipped": 0, "errors": 0}

    # Process each category
    for category_file in sorted(metadata_dir.glob("*.json")):
        # Skip index.json
        if category_file.name == "index.json":
            continue

        # Filter by category if specified
        if args.category and not category_file.stem == args.category:
            continue

        print(f"\nCategory: {category_file.stem}")
        stats = process_category(category_file, examples_dir, args.dry_run)

        for key in total_stats:
            total_stats[key] += stats[key]

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    print(f"  Processed: {total_stats['processed']}")
    print(f"  Skipped:   {total_stats['skipped']}")
    print(f"  Errors:    {total_stats['errors']}")
    print(f"  Total:     {sum(total_stats.values())}")

    if not args.dry_run:
        print("\nMetadata files updated successfully!")

    return 0 if total_stats["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
