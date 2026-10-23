"""Motion, the same in every renderer (UI-19).

Three kinds — fade, slide, expand — at two speeds — fast (150 ms) and normal
(250 ms) — eased out. Where:

- `<ui:window transition="fade|slide">`: the page enters that way each time it
  is shown;
- `enter="fade|slide|expand"` on any `ui:*` element (an expression too:
  `enter="{card.id == moved and 'slide' or ''}"`), and `<ui:animate
  type="fade|slide|expand">`: the element enters that way when its page is shown;
- a tab's content opens with `expand` when the user changes the tab.

`speed="fast|normal"` sets the speed (normal when not given). Each renderer
draws them with what it has — the browser's CSS, Textual's animator in the
terminal — and records the motions it ran, in order, as {kind, speed, what}:
`window.quantumMotions` in the browser, `ConsoleUI.motions` in the terminal.
The same steps on the same page give the same list. `ui.motion: off` in
quantum.config.yaml turns them all off; the browser also stops them for the
system's reduced-motion setting.
"""

from typing import Any, Dict, Optional

KINDS = ('fade', 'slide', 'expand')
PAGE_KINDS = ('fade', 'slide')
SPEEDS = {'fast': 150, 'normal': 250}


def check_literal(attr: str, value: Optional[str], allowed, where: str) -> None:
    """At parse time: a value that is not an expression must be one of `allowed` (UI-19)."""
    if value is None or '{' in value or value in allowed:
        return
    choices = ', '.join(allowed[:-1]) + ' or ' + allowed[-1]
    raise ValueError(f'<{where} {attr}="{value}">: use {choices} (UI-19)')


def motion(kind: Any, speed: Any, what: str) -> Optional[Dict[str, Any]]:
    """The motion an element asks for, resolved; None when it asks for none ('' or not given)."""
    kind = '' if kind is None else str(kind).strip()
    if not kind:
        return None
    if kind not in KINDS:
        raise ValueError(f'a motion is {", ".join(KINDS)}, not "{kind}" (UI-19)')
    speed = str(speed).strip() if speed not in (None, '') else 'normal'
    if speed not in SPEEDS:
        raise ValueError(f'a motion\'s speed is fast or normal, not "{speed}" (UI-19)')
    return {'kind': kind, 'speed': speed, 'what': what, 'ms': SPEEDS[speed]}


def of_props(view_type: str, props: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """The motion of an element from its resolved attributes — a view node's props, or a node's fields."""
    if view_type == 'window':
        return motion(props.get('transition'), props.get('speed'), 'page')
    kind = props.get('enter')
    if not kind and view_type == 'animate' and props.get('anim_type') in KINDS:
        kind = props.get('anim_type')
    return motion(kind, props.get('speed'), props.get('ui_id') or view_type)


def record(m: Dict[str, Any]) -> Dict[str, str]:
    """What a renderer records of a motion it ran."""
    return {'kind': m['kind'], 'speed': m['speed'], 'what': m['what']}


def motion_on(config: Optional[dict]) -> bool:
    """`ui.motion: off` in quantum.config.yaml turns every motion off (YAML reads a bare off as False)."""
    value = ((config or {}).get('ui') or {}).get('motion', True)
    return value not in (False, 'off', 'false', 'no', 0)


MOTION_CSS = """\
/* UI-19: motion — fade, slide, expand; fast 150 ms, normal 250 ms; eased out */
@keyframes q-m-fade { from { opacity: 0; } to { opacity: 1; } }
@keyframes q-m-slide { from { opacity: 0; transform: translateX(24px); } to { opacity: 1; transform: none; } }
@keyframes q-m-expand { from { opacity: 0; transform: scaleY(0.85); } to { opacity: 1; transform: none; } }
.q-m { animation-duration: var(--q-m-ms, 250ms); animation-timing-function: ease-out; animation-fill-mode: both; }
.q-m-fade { animation-name: q-m-fade; }
.q-m-slide { animation-name: q-m-slide; }
.q-m-expand { animation-name: q-m-expand; transform-origin: top; }
@media (prefers-reduced-motion: reduce) { .q-m { animation: none !important; } }
"""


def motion_js(on: bool) -> str:
    """Once per page: whether motion is on, and the record of the motions the page ran."""
    return """<script>
(function () {
  var on = %s && !(window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  window.quantumMotionOn = on;
  window.quantumMotions = window.quantumMotions || [];
  function collect() {
    if (!on) return;
    document.querySelectorAll('[data-motion]').forEach(function (e) {
      window.quantumMotions.push({kind: e.dataset.motionKind, speed: e.dataset.motionSpeed, what: e.dataset.motion});
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', collect); else collect();
})();
</script>
""" % ('true' if on else 'false')


def html_attrs(m: Dict[str, Any]) -> Dict[str, str]:
    """The attributes the browser's element takes for a motion."""
    return {'class': f"q-m q-m-{m['kind']}", 'style': f"--q-m-ms: {m['ms']}ms",
            'data-motion': m['what'], 'data-motion-kind': m['kind'], 'data-motion-speed': m['speed']}


class TerminalMotion:
    """A motion in the terminal: one progress value, 0 to 1, drives the element's opacity and its offset.

    Textual animates the opacity but not an offset, so the animator moves `p`
    and this sets both: fade only shows the element, slide brings it 4 columns
    in from the right, expand drops it one row into place.
    """

    START = {'fade': (0, 0), 'slide': (4, 0), 'expand': (0, -1)}

    def __init__(self, widget, kind: str):
        self.widget = widget
        self.dx, self.dy = self.START[kind]
        self._p = 1.0

    @property
    def p(self) -> float:
        return self._p

    @p.setter
    def p(self, value: float) -> None:
        self._p = value
        rest = 1.0 - value
        self.widget.styles.opacity = max(0.0, min(1.0, value))
        self.widget.styles.offset = (round(self.dx * rest), round(self.dy * rest))

    def run(self, app, ms: int) -> None:
        self.p = 0.0
        app.animator.animate(self, 'p', 1.0, duration=ms / 1000, easing='out_cubic')
