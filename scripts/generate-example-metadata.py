#!/usr/bin/env python3
"""
Quantum Examples Metadata Generator

Scans the examples/ folder and generates JSON metadata files for the VitePress gallery.
Extracts features, complexity, and descriptions from .q files.

Usage:
    python scripts/generate-example-metadata.py

Output:
    examples/_metadata/index.json         - Master category index
    examples/_metadata/{category}.json    - Per-category metadata
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict


# Category definitions
CATEGORIES = {
    "state-management": {
        "name": "State Management",
        "description": "Variables, data binding, and state operations with q:set",
        "icon": "📦",
        "docsPath": "/guide/state-management",
        "patterns": ["test-set-", "test-databinding-"],
        "tags": ["q:set", "databinding", "variables"]
    },
    "loops": {
        "name": "Loops",
        "description": "Iteration with q:loop - arrays, ranges, and lists",
        "icon": "🔄",
        "docsPath": "/guide/loops",
        "patterns": ["test-loop-"],
        "tags": ["q:loop", "iteration", "arrays"]
    },
    "conditionals": {
        "name": "Conditionals",
        "description": "Conditional logic with q:if, q:else, and q:elseif",
        "icon": "🔀",
        "docsPath": "/guide/conditionals",
        "patterns": ["test-if-", "test-else", "test-conditionals", "test-false-"],
        "tags": ["q:if", "q:else", "q:elseif", "conditionals"]
    },
    "functions": {
        "name": "Functions",
        "description": "Reusable logic with q:function and q:invoke",
        "icon": "⚡",
        "docsPath": "/guide/functions",
        "patterns": ["test-function-", "test-invoke-"],
        "tags": ["q:function", "q:invoke", "functions"]
    },
    "queries": {
        "name": "Database Queries",
        "description": "Database operations with q:query and transactions",
        "icon": "🗄️",
        "docsPath": "/guide/query",
        "patterns": ["test-query-", "test-transaction-"],
        "tags": ["q:query", "database", "SQL"]
    },
    "forms-actions": {
        "name": "Forms & Actions",
        "description": "Form handling, validation, and user actions",
        "icon": "📝",
        "docsPath": "/guide/actions",
        "patterns": ["test-action-", "form_validation", "test-upload-"],
        "tags": ["q:action", "forms", "validation"]
    },
    "authentication": {
        "name": "Authentication",
        "description": "Login, logout, roles, and protected routes",
        "icon": "🔐",
        "docsPath": "/guide/authentication",
        "patterns": ["test-auth-"],
        "tags": ["q:auth", "authentication", "security"]
    },
    "agents": {
        "name": "AI Agents",
        "description": "AI agents with q:agent, tools, and multi-agent teams",
        "icon": "🤖",
        "docsPath": "/guide/agents",
        "patterns": ["agent_", "multi_agent", "rag", "llm_", "quantum-assistant"],
        "tags": ["q:agent", "q:team", "AI", "LLM"]
    },
    "ui-theming": {
        "name": "UI & Theming",
        "description": "UI components, themes, and animations",
        "icon": "🎨",
        "docsPath": "/ui/overview",
        "patterns": ["test-ui-", "animations_", "component_library", "dashboard"],
        "tags": ["ui:", "theming", "components"]
    },
    "games": {
        "name": "Games",
        "description": "Game development with qg:scene, sprites, and physics",
        "icon": "🎮",
        "docsPath": "/features/game-engine",
        "patterns": ["snake", "mario", "platformer", "tower_defense", "tictactoe", "adventure", "fighter", "kenney_"],
        "tags": ["qg:scene", "qg:sprite", "games"]
    },
    "data-import": {
        "name": "Data Import",
        "description": "Loading data from CSV, JSON, and XML files",
        "icon": "📊",
        "docsPath": "/guide/data-import",
        "patterns": ["test-data-"],
        "tags": ["q:data", "CSV", "JSON", "XML"]
    },
    "advanced": {
        "name": "Advanced",
        "description": "Complex examples combining multiple features",
        "icon": "🚀",
        "docsPath": "/architecture/",
        "patterns": ["complete-test", "webapp", "api", "chat", "job_", "message_", "python-"],
        "tags": ["advanced", "multi-feature"]
    }
}

# Feature detection patterns
FEATURE_PATTERNS = {
    "q:set": r"<q:set\b",
    "q:loop": r"<q:loop\b",
    "q:if": r"<q:if\b",
    "q:else": r"<q:else\b",
    "q:elseif": r"<q:elseif\b",
    "q:function": r"<q:function\b",
    "q:invoke": r"<q:invoke\b",
    "q:query": r"<q:query\b",
    "q:action": r"<q:action\b",
    "q:auth": r"<q:auth\b",
    "q:agent": r"<q:agent\b",
    "q:team": r"<q:team\b",
    "q:tool": r"<q:tool\b",
    "q:mail": r"<q:mail\b",
    "q:file": r"<q:file\b",
    "q:fetch": r"<q:fetch\b",
    "q:data": r"<q:data\b",
    "q:return": r"<q:return\b",
    "q:param": r"<q:param\b",
    "q:application": r"<q:application\b",
    "q:route": r"<q:route\b",
    "q:transaction": r"<q:transaction\b",
    "q:log": r"<q:log\b",
    "q:dump": r"<q:dump\b",
    "qg:scene": r"<qg:scene\b",
    "qg:sprite": r"<qg:sprite\b",
    "qg:timer": r"<qg:timer\b",
    "qg:input": r"<qg:input\b",
    "qg:hud": r"<qg:hud\b",
    "ui:": r"<ui:\w+",
    "htmx": r"<q:island\b|hx-",
    "session": r"session\.",
    "application_scope": r"application\.",
    "databinding": r"\{[^}]+\}",
}


@dataclass
class ExampleMetadata:
    """Metadata for a single example file."""
    file: str
    title: str
    description: str
    complexity: str  # beginner, intermediate, advanced
    tags: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    relatedDocs: List[str] = field(default_factory=list)
    lineCount: int = 0


def extract_title_from_filename(filename: str) -> str:
    """Convert filename to human-readable title."""
    name = filename.replace(".q", "")
    name = name.replace("test-", "").replace("_", " ").replace("-", " ")
    return name.title()


def extract_description_from_content(content: str, filename: str) -> str:
    """Extract description from file comments or generate one."""
    # Look for structured comment with @description
    desc_match = re.search(r'@description:\s*(.+?)(?:\n|-->)', content, re.IGNORECASE)
    if desc_match:
        return desc_match.group(1).strip()

    # Look for XML comment at the start
    comment_match = re.search(r'<!--\s*(.+?)\s*-->', content)
    if comment_match:
        desc = comment_match.group(1).strip()
        # Skip if it's just the filename or very short
        if len(desc) > 10 and "test" not in desc.lower()[:10]:
            return desc

    # Look for multi-line header comment
    header_match = re.search(r'<!--\s*\n\s*(.+?)\n', content)
    if header_match:
        return header_match.group(1).strip()

    # Generate description based on features detected
    return f"Example demonstrating {extract_title_from_filename(filename)}"


def detect_features(content: str) -> List[str]:
    """Detect Quantum features used in the file."""
    features = []
    for feature, pattern in FEATURE_PATTERNS.items():
        if re.search(pattern, content):
            features.append(feature)
    return sorted(features)


def calculate_complexity(content: str, features: List[str]) -> str:
    """Calculate example complexity based on content analysis."""
    line_count = len(content.split('\n'))
    feature_count = len(features)

    # Advanced indicators
    advanced_features = ["q:agent", "q:team", "q:transaction", "qg:scene", "q:application"]
    has_advanced = any(f in features for f in advanced_features)

    if has_advanced or line_count > 150 or feature_count > 8:
        return "advanced"
    elif line_count > 50 or feature_count > 4:
        return "intermediate"
    else:
        return "beginner"


def categorize_example(filename: str, features: List[str]) -> str:
    """Determine which category an example belongs to."""
    # Check filename patterns first
    for cat_id, cat_info in CATEGORIES.items():
        for pattern in cat_info["patterns"]:
            if pattern in filename.lower():
                return cat_id

    # Check features as fallback
    if "qg:scene" in features or "qg:sprite" in features:
        return "games"
    if "q:agent" in features or "q:team" in features:
        return "agents"
    if "q:query" in features:
        return "queries"
    if "q:function" in features and len(features) <= 3:
        return "functions"
    if "q:loop" in features and len(features) <= 3:
        return "loops"
    if "q:if" in features and len(features) <= 3:
        return "conditionals"
    if "q:set" in features and len(features) <= 3:
        return "state-management"

    return "advanced"


def process_example_file(filepath: Path) -> Optional[ExampleMetadata]:
    """Process a single .q file and extract metadata."""
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  Warning: Could not read {filepath}: {e}")
        return None

    filename = filepath.name
    features = detect_features(content)
    complexity = calculate_complexity(content, features)
    category = categorize_example(filename, features)

    # Extract title from @title comment or filename
    title_match = re.search(r'@title:\s*(.+?)(?:\n|-->)', content, re.IGNORECASE)
    if title_match:
        title = title_match.group(1).strip()
    else:
        title = extract_title_from_filename(filename)

    description = extract_description_from_content(content, filename)

    # Build tags from features and category
    tags = list(set(features[:5] + CATEGORIES.get(category, {}).get("tags", [])[:3]))

    # Related docs
    related_docs = []
    if category in CATEGORIES:
        related_docs.append(CATEGORIES[category]["docsPath"])

    return ExampleMetadata(
        file=filename,
        title=title,
        description=description,
        complexity=complexity,
        tags=tags,
        features=features,
        relatedDocs=related_docs,
        lineCount=len(content.split('\n'))
    )


def generate_metadata(examples_dir: Path, output_dir: Path):
    """Generate all metadata files."""
    print(f"Scanning examples in: {examples_dir}")

    # Collect all examples
    examples_by_category: Dict[str, List[ExampleMetadata]] = defaultdict(list)
    all_examples: List[ExampleMetadata] = []

    q_files = list(examples_dir.glob("*.q"))
    print(f"Found {len(q_files)} .q files")

    for filepath in sorted(q_files):
        metadata = process_example_file(filepath)
        if metadata:
            category = categorize_example(filepath.name, metadata.features)
            examples_by_category[category].append(metadata)
            all_examples.append(metadata)
            print(f"  {filepath.name} -> {category} ({metadata.complexity})")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate master index
    index = {
        "version": "1.0",
        "generated": True,
        "totalExamples": len(all_examples),
        "categories": []
    }

    for cat_id, cat_info in CATEGORIES.items():
        cat_examples = examples_by_category.get(cat_id, [])
        if cat_examples:  # Only include categories with examples
            index["categories"].append({
                "id": cat_id,
                "name": cat_info["name"],
                "description": cat_info["description"],
                "icon": cat_info["icon"],
                "docsPath": cat_info["docsPath"],
                "exampleCount": len(cat_examples),
                "examples": [ex.file for ex in cat_examples]
            })

    index_path = output_dir / "index.json"
    index_path.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGenerated: {index_path}")

    # Generate per-category files
    for cat_id, cat_info in CATEGORIES.items():
        cat_examples = examples_by_category.get(cat_id, [])
        if not cat_examples:
            continue

        cat_data = {
            "category": cat_id,
            "name": cat_info["name"],
            "description": cat_info["description"],
            "icon": cat_info["icon"],
            "docsPath": cat_info["docsPath"],
            "exampleCount": len(cat_examples),
            "examples": [asdict(ex) for ex in cat_examples]
        }

        cat_path = output_dir / f"{cat_id}.json"
        cat_path.write_text(json.dumps(cat_data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Generated: {cat_path} ({len(cat_examples)} examples)")

    print(f"\nTotal: {len(all_examples)} examples across {len(examples_by_category)} categories")


def main():
    # Determine paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    examples_dir = project_root / "examples"
    output_dir = examples_dir / "_metadata"

    if not examples_dir.exists():
        print(f"Error: Examples directory not found: {examples_dir}")
        return 1

    generate_metadata(examples_dir, output_dir)
    return 0


if __name__ == "__main__":
    exit(main())
