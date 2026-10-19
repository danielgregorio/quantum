"""os/config/hive/rules.toml and whitelist.toml are written from os/config/hive/hive.q, and committed as written.

scripts/generate-hive-config.py compiles hive.q (the Hive's rules, in
Quantum) to the two files hive-synapse and hive-actuator load; hive-synapse
embeds rules.toml as its built-in rules. A file edited by hand, or a hive.q
changed without regenerating, fails here: run
`python scripts/generate-hive-config.py`.
"""

import importlib.util
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]


def generator():
    spec = importlib.util.spec_from_file_location(
        'generate_hive_config', REPO / 'scripts' / 'generate-hive-config.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_hive_config_is_current():
    gen = generator()
    for name, text in gen.build().items():
        assert (gen.OUT / name).read_text(encoding='utf-8') == text, (
            f'os/config/hive/{name} is stale: run python scripts/generate-hive-config.py')


def test_the_rules_synapse_embeds_are_the_committed_ones():
    rules = (REPO / 'os' / 'crates' / 'hive-synapse' / 'src' / 'rules.rs').read_text(encoding='utf-8')
    assert 'include_str!("../../../config/hive/rules.toml")' in rules
