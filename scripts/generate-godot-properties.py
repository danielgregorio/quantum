#!/usr/bin/env python
"""Generate quantum/runtime/godot/godot_properties.json from Godot's own class reference.

    python scripts/generate-godot-properties.py    # needs the pinned Godot (scripts/godot.py install)

The file lists, for every Godot class a game tag can become, its settable
properties and their types, inherited ones included. The compiler checks
a `gd:` attribute against it: `gd:zoom="2,2"` on a `qg:camera` is a
Vector2 of Camera2D; `gd:zoon` is a compile error that names the
properties Camera2D has. Regenerate when GODOT_VERSION changes.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.etree import ElementTree as ET

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from quantum.runtime.godot_bin import GODOT_VERSION, ensure_godot  # noqa: E402

OUT = REPO / 'quantum' / 'runtime' / 'godot' / 'godot_properties.json'

# The classes the runtime instantiates for a tag (scene_builder.gd).
CLASSES = ['Node', 'CanvasItem', 'Node2D', 'Sprite2D', 'CollisionObject2D', 'PhysicsBody2D',
           'CharacterBody2D', 'StaticBody2D', 'AnimatableBody2D', 'Area2D', 'Camera2D', 'TileMapLayer',
           'AudioStreamPlayer', 'CanvasLayer', 'Control', 'Label', 'CPUParticles2D', 'Line2D']
TYPES = {'float', 'int', 'bool', 'String', 'Vector2', 'Vector2i', 'Color', 'StringName'}
# What the runtime sets from the language's own attributes (x=/y=, the
# controllers' velocity, the fixed collision layers, node names): a gd:
# override would fight it, so these are not in the table.
OWNED = {'name', 'scene_file_path', 'unique_name_in_owner', 'position', 'global_position', 'velocity',
         'collision_layer', 'collision_mask'}


def main() -> int:
    godot = ensure_godot()
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([str(godot), '--headless', '--doctool', tmp, '--no-docbase'],
                       capture_output=True, text=True, timeout=300, check=True)
        docs = Path(tmp) / 'doc' / 'classes'
        classes = {}
        for name in CLASSES:
            root = ET.parse(str(docs / f'{name}.xml')).getroot()
            props = {}
            for m in root.findall('members/member'):
                if m.get('setter') and m.get('type') in TYPES and m.get('name') not in OWNED:
                    props[m.get('name')] = m.get('type')
            # every member name of the class: a game state may not be called like one
            # (GDScript refuses a variable named like a native property, method or signal)
            members = sorted({m.get('name') for m in root.findall('members/member')}
                             | {m.get('name') for m in root.findall('methods/method')}
                             | {m.get('name') for m in root.findall('signals/signal')})
            classes[name] = {'inherits': root.get('inherits'), 'properties': props, 'members': members}
    OUT.write_text(json.dumps({'godot': GODOT_VERSION, 'classes': classes}, indent=1, sort_keys=True) + '\n',
                   encoding='utf-8')
    print(f'wrote {OUT.relative_to(REPO)}: {sum(len(c["properties"]) for c in classes.values())} properties')
    return 0


if __name__ == '__main__':
    sys.exit(main())
