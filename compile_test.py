import sys
sys.path.insert(0, 'src')

from core.parser import QuantumParser
from runtime.game_code_generator import GameCodeGenerator
from core.features.game_engine_2d.src.ast_nodes import SceneNode

print("1. Imports OK")

with open('examples/smw_tilemap_test.q') as f:
    source = f.read()
print("2. File read OK")

parser = QuantumParser(use_cache=False)
ast = parser.parse(source)
print(f"3. Parsed OK - {len(ast.children)} children")

# Find scene
scene = None
for child in ast.children:
    if isinstance(child, SceneNode):
        scene = child
        break

if not scene:
    print("ERROR: No scene found!")
    sys.exit(1)

print(f"4. Scene found: {scene.name}")

gen = GameCodeGenerator()
html = gen.generate(scene, title="SMW Tilemap Test", source_code=source)
print(f"5. Generated HTML: {len(html)} chars")

with open('smw-tilemap-test.html', 'w') as f:
    f.write(html)
print("6. Saved to smw-tilemap-test.html")
