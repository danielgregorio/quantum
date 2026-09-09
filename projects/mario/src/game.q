<?xml version="1.0" encoding="UTF-8"?>
<!--
  Super Mario World - Multi-Scene Game

  Demonstrates Quantum Framework multi-scene architecture:
  - Title screen with press-start transition
  - World map with path-based navigation
  - Playable level (Yoshi's Island 1)
  - Persistent state (lives, score, coins) across scenes

  Prefabs define full semantic behavior — codegen generates matching GDScript.
-->
<q:application id="super-mario-world" type="game" engine="2d">

  <!-- Persistent state across all scenes -->
  <qg:persistent>
    <q:set name="lives" value="5" type="integer" />
    <q:set name="score" value="0" type="integer" />
    <q:set name="coins" value="0" type="integer" />
    <q:set name="yoshi_coins" value="0" type="integer" />
    <q:set name="levels_cleared" value="" type="string" />
  </qg:persistent>

  <!-- ============================================================ -->
  <!-- Shared prefabs (available in all scenes)                     -->
  <!-- ============================================================ -->

  <!-- Coin: collectible item, Area2D, auto-collected on contact -->
  <qg:prefab name="coin" entity-type="item" collectible="true" reward="score:10">
    <qg:sprite id="coin_body" src="assets/sprites/coin_animated.png"
               frame-width="16" frame-height="16"
               tag="coin" body="static" sensor="true">
      <qg:animation name="spin" frames="0,1,2,1" speed="0.12" loop="true" auto-play="true" />
    </qg:sprite>
  </qg:prefab>

  <!-- Rex: patrol enemy, 2-hit stomp (squish then kill), turn cooldown -->
  <qg:prefab name="rex" entity-type="enemy" movement="patrol" move-speed="30"
             defeated-by="stomp" health="2" turn-cooldown="0.15"
             stomp-bounce="-200" reward="score:100" reward-kill="score:200">
    <qg:sprite id="rex_body" src="assets/sprites/rex_walk.png"
               frame-width="20" frame-height="28"
               tag="enemy" body="dynamic" friction="0"
               collision-layer="enemies" collision-mask="world">
      <qg:animation name="walk" frames="0-1" speed="0.15" loop="true" auto-play="true" />
    </qg:sprite>
  </qg:prefab>

  <!-- Question block: hit from below, spawns content, becomes used -->
  <qg:prefab name="qblock" entity-type="block" content="coin" hits="1">
    <qg:sprite id="qblock_body" src="assets/sprites/qblock_animated.png"
               frame-width="16" frame-height="16"
               tag="qblock" body="static">
      <qg:animation name="shine" frames="0,1,2,1" speed="0.15" loop="true" auto-play="true" />
    </qg:sprite>
  </qg:prefab>

  <!-- Rotating block: breakable, tween rotation + toggle collision -->
  <qg:prefab name="rotating_block" entity-type="block" breakable="true">
    <qg:sprite id="rb_body" src="assets/sprites/rotating_block.png"
               frame-width="16" frame-height="16"
               tag="rotating_block" body="static">
      <qg:animation name="spin" frames="0,1,0,1" speed="0.1" loop="false" />
    </qg:sprite>
  </qg:prefab>

  <!-- Yoshi coin: special collectible with shimmer/rotation effect -->
  <qg:prefab name="yoshi_coin" entity-type="item" collectible="true" reward="score:50">
    <qg:sprite id="yc_body" src="assets/sprites/yoshi_coin.png"
               frame-width="16" frame-height="24"
               tag="yoshi_coin" body="static" sensor="true">
      <qg:animation name="rotate" frames="0,1,2,1" speed="0.15" loop="true" auto-play="true" />
    </qg:sprite>
  </qg:prefab>

  <!-- Checkpoint: one-time activation, saves respawn point -->
  <qg:prefab name="checkpoint" entity-type="goal" checkpoint="true">
    <qg:sprite id="cp_body" src="assets/sprites/checkpoint_gate.png"
               tag="checkpoint" body="static" sensor="true" />
  </qg:prefab>

  <!-- Mushroom: powerup item, moves after spawning -->
  <qg:prefab name="mushroom">
    <qg:sprite id="mush_body" src="assets/sprites/mushroom.png"
               width="16" height="16"
               tag="powerup" body="dynamic" bounce="0" friction="0.1">
    </qg:sprite>
  </qg:prefab>

  <!-- Banzai Bill: giant bullet, charge AI (horizontal flight, no gravity) -->
  <qg:prefab name="banzai_bill" entity-type="enemy">
    <qg:sprite id="bb_body" src="assets/sprites/banzai_bill.png"
               width="64" height="64" tag="enemy" body="dynamic"
               collision-layer="enemies" collision-mask="world" />
  </qg:prefab>

  <!-- Piranha Plant: emerges from pipes on timer -->
  <qg:prefab name="piranha_plant" entity-type="hazard">
    <qg:sprite id="pp_body" src="assets/sprites/piranha_plant.png"
               frame-width="16" frame-height="24"
               tag="hazard" body="static" sensor="true"
               collision-layer="enemies" collision-mask="world">
      <qg:animation name="chomp" frames="0-1" speed="0.2" loop="true" auto-play="true" />
    </qg:sprite>
  </qg:prefab>

  <!-- Flying Qblock: oscillates horizontally, drops mushroom when hit -->
  <qg:prefab name="flying_qblock" entity-type="block" flying="true" content="mushroom" hits="1">
    <qg:sprite id="fqb_body" src="assets/sprites/qblock_animated.png"
               frame-width="16" frame-height="16"
               tag="qblock" body="static">
      <qg:animation name="shine" frames="0,1,2,1" speed="0.15" loop="true" auto-play="true" />
    </qg:sprite>
  </qg:prefab>

  <!-- ============================================================ -->
  <!-- Enemy Behaviors (AI + defeat system)                        -->
  <!-- ============================================================ -->

  <qg:enemy prefab="rex">
    <qg:ai type="patrol" speed="30" turn-cooldown="0.15" turn-on-edge="true" facing="left" />
    <qg:defeat by="stomp" health="2" bounce="-200">
      <qg:on-hit score="100" effect="squish" speed-multiply="1.5" />
      <qg:on-kill score="200" effect="puff" />
    </qg:defeat>
  </qg:enemy>

  <qg:enemy prefab="banzai_bill">
    <qg:ai type="charge" speed="90" facing="left" />
    <qg:defeat by="stomp" health="1" bounce="-250">
      <qg:on-kill score="400" effect="puff" />
    </qg:defeat>
  </qg:enemy>

  <qg:enemy prefab="piranha_plant">
    <qg:ai type="emerge" speed="1.5" />
    <qg:defeat by="fire" health="1">
      <qg:on-kill score="100" effect="puff" />
    </qg:defeat>
  </qg:enemy>

  <!-- ============================================================ -->
  <!-- Scenes                                                       -->
  <!-- ============================================================ -->

  <!-- Complex scenes from external files -->
  <qg:scene-include src="scenes/world_map.q" />
  <qg:scene-include src="scenes/yoshi_island_1.q" />

</q:application>
