"""What the Hive's screen language is: every `qs:` tag, every event a rule can be on, every action.

A `q:application type="screen"` is what the Hive of Quantum OS shows on the
machine's screen: a small pixel-art scene (sprites, text, particles) and,
per event, what happens in it. The daemon `hive-screen` (os/crates) draws
it on the VM's console and lists the Hive's offers for an administrator to
approve. This table is the single source: the model validates against it,
the reference page is generated from it, and anything with no entry does
not exist.

The events are the Hive's own (the table of quantum/runtime/hive/schema.py,
which the rules `qh:` use too), as hive-cortex tells them to its clients,
plus the screen's: a plain notice, an offer, an action done. Every event
has `title`, `body` and `severity` besides its own fields. A rule's texts
and targets may hold `{field}`, filled in from the event itself.

The vocabulary of the scene is the games' (`qg:`): a sheet of frames, an
animation, a tween with the same curves, the same particle presets, with
the same meaning. There are no statements and no expressions.

Attribute types, besides the hive's (text, int, bool, enum):

- `ident`: a name
- `float`: a number
- `color`: `#rgb` or `#rrggbb`
- `tile`: a frame size in pixels, `24` or `16x24`
- `frames`: frame numbers separated by commas
- `src`: a PNG next to the .q, or in a folder below it
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from quantum.runtime.hive.schema import EVENTS as HIVE_EVENTS, Attr, Field, Tag

SCREEN_NS = 'https://quantum.lang/screen'

PRESETS = ('puff', 'sparks', 'smoke', 'dust', 'fire', 'rain', 'snow', 'confetti', 'stars')
TRANS = ('linear', 'sine', 'quad', 'cubic', 'back', 'bounce', 'elastic')
EASES = ('in', 'out', 'in-out')
PROPERTIES = ('x', 'y', 'scale', 'alpha')
SEVERITIES = ('info', 'notice', 'warning', 'error', 'critical')

# What a qs:bar may show of the screen itself, as {field}s in its texts: the
# daemon fills them in as it runs (a test's screen shows none of it).
BAR_FIELDS: Dict[str, str] = {
    'clock': 'the time, HH:MM (--:-- until the daemon has it)',
    'level': 'the presentation level: plain, effects or fine',
    'cores': 'how many cores the machine gives the screen',
    'host': 'the machine\'s name',
    'offers': 'how many offers wait for an approval',
}

# The font every screen gets: 6x10 cells, one per printable ASCII character
# (32-126, cells 0-94) and one per Latin-1 character (160-255, cells 95-190).
FONT_CELL = (6, 10)
FONT_FILE = 'font.png'


@dataclass(frozen=True)
class ScreenEvent:
    doc: str
    fields: Dict[str, Field]
    source: str          # 'hive': an observation, through hive-cortex; 'screen': the screen's own


# ---------------------------------------------------------------- events

COMMON: Dict[str, Field] = {
    'title': Field('text', 'the notice, as hive-cortex titles it'),
    'body': Field('text', 'what it says'),
    'severity': Field('text', 'info, notice, warning, error or critical'),
}

EVENTS: Dict[str, ScreenEvent] = {
    name: ScreenEvent(event.doc, {**event.fields, **COMMON}, 'hive')
    for name, event in HIVE_EVENTS.items()
}
EVENTS.update({
    'notice': ScreenEvent(
        'A notice with no observation behind it (hive-nerve-fs reports its filesystem events this way).',
        dict(COMMON), 'screen'),
    'offer': ScreenEvent(
        'The Hive offered something an administrator may approve; the qs:offers lists it.',
        {'count': Field('int', 'how many offers came together'), **COMMON}, 'screen'),
    'done': ScreenEvent(
        'An action an administrator approved on this screen ran and succeeded.',
        {'action': Field('text', 'what ran: the action\'s name (restart-service)'),
         'service': Field('text', 'the service it was on, when it was on one'),
         'package': Field('text', 'the package it was about, when it was about one'),
         'output': Field('text', 'what it printed, if anything')}, 'screen'),
    'failed': ScreenEvent(
        'An action an administrator approved on this screen ran and failed.',
        {'action': Field('text', 'what ran: the action\'s name (restart-service)'),
         'service': Field('text', 'the service it was on, when it was on one'),
         'package': Field('text', 'the package it was about, when it was about one'),
         'output': Field('text', 'what it said, if anything')}, 'screen'),
})

# ---------------------------------------------------------------- tags

_TARGET = Attr('text', required=True,
               doc='a qs:sprite\'s name, or a {field} that is one (a service name); nothing happens when no '
                   'sprite has that name')
_PANEL_TITLE = Attr('text', None,
                    doc='given, the rows sit in a panel with a bevelled frame, a shadow and this title on its bar; '
                        'x, y and width are then the panel\'s, and it is as tall as its rows')

TAGS: Dict[str, Tag] = {
    'sheet': Tag(
        'A PNG of equal frames, numbered left to right and top to bottom from 0.',
        {'name': Attr('ident', required=True),
         'src': Attr('src', required=True),
         'tile': Attr('tile', required=True, doc='frame size in pixels: 24, or 16x24')},
        parents=('application',)),
    'animation': Tag(
        'Frames of its sheet, cycled: what a qs:sprite plays from the start (animation=) or a rule starts '
        '(qs:animate).',
        {'name': Attr('ident', required=True),
         'frames': Attr('frames', required=True),
         'fps': Attr('float', 8.0),
         'loop': Attr('bool', True, doc='false: it plays once and stays on its last frame')},
        parents=('sheet',)),
    'particles': Tag(
        'A particle effect: a preset and a few overrides, as in a game. qs:emit plays it once where a sprite '
        'is; qs:emitter keeps it going in the scene.',
        {'name': Attr('ident', required=True),
         'preset': Attr('enum:' + '|'.join(PRESETS), required=True,
                        doc='puff, sparks, smoke, dust, confetti and stars play once; fire, rain and snow keep going'),
         'color': Attr('color', None, doc='the preset\'s own when not given'),
         'amount': Attr('int', None, doc='how many particles'),
         'lifetime': Attr('float', None, doc='seconds each one lives'),
         'speed': Attr('float', None, doc='pixels a second, about'),
         'size': Attr('float', None, doc='pixels, about')},
        parents=('application',)),
    'scene': Tag(
        'What is on the screen, in pixels of the scene: the daemon scales it up by a whole number to fill the '
        'display. One per file.',
        {'width': Attr('int', 320),
         'height': Attr('int', 180),
         'background': Attr('color', '#000000')},
        parents=('application',)),
    'sprite': Tag(
        'A picture in the scene: one frame of a sheet, or an animation of it. Its name is how a rule finds '
        'it: a sprite named after a service is the one {service} reaches.',
        {'name': Attr('ident', None),
         'sheet': Attr('ident', required=True),
         'frame': Attr('int', 0),
         'x': Attr('int', required=True),
         'y': Attr('int', required=True),
         'animation': Attr('ident', None, doc='an animation of its sheet, played from the start'),
         'hidden': Attr('bool', False, doc='not drawn until a qs:show')},
        parents=('scene',)),
    'text': Tag(
        'Fixed text in the scene, in the screen\'s font. What an event says goes in a qs:say or the qs:notices.',
        {'name': Attr('ident', None),
         'value': Attr('text', required=True),
         'x': Attr('int', required=True),
         'y': Attr('int', required=True),
         'color': Attr('color', '#ffffff'),
         'align': Attr('enum:left|center|right', 'left', doc='which side of the text x is')},
        parents=('scene',)),
    'emitter': Tag(
        'A particle effect that keeps going in the scene: rain over it, a fire on a spot.',
        {'particles': Attr('ident', required=True),
         'x': Attr('int', required=True),
         'y': Attr('int', required=True),
         'width': Attr('int', 0, doc='for rain and snow, how wide a band they fall across'),
         'level': Attr('int', 1, doc='the presentation level it plays from: 1 whenever the effects are on, '
                                     '2 only at the fine level, which the daemon affords with the cores')},
        parents=('scene',)),
    'offers': Tag(
        'Where the Hive\'s offers are listed, one a row, for an administrator to approve: up and down move, '
        'Enter approves the one with the focus (a dangerous action asks for Enter twice), Escape dismisses it. '
        'At most one.',
        {'x': Attr('int', required=True),
         'y': Attr('int', required=True),
         'width': Attr('int', required=True),
         'rows': Attr('int', 4),
         'title': _PANEL_TITLE,
         'color': Attr('color', '#ffffff'),
         'focus': Attr('color', '#ffd34d', doc='the row with the focus')},
        parents=('scene',)),
    'notices': Tag(
        'The last notices, one a row, newest at the bottom. At most one.',
        {'x': Attr('int', required=True),
         'y': Attr('int', required=True),
         'width': Attr('int', required=True),
         'rows': Attr('int', 3),
         'title': _PANEL_TITLE,
         'color': Attr('color', '#c0c0c0')},
        parents=('scene',)),
    'bar': Tag(
        'A bar across the scene, as a window manager\'s: at the top or at the bottom, a title in the accent at the '
        'left, a text after it and one at the right. The texts may hold the screen\'s own {field}s (below). The '
        'bar at the bottom shows what a qs:say says while it lasts. At most one a side.',
        {'side': Attr('enum:top|bottom', required=True),
         'title': Attr('text', None, doc='at the left, in the accent'),
         'left': Attr('text', None, doc='after the title'),
         'right': Attr('text', None, doc='against the right edge'),
         'color': Attr('color', '#8a8aa0'),
         'accent': Attr('color', '#ffd34d', doc='the title\'s colour')},
        parents=('scene',)),
    'on': Tag(
        'What happens in the scene when an event arrives: the actions inside, in order. One per event.',
        {'event': Attr('enum:' + '|'.join(EVENTS), required=True)},
        parents=('application',)),
    'animate': Tag(
        'Plays an animation of the sprite\'s sheet on it, from its first frame.',
        {'target': _TARGET,
         'name': Attr('ident', required=True)},
        parents=('on',)),
    'frame': Tag(
        'Shows one frame of the sprite\'s sheet on it, and stops whatever it was playing.',
        {'target': _TARGET,
         'frame': Attr('int', required=True)},
        parents=('on',)),
    'show': Tag(
        'Shows or hides a sprite.',
        {'target': _TARGET,
         'visible': Attr('bool', True)},
        parents=('on',)),
    'tween': Tag(
        'Eases a property of a sprite from what it is to a value, over some seconds, with the games\' curves.',
        {'target': _TARGET,
         'property': Attr('enum:' + '|'.join(PROPERTIES), required=True,
                          doc='x, y: where it is; scale: its size (1 is as drawn); alpha: how opaque (0 to 1)'),
         'to': Attr('float', required=True),
         'from': Attr('float', None, doc='where it starts (what it is now when not given)'),
         'seconds': Attr('float', 0.5),
         'trans': Attr('enum:' + '|'.join(TRANS), 'sine', doc='the curve'),
         'ease': Attr('enum:' + '|'.join(EASES), 'out', doc='which end of the curve is slow'),
         'repeat': Attr('int', 0, doc='times it plays again (-1: for ever)'),
         'yoyo': Attr('bool', False, doc='each repeat goes back the other way')},
        parents=('on',)),
    'emit': Tag(
        'Plays a qs:particles effect once where a sprite is.',
        {'particles': Attr('ident', required=True),
         'at': _TARGET,
         'dx': Attr('int', 0),
         'dy': Attr('int', 0, doc='offset in pixels from the sprite\'s top left')},
        parents=('on',)),
    'say': Tag(
        'Shows a line of text at the bottom of the scene for a while: what happened, in words.',
        {'text': Attr('text', required=True),
         'seconds': Attr('float', 4.0)},
        parents=('on',)),
}

ACTIONS = ('animate', 'frame', 'show', 'tween', 'emit', 'say')
