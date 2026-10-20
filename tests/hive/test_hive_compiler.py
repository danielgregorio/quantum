"""The Hive's rules compile from qh: tags to what the daemons load, and what the compiler refuses.

A `q:application type="hive"` is the Hive's rules (what hive-synapse offers
on an event) and hive-actuator's whitelist, in tags. quantum/runtime/hive
reads it against its schema and writes rules.toml and whitelist.toml. A
promise the file cannot keep is refused with the line: a placeholder of a
field the event lacks, or an offer its own whitelist would refuse.
"""

import tomllib
from pathlib import Path

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.hive import HiveCompileError, compile_hive, read_hive
from quantum.runtime.hive.schema import ACTIONS, EVENTS, LIMITS, TAGS, VARIANTS, kebab

REPO = Path(__file__).resolve().parents[2]

GOOD = '''<q:application id="x" type="hive">
  <qh:on event="service-crash">
    <qh:offer title="Restart {service}" description="{unit} stopped (exit {exit_code})"
              action="restart-service" service="{service}" />
    <qh:offer title="Logs of {service}" action="run-command" cmd="journalctl" args="-n 50 -u {service}" />
  </qh:on>
  <qh:on event="port-conflict">
    <qh:offer title="Free port {port}" action="kill-port-process" port="{port}" />
  </qh:on>
  <qh:allow command="journalctl" args="-n 50 -u *" />
  <qh:allow service="nginx redis-server" />
  <qh:block service="hive-*" />
  <qh:allow path="/home/*" />
  <qh:allow dataset="rpool/ROOT/*" />
  <qh:allow delete-snapshot="hive-*" />
  <qh:allow action="kill-port-process" />
  <qh:limit action="kill-port-process" per-minute="2" />
</q:application>'''


def parse(text: str, tmp_path: Path, name: str = 'hive.q'):
    source = tmp_path / name
    source.write_text(text, encoding='utf-8')
    return QuantumParser(use_cache=False).parse_file(str(source))


def wrapped(body: str) -> str:
    return f'<q:application id="x" type="hive">\n{body}\n</q:application>'


def test_a_hive_compiles_to_the_rules_and_the_whitelist(tmp_path):
    written = compile_hive(parse(GOOD, tmp_path), str(tmp_path / 'out'))
    rules = tomllib.loads(Path(written['rules.toml']).read_text(encoding='utf-8'))
    whitelist = tomllib.loads(Path(written['whitelist.toml']).read_text(encoding='utf-8'))

    assert [r['event'] for r in rules['rules']] == ['service-crash', 'port-conflict']
    restart, logs = rules['rules'][0]['offers']
    assert restart == {'title': 'Restart {service}', 'description': '{unit} stopped (exit {exit_code})',
                       'action': 'restart-service', 'service': '{service}'}
    # every parameter is a string: synapse types it after filling the fields in
    assert logs['args'] == '-n 50 -u {service}'
    assert rules['rules'][1]['offers'][0]['port'] == '{port}'

    assert whitelist['run_command']['allowed'] == [{'command': 'journalctl', 'args': ['-n', '50', '-u', '*']}]
    assert whitelist['service'] == {'allowed': ['nginx', 'redis-server'], 'blocked': ['hive-*']}
    assert whitelist['file_ops'] == {'allowed_paths': ['/home/*'], 'blocked_paths': []}
    assert whitelist['zfs'] == {'allowed_datasets': ['rpool/ROOT/*'], 'destroy_snapshot_pattern': 'hive-*'}
    assert whitelist['misc'] == {'kill_port_process': True, 'open_url': False, 'firewall': False,
                                 'set_hostname': False, 'set_keyboard': False, 'set_screen_level': False,
                                 'set_network': False}
    assert whitelist['rate_limits'] == {'KillPortProcess': 2}


def test_the_whitelist_fails_closed_when_nothing_is_allowed(tmp_path):
    hive = read_hive(parse(wrapped(''), tmp_path))
    from quantum.runtime.hive import whitelist_toml
    whitelist = tomllib.loads(whitelist_toml(hive))
    assert whitelist['run_command']['allowed'] == []
    assert whitelist['service']['allowed'] == []
    assert whitelist['misc'] == {'kill_port_process': False, 'open_url': False, 'firewall': False,
                                 'set_hostname': False, 'set_keyboard': False, 'set_screen_level': False,
                                 'set_network': False}


def test_the_os_hive_compiles(tmp_path):
    source = REPO / 'os' / 'config' / 'hive' / 'hive.q'
    hive = read_hive(QuantumParser(use_cache=False).parse_file(str(source)))
    assert {r.event for r in hive.rules} >= {'service-crash', 'command-not-found', 'port-conflict'}


REFUSED = [
    ('an unknown tag', '<qh:rule />', '<qh:rule> is not a hive tag'),
    ('an offer outside qh:on', '<qh:offer title="x" action="update-package-lists" />', 'goes inside <qh:on>'),
    ('an event the Hive does not report',
     '<qh:on event="full-moon"><qh:offer title="x" action="update-package-lists" /></qh:on>',
     'event="full-moon" is not one of'),
    ('an action the actuator lacks',
     '<qh:on event="disk-low"><qh:offer title="x" action="reboot" /></qh:on>',
     'is not an action the actuator has'),
    ('an attribute the action does not take',
     '<qh:on event="disk-low"><qh:offer title="x" action="update-package-lists" foo="1" /></qh:on>',
     "has no attribute 'foo'"),
    ('a parameter the action needs',
     '<qh:on event="service-crash"><qh:offer title="x" action="restart-service" /></qh:on>',
     'needs service='),
    ('a field the event lacks',
     '<qh:on event="service-crash"><qh:offer title="Restart {svc}" action="update-package-lists" /></qh:on>',
     'not a field of service-crash (it has: unit, service, exit_code)'),
    ('a text field where a number goes',
     '<qh:on event="port-conflict"><qh:offer title="x" action="kill-port-process" port="{holder}" /></qh:on>'
     '<qh:allow action="kill-port-process" />',
     'port= is a number; {holder} of port-conflict is text'),
    ('a command no allow permits',
     '<qh:on event="disk-low"><qh:offer title="x" action="run-command" cmd="df" args="-h" /></qh:on>',
     'which no <qh:allow command=> permits'),
    ('a placeholder argument without a * in the allow',
     '<qh:on event="service-crash"><qh:offer title="x" action="run-command" cmd="journalctl" '
     'args="-u {service}" /></qh:on><qh:allow command="journalctl" args="-u nginx" />',
     'which no <qh:allow command=> permits'),
    ('a service a block names',
     '<qh:on event="disk-low"><qh:offer title="x" action="restart-service" service="sshd" /></qh:on>'
     '<qh:allow service="sshd" /><qh:block service="ssh*" />',
     'which a <qh:block service=> blocks'),
    ('a service no allow permits',
     '<qh:on event="disk-low"><qh:offer title="x" action="restart-service" service="nginx" /></qh:on>',
     'which no <qh:allow service=> permits'),
    ('a permission the file does not give',
     '<qh:on event="port-conflict"><qh:offer title="x" action="kill-port-process" port="{port}" /></qh:on>',
     'needs <qh:allow action="kill-port-process"/>'),
    ('a dataset no allow permits',
     '<qh:on event="disk-low"><qh:offer title="x" action="list-snapshots" dataset="tank/data" /></qh:on>',
     'which no <qh:allow dataset=> permits'),
    ('a package a block names',
     '<qh:on event="disk-low"><qh:offer title="x" action="remove-package" package="libc6" /></qh:on>'
     '<qh:block package="libc6" />',
     'which a <qh:block package=> blocks'),
    ('a q: statement', '<q:set name="x" value="1" />', 'not part of the hive language'),
    ('text where declarations go', '<qh:on event="disk-low">if full then clean</qh:on>', 'declarations, not script'),
    ('two rules on one event',
     '<qh:on event="disk-low"><qh:offer title="x" action="update-package-lists" /></qh:on>'
     '<qh:on event="disk-low"><qh:offer title="y" action="update-package-lists" /></qh:on>',
     'two <qh:on event="disk-low">'),
    ('a rule with nothing to offer', '<qh:on event="disk-low" />', 'offers nothing'),
    ('an allow of two things', '<qh:allow service="nginx" path="/tmp/*" />', 'takes exactly one of'),
    ('args without a command', '<qh:allow service="nginx" args="-h" />', 'args= goes with command='),
    ('a limit twice',
     '<qh:limit action="install-package" per-minute="5" /><qh:limit action="install-package" per-minute="1" />',
     'two <qh:limit action="install-package">'),
    ('a limit of nothing', '<qh:limit action="install-package" per-minute="0" />', 'per-minute= is at least 1'),
]


@pytest.mark.parametrize('body,message', [(b, m) for _, b, m in REFUSED], ids=[w for w, _, _ in REFUSED])
def test_what_the_compiler_refuses(body, message, tmp_path):
    with pytest.raises(HiveCompileError) as info:
        read_hive(parse(wrapped(body), tmp_path))
    assert message in str(info.value)
    assert ':2:' in str(info.value) or ':3:' in str(info.value), 'the error names the line'


def test_action_and_limit_names_are_the_kebab_case_of_the_actuators_variants():
    assert kebab('RunCommand') == 'run-command'
    assert kebab('UpdatePackageLists') == 'update-package-lists'
    for name, spec in ACTIONS.items():
        assert spec.variant in VARIANTS and kebab(spec.variant) == name
    assert set(LIMITS) == {kebab(v) for v in VARIANTS}


def test_every_event_and_action_is_an_enum_choice_of_its_tag():
    assert TAGS['on'].attrs['event'].type == 'enum:' + '|'.join(EVENTS)
    assert TAGS['offer'].attrs['action'].type == 'enum:' + '|'.join(ACTIONS)
