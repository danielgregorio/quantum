"""The Hive's rule language is registered as a feature: every tag, event and action has an intention and an example.

quantum/core/features/hive_rules/ holds what the other features hold — a
manifest, intentions and a dataset — for the qh: language, whose single
source is quantum/runtime/hive/schema.py. A tag, an event or an action
added to the schema without a line in the primary intention and a hive in
the dataset that uses it fails here; so does an intention that names a tag
the schema no longer has. Each example compiling, or being refused as it
says, is tests/dataset/test_dataset_features.py's.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

from quantum.runtime.hive import schema

FEATURE = Path(__file__).resolve().parents[2] / 'quantum' / 'core' / 'features' / 'hive_rules'
INTENTIONS = sorted((FEATURE / 'intentions').glob('*.intent'))
PRIMARY = (FEATURE / 'intentions' / 'primary.intent').read_text(encoding='utf-8')


def examples(polarity):
    for path in sorted((FEATURE / 'dataset' / polarity).glob('*.json')):
        yield from json.loads(path.read_text(encoding='utf-8'))['examples']


def code_of(example):
    return (example.get('expected_output') or example['input'])['quantum_code']


def tags_in(text):
    return set(re.findall(r'qh:([a-z][a-z-]*)', text))


@pytest.mark.parametrize('path', [FEATURE / 'manifest.yaml'] + INTENTIONS, ids=lambda p: p.name)
def test_the_manifest_and_the_intentions_are_yaml(path):
    assert yaml.safe_load(path.read_text(encoding='utf-8'))


def test_every_tag_has_a_line_in_the_primary_intention():
    assert sorted(set(schema.TAGS) - tags_in(PRIMARY)) == []


def test_the_intentions_name_no_tag_the_language_does_not_have():
    for path in INTENTIONS:
        assert sorted(tags_in(path.read_text(encoding='utf-8')) - set(schema.TAGS)) == [], path.name


def test_every_event_and_action_is_in_the_primary_intention():
    for name in list(schema.EVENTS) + list(schema.ACTIONS):
        assert re.search(rf'\b{re.escape(name)}\b', PRIMARY), name


def test_every_tag_event_and_action_is_used_by_a_positive_example():
    code = '\n'.join(code_of(e) for e in examples('positive'))
    assert sorted(set(schema.TAGS) - tags_in(code)) == []
    for event in schema.EVENTS:
        assert f'event="{event}"' in code, event
    for action in schema.ACTIONS:
        assert f'action="{action}"' in code, action


def test_example_ids_are_unique_and_the_metadata_counts_them():
    ids = [e['id'] for polarity in ('positive', 'negative') for e in examples(polarity)]
    assert len(ids) == len(set(ids))
    meta = json.loads((FEATURE / 'dataset' / 'metadata.json').read_text(encoding='utf-8'))['statistics']
    positive, negative = len(list(examples('positive'))), len(list(examples('negative')))
    assert (meta['positive_examples'], meta['negative_examples'], meta['total_examples']) == (
        positive, negative, positive + negative)
    assert sum(meta['categories'].values()) == positive + negative


def test_every_negative_example_names_the_compile_error():
    for example in examples('negative'):
        assert example['expected_error']['type'] == 'HiveCompileError', example['id']
        assert example['expected_error']['message'], example['id']
