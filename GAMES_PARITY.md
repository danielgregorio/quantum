# The game language against Godot 4.4 and Unity 6 — a 2D feature map

> 2026-10-21. A map, not a plan. The Quantum column was checked against
> `quantum/runtime/godot/schema.py` (109 tags), the expression functions of
> `quantum/runtime/godot/expressions.py`, the generated reference
> (`docs/targets/games.md`) and the twelve games in `projects/`. Two claims
> were checked by compiling and running small games in Godot 4.4.1 (§2 and
> §6). The thirteen rows the owner approved on 2026-10-21 have landed, with
> Bricks (`projects/bricks/`), the game written for them, and are counted as
> covered. What comes next is PLAN_GAMES_3.md, approved the same day; the
> rows its phases cover are updated as each lands (Phase 1: nine rows, and
> gaps 1, 2, 4, 7, 27 and 28 below, and the maths of 3; Phase 2, with Siege:
> twelve rows more, and gaps 3, 5, 8, 14, 16, 23, 24, 25, 30 and 31; Phase 3,
> with Crates: nine rows more, and gaps 6, 13, 15, 18, 21, 22 and 26; Phase 4,
> into every game: ten rows more, and gaps 9, 10, 11, 19, 29, 33 and 42;
> Phase 5, with Rally: four rows more, and gaps 32, 35 and 39; Phase 6, a game
> at a time: eleven rows more so far, and gaps 12, 17, 34, 36, 37, 38, 40 and 41).

Each row is one feature a 2D game is made of, as Godot 4.4 and Unity 6 (URP
2D with its packages: 2D Tilemap, Physics 2D, Input System, Cinemachine 3,
Timeline, Localization, Netcode for GameObjects) provide it, and what the
`qg:` language says for it. The Godot column comes from its class reference
(`godot --doctool`, as in `GAMES_GAP_ANALYSIS.md`); the Unity column names
the component, package or API, says "script" where Unity ships nothing, and
marks an asset or add-on as third party. The Quantum column names the tag,
attribute or function, or "—". A feature reached only through a `gd:`
attribute (any property of the Godot node a tag becomes, set once as the
scene is built) is **partial**: it cannot change while the game runs and no
rule reads it. Where both engines leave a feature to scripts (a dialogue
box, an inventory, a world map), the row still counts: the comparison is
with what a person has to write. The question for each row is the earlier
analysis's: would a game written in tags need it, and is there a
declarative shape for it.

- **covered**: the language has it, in some form; the Quantum column says which tag, attribute or function.
- **partial**: it has part of it; the verdict says what is missing.
- **gap**: a game would need it and a tag could say it. Every gap is in the ranked list at the end.
- **by design**: imperative or low-level; a declarative, deterministic, tick-based language should not expose it. The verdict says why.

## 1. Scene structure and prefabs

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Screens and levels | scenes (`.tscn`), `SceneTree` | scenes, `SceneManager` | `qg:scene` (`width=`, `height=`, `background=`, `seed=`); the first one is where the game starts | covered |
| Reusable kinds of things | a scene instanced with `PackedScene.instantiate()` | prefabs | `qg:prefab` (`tag=`, `sheet=`, `frame=`, `hitbox=`, `ai=`) | covered |
| Placing things in a level | the 2D scene editor | the Scene view | `qg:instance prefab= x= y=`; a Tiled object layer places prefabs by class | covered |
| Placing a thing only when a condition holds | script (`queue_free()` in `_ready`) | script (`SetActive(false)`) | `if=` on `qg:instance` and `qg:character` | covered |
| Naming an instance for the rules | node names, `%UniqueName` | serialized references, `GameObject.Find` | `qg:instance name=` (`other.name`, and a name in its scene's expressions) | covered |
| Variants of one kind | inherited scenes | Prefab Variants | `extends=` on `qg:prefab`: all of another but what it says itself (Siege's brute, Crates' barrel); `qg:state` gives one prefab several forms (frame, hitbox, speed, fire) | covered |
| Things made of things, things attached at run time | instanced child scenes, `reparent()`, `RemoteTransform2D` | nested prefabs, `Transform.SetParent` | `qg:attach target= to= dx= dy=` (carried, touching nothing), `qg:detach`, `carrying()` (Crates' key); a `shuttle` carries what stands on it | covered |
| Spawning and removing at run time | `instantiate()` + `add_child()`, `queue_free()` | `Instantiate`, `Destroy` | `qg:spawn prefab= at= x= y= dx= dy=`, `qg:swap`, `qg:destroy target=` | covered |
| Object pooling | script | `UnityEngine.Pool.ObjectPool<T>` | — | by design: an optimisation of the runtime, not a rule of the game |
| Assets declared once | import + `preload()` | the Project window | `qg:tileset`, `qg:spritesheet`, `qg:sound`, `qg:particles`, `qg:item` | covered |
| Streaming assets | `ResourceLoader.load_threaded_request` | Addressables | — | by design: loading is the runtime's job |

## 2. Logic and state

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Variables of a level and of the whole game | script members, autoloads | fields, statics, `DontDestroyOnLoad`, `ScriptableObject` | `q:set` in `qg:scene` (reset on entry) and in `q:application` (the autoload `G`, kept across scenes): numbers, strings, arrays, dictionaries | covered |
| Expressions, conditions, loops | GDScript | C# | `{...}` compiled to GDScript with the Core evaluator's meaning; `q:if`, `q:elseif`, `q:else`, `q:loop` | covered |
| Functions | `func` | methods | `q:function`, `q:call`, `q:return`; local variables and recursion (Chess); directly in `q:application`, every scene's and the prefabs' (Delve's and Keep's `hurt`) | covered |
| Arithmetic and maths | `@GlobalScope` (`sin`, `atan2`, `lerp`...) | `Mathf` | `abs()`, `min()`, `max()`, `round()`, `floor()`, `ceil()`, `sqrt()`, `**`, `sin()`, `cos()`, `atan2()` (degrees), `sort()` | covered |
| Random numbers | `RandomNumberGenerator` (seedable), `randf()` | `Random` (one global state, `Random.InitState`) | `random(a, b)` from the scene's seed; `speed="150..250"`; `qg:spawner` draws | covered |
| Asking the scene: how many, which is nearest, what is here | `get_nodes_in_group()`, script | `FindGameObjectsWithTag`, script | `count(tag)`, `nearest(a, who)`, `distance(a, b)`, `thing_at(tag, x, y)`, `tile_at(col, row)`, `held(item)` | covered |
| Reading a thing's fields | any property | any field | `me.state`, `me.health`, `me.doing`, `me.vx`, `me.vy`, `me.on_floor`, `me.col`, `me.row`, `other.name`, `other.tag`, `p1.health` | covered |
| Reading a thing's position | `position` | `transform.position` | `me.x`, `other.y`, `hero.x` (a thing, a character, or a cursor's point); a field the thing does not have is a compile error | covered |
| Messages between objects | signals | C# events, `UnityEvent`, `SendMessage` | handlers on what happens (`qg:on-*`); rules read state (`if=`, `when=`, `q:if`) | by design: wiring is imperative; a rule reads the state instead |
| A handler when a condition becomes true | a setter or a check in `_process` | a check in `Update` | `qg:when condition=` in a scene: read at the start of every tick, run as it turns true (Bricks' last brick) | covered |
| A script of one's own | GDScript, C#, GDExtension | C# | none: text where statements go is a compile error | by design: what the language cannot say grows a tag |

## 3. Transform and drawing

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Position and rotation | `position`, `rotation` | `Transform` | `x=`, `y=` on `qg:character`, `qg:instance`, `qg:sprite`; `qg:put`; `qg:tween property="x"`, `"y"`, `"rotation"`; `rotate=` on a fly prefab | covered |
| Scale | `scale` (a Vector2) | `localScale` | `scale=` on `qg:prefab` and `qg:character` (the picture only); `qg:tween property=` `scale`, `scale-x`, `scale-y` (from its own size): a squash, a stretch (Siege) | covered |
| Opacity | `modulate.a` | `SpriteRenderer.color` alpha | `qg:tween property="alpha"` | covered |
| Tint | `modulate`, `self_modulate` | `SpriteRenderer.color` | `qg:tween property="tint"` (eased in ticks, from= and to= colours); `gd:modulate="#ff0000"` for a fixed one | covered |
| Shown or hidden by a rule | `visible` | `SpriteRenderer.enabled`, `SetActive` | `visible="{...}"` on a prefab or a character, read every tick (it still collides); `gd:visible` once; alpha to 0; `qg:sprite frame="{...}"` | covered |
| Flipping | `flip_h`, `flip_v` | `flipX`, `flipY` | by the runtime from the facing; `qg:face`; a negative tile number; `flip-v="true"` on a prefab or a character; `gd:flip_h`, `gd:flip_v` on `qg:sprite` | covered |
| Draw order | `z_index`, tree order, `CanvasLayer` | Sorting Layers, Order in Layer, `SortingGroup` | tilemaps in order, `qg:parallax` behind, the HUD over; `layer=` on a prefab or a character; `gd:z_index` once | partial: a layer is fixed, it does not change in play |
| Y-sort for top-down depth | `y_sort_enabled` | Transparency Sort Mode, custom axis | `y-sort="true"` on `qg:scene` (Siege) | covered |
| Sheets of equal frames | `hframes`, `vframes`, `SpriteFrames` | Sprite Editor, slice by cell size | `qg:spritesheet tile="24"` or `tile="8x32"`; `qg:tileset` | covered |
| Atlases of uneven sprites, pivots | `AtlasTexture`, `region_rect`, `offset` | Sprite Atlas, automatic slicing, pivots | equal frames, centred on the hitbox; `scripts/pack-sprites.py` packs frames into a sheet; `gd:offset` on `qg:sprite` | partial: no frame of its own size or pivot |
| A picture with no behaviour | `Sprite2D` | `SpriteRenderer` | `qg:sprite` (its `frame=` may follow an expression); `qg:scene background=` | covered |
| Parallax backgrounds | `Parallax2D` | script | `qg:parallax sheet= scroll= repeat= y=` | covered |
| Nine-slice and tiled sprites | `NinePatchRect`, texture repeat | `SpriteRenderer.drawMode` Sliced, Tiled | `slice=` on `qg:spritesheet`: a frame that stretches to a box, `box=` on `qg:dialogue` and `qg:menu` (the RPG's) | partial: boxes only; no sliced or tiled sprite in the world |
| Pixel-perfect scaling | stretch mode `viewport`, nearest filter | Pixel Perfect Camera (URP 2D) | always: the viewport stretches, textures are filtered nearest | covered |
| Skeletal 2D animation | `Skeleton2D`, `Bone2D`, `Polygon2D` | 2D Animation (`SpriteSkin`, bones, 2D IK) | — | by design: rigs are authored in an editor; the language plays frames |
| Spline shapes, masks, immediate drawing | `Path2D` + `Polygon2D`, `clip_children`, `draw_*` | SpriteShape, `SpriteMask`, `GL` | — (`qg:tile shape=`, `shape=` on a solid prefab) | by design: drawn geometry and draw calls belong to an editor and to code |

## 4. Sprite animation and animation state machines

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Frame animation | `AnimatedSprite2D` + `SpriteFrames` | `Animator` + clips | `qg:animation name= frames= fps=` | covered |
| Animations chosen by what the body does | `AnimationTree` + script | Animator parameters and transitions | the controllers play `idle`, `walk`, `jump`, `fall`, `walk-up`, `walk-down`, `attack` (and `-up`, `-down`); a prefab plays `walk` | covered |
| Play once, and when it ends | `loop` off, `animation_finished` | Loop Time off, an Animation Event, `StateMachineBehaviour.OnStateExit` | `qg:animation loop="false"`, `qg:on-animation-end name=` | covered |
| Events on a given frame | method call tracks, `frame_changed` | Animation Events | `qg:move active=` (a fighter's hit frame) | partial: no handler on a frame of any animation |
| Playing an animation from a rule | `play()` | `Animator.Play`, `SetTrigger` | `qg:play-animation target= name=` (`name=""` gives the body its own back) | covered |
| Animation sets per form; skins | `SpriteFrames` swap | Animator layers, Sprite Library | `qg:animation` inside `qg:state`, `qg:become`; `qg:swap` to another prefab | covered |
| State machines with declared transitions, blend trees | `AnimationNodeStateMachine`, `BlendSpace2D` | Animator Controller, Blend Trees | `qg:state` + `qg:become` in handlers; four directions by name and flip | partial: transitions are rules, not a graph; no blending |
| Fighter moves with frame data | script | script | `qg:move frames= active= reach= at= damage= stun= push=` | covered |

## 5. Tweening, timelines and cutscenes

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Tween a property, with a curve | `Tween.tween_property`, `set_trans`, `set_ease` | none built in (DOTween, third party); USS transitions in UI Toolkit | `qg:tween target= property= to= from= seconds= trans= ease=`; in the game's ticks, stopped while paused, the same on every peer | covered |
| Loops, ping-pong, parallel tweens | `set_loops`, `parallel()` | DOTween `SetLoops`, `Join` | `repeat=` (-1 for ever), `yoyo=`; several `qg:tween`s at once, one per property | covered |
| Tweens in sequence | `chain()`, `tween_interval()` | DOTween `Sequence` | a `qg:tween` inside another's `qg:on-end` plays after it (Bricks: the balls fade, the paddle hops, the next level) | covered |
| When a tween ends | `finished`, `tween_callback()` | DOTween `OnComplete` | `qg:on-end` inside `qg:tween`, `me` the thing it moved | covered |
| Cutscene timelines, keyframes on several properties | `AnimationPlayer` (property, method, audio tracks) | Timeline (`PlayableDirector`; Activation, Animation, Audio, Signal tracks) | `qg:timer after=` + `qg:tween` + `qg:say` | partial: no timeline; steps are timers counted from the scene's start |

## 6. Tilemaps

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Tile layers, levels as text | several `TileMapLayer`s | several `Tilemap`s under a `Grid` | several `qg:tilemap`s, drawn in order; inline CSV rows | covered |
| Solid tiles | TileSet physics layers | `TilemapCollider2D` + `CompositeCollider2D` | `collision="true"` on `qg:tilemap` (a Tiled layer's `collision` property) | covered |
| Tile shapes and one-way tiles | per-tile polygons, `one_way` | per-sprite physics shape, `PlatformEffector2D` | `qg:tile frame= shape=`, `one-way="true"` | covered |
| Tile kinds | custom data layers + script | custom `TileBase` + script | `qg:tile kind="ladder"`, `"water"`, `"ice"`, `"hurt"`; `qg:on-tile kind= cooldown=` | covered |
| Data of one's own per tile | custom data layers | custom tile classes | the four kinds; `tile_at()` gives the number | partial: no property of the game's own |
| Flipped tiles | alternative tiles | tile transform (flip, rotate) | a negative number in the rows; `tile="-n"` in `qg:set-tile`; a Tiled map's flipped and turned tiles (Crates' walls) | covered |
| Auto-tiling | terrains, `set_cells_terrain_connect()` | Rule Tile (2D Tilemap Extras) | — (Tiled's terrain brush draws; the compiler reads the result) | by design: authoring belongs to Tiled |
| Animated tiles | TileSet atlas animation | Animated Tile (2D Tilemap Extras) | `frames=` and `fps=` on `qg:tile`: it and the frames after it in turn (Crates' water) | covered |
| Editing and reading tiles at run time | `set_cell()`, `erase_cell()`, `get_cell_source_id()` | `Tilemap.SetTile`, `GetTile` | `qg:set-tile col= row= tile= layer=` (collision and pathfinding follow; the cells are in the state), `tile_at()` | covered |
| Procedural levels, random tiles | script | Random Tile, script | `q:loop`, `random()` and `qg:set-tile`, `qg:spawn` directly in a scene, as it is entered (run in Godot for this map; no game does it yet) | covered |
| Tiled maps | importers (third party) | SuperTiled2Unity (third party) | `qg:tilemap src="level.tmx"`: CSV layers, an external `.tsx`, kinds from a tile's class, object layers placing prefabs by class | covered |
| More of Tiled | importers | importers | several tilesets per map (each a `qg:tileset` with the same image), flipped and turned tiles, objects of class `zone`, `exit` and `path`, an object's `state`, the map's own properties (`tiled('name')`); CSV layers only (Crates' three rooms) | covered |
| Isometric, hexagonal and non-square grids | `TileSet.tile_shape` | `Grid` cell layout (Hexagon, Isometric) | `shape="hex"` or `"iso"` on `qg:tileset` (`tile="28x32"`): neighbours, ways, a grid walker's keys and a cursor's `cells=` follow (Marches) | covered |

## 7. Physics and collision

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Kinematic bodies | `CharacterBody2D.move_and_slide()` | Kinematic `Rigidbody2D`, `Rigidbody2D.Slide` | the controllers (`gravity=`, `max-fall=`) and `qg:gravity strength=` | covered |
| Static solids and one-way platforms | `StaticBody2D`, `one_way_collision` | a `Collider2D` without a body, `PlatformEffector2D` | solid tiles; `qg:prefab solid="true"` (`shape=` a polygon, `one-way=`) | covered |
| Moving platforms that carry | `AnimatableBody2D` | a kinematic `Rigidbody2D` + script | `ai="shuttle" dx= dy= period=` | covered |
| Rigid bodies | `RigidBody2D` (mass, forces, impulses) | Dynamic `Rigidbody2D`, `AddForce` | — | by design: a rigid-body solver cannot run a tick again (rollback) and is not promised the same on every peer |
| Joints | `PinJoint2D`, `DampedSpringJoint2D`, `GrooveJoint2D` | `HingeJoint2D`, `SpringJoint2D`, `DistanceJoint2D`, `SliderJoint2D`, `WheelJoint2D` | — | by design: they belong to the rigid-body solver |
| Triggers, and touching | `Area2D`, `body_entered`, `area_entered` | `isTrigger`, `OnTriggerEnter2D`, `OnTriggerStay2D` | `qg:zone`, `qg:exit`, a prefab that is not solid; `qg:on-collision with=` (`me`, `other`), `cooldown=` re-runs it while still touching | covered |
| When a contact ends | `body_exited`, `area_exited` | `OnTriggerExit2D`, `OnCollisionExit2D` | `qg:on-separate with=` on a character or a prefab (not when the other is destroyed, nor on a pause) | covered |
| The side of a contact | `KinematicCollision2D.get_normal()` | `ContactPoint2D.normal` | `side=` `top` (a stomp), `bottom` (a bump), `left`, `right` (a shield in front: Siege's ram) | covered |
| Layers and masks | `collision_layer`, `collision_mask` (32 layers) | Layer Collision Matrix, `ContactFilter2D` | fixed: tiles, solids and characters stop bodies (two characters stop at each other, and a platformer stands on its partner's head); things overlap and are told apart by `tag=` | partial: the layers are fixed by kind, not chosen |
| Pushing things | `move_and_slide()` + script | script, or Dynamic bodies | `pushable="true"` on a solid prefab: a grid walker's step pushes it a cell on, when the cell beyond is free (Crates) | covered |
| Slopes | `floor_max_angle`, `floor_snap_length` | `Rigidbody2D.Slide` and its slide-movement settings | `qg:tile shape=` slopes (Robot); `gd:floor_max_angle` | covered |
| Collision shapes | rectangle, circle, capsule, polygon, segment | box, circle, capsule, polygon, edge, composite | `hitbox="WxH"` for bodies and things; polygons for solids and tiles | partial: no circle or capsule (Creeps' capsule is a rectangle) |
| On the floor | `is_on_floor()` | contact checks, `IsTouching` | `me.on_floor` | covered |
| On a wall or a ceiling (wall slides, wall jumps) | `is_on_wall()`, `is_on_ceiling()` | contact normals | `me.on_wall`, `me.on_ceiling` (with `me.on_floor`), for every controller; a wall jump is a `qg:velocity` rule | covered |
| Ray casts | `RayCast2D`, `intersect_ray()` | `Physics2D.Raycast`, `Linecast` | `sees(a, b)`: no solid tile between two things | partial: no first hit, no point of contact |
| Point and area queries | `intersect_point()`, `intersect_shape()`, `ShapeCast2D` | `OverlapPoint`, `OverlapCircle`, `OverlapBox` | `thing_at(tag, x, y)`; `nearest()` with `distance()` | partial: no "every thing within a radius" |
| Surfaces and zones (ice, water, wind, bounce pads, conveyors) | `PhysicsMaterial`, `Area2D` gravity and damp overrides | `PhysicsMaterial2D`, `AreaEffector2D`, `BuoyancyEffector2D`, `SurfaceEffector2D` | `qg:tile kind="ice"`, `"water"`; `qg:bounce height=`; `qg:velocity` from a rule | partial: no zone that pushes |

## 8. Character controllers

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Platformer | script on `CharacterBody2D` (a template) | script (Learn templates, `Rigidbody2D.Slide`) | `controller="platformer"`: `run-speed=`, `accel=`, `jump-height=` or `jump-speed=`, `variable-jump=`, `jump-cut=`, `coyote-frames=`, `jump-sound=`; `fire-action=`, `fire-prefab=` | covered |
| Jump buffering | script | script | `buffer-frames=` on `controller="platformer"` and `buffer=` on `qg:jump` (Hopper) | covered |
| Double jump | script | script | `air-jumps=`, `air-jump-boost=`; `qg:jump air=` | covered |
| Dash, knock-back, springs | script on `velocity` | `Rigidbody2D.linearVelocity` | `qg:velocity x= y=` (on `controller="behavior"`); `qg:bounce` | covered |
| Crouch, ladders, swimming, ice | script | script | a fighter crouches; a `qg:state` with a smaller `hitbox=`; `qg:tile kind=` ladder, water, ice | covered |
| Top-down, eight directions | script (`Input.get_vector()`) | script | `controller="topdown"` (`speed=`, `bounds=`, the stick's strength) | covered |
| Top-down melee | script + `Area2D` | script + trigger | `attack-action=`, `attack-reach=`, `attack-frames=`, `attack-sound=`; `qg:on-hit with=` | covered |
| Grid, cell by cell | script, `AStarGrid2D` | script | `controller="grid"` (`step-frames=`, `diagonal=`) | covered |
| Shoot-'em-up ship | script | script | `controller="ship"` (`axis=`, `fire-action=`, `fire-prefab=`, `fire-every=`, `fire-sound=`) | covered |
| Fighting-game fighter | script | script | `controller="fighter"` (`health=`, `facing=`), `qg:move`, `qg:on-ko` | covered |
| World-map walker | script | script | `controller="map"` (`at=`), `qg:map-node`, `qg:map-path` | covered |
| Rotate and thrust (asteroids, cars) | script | script; `WheelJoint2D` for physical cars | `qg:steer turn= thrust= drag= max=`, a part of `qg:behavior` (Siege's knight) | covered |
| Click to move | `NavigationAgent2D` + script | `NavMeshAgent` + script | `controller="pointer"`: a click walks it by the shortest way round the walls and things, into a thing clicked (Crates' worker) | covered |
| A body made of parts | nodes and scripts | components | `controller="behavior"`: a `qg:behavior` of `qg:gravity`, `qg:walk`, `qg:jump`, `qg:keep-inside`, `qg:wrap`, `qg:face` | covered |

## 9. Game rules: health, shots, pickups

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Health and damage | script | script | `health=` on `qg:prefab`, `qg:damage`, `qg:on-damage`, `qg:on-death` (with `of=` in a scene) | covered |
| Projectiles | script + `Area2D` | script + trigger | `ai="fly"` (`heading=`, `accel=`, `lifetime=`, `walls=`); `fire-prefab=` | covered |
| Aiming in any direction (at the mouse, spread shots) | script | script | `qg:spawn heading="{dx},{dy}"` for a flying prefab, a cursor read by its id (`aim.x`), `atan2()` (Siege) | covered |
| Ricochets | `bounce()` on a collision normal | `PhysicsMaterial2D` bounciness | `walls="bounce"` on a flying prefab (off the tiles); `qg:deflect axis=` or `dx= dy=` from a handler | covered |
| Invulnerability after a hit | a timer + script | script | `cooldown=` on `qg:on-collision`; a blink with `qg:tween property="alpha" repeat=` | covered |
| Pickups and items | script | script | `qg:item` (`max=`, `start=`, `sound=`, `particles=`), `gives=` on a prefab, `qg:give`, `qg:take`, `qg:reset-items`, `held()` | covered |
| Keys and locked doors | script | script | `opens-with=`, `keeps=`, `qg:on-locked` | covered |
| Pits, checkpoints, respawn | script | script | `qg:on-fall`, `qg:checkpoint`, `qg:respawn` | covered |
| Power-ups, stomps, blocks bumped from below | script | script | `qg:state` + `qg:become`; `side="top"`, `side="bottom"`, `qg:bounce`, `qg:swap` | covered |
| Spawners and waves | script, `Timer` | script, coroutines | `qg:spawner` (`every=`, `count=`, `from=`, several prefabs, `along="edges"`, `heading="inward"`, `spread=`) | covered |

## 10. AI and navigation

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Patrol and wander | script | script | `ai="patrol"` (`turns-at="edge"`), `ai="wander"`; `qg:patrol distance=`, `qg:wander` | covered |
| Chase, flee, keep a distance | script | script | `ai="chase"`; `qg:seek way="straight"`, `qg:flee`, `qg:keep-distance min= max=` | covered |
| Pathfinding on a grid | `AStarGrid2D` | A* Pathfinding Project (third party) | `ai="pathfind"`, `qg:seek` (breadth first over the free cells, the same on every peer) | covered |
| Navigation meshes | `NavigationRegion2D`, `NavigationAgent2D` | AI Navigation (`NavMeshSurface`, `NavMeshAgent`; 2D through NavMeshPlus, third party) | the tilemap's cells are the graph | by design: levels are tilemaps; a cell graph is exact and deterministic |
| Costs per terrain | `AStarGrid2D.set_point_weight_scale()` | penalties (A* Pathfinding Project) | `cost=` on `qg:tile`: `ai="pathfind"`, a pointer's click, `qg:travel budget=` and `cost()` take the cheapest way (Marches' forests and marshes) | covered |
| Following a route | `Path2D` + `PathFollow2D` | splines (Splines package) + script | `qg:path points=`, `ai="path"`, `qg:spawn at="path"` | covered |
| Flying and jumping enemies | script | script | `ai="fly"`, `ai="sway"`; `qg:leap height= every= at-wall= when=` | covered |
| Shooting at the player | script | script | `qg:shoot prefab= at= every= range=`; `ai="turret" targets= range= attack= damage=` | covered |
| Sight and line of sight | `Area2D`, `RayCast2D` | trigger, `Physics2D.Linecast` | `sight=`; `sees()`; a part notices only what it sees unless `through-walls="true"` | covered |
| Choosing a behaviour; AI states, boss phases | script; LimboAI (third party) | Behavior package (behaviour graphs), Animator as a state machine | the first part of a `qg:behavior` whose `when=` holds, then `qg:stand`; `me.doing`; `qg:state` on a prefab with `qg:become` | covered |
| Avoidance and separation | `NavigationAgent2D` avoidance (RVO) | `NavMeshAgent` obstacle avoidance | `spacing=` on a prefab: things of its tag keep apart as they move (Siege's raiders) | covered |

## 11. Camera

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Follow | `Camera2D` as a child, or script | `CinemachineCamera` + `CinemachineFollow` | `qg:camera follow=` | covered |
| Dead zone, look-ahead, smoothing | `drag_*_margin`, `position_smoothing_*`; look-ahead by script | `CinemachinePositionComposer` (dead zone, lookahead, damping) | `dead-zone="WxH"`, `lead=`, `smooth=` | covered |
| Bounds | `limit_*` | `CinemachineConfiner2D` (any polygon) | `bounds="tilemap"`; `gd:limit_left=` and the others (Robot) | covered |
| Zoom | `zoom` | orthographic size | `zoom=` | covered |
| Several targets | script | `CinemachineTargetGroup` + `CinemachineGroupFraming` | `follow="p1, p2"`, `fit="true"`, `zoom-min=` | covered |
| Shake | script on `offset` | `CinemachineImpulseSource` + `CinemachineImpulseListener` | `qg:shake frames= strength=` | covered |
| Changing what it follows, moving it in a cutscene | script, `AnimationPlayer` | priorities and blends (`CinemachineBrain`), a Timeline Cinemachine track | `qg:camera-to target= x= y= zoom= seconds= hold= pause=`: there, a while, and back to what it follows (Crates' gates, Delve's wall) | covered |
| A camera per room | script | a confiner per room, script | each room a `qg:scene` with `qg:exit`s (Keep); no camera in a room the size of the screen | partial: no snapping between rooms of one scene |
| Split screen | a `SubViewport` per player | cameras with viewport rects | `player=` on `qg:camera`: a view a player, side by side or in quarters on one machine, each machine its own over the network (Rally) | covered |
| A thing entering or leaving the screen | `VisibleOnScreenNotifier2D` | `OnBecameVisible`, `OnBecameInvisible` | `qg:on-screen-exit` and `qg:on-screen-enter` (`side=`; in a scene with `of=` a tag), worked out in the game's ticks from the camera's view | covered |

## 12. Input

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Named actions | `InputMap` | Input System actions (`InputActionAsset`, `PlayerInput`) | `qg:input action= keys= player=`; defaults `left`, `right`, `up`, `down`, `jump`, `select`, `cancel`, `click` | covered |
| Keyboard and gamepad | `InputEventKey`, `InputEventJoypadButton`, `InputEventJoypadMotion` | `Keyboard`, `Gamepad` | Godot key names; `JoyA`...`JoySelect`, the pad, `JoyLeftStickUp` and the others; player n reads joypad n-1 | covered |
| Analog strength | `get_action_strength()`, `get_vector()` | `ReadValue<Vector2>()` | the ship and top-down controllers read the stick's strength; `strength('right')` in an expression (0 or 1 under the lockstep, where pressed or not travels) | covered |
| Vibration | `Input.start_joy_vibration()` | `Gamepad.SetMotorSpeeds()` | `qg:rumble player= strength= seconds=`, a phone in the hand too (Arena's blast and knock-outs) | covered |
| Mouse buttons and pointer | `InputEventMouseButton`, `get_global_mouse_position()` | `Mouse.current` | `MouseLeft`, `MouseRight`, `MouseMiddle`; `qg:cursor` (`step=`, `grid=`, `sheet=`), `cursor.x`, `cursor.y`, `cursor.col`, `cursor.row` | covered |
| Clicking a thing | `input_event` on a `CollisionObject2D` | `OnMouseDown`, `IPointerClickHandler` | `qg:on-select` (`other` is the thing under the cursor) | covered |
| Right-click on a thing, wheel, hover | `MOUSE_BUTTON_WHEEL_UP`, `mouse_entered` | `Mouse.scroll`, `IPointerEnterHandler` | `qg:on-select action=` with a `qg:input` of `MouseRight`; keys `WheelUp`, `WheelDown`; `hovered()` (Towers sells a tower, and says for how much) | covered |
| Touch | `InputEventScreenTouch`, the mouse emulated from touch | `Touchscreen`, EnhancedTouch | a tap is a click; `qg:touch-button` and `qg:touch-stick` take a finger each | partial: no gestures |
| On-screen buttons and sticks | `TouchScreenButton` | `OnScreenButton`, `OnScreenStick` | `qg:touch-button action=` and `qg:touch-stick` press the game's actions (strength() for the stick), on a touch screen or always (every game has them) | covered |
| On press | `is_action_just_pressed()` | `performed` | `qg:on-input action=`; a press between two ticks is kept for the next one | covered |
| On release | `is_action_just_released()` | `canceled`, Press interaction (Release Only) | `qg:on-input on="release"` | covered |
| Held, and for how long (a run button, a charge shot) | `is_action_pressed()` | Hold interaction, `IsPressed()` | `pressing('run')`, `pressed_for('fire')` (ticks; on the tick it is let go, how long it was), for player 1 or another | covered |
| Sequences (double tap, a fighter's motion inputs) | script | MultiTap interaction, script | `qg:on-input sequence="down, forward, punch" within= player=` (forward the way the character faces; Arena's blast) | covered |
| Rebinding in the game | `InputMap.action_erase_events()`, `action_add_event()` | `PerformInteractiveRebinding()` | `qg:rebind action=` in a menu: the next key, mouse or joypad button pressed, kept between runs (every game's options) | covered |

## 13. Audio

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Sound effects, volume, pitch | `AudioStreamPlayer` (`volume_db`, `pitch_scale`) | `AudioSource.PlayOneShot()` | `qg:sound`, `qg:play sound= volume= pitch=`, `qg:stop` | covered |
| Variation | `AudioStreamRandomizer` | Audio Random Container | `qg:play vary=` (a random pitch, from a source of its own), and `sounds="a, b, c"`: one of several each time (Delve's bones) | covered |
| Overlapping voices | `max_polyphony` | several `AudioSource`s | a `qg:play` with `volume=`, `pitch=` or `vary=` plays in a voice of its own | covered |
| Sounds bound to events | script | script | `jump-sound=`, `fire-sound=`, `attack-sound=`; `sound=` on `qg:item`, `qg:jump`, `qg:leap`, `qg:shoot` | covered |
| Music, crossfading between scenes | a looping player in an autoload, a tween on `volume_db` | `AudioSource.loop`, `AudioMixer` snapshots `TransitionTo()` | `qg:sound loop="true"`; `qg:music sound= fade= volume=`: other music crossfades, the same plays on | covered |
| Changing music inside a scene (a boss) | a tween | snapshots | `qg:music` in a handler: it crossfades there and then (Delve's warden, as the archer first sees a delver) | covered |
| Buses and volume settings (music, effects) | `AudioServer` buses | `AudioMixer` groups, exposed parameters | `bus=` on `qg:sound`; `qg:volume bus= value=`, `volume()`, a menu's `qg:slider bus=`, kept between runs | covered |
| Effects (reverb, low-pass under water) | `AudioEffect*` on buses | mixer effects | — | by design: a DSP chain is low-level; a named preset could come later |
| Positional sound | `AudioStreamPlayer2D` | `AudioSource.spatialBlend` | `at=` on `qg:play`; a thing's own sounds (its fire-sound, a leap's or a shot's) come from where it is (Hopper's bouncer) | covered |
| Adaptive music (layers, changes on the beat) | `AudioStreamInteractive`, `AudioStreamSynchronized` | FMOD, Wwise (third party) | — | gap |

## 14. Particles and visual effects

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| One-shot bursts | `CPUParticles2D` `one_shot` | `ParticleSystem` bursts | `qg:emit particles= at= dx= dy=`; `qg:burst color= count=` | covered |
| Continuous emitters | `GPUParticles2D`, `CPUParticles2D` | `ParticleSystem` | `qg:emitter particles= x= y= width=` | covered |
| Presets and overrides, weather | `ParticleProcessMaterial` | modules | `qg:particles preset=` (puff, sparks, smoke, dust, fire, rain, snow, confetti, stars) with `color=`, `amount=`, `lifetime=`, `speed=`, `size=` | covered |
| Curves, textures, sub-emitters, GPU graphs | 68 properties of `CPUParticles2D`, sub-emitters | modules, VFX Graph | — | by design: presets and five overrides, never the 68 knobs |
| An emitter that follows a thing | a child node | a child GameObject | `particles=` on a prefab or a character (Siege's tower and ram) | covered |
| Lines, beams and trails | `Line2D`, `GPUParticles2D` trails | `LineRenderer`, `TrailRenderer` | `qg:beam from= to= seconds=` (Siege's tower, its aiming line); `trail=` on a prefab (the bolt) | covered |

## 15. Lighting, shaders and post-processing

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| 2D lights | `PointLight2D`, `DirectionalLight2D` | `Light2D` (Spot, Freeform, Sprite, Global) | `qg:light radius= color= energy= flicker=` at a place of a scene, or carried by a character or a prefab (Delve's torches and lanterns) | covered |
| Shadows | `LightOccluder2D`, TileSet occlusion layers | `ShadowCaster2D` | `shadows="true"` on `qg:light`: a dark scene's solid tiles stop it, and a wall opened lets it through (Delve's pillars) | covered |
| Darkening or tinting the whole scene | `CanvasModulate` | a Global `Light2D` | `ambient=` on `qg:scene` (Delve's vault); `gd:modulate` on `qg:scene` | partial: fixed for the scene |
| Normal maps | `CanvasTexture` | sprite secondary textures | — | by design: a lighting detail of the art pipeline |
| Shaders, materials, sprite effects (outline, dissolve) | canvas_item shaders, `VisualShader`, `CanvasItemMaterial` | Shader Graph (Sprite Lit, Unlit), HLSL | — | by design: shaders are code |
| Post-processing and full-screen effects (bloom, vignette, CRT) | `WorldEnvironment` glow (HDR 2D), `BackBufferCopy` | URP Volume (Bloom, Vignette, Color Adjustments), Full Screen Pass Renderer Feature | — | by design: rendering settings and shaders, not rules |

## 16. UI

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| A HUD over the game | `CanvasLayer` + `Control` | Canvas (uGUI), `UIDocument` (UI Toolkit) | `qg:hud position= font= size=` | covered |
| Numbers and text from the state | `Label` + script | `TMP_Text` + script | `qg:counter bind=` or `item=`, `label=`; `qg:text bind=` or `value="{...}"` | covered |
| Bars | `ProgressBar`, `TextureProgressBar` | `Slider` or a filled `Image`; UI Toolkit `ProgressBar` | `qg:bar bind= max= width= height= color=` (a `q:set`, or `p1.health`) | covered |
| Pictures in the HUD (icons, portraits, a logo) | `TextureRect` | `Image` | `qg:icon sheet= frame= scale=` (Keep's heart and key); `qg:inventory`; a dialogue's `portrait=` | covered |
| Text and bars in the world (signs, a floating "+100", a bar over a head) | a `Label` or `Control` in the scene | `TextMeshPro`, a world-space Canvas | `qg:label` over a character or a prefab, or at a place of a scene; `qg:emit text=` floats a number up (Siege) | partial: text, not a bar drawn in the world |
| Placement | anchors, offsets, containers | `RectTransform` anchors, layout groups | `position=`: the four corners, `top-center`, `center`, `bottom-center` | partial: no x and y |
| A HUD shown only sometimes | `visible` | `SetActive` | `if=` on `qg:hud`, `qg:menu` and its items | covered |
| Fonts and sizes | `FontFile`, `SystemFont` | TextMeshPro font assets | `font=` (a `.ttf`) and `size=` on `qg:hud`, `qg:menu`, `qg:dialogue`, `qg:lobby`; `size=` per item | covered |
| Text colour, outlines, rich text, panel styles | `Theme`, `LabelSettings`, `RichTextLabel` BBCode | USS, TextMeshPro rich text | `color=` on `qg:bar`; `gd:modulate` on a `qg:counter` or `qg:text` | partial: no text colour of the language's own, no rich text |
| Menus and screens (title, pause, game over) | `Button`, containers, focus | `Button`, `EventSystem` navigation | `qg:menu` + `qg:button` (`label="{...}"`, `if=`): up, down and select, the mouse, the joypad's A; `qg:menu if="{paused()}"` | covered |
| Text fields | `LineEdit` | `TMP_InputField`, `TextField` | `qg:field bind= label= max-length=` (typing is local to the machine) | covered |
| Sliders, toggles, dropdowns (an options screen) | `HSlider`, `CheckBox`, `OptionButton` | `Slider`, `Toggle`, `TMP_Dropdown` | a toggle is a `qg:button` whose label reads the state | partial: no slider or dropdown |
| Grids and scrolling lists | `GridContainer`, `ScrollContainer`, `ItemList` | `GridLayoutGroup`, `ScrollRect`, `ListView` | `columns=` and `rows=` on `qg:menu`: a grid, the rows beyond scrolled into view with the focus (Arena's keys) | covered |
| Dialogue boxes | Dialogic, Dialogue Manager (third party) | Yarn Spinner, Ink (third party) | `qg:dialogue`, `qg:line who= text=`, `qg:say`, `qg:on-end`, `talking()` | covered |
| Dialogue choices | add-ons | Yarn Spinner options | `qg:choice label= if=` in a `qg:line`, with what it does (Crates' foreman, Keep's end) | covered |
| Portraits and typewriter text | `visible_ratio`, add-ons | `maxVisibleCharacters`, add-ons | `speed=` and `sheet=` on `qg:dialogue`, `portrait=` on `qg:line` | covered |

## 17. Time

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| A fixed tick | `_physics_process`, `physics_ticks_per_second` | `FixedUpdate`, `Time.fixedDeltaTime` | every rule runs in the 60 Hz tick | covered |
| Timers | `Timer` | coroutines, `InvokeRepeating()`, `Awaitable.WaitForSecondsAsync()` | `qg:timer after=`, `every=`, `from=`, `count=` | covered |
| A delay started by a handler (a power-up that runs out, a fuse) | `get_tree().create_timer()`, `await` | `Invoke()`, `WaitForSeconds` | `qg:after ticks=` or `seconds=`, `name=` to start one again; it keeps the names of its handler, waits while paused and rolls back | covered |
| The clock in an expression | `Engine.get_physics_frames()` | `Time.time`, `Time.frameCount` | `ticks()`: the ticks the scene has played, not while paused | covered |
| Cooldowns | script | script | `cooldown=`, `fire-every=`, `every=` on `qg:shoot` and `qg:leap` | covered |
| Pause | `SceneTree.paused`, `process_mode` | `Time.timeScale = 0` | `qg:pause`, `qg:resume`, `paused()`; menus, HUD, camera and `qg:on-input` go on; `qg:say` pauses until the last line | covered |
| Slow motion, hit stop | `Engine.time_scale` | `Time.timeScale` | `qg:time-scale scale= seconds=`: the ticks come further apart, each the same tick, so replays and peers agree | covered |
| Coroutines and frame-time logic | `await`, `_process(delta)` | coroutines, `Update`, `Time.deltaTime` | — | by design: logic outside the fixed tick breaks replays and the lockstep |

## 18. Scene flow

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Changing scene, with a fade | `change_scene_to_file()` + script | `SceneManager.LoadScene()` + script | `qg:goto-scene name= fade=` (at the end of the tick; only the picture fades) | covered |
| Arriving at a door of the next scene | script | script | `qg:exit to= at=` (disarmed until left) | covered |
| A world map, levels unlocked | script | script | `qg:map-node scene=`, `qg:map-path requires=` (against `cleared`) | covered |
| Overlays and additive scenes | another scene added as a child | `LoadSceneMode.Additive` | menus, dialogue and the HUD over a scene | partial: one scene runs at a time |
| Restarting a level | `reload_current_scene()` | `LoadScene()` of the active scene | `qg:goto-scene` to the same scene, `qg:respawn`, `qg:reset-items` | covered |
| Groups | `add_to_group()`, `get_nodes_in_group()` | Tags (one per object), layers | `tag=`; `count()`, `with=`, `qg:on-death of=` | covered |
| One action on every thing of a group | `call_group()` | `FindGameObjectsWithTag()` + a loop | `qg:for-each tag= var=` | covered |
| Quitting | `get_tree().quit()` | `Application.Quit()` | `qg:quit`, `can_quit()` (false in a browser) | covered |
| Loading screens, async loading | `ResourceLoader.load_threaded_request()` | `LoadSceneAsync()` | — | by design: small games; loading is the runtime's job |
| Window size and fullscreen | `DisplayServer.window_set_mode()` | `Screen.fullScreenMode` | the window from the first scene's size; `qg:fullscreen`, `fullscreen()`, kept between runs | covered |

## 19. Persistence

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Values kept between runs (a best score, a setting) | `ConfigFile`, `FileAccess` in `user://` | `PlayerPrefs` | `q:set saved="true"` | covered |
| Save and continue | script + `FileAccess`, `JSON` | script + `JsonUtility`, `persistentDataPath` | `qg:save scene=`, `qg:continue`, `has_save()`, `qg:scene save="true"`; items and the things picked up or opened go in the save | covered |
| Save slots | script | script | `slot=` on `qg:save` and `qg:continue`, `has_save(n)` (Keep's three games) | covered |
| Saving in the middle of a scene | script that serialises nodes | script | the saved scene starts over; the game state and the items are kept | partial: no positions or enemies saved |
| A high-score table | script | script | a saved `q:set` (Drift's best), `sort()` and a slice (`sort(best + [t])[:10]`) | covered |
| In a browser | `user://` on IndexedDB | `PlayerPrefs` on IndexedDB | the same, kept by the browser (`scripts/check-save-in-browser.py`) | covered |
| Cloud saves | — | Cloud Save (Unity Gaming Services) | — | by design: a hosted service, not the language |

## 20. Localization

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| String tables, translating composed text | `Translation` (CSV, PO), `tr()` | String Tables, `LocalizedString`, Smart Strings | `qg:language lang= name=` with `qg:phrase text= as=`; `tr(text)` | covered |
| Choosing the language | `TranslationServer.set_locale()` | `LocalizationSettings.SelectedLocale` | `?lang=`, `--q-lang=`, the system's; `qg:next-language` (kept for the next run); `language()` | covered |
| Interface texts translated by themselves | `auto_translate_mode` | `LocalizeStringEvent` | labels, buttons and dialogue through Godot's translation; `qg:lobby`'s texts come in pt and es | covered |
| Plurals | `tr_n()` | Smart Strings plural formatter | `tr_n(one, other, n)`; `one=`, `few=`, `many=` on `qg:phrase`, as the language counts (the RPG's potions in Russian) | covered |
| Localized pictures and sounds | locale remaps | Asset Tables | `qg:asset name= src=` in a `qg:language`: a sheet's or a sound's file in it (the RPG's banner) | covered |
| Fonts per language, right-to-left text | font fallbacks, `TextServer` | TextMeshPro font fallbacks | `font=` on `qg:language`: every font falls back on it for the letters it lacks (the RPG's Cyrillic); Godot shapes the text | covered |
| The game itself in one language | — | — | only what is shown is translated: peers in different languages play the same game, and an agent's observations carry `lang` | covered |

## 21. Multiplayer and networking

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Several players on one machine | device ids + script | `PlayerInputManager` | `player=` on `qg:input` and `qg:character`; joypad n-1 for player n | covered |
| Online play | the high-level multiplayer API + script | Netcode for GameObjects + script | `qg:multiplayer players=`: every peer runs the whole game in lockstep; only inputs travel | covered |
| Input delay | script | script | `delay=` | covered |
| Rollback | netfox (third party) | Netcode for Entities client prediction | `rollback=` | partial: only scenes of fighters, timers, menus, the HUD, pictures and a camera |
| Tweens and tile edits under rollback | — | — | the scene's tweens are records the rollback saves and runs again; a tilemap saves the cells `qg:set-tile` changed | covered |
| Desync detection | — | — | `check-every=`: a hash of the whole state compared; a difference is reported and fatal | covered |
| Transports | `ENetMultiplayerPeer`, `WebSocketMultiplayerPeer`, `WebRTCMultiplayerPeer` | Unity Transport (UDP, WebSockets) | `transport="enet"` or `"websocket"` | covered |
| Hosting, joining, a lobby | script | `NetworkManager.StartHost()`, `StartClient()`; Multiplayer Services sessions | `qg:host port=`, `qg:join address=`, `qg:leave`, `qg:lobby`; `net_status()`, `net_players()`, `net_player()`; `start=` | covered |
| Browsers playing each other | WebSocket or WebRTC + a server of one's own | Unity Relay + WebSockets | `quantum relay` rooms (`wss://.../pong/ROOM`), `url_param()`; a room is a link | covered |
| Rejoin, late join | `MultiplayerSpawner` replicates for a new peer | scene synchronization on connect | the next to join takes the free seat and catches up 16 times faster | covered |
| Spectators | script | a client with no player object | `qg:watch address=`, the lobby's Watch, `--q-watch=`: no seat, caught up when late | covered |
| Three or more players | any number | any number | `players=` up to any number, `min-players=` and `qg:start-now` (or `--q-players=`) to start with fewer; Bricks is for two to four | covered |
| Authority and ownership | `set_multiplayer_authority()` | ownership, Distributed Authority | — | by design: every peer runs the whole game; nobody owns anything |
| RPCs, synced state, interpolation | `@rpc`, `MultiplayerSynchronizer` | `[Rpc]`, `NetworkVariable`, `NetworkTransform` | — | by design: the state is computed on every peer, never sent |
| Matchmaking and room lists | — | Lobby, Matchmaker (Unity Gaming Services) | — (a room is a link to send) | partial: no list of rooms |
| Names and chat between players | RPCs | RPCs, Vivox | `shared="true"` on `qg:field`: sent with the inputs on Enter, set on every machine on one tick; `qg:menu local="true"` (Bricks' who is who) | covered |
| Testing several peers, latency | — | Multiplayer Play Mode, Network Simulator | `replay_peers()` (N headless Godots under tapes, `latency_ms=`, `net_report=`) | covered |

## 22. Testing and determinism

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| A deterministic game | not promised (GodotPhysics2D, `_process`) | Box2D repeats on one platform with the same inputs | by construction: the fixed tick, `qg:scene seed=`, kinematic movement; what is only seen or heard stays out of the state (a test plays with and without effects) | covered |
| Recording and replaying input | — | `InputEventTrace` | input tapes (`tape_from_holds`), `godot_replay.replay()` | covered |
| Replays as tests | — | — | `tests/godot/`: every game replayed in CI against `quantum_state()` | covered |
| A test framework, headless runs | GUT, GdUnit4 (third party); `--headless` | Unity Test Framework (Edit Mode, Play Mode); `-batchmode` | pytest over replays; `quantum run game.q --check` | covered |
| CI | script | `-runTests` in batch mode | the Laboratory job with the pinned Godot; `games-in-browser` opens every web build in Chromium | covered |
| Agents that play | Godot RL Agents (third party, training) | ML-Agents (training) | `PlaySession`, `quantum play`, `quantum play --mcp` (`play_*`), `reflex` rules, `quantum playtest` | covered |
| Branching a session; a session as a test | — | — | `play_snapshot`, `play_restore`, `play_tape`; kept tapes in `tests/godot/playtests/` | covered |
| Screenshots and frames | Movie Maker mode (`--write-movie`) | Recorder package | `play_frame`; a screenshot of each game in CI | covered |
| Determinism across machines | — | — | Linux is what CI replays on | partial: not promised across architectures |
| Errors before the game runs | GDScript analyzer warnings | the C# compiler | unknown tags, attributes, parents, names, prefabs, sounds and scenes, fields after a dot (`hero.foo`, against the character's controller), actions read by name, and `gd:` properties against Godot's class reference, are errors with the line | covered |

## 23. Export and platforms

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Web | Web export (threads optional since 4.3) | Web (WebGL; WebGPU experimental) | `scripts/export-games.py --preset Web`, without threads, for a static host | covered |
| Linux and Windows | export presets, `--export-release` | Build Profiles | `--preset Linux`, `--preset Windows` | covered |
| macOS | export preset | Build Profile | `--preset macOS` in `scripts/export-games.py`: an unsigned universal .app | covered |
| Android and iOS | export presets | Build Profiles | `--preset Android` (with the Android SDK) and `--preset iOS` (an Xcode project a Mac builds); the touch controls | covered |
| Consoles | third-party porting companies | licensed platform Build Profiles | — | by design: closed SDKs, licensed per developer |
| A headless server | dedicated-server export | Dedicated Server build target | `--q-relay=PORT`: the game hosts without a seat | covered |

## 24. Tooling

| Feature | Godot 4.4 | Unity 6 | Quantum (qg:) | Verdict |
|---|---|---|---|---|
| Visual and animation editors | the Godot editor, the Animation panel | the Unity Editor, the Animation and Animator windows | — (the generated project opens in Godot, but output is never edited) | by design: the game is the `.q`; the editor is Godot's or Tiled's |
| A level editor | the TileMap editor | the Tile Palette | Tiled (`.tmx`), or CSV rows | covered |
| Editor support | the GDScript language server | C# in Visual Studio, Rider, VS Code | `quantum-lsp` and `vscode-quantum` from `schema.py`: completion, hover, required attributes, values | covered |
| A reference that cannot go stale | the class reference | the Scripting Reference | `docs/targets/games.md`, generated from `schema.py`; a test fails when it is stale | covered |
| Hot reload | script and scene sync while running | domain reload; Hot Reload (third party) | — (rebuild with `quantum run`) | gap |
| Debugging | breakpoints, the remote scene tree, Visible Collision Shapes | breakpoints, the Inspector in Play Mode, gizmos | Godot's debugger on the generated GDScript; `play_view` and the `map` | partial: no breakpoint on a line of the `.q` |
| Profiling | the profiler, the visual profiler, monitors | Profiler, Frame Debugger, Memory Profiler | Godot's, on the generated project | by design: performance is the runtime's |
| Playing by hand, a step at a time | — | — | `quantum play rpg` (the console) | covered |

## The count

| Area | covered | partial | gap | by design | rows |
|---|---|---|---|---|---|
| Scene structure and prefabs | 9 | 0 | 0 | 2 | 11 |
| Logic and state | 9 | 0 | 0 | 2 | 11 |
| Transform and drawing | 11 | 3 | 0 | 2 | 16 |
| Sprite animation and animation state machines | 6 | 2 | 0 | 0 | 8 |
| Tweening, timelines and cutscenes | 4 | 1 | 0 | 0 | 5 |
| Tilemaps | 11 | 1 | 0 | 1 | 13 |
| Physics and collision | 10 | 5 | 0 | 2 | 17 |
| Character controllers | 14 | 0 | 0 | 0 | 14 |
| Game rules: health, shots, pickups | 10 | 0 | 0 | 0 | 10 |
| AI and navigation | 10 | 0 | 0 | 1 | 11 |
| Camera | 9 | 1 | 0 | 0 | 10 |
| Input | 13 | 1 | 0 | 0 | 14 |
| Audio | 8 | 0 | 1 | 1 | 10 |
| Particles and visual effects | 5 | 0 | 0 | 1 | 6 |
| Lighting, shaders and post-processing | 2 | 1 | 0 | 3 | 6 |
| UI | 12 | 4 | 0 | 0 | 16 |
| Time | 7 | 0 | 0 | 1 | 8 |
| Scene flow | 8 | 1 | 0 | 1 | 10 |
| Persistence | 5 | 1 | 0 | 1 | 7 |
| Localization | 7 | 0 | 0 | 0 | 7 |
| Multiplayer and networking | 13 | 2 | 0 | 2 | 17 |
| Testing and determinism | 9 | 1 | 0 | 0 | 10 |
| Export and platforms | 5 | 0 | 0 | 1 | 6 |
| Tooling | 4 | 1 | 1 | 2 | 8 |
| **Total** | **201** | **25** | **2** | **23** | **251** |

Of 251 rows, 201 are covered and 25 partial; 2 are gaps, and 23 are left
out by design: four in five covered (146, 42 and 40 when the map was made;
Phase 1 of PLAN_GAMES_3.md covered nine rows, and the clock in an expression,
its `ticks()`, counted late; Phase 2 twelve more, Phase 3 nine more, Phase 4
ten more, Phase 5 four more, Phase 6 eleven so far, and a frame for boxes). The gaps left
are hot reload, the last of Phase 6's list, and adaptive music. The rows
left out by design are mostly the rigid-body solver, shaders and post-
processing, what belongs to an editor, and the networking machinery that
lockstep makes unnecessary.

## New gaps this map finds

Not in the approved list and not by design. Ranked by how many kinds of
game need them, the most useful for the next genre first; each with the
smallest tag that would say it, and who asks for it. Every **gap** row
above is in this list, and so are many **partial** ones.

1. **A delay started by a handler.** *Done: PLAN_GAMES_3.md, Phase 1.* `<qg:after ticks="600">...</qg:after>` inside a handler, and `ticks()` (ticks since the scene began) in expressions. Every genre: a power-up that runs out, a bomb's fuse, a respawn after a pause, a lap time.
2. **A handler when a condition becomes true.** *Done: PLAN_GAMES_3.md, Phase 1.* `<qg:when condition="{count('enemy') == 0}">` in a scene (in a prefab, with `me`). Wave and puzzle games: a wave cleared, a room solved, a score reached, without testing it in every handler that changes it.
3. **Aiming.** *Done: PLAN_GAMES_3.md, Phases 1 and 2.* `heading="{dx},{dy}"` on `qg:spawn` for an `ai="fly"` prefab (as `qg:deflect dx= dy=` sets it later), and `sin()`, `cos()`, `atan2()` in expressions. Twin-stick and bullet-pattern shooters, a bow aimed with the mouse.
4. **Fields checked at compile time.** *Done: PLAN_GAMES_3.md, Phase 1.* A field after a dot that the thing does not have (`hero.foo`) is a compile error naming the fields it has. Every game: it is the language's own promise.
5. **Text and bars in the world.** *Done: PLAN_GAMES_3.md, Phase 2.* `<qg:label x= y= value=>` in a scene (on a prefab, following it), and `text=` on `qg:emit` for a number that floats up. RPGs and brawlers (damage numbers), adventures (signs), networked games (names over the players).
6. **Pushable things.** *Done: PLAN_GAMES_3.md, Phase 3.* `pushable="true"` on a solid prefab: a character walking into it moves it, a cell on a grid, unless something stops it. Box puzzles, puzzle rooms in an adventure.
7. **Held actions, and how far.** *Done: PLAN_GAMES_3.md, Phase 1.* `pressing('run')`, `pressed_for('fire')` (ticks) and `strength('right')` in expressions (`held()` is taken by items). Charge shots, a run button, hold-to-confirm, analog speed in a rule.
8. **Rotate and thrust.** *Done: PLAN_GAMES_3.md, Phase 2.* `<qg:steer turn= thrust= drag=>`, a part of `qg:behavior`: left and right turn the body, up pushes it the way it points. Asteroids-likes, top-down racing.
9. **An options screen.** *Done: PLAN_GAMES_3.md, Phase 4.* `bus=` on `qg:sound` with `<qg:volume bus= value=>` (kept between runs), `<qg:slider bind= min= max=>` in a `qg:menu`, and `<qg:fullscreen>`. Every game that ships.
10. **Touch controls and phones.** *Done: PLAN_GAMES_3.md, Phase 4.* `<qg:touch-button action= x= y=>` and a touch stick that press the game's own actions (so replays and peers see them); Android and iOS presets in `scripts/export-games.py`. Mobile browsers and phones.
11. **Save slots.** *Done: PLAN_GAMES_3.md, Phase 4.* `slot=` on `qg:save`, `qg:continue` and `has_save()`; later, a save in the middle of a scene kept as the scene's input tape and replayed. RPGs and long adventures.
12. **2D lights and shadows.** *Done: PLAN_GAMES_3.md, Phase 6, for Delve's vault (`ambient=` for darkness=).* `<qg:light radius= color=>` on a character or a prefab, `darkness=` on `qg:scene`, shadows from solid tiles; only seen, like the camera. Caves, horror, stealth.
13. **Camera direction.** *Done: PLAN_GAMES_3.md, Phase 3.* `<qg:camera-to target= x= y= zoom= seconds=>`, then back to `follow=`. Cutscenes, a boss's entrance, showing the door a lever opened.
14. **Lines, beams and trails.** *Done: PLAN_GAMES_3.md, Phase 2.* `<qg:beam from= to= color= width=>` between two things, `trail=` on a prefab. Laser turrets (Towers' ray turret), grappling hooks, a fast ship's wake.
15. **Click to move.** *Done: PLAN_GAMES_3.md, Phase 3.* `controller="pointer"`: the character walks, by the shortest way over the free cells, to where its `qg:cursor` selects. Point-and-click adventures, tactics.
16. **Jump buffering.** *Done: PLAN_GAMES_3.md, Phase 2.* `buffer-frames=` on `controller="platformer"` and on `qg:jump`: a press just before landing still jumps. Every platformer.
17. **The other mouse button, the wheel, hover.** *Done: PLAN_GAMES_3.md, Phase 6, in Towers: `WheelUp`/`WheelDown`, and `hovered()` for hover.* `action=` on `qg:on-select` (`cancel` for a right-click), `MouseWheelUp` and `MouseWheelDown` in `keys=`, `qg:on-select on="hover"`. Strategy (selling a tower, as Towers' README asks), point-and-click (look or use).
18. **Dialogue choices, portraits, typewriter text.** *Done: PLAN_GAMES_3.md, Phase 3.* `<qg:choice label=>` holding actions inside a `qg:line`, `portrait=` on `qg:line`, `speed=` on `qg:dialogue`. RPGs, visual novels.
19. **HUD layout and pictures.** *Done: PLAN_GAMES_3.md, Phase 4.* `bottom-left` and `bottom-right`, `color=` on HUD items, `if=` on `qg:hud`, and `<qg:icon sheet= frame=>` in a HUD. Every game's HUD; a title with a logo.
20. **Characters that block each other.** *Not a gap: PLAN_GAMES_3.md's Phase 6 found it so already.* A character is a body on the layer tiles and solids are on: two stop at each other, and a platformer stands on its partner's head (`tests/godot/test_godot_bodies.py`; Rally's cars bump). Co-op platformers, sports.
21. **Things made of things.** *Done: PLAN_GAMES_3.md, Phase 3.* `<qg:attach target= to= dx= dy=>` (and `qg:detach`), and `extends=` on `qg:prefab`. A carried item, a turret on a tank, a family of enemies that differ in one number.
22. **Animated tiles.** *Done: PLAN_GAMES_3.md, Phase 3.* `frames=` and `fps=` on `qg:tile`. Water, lava and torches in any tile game.
23. **Emitters on things.** *Done: PLAN_GAMES_3.md, Phase 2.* `particles=` on a prefab or a character, kept going where it is. An engine's flame, a burning enemy, a carried torch.
24. **Keeping apart.** *Done: PLAN_GAMES_3.md, Phase 2.* `spacing=` on a prefab: things of one tag keep that far from each other as they move. Swarms, crowds of enemies, strategy units.
25. **Squash and stretch, visibility, depth.** *Done: PLAN_GAMES_3.md, Phase 2.* `scale-x` and `scale-y` for `qg:tween`, `visible="{...}"` and `flip-v=` on prefabs and characters, `layer=` for draw order, and `y-sort="true"` on `qg:scene` (the `gd:` attribute promoted). Every game's juice; depth in top-down games.
26. **More of Tiled.** *Done: PLAN_GAMES_3.md, Phase 3.* Zones, exits and paths drawn as Tiled objects (a rectangle of class `zone`, a polyline as a `qg:path`), object and tile properties of the game's own, several tilesets per map, flipped tiles. Large levels drawn wholly in Tiled.
27. **Functions for every scene.** *Done: PLAN_GAMES_3.md, Phase 1.* `q:function` directly in `q:application`. Games with several levels that share rules.
28. **Sorting.** *Done: PLAN_GAMES_3.md, Phase 1, as the Core's `sort(list)`.* `sorted(list)` in expressions. High-score tables, turn order in tactics.
29. **Rebinding keys.** *Done: PLAN_GAMES_3.md, Phase 4.* `<qg:rebind action=>` in a menu: the next key pressed becomes the action's, kept between runs. Desktop releases, accessibility.
30. **Collision sides left and right.** *Done: PLAN_GAMES_3.md, Phase 2.* `side="left"` and `side="right"` on `qg:on-collision`, as `qg:on-screen-exit` has. Switches hit from the side, bumpers, shields.
31. **Flying things that bounce off tiles.** *Done: PLAN_GAMES_3.md, Phase 2.* `walls="bounce"` on `ai="fly"`, with the cell it hit in reach of `tile_at()`. Ricochet shots, a ball in a level of tiles.
32. **Split screen.** *Done: PLAN_GAMES_3.md, Phase 5, with Rally.* `player=` on `qg:camera`, one view per player. Local versus racing, co-op that splits up.
33. **Grids and lists in menus.** *Done: PLAN_GAMES_3.md, Phase 4.* `columns=` on `qg:menu`, scrolling past the screen. Level select, a shop, an inventory screen.
34. **Music and sounds inside a scene.** *Done: PLAN_GAMES_3.md, Phase 6, for Delve's warden (the crossfade and `sounds=`; layers that come in, not yet).* `qg:music` as an action (a crossfade inside a scene, layers that come in), and `sounds="a, b, c"` on `qg:play` (one drawn each time). A boss fight's music, footsteps.
35. **Input sequences and vibration.** *Done: PLAN_GAMES_3.md, Phase 5 (Arena's blast).* `qg:on-input sequence="down, right, punch" within=` and `<qg:rumble player= strength= seconds=>`. Fighting games (motion inputs), any game on a gamepad.
36. **Sound in place.** *Done: PLAN_GAMES_3.md, Phase 6, for Hopper's bouncer.* `at=` on `qg:play`: softer, and to one side, the farther the thing is from the middle of the screen. Large levels.
37. **Costs per terrain.** *Done: PLAN_GAMES_3.md, Phase 6, for Marches.* `cost=` on `qg:tile` for `ai="pathfind"` and `qg:seek`. Strategy and tactics maps (mud, roads).
38. **Plurals, localized assets, fonts per language.** *Done: PLAN_GAMES_3.md, Phase 6, for the RPG in Russian.* Plural forms on `qg:phrase`, `src=` per language on a sheet or a sound, `font=` on `qg:language`. Translated games with counts, voices or a script Latin fonts lack.
39. **Names and messages between players.** *Done: PLAN_GAMES_3.md, Phase 5 (Bricks' who is who).* `shared="true"` on a `qg:field`: its text travels with the inputs when it is entered, not as it is typed. Networked games that show who is who, or let the players talk.
40. **Nine-slice pictures.** *Done: PLAN_GAMES_3.md, Phase 6, for the RPG's dialogues and fight menu.* `slice=` on `qg:spritesheet`, for boxes that stretch. Dialogue boxes, framed menus.
41. **Isometric and hexagonal maps.** *Done: PLAN_GAMES_3.md, Phase 6, for Marches (hexes; diamonds tested, no game yet).* `shape="hex"` or `"iso"` on `qg:tileset`, with neighbours and pathfinding to match. Strategy and tactics games.
42. **macOS builds.** *Done: PLAN_GAMES_3.md, Phase 4.* A `macOS` preset in `scripts/export-games.py`. Desktop releases.
43. **Hot reload.** `quantum run game.q --watch`: rebuild on save and come back to the same tick from the session's tape. Whoever writes a game.

## What Quantum has that neither engine has

Both engines can be made to do each of these with enough script and
discipline. Neither does them by construction, and none of them is a
setting there.

- **Determinism by construction.** All logic runs in the fixed 60 Hz tick; the only random source is the scene's seed (`qg:scene seed=`, `random()`); movement is the runtime's own kinematics, never a rigid-body solver. What is only seen or heard (`qg:camera`, `qg:particles`, `qg:shake`, how `qg:play` sounds) never enters the state, and a test proves it by playing a game with and without its effects.
- **Replays as tests.** An input tape and a tick count give the whole state back (`quantum.runtime.godot_replay.replay()`, `tape_from_holds`, `quantum_state()`). Every game in `projects/` is replayed in CI (`tests/godot/`); a mechanic is a number a tape reproduces, such as a 64 px jump.
- **Every name checked before the game runs.** An unknown tag, attribute or parent, an undeclared name, a prefab, sound or scene that does not exist, text where statements go, and a `gd:` property Godot's class reference does not list (`godot_properties.json`) are compile errors with the line. (A field after a dot is the hole this map found: gap 4.)
- **Multiplayer from one declaration.** `qg:multiplayer players=` makes any game a lockstep game; nothing else in it knows. `check-every=` compares a hash of the whole state and reports a desync instead of drifting; `rollback=` runs ahead on guessed input; a player who leaves is replaced by the next to join, who catches up from the inputs; `quantum relay` lets browsers meet; `replay_peers()` tests N peers headless.
- **A protocol for agents.** `PlaySession`, `quantum play`, the MCP tools `play_*` and the browser bridge `window.quantumPlay` let an agent play any game a step at a time, from what a player would see (`quantum_view()`, the `map`, `events`), with `reflex` rules between steps, snapshots to branch, and the session saved as a replay test. `quantum playtest` sends an agent after each game's goal in `projects/games.json`.
- **One file per game, and no script.** A game is `projects/<name>/<name>.q`, tags and expressions only; `/games/<name>/source/` shows it with every tag linked to the reference.
- **A genre kit in the language.** Seven controllers (one of them a body of parts), ten `ai=` kinds and eight enemy parts, items and locks (`qg:item`, `opens-with=`), exits that arrive at a named door (`qg:exit at=`), a world map (`qg:map-path requires=`), saves (`qg:save`), a lobby (`qg:lobby`). In both engines each is a script, a template or a third-party asset.
- **One schema for everything around it.** The reference (`docs/targets/games.md`), the editors (`quantum-lsp`, `vscode-quantum`) and the feature's dataset of games and refusals (`quantum/core/features/game_engine/`) are generated from `schema.py` or checked against it, so none of them can fall behind the compiler.
- **Translations that leave the game alone.** `qg:language` changes only what is shown, so peers in different languages play the same game, and an agent can be told the screen in any of them.
