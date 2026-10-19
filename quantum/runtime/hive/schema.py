"""What the Hive's rule language is: every `qh:` tag, every event, every action.

This table is the single source: the model validates against it, the
reference page is generated from it, and anything with no entry does not
exist. The events are the observations hive-cortex passes to hive-synapse
(`HiveMessage` in os/crates/hive-common/src/messages.rs); the actions are
the `Action` variants hive-actuator runs (actions.rs), under the names of
the variants in kebab-case, so a rule can only offer what the actuator has
a type for.

A rule's texts and parameters may hold `{field}`: a field of the event the
rule is on, filled in by hive-synapse from the event itself, never from the
model's text. Attribute types:

- `text`: a string, placeholders allowed
- `args`: words separated by spaces, each a placeholder or not
- `int`: a number, or a placeholder of a field that is one
- `bool`: true or false
- `words`: one or more names separated by spaces
- `enum:a|b|c`
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class Attr:
    type: str
    default: object = None
    required: bool = False
    doc: str = ''


@dataclass(frozen=True)
class Tag:
    doc: str
    attrs: Dict[str, Attr] = field(default_factory=dict)
    parents: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Field:
    type: str   # text | int
    doc: str


@dataclass(frozen=True)
class Event:
    doc: str
    message: str                      # the HiveMessage variant
    fields: Dict[str, Field]


@dataclass(frozen=True)
class ActionSpec:
    doc: str
    variant: str                      # the Action variant
    params: Dict[str, Attr] = field(default_factory=dict)
    # what a literal use of it is checked against, in the same file:
    # 'command' (a qh:allow command=), 'service', 'package' (not blocked),
    # 'dataset', or a permit name
    checked: str = ''


# ---------------------------------------------------------------- events

EVENTS: Dict[str, Event] = {
    'service-crash': Event(
        'A unit stopped unexpectedly (hive-nerve-journal saw it in the journal).',
        'ServiceCrash',
        {'unit': Field('text', 'the unit, as systemd names it (nginx.service)'),
         'service': Field('text', 'the service name the actuator uses (nginx); absent when the unit is '
                                  'not a .service, and the offers that need it are left out'),
         'exit_code': Field('int', 'how it exited')}),
    'log-anomaly': Event(
        'A unit logs an unusual number of errors.',
        'LogAnomaly',
        {'unit': Field('text', 'the unit, as systemd names it'),
         'service': Field('text', 'the service name, as in service-crash')}),
    'port-conflict': Event(
        'A program could not bind a port another one holds (hive-nerve-network).',
        'PortConflict',
        {'port': Field('int', 'the port'),
         'requester': Field('text', 'the program that failed to bind'),
         'holder': Field('text', 'the program that holds the port')}),
    'disk-low': Event(
        'A filesystem is nearly full.',
        'DiskSpaceLow',
        {'mount': Field('text', 'the mount point'),
         'percent': Field('int', 'how full, in percent'),
         'free_mb': Field('int', 'megabytes free')}),
    'memory-pressure': Event(
        'The system is running low on memory.',
        'MemoryPressure',
        {'free_mb': Field('int', 'megabytes available'),
         'total_mb': Field('int', 'megabytes in all')}),
    'command-observed': Event(
        'A user ran a command the Hive judges dangerous (hive-nerve-process, from the audit log).',
        'CommandObserved',
        {'cmd': Field('text', 'the command line'),
         'program': Field('text', 'the program')}),
    'command-not-found': Event(
        'A user ran a program that is not installed, and a package of that name exists (grove).',
        'CommandNotFound',
        {'command': Field('text', 'what the user typed'),
         'package': Field('text', 'the package that would provide it')}),
}

# ---------------------------------------------------------------- actions

ACTIONS: Dict[str, ActionSpec] = {
    'run-command': ActionSpec(
        'Runs a command. It must match a <qh:allow command=> of this file, argument for argument.',
        'RunCommand',
        {'cmd': Attr('text', required=True, doc='the program'),
         'args': Attr('args', '', doc='its arguments')},
        checked='command'),
    'start-service': ActionSpec('Starts a service (`systemctl start`).', 'StartService',
                                {'service': Attr('text', required=True)}, checked='service'),
    'stop-service': ActionSpec('Stops a service.', 'StopService',
                               {'service': Attr('text', required=True)}, checked='service'),
    'restart-service': ActionSpec('Restarts a service.', 'RestartService',
                                  {'service': Attr('text', required=True)}, checked='service'),
    'reload-service': ActionSpec('Reloads a service.', 'ReloadService',
                                 {'service': Attr('text', required=True)}, checked='service'),
    'enable-service': ActionSpec('Enables a service at boot, and starts it now unless now=false.',
                                 'EnableService',
                                 {'service': Attr('text', required=True), 'now': Attr('bool', True)},
                                 checked='service'),
    'disable-service': ActionSpec('Disables a service at boot, and stops it now unless now=false.',
                                  'DisableService',
                                  {'service': Attr('text', required=True), 'now': Attr('bool', True)},
                                  checked='service'),
    'install-package': ActionSpec('Installs a package through PackageKit, after a safety snapshot.',
                                  'InstallPackage', {'package': Attr('text', required=True)}),
    'remove-package': ActionSpec('Removes a package (never one a <qh:block package=> names), after a '
                                 'safety snapshot; dangerous, so the dashboard asks twice.',
                                 'RemovePackage',
                                 {'package': Attr('text', required=True),
                                  'purge': Attr('bool', False, doc='remove its configuration too')},
                                 checked='package'),
    'update-package-lists': ActionSpec('Refreshes the package lists.', 'UpdatePackageLists'),
    'upgrade-packages': ActionSpec('Upgrades packages, after a safety snapshot.', 'UpgradePackages',
                                   {'packages': Attr('words', '', doc='which; none means all')}),
    'clean-package-cache': ActionSpec('Cleans the package cache.', 'CleanPackageCache'),
    'kill-port-process': ActionSpec('Ends the process holding a port; needs <qh:allow action="kill-port-process"/>.',
                                    'KillPortProcess',
                                    {'port': Attr('int', required=True),
                                     'signal': Attr('int', None, doc='the signal, 15 when not given')},
                                    checked='kill-port-process'),
    'create-snapshot': ActionSpec('Takes a ZFS snapshot of a dataset a <qh:allow dataset=> names.',
                                  'CreateSnapshot',
                                  {'dataset': Attr('text', required=True),
                                   'name': Attr('text', required=True),
                                   'recursive': Attr('bool', True)},
                                  checked='dataset'),
    'list-snapshots': ActionSpec('Lists ZFS snapshots.', 'ListSnapshots',
                                 {'dataset': Attr('text', None, doc='of one dataset; all when not given')},
                                 checked='dataset'),
}

# Every Action variant, under its kebab-case name: what a qh:limit may name.
VARIANTS = ('RunCommand', 'CreateSnapshot', 'RestoreSnapshot', 'ListSnapshots', 'DeleteSnapshot',
            'ShowNotification', 'OpenFile', 'OpenUrl', 'InstallPackage', 'RemovePackage', 'UpdatePackageLists',
            'UpgradePackages', 'StartService', 'StopService', 'RestartService', 'ReloadService', 'EnableService',
            'DisableService', 'CreateDirectory', 'MoveFile', 'CopyFile', 'DeleteFile', 'ChangePermissions',
            'KillPortProcess', 'AddFirewallRule', 'Reboot', 'Shutdown', 'Suspend', 'CleanPackageCache',
            'CleanSystem')


def kebab(variant: str) -> str:
    return ''.join('-' + c.lower() if c.isupper() and i else c.lower() for i, c in enumerate(variant))


LIMITS: Dict[str, str] = {kebab(v): v for v in VARIANTS}

# What <qh:allow action=> may switch on: the actuator's permissions with no
# list behind them.
PERMITS = ('kill-port-process', 'open-url', 'firewall')

# ---------------------------------------------------------------- tags

TAGS: Dict[str, Tag] = {
    'on': Tag(
        'What the Hive offers when an event happens: the qh:offers inside, in order. One per event.',
        {'event': Attr('enum:' + '|'.join(EVENTS), required=True)},
        parents=('application',)),
    'offer': Tag(
        'One thing an administrator may approve for the actuator to do. title= and description= are shown '
        'on the dashboard; action= names what runs, with the attributes that action takes. Any of them may '
        'hold {field}, a field of the event, filled in from the event itself.',
        {'title': Attr('text', required=True),
         'description': Attr('text', ''),
         'action': Attr('enum:' + '|'.join(ACTIONS), required=True)},
        parents=('on',)),
    'allow': Tag(
        'What the actuator may do at all: its whitelist, which fails closed. Exactly one of command= '
        '(with args=: `*` is any one argument; the argument count must match), service=, path=, dataset=, '
        'action= (a permission with no list: kill-port-process, open-url, firewall) or delete-snapshot= '
        '(the snapshot names the Hive may destroy, a pattern).',
        {'command': Attr('text', None, doc='one program'),
         'args': Attr('args', '', doc='its arguments, with command='),
         'service': Attr('words', None, doc='services it may start, stop, restart, reload, enable, disable'),
         'path': Attr('words', None, doc='where files may be created, moved, copied, deleted (patterns)'),
         'dataset': Attr('words', None, doc='ZFS datasets it may snapshot (patterns)'),
         'action': Attr('enum:' + '|'.join(PERMITS), None),
         'delete-snapshot': Attr('text', None, doc='a pattern of snapshot names')},
        parents=('application',)),
    'block': Tag(
        'What the actuator may never do, whatever is allowed: exactly one of service= (patterns), package= '
        '(never removed; patterns) or path= (patterns).',
        {'service': Attr('words', None),
         'package': Attr('words', None),
         'path': Attr('words', None)},
        parents=('application',)),
    'limit': Tag(
        'At most this many of an action a minute, under the actuator\'s overall limit.',
        {'action': Attr('enum:' + '|'.join(LIMITS), required=True),
         'per-minute': Attr('int', required=True)},
        parents=('application',)),
}
