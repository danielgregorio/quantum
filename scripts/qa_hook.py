#!/usr/bin/env python3
"""
QA hook for Quantum features.

Detects modified features (via git diff or direct invocation) and analyses
their test coverage.  Designed to run as a git pre-commit hook (warns but
does NOT block commits) or standalone.

Usage:
    python scripts/qa_hook.py                  # Analyse staged features
    python scripts/qa_hook.py --feature loops  # Analyse a specific feature
    python scripts/qa_hook.py --all            # Analyse every feature
"""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEATURES_DIR = ROOT / "src" / "core" / "features"
EXAMPLES_DIR = ROOT / "examples"


def git_staged_files() -> list[str]:
    """Return list of staged file paths (relative to repo root)."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        return result.stdout.strip().splitlines()
    except Exception:
        return []


def detect_modified_features(files: list[str]) -> set[str]:
    """Extract feature names from a list of changed paths."""
    features = set()
    for f in files:
        parts = Path(f).parts
        # src/core/features/{name}/...
        if len(parts) >= 4 and parts[0] == "src" and parts[2] == "features":
            features.add(parts[3])
    return features


def analyse_feature(name: str) -> dict:
    """Compute QA score (0-6) for a feature."""
    feat_dir = FEATURES_DIR / name
    if not feat_dir.is_dir():
        return {"name": name, "exists": False, "score": 0}

    manifest = (feat_dir / "manifest.yaml").exists()
    intent = (feat_dir / "intentions" / "primary.intent").exists()

    pos_dir = feat_dir / "dataset" / "positive"
    neg_dir = feat_dir / "dataset" / "negative"
    n_positive = len(list(pos_dir.glob("*.json"))) if pos_dir.is_dir() else 0
    n_negative = len(list(neg_dir.glob("*.json"))) if neg_dir.is_dir() else 0

    # Count regression .q files (heuristic: feature name or tag prefix)
    q_files = []
    if EXAMPLES_DIR.is_dir():
        tag = _feature_to_tag(name)
        q_files = list(EXAMPLES_DIR.glob(f"test-{tag}-*.q"))

    qa_spec = (feat_dir / "qa_spec.yaml").exists()

    score = sum([
        manifest,
        intent,
        n_positive >= 1,
        n_negative >= 1,
        len(q_files) >= 1,
        qa_spec,
    ])

    return {
        "name": name,
        "exists": True,
        "score": score,
        "manifest": manifest,
        "intent": intent,
        "positive_datasets": n_positive,
        "negative_datasets": n_negative,
        "q_files": len(q_files),
        "qa_spec": qa_spec,
    }


def _feature_to_tag(feature_name: str) -> str:
    """Convert feature directory name to .q file prefix tag.

    e.g. state_management -> set, forms_actions -> action, etc.
    """
    mapping = {
        "state_management": "set",
        "forms_actions": "action",
        "conditionals": "if",
        "loops": "loop",
        "functions": "function",
        "query": "query",
        "session_management": "session",
        "authentication": "auth",
        "file_uploads": "upload",
        "email_sending": "email",
        "htmx_partials": "htmx",
        "islands_architecture": "island",
        "invocation": "invoke",
        "data_import": "data",
        "logging": "log",
        "dump": "dump",
        "database_backend": "transaction",
        "developer_experience": "dump",
    }
    return mapping.get(feature_name, feature_name.split("_")[0])


def print_report(results: list[dict]):
    """Print a human-readable QA report."""
    print("\n" + "=" * 60)
    print("QUANTUM QA COVERAGE REPORT")
    print("=" * 60)

    for r in results:
        if not r["exists"]:
            print(f"\n  {r['name']}: directory not found")
            continue

        score = r["score"]
        icon = "OK" if score >= 5 else ("WARN" if score >= 3 else "LOW")
        print(f"\n  [{icon}] {r['name']}  score={score}/6")
        print(f"        manifest={r['manifest']}  intent={r['intent']}")
        print(f"        datasets: {r['positive_datasets']}+ / {r['negative_datasets']}-")
        print(f"        regression .q: {r['q_files']}  qa_spec: {r['qa_spec']}")

        if score < 5 and not r["qa_spec"]:
            print(f"        -> Sugestao: rode /qa {r['name']} para gerar qa_spec.yaml")

    print("\n" + "=" * 60)

    low = [r for r in results if r.get("score", 0) < 3]
    if low:
        print(f"ATENCAO: {len(low)} feature(s) com score < 3: {', '.join(r['name'] for r in low)}")
    else:
        print("Todas as features analisadas tem score >= 3.")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Quantum QA coverage hook")
    parser.add_argument("--feature", type=str, help="Analyse a specific feature")
    parser.add_argument("--all", action="store_true", help="Analyse all features")
    args = parser.parse_args()

    if args.feature:
        features = {args.feature}
    elif args.all:
        features = {d.name for d in FEATURES_DIR.iterdir() if d.is_dir() and not d.name.startswith("_")}
    else:
        # Detect from staged git files
        staged = git_staged_files()
        features = detect_modified_features(staged)
        if not features:
            print("[QA Hook] No feature changes detected in staged files.")
            sys.exit(0)

    results = [analyse_feature(f) for f in sorted(features)]
    print_report(results)

    # Non-blocking exit (always 0) – this is a warning-only hook
    sys.exit(0)


if __name__ == "__main__":
    main()
