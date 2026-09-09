#!/usr/bin/env python3
"""
Recompile all Quantum MXML demos

This script recompiles all demo applications and updates the docs folder.
"""

import subprocess
import shutil
from pathlib import Path


DEMOS = [
    "hello",
    "databinding",
    "stopwatch",
    "components-demo",
    "nested-containers",
    "fase1-mvp-demo",
    "advanced-components",
    "enhanced-components-demo",
    "effects-demo",
    "formatters-demo",
    "ecommerce-admin",
    "quantum-integration-demo",
]


def recompile_demo(demo_name: str) -> bool:
    """Recompile a single demo"""
    mxml_file = Path(f"examples/{demo_name}.mxml")

    if not mxml_file.exists():
        print(f"  [SKIP] MXML file not found: {mxml_file}")
        return False

    print(f"\n[{DEMOS.index(demo_name) + 1}/{len(DEMOS)}] Recompiling: {demo_name}")
    print(f"  Source: {mxml_file}")

    try:
        # Run compiler
        result = subprocess.run(
            ["python", "quantum-mxml", "build", str(mxml_file)],
            capture_output=True,
            text=True,
            check=True
        )

        # Copy files to docs folder
        dist_dir = Path("dist")
        docs_dir = Path(f"docs/{demo_name}")

        if not docs_dir.exists():
            docs_dir.mkdir(parents=True)

        # Copy main files
        if (dist_dir / "app.js").exists():
            shutil.copy(dist_dir / "app.js", docs_dir / "app.js")

        if (dist_dir / "index.html").exists():
            shutil.copy(dist_dir / "index.html", docs_dir / "index.html")

        if (dist_dir / "styles.css").exists():
            shutil.copy(dist_dir / "styles.css", docs_dir / "styles.css")

        print(f"  [SUCCESS] Compiled and updated docs/{demo_name}/")
        return True

    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] Compilation failed:")
        print(e.stderr)
        return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def main():
    print("=" * 70)
    print("RECOMPILING ALL QUANTUM MXML DEMOS")
    print("=" * 70)
    print(f"\nTotal demos: {len(DEMOS)}")

    success_count = 0
    failed_demos = []

    for demo in DEMOS:
        if recompile_demo(demo):
            success_count += 1
        else:
            failed_demos.append(demo)

    print("\n" + "=" * 70)
    print("RECOMPILE SUMMARY")
    print("=" * 70)
    print(f"Success: {success_count}/{len(DEMOS)}")
    print(f"Failed: {len(failed_demos)}/{len(DEMOS)}")

    if failed_demos:
        print("\nFailed demos:")
        for demo in failed_demos:
            print(f"  - {demo}")

    print("=" * 70)


if __name__ == '__main__':
    main()
