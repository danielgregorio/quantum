"""The Hive's screen in Quantum: `q:application type="screen"` and its `qs:` tags.

What hive-screen (Quantum OS) draws on the machine's screen and what
happens in it when the Hive's events arrive, compiled to screen.toml, a
font sheet and the sprite sheets. Laboratory tier.
"""

from quantum.runtime.screen.compiler import compile_screen, screen_toml, write_font
from quantum.runtime.screen.errors import ScreenCompileError
from quantum.runtime.screen.model import Screen, read_screen

__all__ = ['ScreenCompileError', 'Screen', 'compile_screen', 'read_screen', 'screen_toml', 'write_font']
