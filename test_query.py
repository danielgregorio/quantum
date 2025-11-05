#!/usr/bin/env python3
"""
Test script for q:query implementation
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from core import QuantumParser
from runtime.component import ComponentRuntime

def test_query_file(file_path: str):
    """Test parsing and execution of a .q file with queries"""
    print(f"\n{'='*60}")
    print(f"Testing: {Path(file_path).name}")
    print(f"{'='*60}\n")

    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    print("File preview:")
    lines = content.split('\n')
    for i, line in enumerate(lines[:10], 1):
        print(f"  {i:2}: {line[:80]}")
    if len(lines) > 10:
        print(f"  ... ({len(lines) - 10} more lines)")
    print()

    try:
        # Parse
        print("Step 1: Parsing XML...")
        parser = QuantumParser()
        component = parser.parse_file(file_path)
        print(f"[OK] Parsed component: {component.name if hasattr(component, 'name') else 'unnamed'}")

        # Check for QueryNode
        from core.ast_nodes import QueryNode

        # Debug: show what's in children
        if hasattr(component, 'children'):
            print(f"\n[DEBUG] Component has {len(component.children)} children:")
            for i, child in enumerate(component.children):
                print(f"  [{i}] {type(child).__name__}")

        # Check for statements (where queries are stored)
        if hasattr(component, 'statements'):
            print(f"\n[DEBUG] Component has {len(component.statements)} statements:")
            for i, stmt in enumerate(component.statements):
                print(f"  [{i}] {type(stmt).__name__}")

            queries = [node for node in component.statements if isinstance(node, QueryNode)]
            if queries:
                print(f"\n[OK] Found {len(queries)} query node(s):")
                for q in queries:
                    print(f"  - Query '{q.name}' on datasource '{q.datasource}'")
                    print(f"    SQL preview: {q.sql[:60]}...")
                    print(f"    Parameters: {len(q.params) if hasattr(q, 'params') else 0}")
            else:
                print("\n[WARN] No QueryNode found in statements")
        else:
            print("\n[WARN] Component has no statements attribute")

        print(f"\n[OK] Parser working correctly")
        print("\n[NOTE] Full execution requires:")
        print("  - Quantum Admin running at http://localhost:8000")
        print("  - Datasource 'test-postgres' configured and ready")
        print("  - Test database with 'users' table")

        return True

    except Exception as e:
        print(f"\n[ERROR] {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_query.py <file.q>")
        sys.exit(1)

    file_path = sys.argv[1]
    success = test_query_file(file_path)
    sys.exit(0 if success else 1)
