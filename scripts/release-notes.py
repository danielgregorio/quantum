"""Print the CHANGELOG.md section for a version; exit 1 if there is none.

    python scripts/release-notes.py 0.10.0 > release_notes.md

Used by the release workflow twice: the build job refuses to publish a version
that has no changelog section, and the GitHub Release uses the section as its
text. Pre-1.0 versions may break compatibility, so "what changed" is part of
the release, not an afterthought.
"""
import pathlib
import re
import sys


def section(version: str, text: str):
    match = re.search(rf'^## {re.escape(version)}[ \t]*\n(.*?)(?=^## |\Z)', text, re.S | re.M)
    return match.group(1).strip() if match else None


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: release-notes.py <version>", file=sys.stderr)
        return 2
    version = sys.argv[1].lstrip('v')
    changelog = pathlib.Path(__file__).resolve().parent.parent / 'CHANGELOG.md'
    notes = section(version, changelog.read_text(encoding='utf-8'))
    if not notes:
        print(f"CHANGELOG.md has no '## {version}' section. Write what changed "
              f"before releasing it.", file=sys.stderr)
        return 1
    sys.stdout.reconfigure(encoding='utf-8')
    print(notes)
    return 0


if __name__ == '__main__':
    sys.exit(main())
