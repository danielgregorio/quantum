"""The event table the rules and the screen compile against is the one the daemons fill in.

quantum/runtime/hive/schema.py lists the events and their fields;
os/crates/hive-common/src/events.rs names and fills them for every
daemon (hive-synapse's offers, hive-cortex's notices to hive-screen). A
field added on one side without the other fails here.
"""

import re
from pathlib import Path

from quantum.runtime.hive.schema import EVENTS

REPO = Path(__file__).resolve().parents[2]
EVENTS_RS = REPO / 'os' / 'crates' / 'hive-common' / 'src' / 'events.rs'


def rust_events():
    text = EVENTS_RS.read_text(encoding='utf-8')
    names = dict(re.findall(r'Event::(\w+) => "([a-z-]+)",', text))
    fields = {variant: re.findall(r'"(\w+)"', body)
              for variant, body in re.findall(r'Event::(\w+) => &\[([^\]]*)\],', text)}
    return {names[v]: f for v, f in fields.items()}


def test_the_same_events_with_the_same_fields():
    rust = rust_events()
    assert set(rust) == set(EVENTS)
    for name, event in EVENTS.items():
        assert rust[name] == list(event.fields), name
