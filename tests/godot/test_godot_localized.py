"""A game in another language and alphabet (PLAN_GAMES_3.md, Phase 6), with the RPG that asked for it.

A count's word takes the forms its language has: `tr_n('potion', 'potions', n)` is 1 potion, 2 potions in
English, and in Russian 1 зелье, 2 зелья, 5 зелий, 21 зелье (qg:phrase one= few= many=). A qg:asset in a
qg:language is a picture or a sound as it is in the language: the RPG's "FIGHT!" banner is drawn in each. A
language's font= has the letters of its alphabet the game's fonts lack: Montserrat has no Cyrillic, so the
RPG in Russian draws it from Xolonium, and its Latin letters stay Montserrat's. A sheet with slice= is a
frame that stretches to a box (box= on qg:dialogue and qg:menu): the RPG's dialogues and fight menu.

The pictures are checked in rendered frames (xvfb), as test_godot_play.py's frame is.
"""

import shutil
from pathlib import Path

import pytest
from PIL import Image

from quantum.runtime.godot_bin import check_project, run_godot
from quantum.runtime.godot_play import PlaySession

REPO = Path(__file__).resolve().parents[2]
RPG = REPO / 'projects' / 'rpg'
COUNTS = [0, 1, 2, 5, 11, 21, 22, 112]

COUNTED = """<q:application id="counted" type="game">
  <qg:language lang="ru" name="Русский">
    <qg:phrase text="potion" as="зелье" />
    <qg:phrase text="potions" as="зелий" one="зелье" few="зелья" />
  </qg:language>
  <qg:language lang="pl" name="Polski">
    <qg:phrase text="potions" as="mikstur" one="mikstura" few="mikstury" />
  </qg:language>
  <qg:language lang="cs" name="Čeština">
    <qg:phrase text="potions" as="lektvarů" one="lektvar" few="lektvary" />
  </qg:language>
  <qg:language lang="fr" name="Français">
    <qg:phrase text="potion" as="potion" />
    <qg:phrase text="potions" as="potions" />
  </qg:language>
  <qg:language lang="pt" name="Português">
    <qg:phrase text="potion" as="poção" />
    <qg:phrase text="potions" as="poções" />
  </qg:language>
  <qg:scene name="main" width="320" height="180">
    <qg:hud>
""" + ''.join(f"      <qg:text value=\"{{'{n} ' + tr_n('potion', 'potions', {n})}}\" />\n" for n in COUNTS) + """    </qg:hud>
    <qg:menu position="bottom-center"><qg:button label="next"><qg:next-language /></qg:button></qg:menu>
  </qg:scene>
</q:application>
"""

# Latin over Cyrillic, in a font with no Cyrillic, in Russian with and without a font that has it
LETTERS = """<q:application id="letters" type="game">
  <qg:language lang="ru"{font}>
    <qg:phrase text="potion" as="зелье" />
  </qg:language>
  <qg:scene name="main" width="320" height="180" background="#202020">
    <qg:hud font="projects/rpg/assets/montserrat_extra_bold.otf" size="32">
      <qg:text value="{{'JRPG'}}" />
      <qg:text value="{{tr('potion')}}" />
    </qg:hud>
  </qg:scene>
</q:application>
"""

VOICE = """<q:application id="voice" type="game">
  <qg:sound name="hello" src="assets/kenney/audio/coin.ogg" />
  <qg:language lang="ru"><qg:asset name="hello" src="hello-ru.ogg" /></qg:language>
  <qg:scene name="main" width="320" height="180" />
</q:application>
"""


def _build(folder: Path, text: str, source_dir: Path = REPO) -> Path:
    from quantum.core.parser import QuantumParser
    from quantum.runtime.godot import compile_game
    (folder / 'game.q').write_text(text, encoding='utf-8')
    app = QuantumParser(use_cache=False).parse_file(str(folder / 'game.q'))
    return Path(compile_game(app, str(folder / 'godot'), source_dir=str(source_dir)))


@pytest.fixture(scope='module')
def rpg(godot, tmp_path_factory) -> Path:
    src = tmp_path_factory.mktemp('rpg')
    shutil.copytree(RPG, src / 'rpg', ignore=shutil.ignore_patterns('godot'))
    out = _build(src / 'rpg', (src / 'rpg' / 'rpg.q').read_text(encoding='utf-8'), src / 'rpg')
    assert check_project(out, binary=godot) == []
    return out


def _hud(seen: dict) -> list:
    return PlaySession.screen(seen, 'hud')['items']


def test_a_count_in_each_language_s_forms(godot, tmp_path):
    out = _build(tmp_path, COUNTED)
    assert check_project(out, binary=godot) == []
    words = {
        '': 'potions potion potions potions potions potions potions potions',
        'ru': 'зелий зелье зелья зелий зелий зелье зелья зелий',             # 21 зелье, 22 зелья, 112 зелий
        'pl': 'mikstur mikstura mikstury mikstur mikstur mikstur mikstury mikstur',   # 21 mikstur
        'cs': 'lektvarů lektvar lektvary lektvarů lektvarů lektvarů lektvarů lektvarů',
        'fr': 'potion potion potions potions potions potions potions potions',   # 0 is one in French
        'pt': 'poções poção poções poções poções poções poções poções',
    }
    with PlaySession(out, binary=godot) as game:
        seen = game.observe()
        for lang in ['', 'ru', 'pl', 'cs', 'fr', 'pt']:                   # qg:next-language, one after another
            assert seen['lang'] == lang
            assert _hud(seen) == [f'{n} {w}' for n, w in zip(COUNTS, words[lang].split())], lang
            seen = game.act(tap=['select'], ticks=2)
        assert seen['lang'] == ''                                           # and round to the game's own


def test_the_rpg_counts_its_potions_in_russian(rpg, godot):
    with PlaySession(rpg, binary=godot, lang='ru') as game:
        assert _hud(game.observe()) == ['0 зелий', '0 ключей']
        game.act(hold=['up'], ticks=45)
        took = game.act(hold=['left'], ticks=25)                            # into the potion at (1, 1)
        assert _hud(took) == ['1 зелье', '0 ключей']
        assert PlaySession.screen(took, 'dialogue')['text'] == 'Зелье! В бою оно возвращает 5 жизни.'


def _to_the_fight(game) -> None:
    game.until('player.row == 7', hold=['down'])
    game.until('talking', hold=['right'])
    seen = game.observe()
    while seen['scene'] == 'exploration':
        seen = game.act(tap=['select'], ticks=2)


GOLD, PLAIN_BOX = (236, 196, 92), (95, 125, 140)       # the frame's ring; the box drawn without a frame


def _colours(image: Image.Image) -> dict:
    return {colour: n for n, colour in image.getcolors(image.width * image.height)}


@pytest.mark.parametrize('lang', ['en', 'ru'])
def test_the_rpg_frames_its_boxes_and_draws_its_banner_in_the_language(rpg, godot, tmp_path, lang):
    with PlaySession(rpg, binary=godot, lang=lang, frames=True) as game:
        game.until('player.row == 7', hold=['down'])
        game.until('talking', hold=['right'])
        game.act(ticks=2)
        talk = Image.open(game.frame(tmp_path / 'talk.png')['frame']).convert('RGB')
        _to_the_fight(game)
        game.act(ticks=40)                                                  # faded in; the banner goes at 60
        fight = Image.open(game.frame(tmp_path / 'fight.png')['frame']).convert('RGB')
    box = _colours(talk.crop((0, 540, 1280, 720)))
    assert box.get(GOLD, 0) > 2000 and PLAIN_BOX not in box                # the frame, stretched to the box
    assert _colours(fight.crop((400, 400, 880, 720))).get(GOLD, 0) > 1000   # the fight's menu in it too
    banner = Image.open(RPG / 'assets' / f'banner-{lang}.png').convert('RGBA')
    drawn = fight.crop((400, 190, 880, 310))                                # 480x120 around (640, 250)
    solid = [(x, y) for y in range(120) for x in range(480) if banner.getpixel((x, y))[3] == 255]
    same = sum(drawn.getpixel(p) == banner.getpixel(p)[:3] for p in solid)
    assert len(solid) > 5000 and same / len(solid) > 0.98                   # the language's own picture


def test_a_language_s_font_draws_the_letters_the_game_s_font_lacks(godot, tmp_path):
    shots = {}
    for name, font in (('without', ''), ('with', ' font="projects/rpg/assets/Xolonium-Regular.ttf"')):
        folder = tmp_path / name
        folder.mkdir()
        out = _build(folder, LETTERS.format(font=font))
        assert check_project(out, binary=godot) == []
        with PlaySession(out, binary=godot, lang='ru', frames=True) as game:
            game.act(ticks=2)
            shots[name] = Image.open(game.frame(folder / 'shot.png')['frame']).convert('RGB')
    latin, cyrillic = (0, 0, 160, 40), (0, 40, 160, 80)                  # the HUD's two lines
    assert shots['with'].crop(latin).tobytes() == shots['without'].crop(latin).tobytes()   # Montserrat's own
    assert shots['with'].crop(cyrillic).tobytes() != shots['without'].crop(cyrillic).tobytes()
    assert len(_colours(shots['with'].crop(cyrillic))) > 2                 # and drawn: not the background


def test_a_language_s_own_sound_is_the_one_loaded(godot, tmp_path):
    (tmp_path / 'hello-ru.ogg').write_text('not a sound', encoding='utf-8')    # so a log says which is read
    out = _build(tmp_path, VOICE)
    heard = {}
    for lang in ('en', 'ru'):
        ran = run_godot(['--path', str(out), '--quit-after', '10', '--', f'--q-lang={lang}'], godot)
        heard[lang] = ran.stdout + ran.stderr
    assert 'cannot load the sound hello-ru.ogg' in heard['ru']
    assert 'cannot load the sound' not in heard['en']
