"""
Game Engine 2D - Builder/Orchestrator

Orchestrates the compilation pipeline:
  ApplicationNode (type="game") → extract scenes/behaviors/prefabs → GameCodeGenerator → HTML file

Usage:
    builder = GameBuilder()
    html = builder.build(app_node)
    builder.build_to_file(app_node, "output.html")
"""

import os
from pathlib import Path
from typing import Optional

from core.ast_nodes import ApplicationNode
from core.features.game_engine_2d.src.ast_nodes import (
    SceneNode, BehaviorNode, PrefabNode,
)
from runtime.game_code_generator import GameCodeGenerator


class GameBuildError(Exception):
    """Error during game build."""
    pass


class GameBuilder:
    """Builds a standalone HTML game from a Quantum game ApplicationNode."""

    def build(self, app: ApplicationNode) -> str:
        """Build HTML string from an ApplicationNode with type='game'.

        The ApplicationNode is expected to have:
        - app.scenes: list of SceneNode
        - app.behaviors: list of BehaviorNode
        - app.prefabs: list of PrefabNode

        These are populated by the parser when processing <q:application type="game">.
        """
        scenes = getattr(app, 'scenes', [])
        behaviors = getattr(app, 'behaviors', [])
        prefabs = getattr(app, 'prefabs', [])

        if not scenes:
            raise GameBuildError("No scenes found in game application")

        valid_behaviors = [b for b in behaviors if isinstance(b, BehaviorNode)]
        valid_prefabs = [p for p in prefabs if isinstance(p, PrefabNode)]

        # Multi-scene: use generate_multi
        if len(scenes) > 1:
            # Find initial scene (first active, or just the first)
            initial_name = scenes[0].name
            for scene in scenes:
                if isinstance(scene, SceneNode) and scene.active:
                    initial_name = scene.name
                    break

            generator = GameCodeGenerator()
            html = generator.generate_multi(
                scenes=[s for s in scenes if isinstance(s, SceneNode)],
                initial=initial_name,
                behaviors=valid_behaviors,
                prefabs=valid_prefabs,
                title=app.app_id,
            )
            return html

        # Single scene: use existing generate for backward compat
        active_scene = scenes[0]
        for scene in scenes:
            if isinstance(scene, SceneNode) and scene.active:
                active_scene = scene
                break

        generator = GameCodeGenerator()
        html = generator.generate(
            scene=active_scene,
            behaviors=valid_behaviors,
            prefabs=valid_prefabs,
            title=app.app_id,
        )
        return html

    def build_to_file(self, app: ApplicationNode, output_path: Optional[str] = None) -> str:
        """Build and write HTML file. Returns the output file path."""
        html = self.build(app)

        if output_path is None:
            output_path = f"{app.app_id}.html"

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(html, encoding='utf-8')

        return str(path.resolve())
