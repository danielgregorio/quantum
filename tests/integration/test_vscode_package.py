"""The VS Code extension packages: every file its manifest names is there.

`vsce package` stopped on an icon that was never committed. It runs with npm,
which the Python suite does not; this holds the part that broke.
"""

import json
from pathlib import Path

EXTENSION = Path(__file__).resolve().parents[2] / 'vscode-quantum'


def _paths(node):
    # Every "icon", "path" and "language configuration" that names a file.
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ('icon', 'path', 'configuration') and isinstance(value, str) \
                    and not value.startswith('$('):
                yield value
            else:
                yield from _paths(value)
    elif isinstance(node, list):
        for item in node:
            yield from _paths(item)


def test_every_file_the_manifest_names_exists():
    manifest = json.loads((EXTENSION / 'package.json').read_text(encoding='utf-8'))
    named = sorted(set(_paths(manifest)))
    assert 'images/quantum-icon.png' in named
    missing = [p for p in named if not (EXTENSION / p).is_file()]
    assert not missing, f'named in vscode-quantum/package.json but not in the repository: {missing}'


def test_the_package_carries_the_license():
    assert (EXTENSION / 'LICENSE').read_text(encoding='utf-8').startswith('MIT')
