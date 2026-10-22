# The RPG assets

From the "JRPG" demo in godotengine/godot-demo-projects
(`2d/role_playing_game`, MIT, copyright 2014-present Godot Engine contributors
and 2007-2014 Juan Linietsky, Ariel Manzur), packed by `scripts/art/rpg.py`:

- `tiles.png`: the demo's tile images (`grid_movement/grid/tiles/`), each one
  flipped or turned as the demo's map places it, one 64 px tile per placement.
- `pawns.png`: the player's two faces on the map, the opponent's, and the key
  (`grid_movement/pawns/`, `grid_movement/grid/tiles/object.png`), and a
  potion, which the demo does not have, drawn by the script (CC0).
- `fighters.png`: the two slimes in the fight, each calm and surprised, and
  their shadow (`combat/combatants/sprites/`).
- `arena.png`: the fight's background (`combat/background/combat_background.png`).

`montserrat_extra_bold.otf` is the demo's font, Montserrat by Julieta
Ulanovsky and the Montserrat project authors, under the SIL Open Font
License 1.1 (https://openfontlicense.org).

`Xolonium-Regular.ttf`, the font of the game in Russian (Montserrat has no
Cyrillic letters), is Xolonium by Severin Meyer, under the SIL Open Font
License 1.1 (`Xolonium-LICENSE.txt`, next to it).

`frame.png` (the dialogue box's frame, a nine-slice picture) and
`banner-en.png`, `banner-pt.png`, `banner-es.png`, `banner-ru.png` ("FIGHT!"
in each language) are drawn for the game by `scripts/art/rpg_extra.py`, in
the fonts above: CC0.

`meadow.ogg` (the map) and `clash.ogg` (the fight) are this project's own
music, written and synthesized by `scripts/art/rpg_music.py`, and dedicated
to the public domain (CC0).
