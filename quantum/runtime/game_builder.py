"""
Game Engine 2D - Builder/Orchestrator

Orchestrates the compilation pipeline:
  ApplicationNode (type="game") → quantum.runtime.godot.compile_game → project directory

The only backend is Godot 4: a game builds to a project directory with
.tscn + .gd files (project.godot, export_presets.cfg), which Godot opens,
runs and exports.

Usage:
    builder = GameBuilder()
    builder.build_to_file(app_node)            # projects/<id>/godot/
"""

from typing import Optional

from quantum.core.ast_nodes import ApplicationNode


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
        return self._build_godot(app, [], [], [], output_dir, [])

    def _build_godot(self, app: ApplicationNode, scenes, behaviors, prefabs,
                     output_dir: Optional[str] = None,
                     enemies: list = None) -> str:
        """Build with the Godot 4 backend (returns output directory path)."""
        from quantum.runtime.godot import compile_game

        if output_dir is None:
            output_dir = f"projects/{app.app_id}/godot"
        return compile_game(app, output_dir, source_dir=self.source_dir)

    def build_to_file(self, app: ApplicationNode, output_path: Optional[str] = None) -> str:
        """Build and write the project. Returns the output directory path."""
        return self.build(app, output_dir=output_path)
