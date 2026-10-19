"""Every ```xml block of docs/targets/hive.md is a hive that compiles.

The page is generated from the schema (scripts/generate-hive-reference.py)
and shows whole files; each one is written out here and compiled to
rules.toml and whitelist.toml, so the page cannot show what the compiler
refuses. (tests/docs/docs_blocks.py lists the page under RUN_BY_TEST.)
"""

import re
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.hive import compile_hive

REPO = Path(__file__).resolve().parents[2]
PAGE = REPO / 'docs' / 'targets' / 'hive.md'

BLOCKS = re.findall(r'```xml\n(.*?)```', PAGE.read_text(encoding='utf-8'), re.S)


def test_the_page_shows_hives():
    assert len(BLOCKS) >= 2
    for block in BLOCKS:
        assert 'type="hive"' in block


@pytest.mark.parametrize('block', BLOCKS, ids=[f'block-{i + 1}' for i in range(len(BLOCKS))])
def test_every_block_of_the_hive_page_compiles(block, tmp_path):
    source = tmp_path / 'hive.q'
    source.write_text(block, encoding='utf-8')
    written = compile_hive(QuantumParser(use_cache=False).parse_file(str(source)), str(tmp_path / 'out'))
    assert Path(written['rules.toml']).is_file()
