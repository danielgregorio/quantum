"""The playtest job (PLAN_PLAY_PROTOCOL.md, phase 7): an agent tries to finish each game.

Each game of ``projects/games.json`` may have a ``goal``::

    "goal": {"say": "win the fight with the opponent", "done": "game.outcome == 'won'", "calls": 60}

``say`` is what the agent is told, ``done`` is a condition of the play
protocol (any form ``godot_play.condition`` takes), checked by the job after
every call, and ``calls`` is how many calls the agent may make. The agent
is not told ``done``: it plays from what the game shows, as a player would.

    quantum playtest                  # every game with a goal, a Claude agent
    quantum playtest rpg keep --out playtest/

For each game the job writes the session's tape and a line of the report:
**reached**, **not reached** (out of calls, or the agent stopped), **stuck**
(ten calls in a row changed nothing) or **error**. A reached goal's tape,
copied into ``tests/godot/playtests/``, is a regression test as it is:
``test_godot_playtests.py`` replays it and checks the goal again.

The agent is anything with ``play(run, goal, start) -> str``. ``ClaudeAgent``
plays through the Claude API (``pip install "quantum[play]"`` and an
``ANTHROPIC_API_KEY``); the tests use scripted agents.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from quantum.runtime.godot_play import PlayError, condition
from quantum.runtime.play_tools import PlayTools

STUCK_AFTER = 10      # calls in a row that change nothing


class GoalReached(Exception):
    """The goal's condition holds: the run is over."""


class Stuck(Exception):
    """Calls keep running ticks and nothing changes."""


class OutOfCalls(Exception):
    """The agent used every call it had."""


# --- conditions, read by the job (the same rules as the driver's) ---

def lookup(obs: dict, path: str) -> Any:
    """A path of an observation: its own keys, then the state, the state's nodes and named
    things, the game's state, and the screen's views by kind (as godot_play.gd looks)."""
    parts = path.split('.')
    state = obs.get('state', {}) or {}
    views: Dict[str, dict] = {}
    for v in obs.get('screen', []) or []:
        views.setdefault(v.get('kind'), v)
    for base in (obs, state, state.get('nodes', {}), state.get('named', {}), state.get('game', {}), views):
        if isinstance(base, dict) and parts[0] in base:
            cur: Any = base
            for p in parts:
                if isinstance(cur, dict) and p in cur:
                    cur = cur[p]
                elif isinstance(cur, list) and p.isdigit() and int(p) < len(cur):
                    cur = cur[int(p)]
                else:
                    break
            else:
                return cur
    return None


def _number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def holds(cond: Union[str, list, dict], obs: dict) -> bool:
    """Whether a condition holds on an observation (``event:`` looks at its events)."""
    cond = condition(cond)
    if 'any' in cond:
        return any(holds(c, obs) for c in cond['any'])
    if 'all' in cond:
        return all(holds(c, obs) for c in cond['all'])
    if 'event' in cond:
        want = {k: str(v) for k, v in cond.items() if k != 'event'}
        return any(e.get('kind') == cond['event'] and all(str(e.get(k)) == v for k, v in want.items())
                   for e in obs.get('events', []) or [])
    if 'path' not in cond:
        return False
    v, op, w = lookup(obs, cond['path']), cond.get('op', 'truthy'), cond.get('value')
    if isinstance(w, dict) and 'path' in w:
        other = lookup(obs, w['path'])
        w = other + w.get('plus', 0) if _number(other) else other
    if op == 'truthy':
        return bool(v)
    if op == 'falsy':
        return not v
    if op in ('==', '!='):
        same = abs(float(v) - float(w)) < 1e-6 if _number(v) and _number(w) else v == w
        return same if op == '==' else not same
    if not (_number(v) and _number(w)):
        return False
    return {'<': v < w, '<=': v <= w, '>': v > w, '>=': v >= w}[op]


# --- one game, one goal ---

class Run:
    """One session handed to an agent: the play tools, bound to the session, watched by the
    job. Every call that runs ticks is checked against the goal; the run ends (by raising)
    when it is reached, when the calls are used up, or when nothing changes any more."""

    def __init__(self, tools: PlayTools, sid: str, done: Union[str, list, dict], calls: int):
        self.tools, self.sid, self.done = tools, sid, condition(done)
        self.calls_left = calls
        self.calls = 0
        self.last: Optional[dict] = None
        self._same = 0
        self._seen: Optional[str] = None

    def _spend(self) -> None:
        if self.calls_left <= 0:
            raise OutOfCalls()
        self.calls_left -= 1
        self.calls += 1

    def _check(self, obs: dict) -> dict:
        self.last = obs
        if holds(self.done, obs):
            raise GoalReached()
        now = json.dumps([obs.get('scene'), obs.get('state'), obs.get('screen')], sort_keys=True, default=str)
        self._same = self._same + 1 if now == self._seen else 0
        self._seen = now
        if self._same >= STUCK_AFTER:
            raise Stuck()
        return obs

    def act(self, **kwargs) -> dict:
        self._spend()
        return self._check(self.tools.act(self.sid, **kwargs))

    def until(self, cond, **kwargs) -> dict:
        self._spend()
        return self._check(self.tools.until(self.sid, cond, **kwargs))

    def observe(self) -> dict:
        self._spend()
        return self.tools.observe(self.sid)

    def view(self) -> dict:
        self._spend()
        return self.tools.view(self.sid)

    def map(self) -> Optional[dict]:
        self._spend()
        return self.tools.map(self.sid)

    def snapshot(self) -> dict:
        self._spend()
        return self.tools.snapshot(self.sid)

    def restore(self, snapshot: str) -> dict:
        self._spend()
        obs = self.tools.restore(self.sid, snapshot)
        self.last = obs
        return obs


def playtest(game: str, goal: dict, agent, tools: PlayTools, out_dir: Union[str, Path]) -> dict:
    """Plays one game toward its goal with ``agent``; answers the report's line and saves the
    session's tape (with the goal, so a reached one can be kept as a test) in ``out_dir``."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    row = {'game': game, 'goal': goal['say'], 'result': 'error', 'calls': 0, 'ticks': 0, 'tape': '', 'note': ''}
    try:
        start = tools.start(game)
    except PlayError as e:
        row['note'] = f'it did not start: {e}'
        return row
    run = Run(tools, start['session'], goal['done'], int(goal.get('calls', 60)))
    try:
        try:
            row['note'] = agent.play(run, goal['say'], start) or ''
            row['result'] = 'not reached'
        except GoalReached:
            row['result'] = 'reached'
        except OutOfCalls:
            row['result'], row['note'] = 'not reached', f'out of calls ({run.calls})'
        except Stuck:
            row['result'], row['note'] = 'stuck', f'{STUCK_AFTER} calls in a row changed nothing'
        except PlayError as e:
            row['note'] = str(e)
        row['calls'] = run.calls
        session = tools.sessions[start['session']]
        tape = session.tape()
        row['ticks'] = tape['ticks']
        path = out_dir / f'{game}.json'
        path.write_text(json.dumps({'game': game, 'goal': goal['say'], 'done': goal['done'], 'result': row['result'],
                                    'ticks': tape['ticks'],
                                    'tape': {str(k): [list(e) for e in v] for k, v in tape['tape'].items()}},
                                   indent=1), encoding='utf-8')
        row['tape'] = path.name
    finally:
        tools.end(start['session'])
    return row


def goals(projects: Path, only: Optional[List[str]] = None) -> Dict[str, dict]:
    """The games that have a goal in games.json (all, or those named)."""
    listing = json.loads((projects / 'games.json').read_text(encoding='utf-8'))['games']
    found = {g['name']: g['goal'] for g in listing if g.get('goal')}
    if only:
        missing = [n for n in only if n not in found]
        if missing:
            raise PlayError(f'no goal for {", ".join(missing)} (games with one: {", ".join(found)})')
        found = {n: found[n] for n in only}
    return found


def report(rows: List[dict]) -> str:
    """The report as Markdown: one line a game, then what to do with a reached goal."""
    lines = ['# Playtest', '', '| Game | Goal | Result | Calls | Ticks | Tape | Note |', '|---|---|---|---|---|---|---|']
    for r in rows:
        note = r['note'].replace('|', '\\|').replace('\n', ' ')[:300]
        lines.append(f"| {r['game']} | {r['goal']} | **{r['result']}** | {r['calls']} | {r['ticks']} | {r['tape']} "
                     f"| {note} |")
    reached = [r for r in rows if r['result'] == 'reached']
    lines += ['', f'{len(reached)} of {len(rows)} reached.']
    if reached:
        lines += ['', 'A reached goal is a test as it is: copy its tape into `tests/godot/playtests/`.']
    return '\n'.join(lines) + '\n'


# --- an agent: Claude ---

_STR_LIST = {'type': 'array', 'items': {'type': 'string'}}
_ACTIONS = {
    'hold': {**_STR_LIST, 'description': 'actions pressed for all the ticks of this call'},
    'tap': {**_STR_LIST, 'description': 'actions pressed for one tick'},
    'press': {**_STR_LIST, 'description': 'actions held across calls, until released'},
    'release': {**_STR_LIST, 'description': 'actions to let go of'},
    'cursor': {'type': 'array', 'items': {'type': 'number'}, 'description': "[x, y] where the player's pointer is"},
    'reflex': {'type': 'array', 'description': 'rules checked before every tick until replaced ([] clears them)',
               'items': {'type': 'object', 'properties': {'when': {'type': 'string'}, 'hold': _STR_LIST},
                         'required': ['hold']}},
}
TOOLS = [
    {'name': 'play_act', 'description': 'Apply actions and run `ticks` ticks (60 a second). Answers the observation '
                                        'after, with the events of those ticks.',
     'input_schema': {'type': 'object', 'properties': {'ticks': {'type': 'integer'}, **_ACTIONS}}},
    {'name': 'play_until', 'description': 'As play_act, but runs until any of the conditions holds or max_ticks have '
                                          'run: "talking", "player.col == 11", "scene == \'combat\'", "changed scene", '
                                          '"event:say", "event:touch with=key", "ball.y < left.y - 8". The answer\'s '
                                          '`stopped` says which.',
     'input_schema': {'type': 'object', 'properties': {'condition': _STR_LIST, 'max_ticks': {'type': 'integer'},
                                                       **_ACTIONS}, 'required': ['condition']}},
    {'name': 'play_observe', 'description': 'What the game shows now, without running it.',
     'input_schema': {'type': 'object', 'properties': {}}},
    {'name': 'play_view', 'description': 'The screen drawn as text, a character a map cell, with a legend.',
     'input_schema': {'type': 'object', 'properties': {}}},
    {'name': 'play_map', 'description': "The scene's tilemap: # stops, - one-way, . open.",
     'input_schema': {'type': 'object', 'properties': {}}},
    {'name': 'play_snapshot', 'description': 'Mark this point; play_restore comes back to it.',
     'input_schema': {'type': 'object', 'properties': {}}},
    {'name': 'play_restore', 'description': 'Back to a snapshot, exactly as it was.',
     'input_schema': {'type': 'object', 'properties': {'snapshot': {'type': 'string'}}, 'required': ['snapshot']}},
    {'name': 'give_up', 'description': 'Stop playing, and say why: what blocks you, what looks wrong in the game.',
     'input_schema': {'type': 'object', 'properties': {'why': {'type': 'string'}}, 'required': ['why']}},
]

SYSTEM = """You are playtesting a game made with Quantum. You play it through tools, as a player would: \
you press the game's actions and read what the screen shows. The game stands still between your calls.

Every observation has the scene, its state (characters, things, variables), what the screen shows \
(`screen`: the HUD, the menus with their focus, the dialogue) and the `events` since your last call. \
play_until saves many calls: hold an action until something happens. In an action game, give `reflex` \
rules ([{"when": "ball.y < left.y - 4", "hold": ["up"]}]) that the game checks every tick while you plan. \
Try a risky choice from a snapshot and restore it if it fails.

You have a limited number of calls. When you cannot make progress, call give_up and say what blocks you; \
if something in the game looks wrong (a wall you cannot pass that should open, a menu you cannot leave), \
say so: that is a finding."""


class ClaudeAgent:
    """Plays through the Claude API: a manual tool loop over the run's tools. The job stops it
    (by raising out of a tool) when the goal is reached, the calls are spent or it is stuck."""

    def __init__(self, model: str = 'claude-opus-5-5', effort: str = 'medium', client=None):
        self.model, self.effort = model, effort
        if client is None:
            import anthropic
            client = anthropic.Anthropic()
        self.client = client

    def play(self, run: Run, goal: str, start: dict) -> str:
        first = {k: v for k, v in start.items() if k != 'session'}
        messages: List[dict] = [{'role': 'user', 'content': f'Your goal: {goal}\n\nThe game, as it starts:\n'
                                                            f'{json.dumps(first, separators=(",", ":"))}'}]
        while True:
            response = self.client.beta.messages.create(
                model=self.model, max_tokens=16000, system=SYSTEM, tools=TOOLS, messages=messages,
                output_config={'effort': self.effort}, cache_control={'type': 'ephemeral'},
                betas=['server-side-fallback-2026-07-01'], fallbacks='default')
            if response.stop_reason == 'refusal':
                return 'the model declined to go on'
            messages.append({'role': 'assistant', 'content': response.content})
            uses = [b for b in response.content if b.type == 'tool_use']
            if not uses:
                return ' '.join(b.text for b in response.content if b.type == 'text').strip()
            results = []
            for use in uses:
                if use.name == 'give_up':
                    return str(use.input.get('why', ''))
                try:
                    out = json.dumps(self._call(run, use.name, dict(use.input)), separators=(',', ':'))
                    results.append({'type': 'tool_result', 'tool_use_id': use.id, 'content': out})
                except (PlayError, ValueError, TypeError) as e:
                    results.append({'type': 'tool_result', 'tool_use_id': use.id, 'content': str(e), 'is_error': True})
            messages.append({'role': 'user', 'content': results})

    @staticmethod
    def _call(run: Run, name: str, args: dict):
        if name == 'play_act':
            return run.act(**{k: v for k, v in args.items() if k in ('ticks', *_ACTIONS)})
        if name == 'play_until':
            cond = args.pop('condition')
            cond = cond[0] if isinstance(cond, list) and len(cond) == 1 else cond
            return run.until(cond, **{k: v for k, v in args.items() if k in ('max_ticks', *_ACTIONS)})
        if name == 'play_restore':
            return run.restore(args['snapshot'])
        if name in ('play_observe', 'play_view', 'play_map', 'play_snapshot'):
            return getattr(run, name[5:])()
        raise ValueError(f'no tool {name}')


def add_arguments(parser) -> None:
    parser.add_argument('games', nargs='*', help='games of projects/ with a goal (all, by default)')
    parser.add_argument('--out', default='playtest', help='where the report and the tapes go (default ./playtest)')
    parser.add_argument('--model', default='claude-opus-5-5', help='the Claude model that plays')
    parser.add_argument('--effort', default='medium', choices=['low', 'medium', 'high', 'xhigh', 'max'],
                        help='how hard the model thinks before each call')


def main(args) -> int:
    tools = PlayTools()
    try:
        wanted = goals(tools.projects, args.games)
    except PlayError as e:
        print(f'[ERROR] {e}')
        return 2
    try:
        agent = ClaudeAgent(model=args.model, effort=args.effort)
    except ImportError:
        print('quantum playtest needs the anthropic package: pip install "quantum[play]"')
        return 1
    out = Path(args.out)
    rows = []
    try:
        for game, goal in wanted.items():
            row = playtest(game, goal, agent, tools, out)
            print(f"{row['result']:12} {game}: {row['calls']} calls, {row['ticks']} ticks {row['note'][:120]}")
            rows.append(row)
    finally:
        tools.close()
    (out / 'playtest.md').write_text(report(rows), encoding='utf-8')
    print(f'report: {out / "playtest.md"}')
    return 0
