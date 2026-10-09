# The game language against Godot's 2D surface — a gap analysis

> 2026-10-09. Method: Godot 4.4.1's own class reference, dumped with
> `godot --doctool`, for the classes a 2D game is made of (58 classes,
> ~1,800 properties/methods/signals), crossed with `quantum/runtime/godot/schema.py`
> (38 tags, 140 attributes, 12 actions). The question for each area is not
> "do we expose this?" but "would a game written in tags need it, and is
> there a declarative shape for it?" — Godot's surface is imperative; most of
> it is not meant to be mirrored.

## Reading the verdicts

- **covered**: the `qg:` language has it, in some form.
- **gap**: a game would need it and a tag can say it; worth adding when a game asks.
- **by design**: imperative or low-level; a declarative language should not expose it (or should, only through a higher-level tag).

## 1. Transform and drawing (`Node2D`, `CanvasItem`, `Sprite2D`)

| Godot | `qg:` | Verdict |
|---|---|---|
| `position` | `x`, `y` on character/instance/exit; `me.x`/`me.y` **not readable in expressions** | gap: expressions cannot read a thing's position |
| `rotation`, `scale`, `skew`, `flip_v` | — (only `flip_h`, by the runtime, from the facing) | gap, small: `rotation=`/`scale=` on sprites and prefabs; a `qg:tween` to change them |
| `visible`, `modulate`, `z_index`, `y_sort_enabled` | — | gap: `visible="{expr}"`, `tint=`, `layer=` (draw order); y-sort for top-down |
| `texture`, `hframes/vframes`, `frame`, `region_rect`, `offset`, `centered` | sheet + `frame` (square tiles only) | gap: non-square frames, an offset; a sprite larger than one tile |
| `draw_*` (60 methods), `material`, shaders, lights (`PointLight2D`, `CanvasModulate`) | — | by design (a `qg:light` could come later for a game that needs darkness) |

## 2. Bodies and collisions (`CharacterBody2D`, `Area2D`, `CollisionObject2D`, `RigidBody2D`, casts)

| Godot | `qg:` | Verdict |
|---|---|---|
| `velocity`, `move_and_slide`, `is_on_floor/wall/ceiling`, floor snap, slopes | inside the three controllers; `run-speed`, `jump-height`, `gravity`, `max-fall`, `coyote-frames`, `variable-jump` | covered for the three genres; **gap**: `me.velocity`, `me.on_floor` in expressions |
| `floor_max_angle`, `floor_constant_speed` (slopes), `platform_on_leave` | — | gap when a level has slopes; the lift already carries |
| `area_entered/exited`, `body_entered/exited` | `qg:on-collision` (enter + cooldown re-fire), `qg:exit` | covered; **gap**: an *on-leave* handler (`qg:on-separate`) — doors that close behind you |
| `collision_layer/mask`, `one_way_collision` | fixed layers (1 characters, 2 things), `one-way=` | covered by convention; a `qg:collision-layer` only when a game needs things that pass through other things |
| `get_overlapping_areas/bodies`, `RayCast2D`, `ShapeCast2D` | used inside the runtime (edge detection, "still touching") | **gap**: queries in expressions — `nearest('enemy')`, `count('coin')`, `distance(me, other)`, `sees(me, other)` (a ray) |
| `RigidBody2D` (mass, forces, impulses, joints) | — | by design: kinematic only; a game with physics puzzles would reopen this |
| `input_pickable`, `mouse_entered`, `input_event` | — | gap: `qg:on-click` on a thing (menus, point-and-click) |
| `VisibleOnScreenNotifier2D` (`screen_entered/exited`) | the runtime kills a `fly` off-screen | gap, small: `qg:on-screen`/`qg:off-screen` handlers |

## 3. Camera (`Camera2D`)

| Godot | `qg:` | Verdict |
|---|---|---|
| `limit_*`, follow (a child of the target) | `follow=`, `bounds="tilemap"` | covered |
| `drag_*_margin`, `drag_horizontal/vertical_enabled` (dead zone) | — | gap: `dead-zone="WxH"` |
| `position_smoothing_*`, `limit_smoothed` | off (determinism) | gap, cosmetic: `smooth=` (does not change the simulation) |
| `zoom`, `offset`, `rotation` | — | gap: `zoom=`, look-ahead (`lead=`), and a `qg:camera-to` action for cutscenes |
| `anchor_mode`, `process_callback`, `custom_viewport` | — | by design |

## 4. Tiles (`TileMapLayer`, `TileSet`)

| Godot | `qg:` | Verdict |
|---|---|---|
| layers, `set_cell`, CSV | inline CSV, Tiled `.tmx` layers | covered |
| physics per tile, `collision_enabled` | per layer (`collision=`) | gap: per-tile kinds — solid, one-way, ladder, water, ice, hurt — from Tiled tile properties (`class`) |
| terrains / auto-tiling (`set_cells_terrain_*`) | — | gap, authoring: Tiled does it; the compiler reads the result |
| navigation layers (`NavigationAgent2D`, 26 props) | — | gap when an enemy must path around walls (today chase is a straight line) — `ai="pathfind"` |
| `erase_cell`, `set_cell` at run time | — | gap: a `qg:set-tile` action (breakable terrain, doors drawn as tiles) |
| `get_used_rect`, `local_to_map` | pixel size for the camera and the fall line | covered internally |

## 5. Animation (`AnimatedSprite2D`, `AnimationPlayer`, `Tween`)

| Godot | `qg:` | Verdict |
|---|---|---|
| frames, fps, loop, `play/stop/pause` | `qg:animation` (frames, fps; chosen by what the body does) | covered for idle/walk/jump/walk; **gap**: `loop="false"` + `qg:on-animation-end` (attack, death frames), `qg:play-animation` action |
| `animation_finished`, `frame_changed` | — | gap (same) |
| `Tween` (26 methods: property, ease, trans, loops, chain, parallel) | — | gap: `qg:tween target= property= to= over= ease=` as an action; the most-asked "juice" primitive |
| `AnimationPlayer` (keyframed tracks, method calls) | — | by design: a tween action covers 90 %; keyframe timelines would be a `qg:timeline` for cutscenes |

## 6. Sound (`AudioStreamPlayer`, `AudioStreamPlayer2D`)

| Godot | `qg:` | Verdict |
|---|---|---|
| `play`, `stop`, `stream` | `qg:sound` + `qg:play` | covered |
| `volume_db`, `pitch_scale`, `bus`, `max_polyphony` | — | gap: `volume=`, `pitch=` on `qg:play`; random pitch is the usual ask |
| loop, `finished` | — | gap: `qg:music` (looping, cross-fade on scene change) and `qg:stop` |
| 2D positional (`AudioStreamPlayer2D`, attenuation) | — | by design for a screen-sized game; `qg:play at="other"` later |

## 7. Particles (`CPUParticles2D`, 68 properties)

| Godot | `qg:` | Verdict |
|---|---|---|
| one-shot burst | `qg:burst` (color, count) | covered, minimally |
| continuous emitters (fire, rain, smoke), gravity, spread, scale/color curves, texture | — | gap: a `qg:particles` *declaration* (named presets: puff, sparks, smoke, rain) and `qg:emit name=` — never the 68 knobs |

## 8. Time (`Timer`, `SceneTree.paused`, `Engine.time_scale`)

| Godot | `qg:` | Verdict |
|---|---|---|
| `Timer` (`wait_time`, `one_shot`, `timeout`) | `qg:timer after=/every=/count=` | covered |
| `paused`, `process_mode` | — | gap: `qg:pause`/`qg:resume` actions and a pause scene (every game ships one) |
| `time_scale` | — | gap, small: slow motion as an action (`qg:time-scale`) |
| `SceneTree.create_timer` (await) | — | by design: `qg:timer` and `after=` cover it |

## 9. Input (`Input`, `InputMap`)

| Godot | `qg:` | Verdict |
|---|---|---|
| actions, `is_action_pressed/just_pressed`, key binding | five fixed actions, `qg:input action= keys=`, `qg:on-input` | covered; **gap**: *named* actions (`action="attack"`, `"dash"`) instead of five enums |
| `is_action_just_released`, `get_action_strength`, `get_vector` (analog) | — | gap: `qg:on-release`, analog strength for gamepads |
| joypad (buttons, axes, vibration), mouse, touch | keyboard only | gap: `keys=` accepting `JoyA`, `MouseLeft`; touch = click for a web export |
| `parse_input_event`, device management | the replay harness | by design |

## 10. UI (`CanvasLayer`, `Control`, `Label`, `RichTextLabel`, `Button`, `ProgressBar`)

| Godot | `qg:` | Verdict |
|---|---|---|
| labels bound to state | `qg:hud` (3 positions) + `qg:counter`/`qg:text` | covered, minimally |
| placement (`anchor_*`, `offset_*`, `size`), fonts, themes | — | gap: `x=`/`y=`/`anchor=` on HUD items, `font=`/`size=`/`color=` |
| `ProgressBar`/`TextureProgressBar` | — | gap: `qg:bar bind="health" max="{...}"` (health bars, boss bars) |
| `RichTextLabel` (bbcode, `visible_characters`, typewriter) | — | gap: `qg:dialogue` with paging and typewriter (`visible_ratio`) — Keep did it with `qg:text` |
| `Button`, focus, `gui_input` | — | gap: `qg:menu` / `qg:button action=` — title screens, options, pause |
| `qg:image` (a static sprite in the HUD: icons, portraits) | — | gap |

## 11. Scene flow (`SceneTree`, `Node`)

| Godot | `qg:` | Verdict |
|---|---|---|
| `change_scene_to_*`, `reload_current_scene` | `qg:goto-scene`, game state in `G` | covered |
| groups (`get_nodes_in_group`, `call_group`) | tags (`things` by tag) | covered; a `qg:for-each tag=` action (freeze all enemies) is the missing half |
| `quit` | — | gap, small: `qg:quit` for a desktop build |
| signals between nodes, `call_deferred`, `await` | handlers | by design |
| `Node.process_mode`, `_process` vs `_physics_process` | all physics | by design (determinism) |
| `RemoteTransform2D`, `Marker2D`, `Path2D`+`PathFollow2D` | — | gap: `ai="path"` along a `qg:path` (patrol routes, rail enemies) |
| `Parallax2D`/`ParallaxBackground` | — | gap, cosmetic: `qg:background src= scroll=` layers |

## 12. Persistence and data (`FileAccess`, `JSON`, `ConfigFile`)

| Godot | `qg:` | Verdict |
|---|---|---|
| read/write files | `saved="true"` on game state | covered for scores and flags; **gap**: save slots with the current scene and position (`qg:save slot=`, `qg:load`) |
| `JSON` | `game.json` | internal |

## 13. What has no counterpart in Godot and is ours

Replay tapes and `quantum_state()` dumps, the seeded scene RNG as the only
random source, compile-time checks of every name, tag and reference, the
Tiled object layer placing prefabs by class, `qg:exit`/`at=` arrival,
`qg:map-node`/`qg:map-path requires=`, `if=` on instances. These are the
language's reason to exist; Godot has nothing to compare them with.

## The count

Of the areas above: **covered** 14, **gap** 31, **by design** 12. The
gaps cluster into five families, in the order a fourth game would hit them:

1. **The world in expressions** — `me.x`, `me.velocity`, `nearest()`, `count()`, `distance()`, `sees()`. Nothing else unlocks real AI or rules.
2. **Juice** — `qg:tween`, particle presets, sound volume/pitch, `qg:music`, camera dead zone/zoom/look-ahead, parallax. Each is one tag over one Godot node.
3. **UI** — placement and fonts for the HUD, `qg:bar`, `qg:dialogue`, `qg:menu`/`qg:button`, pause. The three games have no title screen.
4. **Input** — named actions, release, gamepad, mouse/touch.
5. **Content** — per-tile kinds, `qg:set-tile`, paths, pathfinding, animation end events, save slots.

And the one that is not a Godot gap but a language gap, repeated from the
plan's closing notes: `qg:behavior` composed from tags, so a fourth
controller is written in the language rather than in the runtime. Godot's
`CharacterBody2D` surface (15 properties, 18 methods) is exactly the set
such a behavior tag would expose, as `qg:gravity`, `qg:move`, `qg:jump`,
`qg:face`, `qg:bounds`.

## Postscript: `gd:` attributes

The analysis above led to one general mechanism before any of the families:
`gd:name="value"` on a game tag forwards a property to the Godot node the tag
becomes, checked at compile time against Godot's class reference (see
`docs/targets/games.md`, "gd: attributes"). It covers, with no new tag, the
*property-shaped* gaps in the tables: camera zoom and smoothing, sound
volume and pitch, `modulate`/`visible`/`z_index`/`scale`/`rotation`,
`y_sort_enabled`, slope settings on a body, `layer` on the HUD. It covers
none of the others — queries in expressions, tweens, handlers, UI widgets —
which need a tag with semantics of its own. The rule: a `gd:` attribute used
by a second game is promoted to a `qg:` attribute.
