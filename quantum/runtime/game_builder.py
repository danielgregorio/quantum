"""
Game Engine 2D - Builder/Orchestrator

Orchestrates the compilation pipeline:
  ApplicationNode (type="game") → extract scenes/behaviors/prefabs → GodotCodeGenerator → project directory

The only backend is Godot 4: a game builds to a project directory with
.tscn + .gd files (project.godot, export_presets.cfg), which Godot opens,
runs and exports.

Usage:
    builder = GameBuilder()
    builder.build_to_file(app_node)            # projects/<id>/godot/
"""

from typing import Optional

from quantum.core.ast_nodes import ApplicationNode
from quantum.core.features.game_engine_2d.src.ast_nodes import (
    SceneNode, BehaviorNode, PrefabNode, EnemyNode,
)


class GameBuildError(Exception):
    """Error during game build."""
    pass


class GameBuilder:
    """Builds a Godot 4 project from a Quantum game ApplicationNode.

    Args:
        engine: Backend engine. Only 'godot' exists; the argument stays so a
            caller that names the engine keeps working.
    """

    VALID_ENGINES = ('godot',)

    def __init__(self, engine: str = 'godot', source_dir: str = None):
        if engine not in self.VALID_ENGINES:
            raise GameBuildError(
                f"Unknown engine '{engine}'. Valid engines: {', '.join(self.VALID_ENGINES)}"
            )
        self.engine = engine
        self.source_dir = source_dir

    def build(self, app: ApplicationNode, output_dir: Optional[str] = None) -> str:
        """Build the game from an ApplicationNode with type='game'.

        Returns the output directory path (``projects/<id>/godot`` by default).
        """
        scenes = getattr(app, 'scenes', [])
        behaviors = getattr(app, 'behaviors', [])
        prefabs = getattr(app, 'prefabs', [])
        enemies = getattr(app, 'enemies', [])

        if not scenes:
            raise GameBuildError("No scenes found in game application")

        valid_behaviors = [b for b in behaviors if isinstance(b, BehaviorNode)]
        valid_prefabs = [p for p in prefabs if isinstance(p, PrefabNode)]
        valid_enemies = [e for e in enemies if isinstance(e, EnemyNode)]

        return self._build_godot(app, scenes, valid_behaviors, valid_prefabs, output_dir, valid_enemies)

    def _build_godot(self, app: ApplicationNode, scenes, behaviors, prefabs,
                     output_dir: Optional[str] = None,
                     enemies: list = None) -> str:
        """Build with the Godot 4 backend (returns output directory path)."""
        from quantum.runtime.godot_code_generator import GodotCodeGenerator

        if output_dir is None:
            output_dir = f"projects/{app.app_id}/godot"

        generator = GodotCodeGenerator(source_dir=self.source_dir)
        persistent = getattr(app, 'persistent', [])

        if len(scenes) > 1:
            initial_name = scenes[0].name
            for scene in scenes:
                if isinstance(scene, SceneNode) and (getattr(scene, 'initial', False) or scene.active):
                    initial_name = scene.name
                    break

            return generator.generate_multi(
                scenes=[s for s in scenes if isinstance(s, SceneNode)],
                initial=initial_name,
                behaviors=behaviors,
                prefabs=prefabs,
                enemies=enemies or [],
                persistent=persistent,
                output_dir=output_dir,
                project_name=app.app_id,
            )

        active_scene = scenes[0]
        for scene in scenes:
            if isinstance(scene, SceneNode) and scene.active:
                active_scene = scene
                break

        return generator.generate(
            scene=active_scene,
            behaviors=behaviors,
            prefabs=prefabs,
            enemies=enemies or [],
            output_dir=output_dir,
            project_name=app.app_id,
        )

    def build_to_file(self, app: ApplicationNode, output_path: Optional[str] = None) -> str:
        """Build and write the project. Returns the output directory path."""
        return self.build(app, output_dir=output_path)
