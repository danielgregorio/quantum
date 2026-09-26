#!/usr/bin/env python3
"""The playground's examples: the Cookbook's recipes, as the playground loads them.

Writes docs/public/playground/recipes.json — each recipe's files (as in
examples/cookbook/<topic>/<name>/, without its generated output/), its title
from its Cookbook page, and the page the preview opens first (the page its
first test visits, or its tests for a recipe about testing).

The AI recipes stay out: they need a model, and the playground runs in the
visitor's browser with none. tests/docs/test_playground.py fails when the file
is stale, and runs every recipe here through the playground's bridge.

    python scripts/generate-playground.py
"""

import importlib.util
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
RECIPES = REPO / 'examples' / 'cookbook'
PAGES = REPO / 'docs' / 'cookbook'
OUT = REPO / 'docs' / 'public' / 'playground' / 'recipes.json'
LEFT_OUT = {'ai'}
_FIRST_PAGE = re.compile(r'<q:test\b[^>]*\bpage="([^"]+)"')


def _cookbook():
    spec = importlib.util.spec_from_file_location('generate_cookbook', REPO / 'scripts' / 'generate-cookbook.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _files(recipe: pathlib.Path) -> dict:
    return {p.relative_to(recipe).as_posix(): p.read_text(encoding='utf-8').replace('\r\n', '\n')
            for p in sorted(recipe.rglob('*'))
            if p.is_file() and 'output' not in p.relative_to(recipe).parts}


def _start(files: dict) -> str:
    for name in sorted(files):
        if name.endswith('.test.q'):
            match = _FIRST_PAGE.search(files[name])
            if match:
                return match.group(1)
    return '/'


def build() -> str:
    cookbook = _cookbook()
    topics = []
    for topic, title in cookbook.TOPICS.items():
        if topic in LEFT_OUT:
            continue
        entries = []
        for recipe in sorted((RECIPES / topic).glob('*/quantum.config.yaml')):
            recipe = recipe.parent
            page = PAGES / topic / f'{recipe.name}.md'
            meta = cookbook.front_matter(page.read_text(encoding='utf-8').replace('\r\n', '\n'))
            files = _files(recipe)
            entries.append({
                'id': f'{topic}/{recipe.name}',
                'title': meta.get('title', recipe.name),
                'description': meta.get('description', ''),
                'order': int(meta.get('order', 99)),
                'cookbook': f'/cookbook/{topic}/{recipe.name}',
                'start': _start(files),
                # A testing recipe is about its tests: the playground opens on them.
                'view': 'tests' if topic == 'testing' else 'preview',
                'files': files,
            })
        entries.sort(key=lambda e: (e['order'], e['id']))
        for e in entries:
            del e['order']
        topics.append({'topic': topic, 'title': title, 'recipes': entries})
    return json.dumps({'topics': topics}, ensure_ascii=False, indent=1) + '\n'


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build(), encoding='utf-8', newline='\n')
    count = sum(len(t['recipes']) for t in json.loads(OUT.read_text(encoding='utf-8'))['topics'])
    print(f'{OUT.relative_to(REPO).as_posix()}: {count} recipes')
    return 0


if __name__ == '__main__':
    sys.exit(main())
