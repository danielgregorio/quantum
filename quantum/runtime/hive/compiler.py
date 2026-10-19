"""Writes what the daemons load: rules.toml for hive-synapse, whitelist.toml for hive-actuator."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from quantum.runtime.hive.model import Hive, read_hive
from quantum.runtime.hive.schema import ACTIONS, PERMITS

HEADER = ('# Written by Quantum from {source}: {what}. Do not edit; edit the .q and run it again '
          '(`quantum run {source}`).\n')


def _s(text: str) -> str:
    """A TOML basic string."""
    out = ['"']
    for ch in text:
        if ch == '"':
            out.append('\\"')
        elif ch == '\\':
            out.append('\\\\')
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\t':
            out.append('\\t')
        elif ord(ch) < 0x20 or ch == '\x7f':
            out.append(f'\\u{ord(ch):04X}')
        else:
            out.append(ch)
    out.append('"')
    return ''.join(out)


def _list(values: List[str], per_line: bool = False) -> str:
    if not values:
        return '[]'
    if per_line:
        return '[\n' + ''.join(f'    {_s(v)},\n' for v in values) + ']'
    return '[' + ', '.join(_s(v) for v in values) + ']'


def _source(hive: Hive) -> str:
    return Path(hive.source_path).name if hive.source_path else 'a hive file'


def rules_toml(hive: Hive) -> str:
    """The offers, by event: what hive-synapse adds to the model's text, with the
    event's fields filled in. Every parameter is a string; synapse types them."""
    out = [HEADER.format(source=_source(hive), what="the Hive's rules"), '\n[meta]\nversion = 1\n']
    for rule in hive.rules:
        out.append(f'\n[[rules]]\nevent = {_s(rule.event)}\n')
        for offer in rule.offers:
            out.append(f'\n[[rules.offers]]\ntitle = {_s(offer.title)}\n')
            if offer.description:
                out.append(f'description = {_s(offer.description)}\n')
            out.append(f'action = {_s(offer.action)}\n')
            for name in ACTIONS[offer.action].params:
                if name in offer.params:
                    out.append(f'{name} = {_s(offer.params[name])}\n')
    return ''.join(out)


def whitelist_toml(hive: Hive) -> str:
    """hive-actuator's whitelist, in the format it reads (os/crates/hive-actuator/src/whitelist.rs).
    It fails closed: an action no table here allows is denied."""
    out = [HEADER.format(source=_source(hive), what="hive-actuator's whitelist, which fails closed"),
           '\n[meta]\nversion = 2\n',
           '\n[run_command]\nallowed = [\n']
    for c in hive.commands:
        out.append(f'    {{ command = {_s(c.command)}, args = {_list(c.args)} }},\n')
    out.append(']\n')
    out.append(f'\n[service]\nallowed = {_list(hive.services, per_line=True)}\n'
               f'blocked = {_list(hive.blocked_services)}\n')
    out.append(f'\n[apt_remove]\nblocked_packages = {_list(hive.blocked_packages, per_line=True)}\n')
    out.append(f'\n[file_ops]\nallowed_paths = {_list(hive.paths)}\n'
               f'blocked_paths = {_list(hive.blocked_paths, per_line=True)}\n')
    out.append(f'\n[zfs]\nallowed_datasets = {_list(hive.datasets)}\n')
    if hive.delete_snapshot is not None:
        out.append(f'destroy_snapshot_pattern = {_s(hive.delete_snapshot)}\n')
    out.append('\n[misc]\n')
    for permit in PERMITS:
        out.append(f'{permit.replace("-", "_")} = {"true" if permit in hive.permits else "false"}\n')
    out.append('\n[rate_limits]\n')
    for variant, n in hive.limits.items():
        out.append(f'{variant} = {n}\n')
    return ''.join(out)


def compile_hive(app, output_dir: str, source_dir: Optional[str] = None) -> Dict[str, str]:
    """Reads the application and writes rules.toml and whitelist.toml into
    output_dir. Returns the paths written, by name."""
    hive = read_hive(app)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = {}
    for name, text in (('rules.toml', rules_toml(hive)), ('whitelist.toml', whitelist_toml(hive))):
        path = out / name
        path.write_text(text, encoding='utf-8')
        written[name] = str(path)
    return written
