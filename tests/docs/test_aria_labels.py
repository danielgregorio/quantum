"""Screen-reader labels in each language (docs/.vitepress/theme/aria-labels.js).

VitePress writes "Main Navigation", "Sidebar Navigation" and "Pager" in English;
the theme sets them from themeConfig.ariaLabels (locales.js) after each render.
Every language has the three labels, a label element that is missing is
skipped, and nothing throws.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
VITEPRESS = REPO / 'docs' / '.vitepress'
NODE = shutil.which('node')

pytestmark = pytest.mark.skipif(not NODE, reason='node is needed to run the site config')

SCRIPT = """
const { locales } = await import(%(locales)s);
const { applyAriaLabels } = await import(%(aria)s);
const labels = Object.fromEntries(Object.entries(locales()).map(([k, v]) => [k, v.themeConfig.ariaLabels]));
const nav = { textContent: 'Main Navigation' };
const doc = { getElementById: id => (id === 'main-nav-aria-label' ? nav : null) };
applyAriaLabels(doc, labels.pt);          // the sidebar and the pager are not on this page
applyAriaLabels(null, labels.pt);
applyAriaLabels({}, labels.pt);
applyAriaLabels(doc, undefined);
console.log(JSON.stringify({ labels, nav: nav.textContent }));
"""


def test_every_language_has_its_labels_and_a_missing_element_is_skipped():
    script = SCRIPT % {'locales': json.dumps((VITEPRESS / 'locales.js').as_uri()),
                       'aria': json.dumps((VITEPRESS / 'theme' / 'aria-labels.js').as_uri())}
    out = subprocess.run([NODE, '--input-type=module', '-e', script],
                         capture_output=True, text=True, check=True, encoding='utf-8').stdout
    result = json.loads(out)
    ids = {'main-nav-aria-label', 'sidebar-aria-label', 'doc-footer-aria-label'}
    for key, labels in result['labels'].items():
        assert set(labels) == ids and all(labels.values()), key
        if key != 'root':
            assert labels['main-nav-aria-label'] != 'Main Navigation', key
    assert result['nav'] == result['labels']['pt']['main-nav-aria-label']
