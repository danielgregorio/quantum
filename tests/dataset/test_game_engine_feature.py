"""The game language is registered as a feature: every tag has an intention and an example.

quantum/core/features/game_engine/ holds what the other features hold — a
manifest, intentions and a dataset — for the qg: language, whose single
source is quantum/runtime/godot/schema.py. A tag added to the schema without
a line in the primary intention and a whole game in the dataset that uses it
fails here; so does an intention that names a tag the schema no longer has.
Each example compiling, or being refused as it says, is
tests/dataset/test_dataset_features.py's.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

from quantum.runtime.godot import schema
from quantum.runtime.godot.expressions import _FUNCTIONS

FEATURE = Path(__file__).resolve().parents[2] / 'quantum' / 'core' / 'features' / 'game_engine'
INTENTIONS = sorted((FEATURE / 'intentions').glob('*.intent'))
PRIMARY = (FEATURE / 'intentions' / 'primary.intent').read_text(encoding='utf-8')


def examples(polarity):
    for path in sorted((FEATURE / 'dataset' / polarity).glob('*.json')):
        yield from json.loads(path.read_text(encoding='utf-8'))['examples']


def code_of(example):
    return (example.get('expected_output') or example['input'])['quantum_code']


def tags_in(text):
    return set(re.findall(r'qg:([a-z][a-z-]*)', text))


@pytest.mark.parametrize('path', [FEATURE / 'manifest.yaml'] + INTENTIONS, ids=lambda p: p.name)
def test_the_manifest_and_the_intentions_are_yaml(path):
    assert yaml.safe_load(path.read_text(encoding='utf-8'))


def test_every_tag_has_a_line_in_the_primary_intention():
    assert sorted(set(schema.TAGS) - tags_in(PRIMARY)) == []


def test_the_intentions_name_no_tag_the_language_does_not_have():
    for path in INTENTIONS:
        assert sorted(tags_in(path.read_text(encoding='utf-8')) - set(schema.TAGS)) == [], path.name


def test_every_statement_and_function_is_in_the_primary_intention():
    for statement in schema.STATEMENTS:
        assert f'q:{statement}' in PRIMARY, statement
    for function in _FUNCTIONS:
        assert re.search(rf'\b{function}\b', PRIMARY), function


def test_every_tag_is_used_by_a_whole_game_of_the_dataset():
    used = set()
    for example in examples('positive'):
        used |= set(re.findall(r'<qg:([a-z][a-z-]*)', code_of(example)))
    assert sorted(set(schema.TAGS) - used) == []


def test_the_examples_have_their_own_ids_and_the_metadata_counts_them():
    positive, negative = list(examples('positive')), list(examples('negative'))
    ids = [e['id'] for e in positive + negative]
    assert len(ids) == len(set(ids))
    stats = json.loads((FEATURE / 'dataset' / 'metadata.json').read_text(encoding='utf-8'))['statistics']
    assert (stats['positive_examples'], stats['negative_examples']) == (len(positive), len(negative))
    for example in negative:
        assert example['expected_error']['message'], example['id']
