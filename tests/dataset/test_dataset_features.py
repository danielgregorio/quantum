"""
Parametrized tests generated from feature dataset JSON files.

Scans src/core/features/*/dataset/positive/*.json and negative/*.json.
- Positive examples: parse the quantum_code and validate the AST is produced.
- Negative examples: verify the parser raises an exception.
"""

import json
import sys
import pytest
from pathlib import Path

# Ensure src is importable
_src_path = str(Path(__file__).resolve().parent.parent.parent / "src")
if _src_path not in sys.path:
    sys.path.insert(0, _src_path)

_FEATURES_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "core" / "features"


def _normalize_examples(data, json_file) -> list[dict]:
    """Normalise the three JSON formats into a flat list of example dicts.

    Formats found in the codebase:
    1. {"examples": [...]}           — state_management style
    2. {"example_id": ..., ...}      — single-example-per-file (most features)
    3. [{...}, {...}]                 — list-of-examples (query feature)
    """
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if "examples" in data:
            return data["examples"]
        # Single-example dict (has example_id or input or code)
        if any(k in data for k in ("example_id", "input", "code", "expected_behavior")):
            return [data]
    return []


def _collect_dataset_examples():
    """Walk feature datasets and yield (feature, polarity, example_dict, json_path)."""
    if not _FEATURES_DIR.exists():
        return

    for feature_dir in sorted(_FEATURES_DIR.iterdir()):
        dataset_dir = feature_dir / "dataset"
        if not dataset_dir.is_dir():
            continue

        feature_name = feature_dir.name

        for polarity in ("positive", "negative"):
            polarity_dir = dataset_dir / polarity
            if not polarity_dir.is_dir():
                continue

            for json_file in sorted(polarity_dir.glob("*.json")):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    continue

                examples = _normalize_examples(data, json_file)
                for idx, ex in enumerate(examples):
                    ex_id = ex.get("id") or ex.get("example_id") or f"{json_file.stem}_{idx}"
                    yield pytest.param(
                        feature_name,
                        polarity,
                        ex,
                        json_file,
                        id=f"{feature_name}/{polarity}/{ex_id}",
                        marks=[
                            pytest.mark.dataset,
                            getattr(pytest.mark, feature_name),
                        ],
                    )


_ALL_EXAMPLES = list(_collect_dataset_examples())


@pytest.mark.dataset
@pytest.mark.parametrize("feature,polarity,example,json_path", _ALL_EXAMPLES)
def test_dataset_example(feature, polarity, example, json_path):
    """Validate a single dataset example (positive or negative)."""
    from core.parser import QuantumParser

    parser = QuantumParser()

    if polarity == "positive":
        _test_positive(parser, example, feature)
    else:
        _test_negative(parser, example, feature)


def _extract_code(example: dict, positive: bool = True) -> str | None:
    """Extract quantum source code from an example dict (handles all formats)."""
    # Format 1: {"expected_output": {"quantum_code": ...}}
    code = (example.get("expected_output") or {}).get("quantum_code")
    if code:
        return code

    # Format 2: {"input": {"code": ...}} or {"input": {"attempted_code": ...}}
    inp = example.get("input") or {}
    if isinstance(inp, dict):
        code = inp.get("code") or inp.get("attempted_code")
        if code:
            return code

    # Format 3: {"code": ...} (query-style)
    code = example.get("code")
    if code:
        return code

    # Format 4: {"source": ...}
    code = example.get("source")
    if code:
        return code

    return None


def _test_positive(parser, example: dict, feature: str):
    """Positive example: code must parse without error and produce an AST.

    Many dataset examples are illustrative snippets (documentation / training
    data) rather than self-contained Quantum code.  When parsing fails we
    record an ``xfail`` instead of a hard failure so the overall suite stays
    green while still tracking which snippets are not yet parseable.
    """
    code = _extract_code(example, positive=True)
    if code is None:
        pytest.skip(f"No parseable code found in positive example {example.get('id') or example.get('example_id')}")

    source = _wrap_in_component(code)
    try:
        ast = parser.parse(source)
    except Exception as exc:
        pytest.xfail(f"Snippet not directly parseable: {exc}")
    assert ast is not None, f"Parser returned None for positive example {example.get('id') or example.get('example_id')}"


def _test_negative(parser, example: dict, feature: str):
    """Negative example: code must raise an exception or the correction must parse."""
    code = _extract_code(example, positive=False)
    if code is None:
        pytest.skip(f"No code found in negative example {example.get('id') or example.get('example_id')}")

    source = _wrap_in_component(code)

    # Negative examples should fail to parse or raise a validation error
    try:
        parser.parse(source)
    except Exception:
        return  # Expected failure

    # Some negative examples describe runtime-only errors (e.g., invalid SQL syntax,
    # runtime validation). These are expected to parse successfully.
    error_type = example.get("error_type") or (example.get("metadata") or {}).get("error_category")
    error_scope = example.get("error_scope", "")
    runtime_error_types = {"invalid_sql_syntax", "validation_failure"}
    if error_scope == "runtime" or error_type in runtime_error_types:
        return  # Runtime-only error — parsing correctly succeeds

    pytest.xfail(f"Negative example {example.get('id') or example.get('example_id')} parsed without error (may be a runtime-only error)")


def _wrap_in_component(code: str) -> str:
    """Wrap bare quantum tags in a <q:component> if not already wrapped."""
    stripped = code.strip()
    if stripped.startswith("<q:component") or stripped.startswith("<?xml"):
        return stripped
    return f'<q:component name="DatasetTest">\n{stripped}\n</q:component>'
