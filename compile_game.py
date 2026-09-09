#!/usr/bin/env python
"""
Direct game compiler - bypasses problematic runtime imports.
"""
import sys
import importlib.util

sys.path.insert(0, 'src')

# Load game_templates directly without triggering runtime/__init__.py
spec = importlib.util.spec_from_file_location('game_templates', 'src/runtime/game_templates.py')
game_templates = importlib.util.module_from_spec(spec)
sys.modules['runtime.game_templates'] = game_templates
spec.loader.exec_module(game_templates)

# Load game_code_generator
spec2 = importlib.util.spec_from_file_location('game_code_generator', 'src/runtime/game_code_generator.py')
game_code_generator = importlib.util.module_from_spec(spec2)
sys.modules['runtime.game_code_generator'] = game_code_generator
spec2.loader.exec_module(game_code_generator)

from core.parser import QuantumParser
from core.features.game_engine_2d.src.ast_nodes import SceneNode

def compile_game(input_file, output_file=None):
    print(f"Compiling: {input_file}")

    with open(input_file) as f:
        source = f.read()

    parser = QuantumParser(use_cache=False)
    ast = parser.parse(source)

    scene = None
    # Game scenes are in ast.scenes
    if hasattr(ast, 'scenes') and ast.scenes:
        scene = ast.scenes[0]
    else:
        # Fallback: check ui_children
        children = getattr(ast, 'children', None) or getattr(ast, 'ui_children', [])
        for child in children:
            if isinstance(child, SceneNode):
                scene = child
                break

    if not scene:
        print("ERROR: No scene found!")
        return False

    gen = game_code_generator.GameCodeGenerator()
    html = gen.generate(scene, title=input_file.split('/')[-1], source_code=source)

    if output_file is None:
        output_file = input_file.rsplit('.', 1)[0].split('/')[-1] + '.html'

    with open(output_file, 'w') as f:
        f.write(html)

    print(f"SUCCESS: {output_file} ({len(html)} chars)")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python compile_game.py <input.q> [output.html]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    if compile_game(input_file, output_file):
        sys.exit(0)
    else:
        sys.exit(1)
