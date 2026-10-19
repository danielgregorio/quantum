"""The hive model: the .q's elements, read and checked against the schema.

`read_hive(app)` takes the ApplicationNode (for its `xml_root`) and returns
a `Hive`: the rules (an event, its offers) and the whitelist (what the
actuator may do, may never do, and how often). Anything the schema does not
know is a HiveCompileError with the line, and so is a promise the file
cannot keep: a placeholder of a field the event does not have, or an offer
the file's own whitelist would refuse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from xml.etree import ElementTree as ET

from quantum.runtime.hive.errors import HiveCompileError
from quantum.runtime.hive.schema import ACTIONS, EVENTS, LIMITS, TAGS, Attr

HIVE_NS = '{https://quantum.lang/hive}'
Q_NS = '{https://quantum.lang/ns}'

_PLACEHOLDER = re.compile(r'\{([^{}]*)\}')
_INT = re.compile(r'^-?\d+$')


@dataclass
class Offer:
    title: str
    description: str
    action: str                  # the action's name (restart-service)
    params: Dict[str, str]       # as written: placeholders kept, numbers and booleans as text
    line: Optional[int]


@dataclass
class Rule:
    event: str
    offers: List[Offer]
    line: Optional[int]


@dataclass
class Command:
    command: str
    args: List[str]
    line: Optional[int]


@dataclass
class Hive:
    id: str
    source_path: Optional[str]
    rules: List[Rule] = field(default_factory=list)
    commands: List[Command] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    blocked_services: List[str] = field(default_factory=list)
    blocked_packages: List[str] = field(default_factory=list)
    paths: List[str] = field(default_factory=list)
    blocked_paths: List[str] = field(default_factory=list)
    datasets: List[str] = field(default_factory=list)
    delete_snapshot: Optional[str] = None
    permits: List[str] = field(default_factory=list)
    limits: Dict[str, int] = field(default_factory=dict)   # Action variant -> a minute


def _local(element: ET.Element) -> tuple:
    tag = element.tag
    if not isinstance(tag, str):
        return None, None             # a comment
    if tag.startswith(HIVE_NS):
        return 'hive', tag[len(HIVE_NS):]
    if tag.startswith(Q_NS):
        return 'q', tag[len(Q_NS):]
    if tag.startswith('qh:'):
        return 'hive', tag[3:]
    if tag.startswith('q:'):
        return 'q', tag[2:]
    return 'other', tag.split('}')[-1]


def _line(element: ET.Element) -> Optional[int]:
    return getattr(element, 'sourceline', None)


def _no_text(element: ET.Element, what: str) -> None:
    texts = [element.text] + [child.tail for child in element]
    for text in texts:
        if text and text.strip():
            raise HiveCompileError(
                f'{what} holds text ({text.strip().splitlines()[0][:40]!r}): a hive file is declarations, '
                f'not script', _line(element))


def _convert(tag: str, name: str, attr: Attr, raw: str, line: Optional[int]) -> object:
    t = attr.type
    if t in ('text', 'args', 'words'):
        return raw
    if t == 'bool':
        low = raw.strip().lower()
        if low in ('true', '1', 'yes'):
            return True
        if low in ('false', '0', 'no'):
            return False
        raise HiveCompileError(f'<qh:{tag}> {name}= is true or false, not {raw!r}', line)
    if t == 'int':
        if _INT.match(raw.strip()):
            return int(raw)
        if _PLACEHOLDER.fullmatch(raw.strip()):
            return raw.strip()        # a placeholder: checked against the event's fields later
        raise HiveCompileError(f'<qh:{tag}> {name}= is a number, not {raw!r}', line)
    if t.startswith('enum:'):
        options = t[5:].split('|')
        if raw not in options:
            raise HiveCompileError(
                f'<qh:{tag}> {name}="{raw}" is not one of: {", ".join(options)}', line)
        return raw
    raise HiveCompileError(f'<qh:{tag}> {name}=: unknown type {t}', line)


def _read_attrs(tag: str, element: ET.Element, attrs: Dict[str, Attr], what: str) -> Dict[str, object]:
    line = _line(element)
    out: Dict[str, object] = {}
    for name, raw in element.attrib.items():
        if name.startswith('xmlns') or name.startswith('{'):
            continue
        if name not in attrs:
            raise HiveCompileError(f'{what} has no attribute {name!r} (it has: {", ".join(attrs)})', line)
        out[name] = _convert(tag, name, attrs[name], raw, line)
    for name, attr in attrs.items():
        if name not in out:
            if attr.required:
                raise HiveCompileError(f'{what} needs {name}=', line)
            out[name] = attr.default
    return out


def _placeholders(text: str) -> List[str]:
    return _PLACEHOLDER.findall(text)


def _check_placeholders(event: str, text: str, what: str, line: Optional[int]) -> None:
    fields = EVENTS[event].fields
    for name in _placeholders(text):
        if name not in fields:
            raise HiveCompileError(
                f'{what} holds {{{name}}}, which is not a field of {event} (it has: {", ".join(fields)})', line)


def _read_offer(element: ET.Element, event: str) -> Offer:
    line = _line(element)
    _no_text(element, '<qh:offer>')
    if len(element):
        raise HiveCompileError('<qh:offer> holds no tags', line)
    action = element.get('action')
    if action is None:
        raise HiveCompileError('<qh:offer> needs action=', line)
    if action not in ACTIONS:
        raise HiveCompileError(
            f'<qh:offer action="{action}"> is not an action the actuator has (it has: {", ".join(ACTIONS)})', line)
    spec = ACTIONS[action]
    attrs = dict(TAGS['offer'].attrs)
    attrs.update(spec.params)
    values = _read_attrs('offer', element, attrs, f'<qh:offer action="{action}">')
    params: Dict[str, str] = {}
    for name, attr in spec.params.items():
        value = values[name]
        if value is None:
            continue
        if attr.type == 'int':
            if isinstance(value, str):      # a placeholder
                field_name = value[1:-1]
                _check_placeholders(event, value, f'<qh:offer> {name}=', line)
                if EVENTS[event].fields[field_name].type != 'int':
                    raise HiveCompileError(
                        f'<qh:offer> {name}= is a number; {{{field_name}}} of {event} is text', line)
                params[name] = value
            else:
                params[name] = str(value)
        elif attr.type == 'bool':
            params[name] = 'true' if value else 'false'
        else:
            _check_placeholders(event, value, f'<qh:offer> {name}=', line)
            params[name] = ' '.join(value.split()) if attr.type in ('args', 'words') else value
    for name in ('title', 'description'):
        _check_placeholders(event, values[name], f'<qh:offer> {name}=', line)
    if not values['title'].strip():
        raise HiveCompileError('<qh:offer> needs a title', line)
    return Offer(values['title'], values['description'], action, params, line)


def _read_on(element: ET.Element) -> Rule:
    line = _line(element)
    values = _read_attrs('on', element, TAGS['on'].attrs, '<qh:on>')
    event = values['event']
    _no_text(element, f'<qh:on event="{event}">')
    offers = []
    for child in element:
        ns, name = _local(child)
        if ns is None:
            continue
        if ns == 'hive' and name == 'offer':
            offers.append(_read_offer(child, event))
        elif ns == 'hive':
            raise HiveCompileError(f'<qh:{name}> cannot go inside <qh:on>; it holds <qh:offer>s', _line(child))
        else:
            raise HiveCompileError(f'<{name}> is not a hive tag; <qh:on> holds <qh:offer>s', _line(child))
    if not offers:
        raise HiveCompileError(f'<qh:on event="{event}"> offers nothing: give it a <qh:offer>, or leave it out', line)
    return Rule(event, offers, line)


def _words(value: str) -> List[str]:
    return value.split()


def _exactly_one(values: Dict[str, object], names: List[str], what: str, line: Optional[int]) -> str:
    given = [n for n in names if values.get(n) is not None]
    if len(given) != 1:
        raise HiveCompileError(f'{what} takes exactly one of: {", ".join(names)}', line)
    return given[0]


def _read_allow(element: ET.Element, hive: Hive) -> None:
    line = _line(element)
    _no_text(element, '<qh:allow>')
    values = _read_attrs('allow', element, TAGS['allow'].attrs, '<qh:allow>')
    which = _exactly_one(values, ['command', 'service', 'path', 'dataset', 'action', 'delete-snapshot'],
                         '<qh:allow>', line)
    if values['args'] and which != 'command':
        raise HiveCompileError('<qh:allow> args= goes with command=', line)
    if which == 'command':
        command = values['command'].strip()
        if not command or ' ' in command:
            raise HiveCompileError(f'<qh:allow command="{values["command"]}">: one program, its arguments in args=', line)
        hive.commands.append(Command(command, _words(values['args']), line))
    elif which == 'service':
        hive.services.extend(w for w in _words(values['service']) if w not in hive.services)
    elif which == 'path':
        hive.paths.extend(w for w in _words(values['path']) if w not in hive.paths)
    elif which == 'dataset':
        hive.datasets.extend(w for w in _words(values['dataset']) if w not in hive.datasets)
    elif which == 'action':
        if values['action'] not in hive.permits:
            hive.permits.append(values['action'])
    else:
        if hive.delete_snapshot is not None:
            raise HiveCompileError('one <qh:allow delete-snapshot=> per file', line)
        hive.delete_snapshot = values['delete-snapshot'].strip()


def _read_block(element: ET.Element, hive: Hive) -> None:
    line = _line(element)
    _no_text(element, '<qh:block>')
    values = _read_attrs('block', element, TAGS['block'].attrs, '<qh:block>')
    which = _exactly_one(values, ['service', 'package', 'path'], '<qh:block>', line)
    target = {'service': hive.blocked_services, 'package': hive.blocked_packages, 'path': hive.blocked_paths}[which]
    target.extend(w for w in _words(values[which]) if w not in target)


def _read_limit(element: ET.Element, hive: Hive) -> None:
    line = _line(element)
    _no_text(element, '<qh:limit>')
    values = _read_attrs('limit', element, TAGS['limit'].attrs, '<qh:limit>')
    variant = LIMITS[values['action']]
    if variant in hive.limits:
        raise HiveCompileError(f'two <qh:limit action="{values["action"]}">', line)
    if values['per-minute'] < 1:
        raise HiveCompileError('<qh:limit> per-minute= is at least 1', line)
    hive.limits[variant] = values['per-minute']


def _glob(pattern: str) -> re.Pattern:
    return re.compile('^' + '.*'.join(re.escape(part) for part in pattern.split('*')) + '$')


def _literal(text: str) -> bool:
    return not _placeholders(text)


def _check_offers_against_whitelist(hive: Hive) -> None:
    """An offer the file's own whitelist would refuse is a rule that can never
    run: refused here, not found out on the dashboard."""
    for rule in hive.rules:
        for offer in rule.offers:
            spec = ACTIONS[offer.action]
            what = f'<qh:offer action="{offer.action}">'
            if spec.checked == 'command':
                cmd, args = offer.params['cmd'], offer.params.get('args', '').split()
                if not _literal(cmd):
                    continue
                shown = ' '.join([cmd] + args)
                if not any(c.command == cmd and len(c.args) == len(args) and
                           all(p == '*' or (_literal(a) and p == a) for p, a in zip(c.args, args))
                           for c in hive.commands):
                    raise HiveCompileError(
                        f'{what} runs `{shown}`, which no <qh:allow command=> permits (an argument that is a '
                        f'{{field}} needs a `*` in its place): the actuator would refuse it', offer.line)
            elif spec.checked == 'service':
                service = offer.params['service']
                if not _literal(service):
                    continue
                if any(_glob(b).match(service) for b in hive.blocked_services):
                    raise HiveCompileError(
                        f'{what} names {service!r}, which a <qh:block service=> blocks', offer.line)
                if service not in hive.services:
                    raise HiveCompileError(
                        f'{what} names {service!r}, which no <qh:allow service=> permits: the actuator would '
                        f'refuse it', offer.line)
            elif spec.checked == 'package':
                package = offer.params['package']
                if _literal(package) and any(_glob(b).match(package) for b in hive.blocked_packages):
                    raise HiveCompileError(
                        f'{what} names {package!r}, which a <qh:block package=> blocks', offer.line)
            elif spec.checked == 'dataset':
                dataset = offer.params.get('dataset')
                if dataset is None or not _literal(dataset):
                    continue
                if not any(_glob(d).match(dataset) for d in hive.datasets):
                    raise HiveCompileError(
                        f'{what} names {dataset!r}, which no <qh:allow dataset=> permits', offer.line)
            elif spec.checked and spec.checked not in hive.permits:
                raise HiveCompileError(
                    f'{what} needs <qh:allow action="{spec.checked}"/>: the actuator would refuse it', offer.line)


def read_hive(app) -> Hive:
    root = getattr(app, 'xml_root', None)
    if root is None:
        raise HiveCompileError('the application was not parsed from a file with its elements')
    hive = Hive(getattr(app, 'app_id', 'hive'), getattr(app, 'source_path', None))
    try:
        _no_text(root, '<q:application>')
        for child in root:
            ns, name = _local(child)
            if ns is None:
                continue
            if ns == 'hive':
                if name == 'on':
                    rule = _read_on(child)
                    if any(r.event == rule.event for r in hive.rules):
                        raise HiveCompileError(
                            f'two <qh:on event="{rule.event}">: put every offer for it in one', rule.line)
                    hive.rules.append(rule)
                elif name == 'allow':
                    _read_allow(child, hive)
                elif name == 'block':
                    _read_block(child, hive)
                elif name == 'limit':
                    _read_limit(child, hive)
                elif name == 'offer':
                    raise HiveCompileError('<qh:offer> goes inside <qh:on>', _line(child))
                else:
                    raise HiveCompileError(
                        f'<qh:{name}> is not a hive tag (they are: {", ".join(TAGS)})', _line(child))
            elif ns == 'q':
                raise HiveCompileError(
                    f'<q:{name}> is not part of the hive language: a hive file is declarations '
                    f'(qh:on, qh:allow, qh:block, qh:limit), with nothing to compute', _line(child))
            else:
                raise HiveCompileError(f'<{name}> is not a hive tag', _line(child))
        _check_offers_against_whitelist(hive)
    except HiveCompileError as e:
        if e.file is None:
            e.file = hive.source_path
        raise
    return hive
