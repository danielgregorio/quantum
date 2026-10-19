"""Every ```xml block of docs/targets/screen.md is a screen that compiles.

The page is generated from the schema (scripts/generate-screen-reference.py)
and shows whole files; each one is written out here, with the sheets it
names drawn as blank PNGs of the right size, and compiled to screen.toml,
so the page cannot show what the compiler refuses.
(tests/docs/docs_blocks.py lists the page under RUN_BY_TEST.)
"""

import re
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.screen import compile_screen, png

REPO = Path(__file__).resolve().parents[2]
PAGE = REPO / 'docs' / 'targets' / 'screen.md'
ART = REPO / 'os' / 'config' / 'screen' / 'art'

BLOCKS = re.findall(r'```xml\n(.*?)```', PAGE.read_text(encoding='utf-8'), re.S)


def test_the_page_shows_screens():
    assert len(BLOCKS) >= 2
    for block in BLOCKS:
        assert 'type="screen"' in block


@pytest.mark.parametrize('block', BLOCKS, ids=[f'block-{i + 1}' for i in range(len(BLOCKS))])
def test_every_block_of_the_screen_page_compiles(block, tmp_path):
    source = tmp_path / 'screen.q'
    source.write_text(block, encoding='utf-8')
    for src in set(re.findall(r'src="([^"]+)"', block)):
        target = tmp_path / src
        target.parent.mkdir(parents=True, exist_ok=True)
        real = ART / Path(src).name
        if real.is_file():
            target.write_bytes(real.read_bytes())      # the OS's own art
        else:
            png.write(target, 96, 24, [b'\x00' * (96 * 4)] * 24)
    written = compile_screen(QuantumParser(use_cache=False).parse_file(str(source)), str(tmp_path / 'out'))
    assert Path(written['screen.toml']).is_file()
