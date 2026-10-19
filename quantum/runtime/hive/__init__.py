"""The Hive's rules: a `q:application type="hive"` to what hive-synapse and hive-actuator load.

- `schema.py` says which tags, events and actions exist. An unknown one is a
  compile error with its line.
- `model.py` reads the XML elements against the schema and checks what a
  file promises against itself: a placeholder names a field the event has,
  of the right type; an offer is one the whitelist in the same file would
  let the actuator run.
- `compiler.py` writes `rules.toml` (the offers, for hive-synapse) and
  `whitelist.toml` (the actuator's whitelist, in the format it already
  reads).

The daemons keep the final word: hive-synapse fills the placeholders from
the event and never from the model's text, and hive-actuator checks every
action against the whitelist before running it.
"""

from quantum.runtime.hive.compiler import compile_hive, rules_toml, whitelist_toml  # noqa: F401
from quantum.runtime.hive.errors import HiveCompileError  # noqa: F401
from quantum.runtime.hive.model import read_hive  # noqa: F401
