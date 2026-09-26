"""Screen-reader labels in each language (docs/.vitepress/theme/aria-labels.js).

VitePress writes "Main Navigation", "Sidebar Navigation" and "Pager" in English;
the build writes them from themeConfig.ariaLabels (locales.js) into each page's
HTML, and the theme sets them again after each render.
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


HTML = """
const { locales } = await import(%(locales)s);
const { ariaLabelsInHtml } = await import(%(aria)s);
const labels = locales().zh.themeConfig.ariaLabels;
const page = '<nav><span id="main-nav-aria-label" class="visually-hidden" data-v-1> Main Navigation </span></nav>'
  + '<span class="visually-hidden" id="doc-footer-aria-label" data-v-2>Pager</span><p id="other">Pager</p>';
console.log(JSON.stringify({ out: ariaLabelsInHtml(page, labels), labels,
                             none: ariaLabelsInHtml('<p>x</p>', labels), same: ariaLabelsInHtml(page, undefined) === page }));
"""


def test_the_built_html_carries_the_labels_of_its_language():
    script = HTML % {'locales': json.dumps((VITEPRESS / 'locales.js').as_uri()),
                     'aria': json.dumps((VITEPRESS / 'theme' / 'aria-labels.js').as_uri())}
    out = subprocess.run([NODE, '--input-type=module', '-e', script],
                         capture_output=True, text=True, check=True, encoding='utf-8').stdout
    result = json.loads(out)
    labels = result['labels']
    assert f'data-v-1>{labels["main-nav-aria-label"]}</span>' in result['out']
    assert f'data-v-2>{labels["doc-footer-aria-label"]}</span>' in result['out']
    assert '<p id="other">Pager</p>' in result['out']   # only the labelled elements change
    assert 'Main Navigation' not in result['out']
    assert result['none'] == '<p>x</p>' and result['same']
