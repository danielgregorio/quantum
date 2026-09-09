<?xml version="1.0" encoding="UTF-8"?>
<!--
  Yoshi's Island 1 - Playable Level

  Full SMW level with 64 entities: 18 Rex, 12 QBlocks, 14 Coins,
  15 Rotating Blocks, 4 Yoshi Coins, 1 Checkpoint, goal, and deathzone.

  Positions match the manually-tuned Godot project (main.tscn).
  Death sequence uses SMW pattern (pause → timer → iris-out → reload).
-->
<qg:scene name="yoshi-island-1" type="level" initial="true"
          width="5120" height="432"
          viewport-width="256" viewport-height="224"
          background="#5C94FC"
          death-sequence="smw" death-timer="3.0"
          game-over-jingle="assets/sounds/smw_game_over.wav"
          game-over-alphabet="assets/sprites/hud_alphabet.png">

  <!-- Physics with named collision layers -->
  <qg:physics gravity-y="1.5">
    <qg:collision-layer id="1" name="world" />
    <qg:collision-layer id="2" name="enemies" />
  </qg:physics>

  <qg:camera follow="mario" lerp="0.08" bounds="scene" offset-y="-80" />

  <!-- Per-scene state -->
  <q:set name="isDead" value="0" type="number" />
  <q:set name="time_left" value="300" type="number" />

  <!-- Preload textures -->
  <qg:sprite id="_preload_used" src="assets/sprites/qblock_used.png"
             x="-100" y="-100" width="16" height="16" visible="false" />
  <qg:sprite id="_preload_death" src="assets/sprites/mario_death.png"
             x="-100" y="-100" width="16" height="16" visible="false" />

  <!-- ============================================================ -->
  <!-- Sound Effects                                                -->
  <!-- ============================================================ -->
  <qg:sound id="sfx-jump" src="assets/sounds/smw_jump.wav" trigger="player.jump" />
  <qg:sound id="sfx-coin" src="assets/sounds/smw_coin.wav" trigger="coin-collected" />
  <qg:sound id="sfx-stomp" src="assets/sounds/smw_stomp.wav" trigger="enemy-stomped" />
  <qg:sound id="sfx-death" src="assets/sounds/smw_lost_a_life.wav" trigger="mario-died" />
  <qg:sound id="sfx-clear" src="assets/sounds/smw_course_clear.wav" trigger="level-complete" />
  <qg:sound id="sfx-block" src="assets/sounds/smw_message_block.wav" trigger="block-hit" />
  <qg:sound id="sfx-powerup" src="assets/sounds/smw_power-up.wav" trigger="powerup-collected" />
  <qg:sound id="sfx-banzai" src="assets/sounds/smw_banzai_launch.wav" trigger="banzai-launch" />

  <!-- Background Music -->
  <qg:sound id="bgm-level" src="assets/sounds/music/music-map1.wav"
            trigger="scene.start" loop="true" volume="0.5" channel="music" />

  <!-- ============================================================ -->
  <!-- Level background                                             -->
  <!-- ============================================================ -->
  <qg:sprite id="level-bg" src="assets/sprites/yoshi-island-1.png"
             x="2560" y="216" width="5120" height="432" />

  <!-- ============================================================ -->
  <!-- Terrain collision tilemap (loaded from external JSON)        -->
  <!-- ============================================================ -->
  <qg:tilemap id="terrain" src="assets/collision_tileset.tres"
              data-src="assets/tile_map.json"
              tile-width="16" tile-height="16">
    <qg:layer name="terrain" collision="true" />
  </qg:tilemap>

  <!-- ============================================================ -->
  <!-- Question Blocks (8) — positions from main.tscn               -->
  <!-- ============================================================ -->
  <qg:instance prefab="qblock" id="qb1" x="1927" y="327" data-content="mushroom" />
  <qg:instance prefab="qblock" id="qb2" x="1943" y="327" />
  <qg:instance prefab="qblock" id="qb3" x="2503" y="327" />
  <qg:instance prefab="qblock" id="qb4" x="3351" y="247" />
  <!-- qb5-qb8 were blocking pipes — changed to rotating_block -->
  <qg:instance prefab="rotating_block" id="rb16" x="3415" y="391" />
  <qg:instance prefab="rotating_block" id="rb17" x="3431" y="391" />
  <qg:instance prefab="rotating_block" id="rb18" x="3655" y="391" />
  <qg:instance prefab="rotating_block" id="rb19" x="3671" y="391" />
  <qg:instance prefab="qblock" id="qb9" x="3831" y="327" />
  <qg:instance prefab="qblock" id="qb10" x="3895" y="279" />
  <qg:instance prefab="qblock" id="qb11" x="3895" y="343" />
  <qg:instance prefab="qblock" id="qb12" x="3959" y="327" />

  <!-- ============================================================ -->
  <!-- Coins (14) — positions match main.tscn                      -->
  <!-- ============================================================ -->
  <qg:instance prefab="coin" id="coin1" x="160" y="288" />
  <qg:instance prefab="coin" id="coin2" x="528" y="224" />
  <qg:instance prefab="coin" id="coin3" x="560" y="224" />
  <qg:instance prefab="coin" id="coin4" x="1600" y="288" />
  <qg:instance prefab="coin" id="coin5" x="2656" y="176" />
  <qg:instance prefab="coin" id="coin6" x="2672" y="176" />
  <qg:instance prefab="coin" id="coin7" x="2688" y="176" />
  <qg:instance prefab="coin" id="coin8" x="2704" y="176" />
  <qg:instance prefab="coin" id="coin9" x="2720" y="176" />
  <qg:instance prefab="coin" id="coin10" x="3600" y="272" />
  <qg:instance prefab="coin" id="coin11" x="3616" y="272" />
  <qg:instance prefab="coin" id="coin12" x="4080" y="288" />
  <qg:instance prefab="coin" id="coin13" x="4096" y="288" />
  <qg:instance prefab="coin" id="coin14" x="4112" y="288" />

  <!-- ============================================================ -->
  <!-- Rex Enemies (18) — positions from main.tscn, y=370           -->
  <!-- ============================================================ -->
  <qg:instance prefab="rex" id="rex1" x="416" y="370" />
  <qg:instance prefab="rex" id="rex2" x="560" y="370" />
  <qg:instance prefab="rex" id="rex3" x="672" y="370" />
  <qg:instance prefab="rex" id="rex4" x="768" y="370" />
  <qg:instance prefab="rex" id="rex5" x="880" y="370" />
  <qg:instance prefab="rex" id="rex6" x="944" y="370" />
  <qg:instance prefab="rex" id="rex7" x="1088" y="370" />
  <qg:instance prefab="rex" id="rex8" x="1312" y="370" />
  <qg:instance prefab="rex" id="rex9" x="1488" y="370" />
  <qg:instance prefab="rex" id="rex10" x="1728" y="370" />
  <qg:instance prefab="rex" id="rex11" x="1840" y="370" />
  <qg:instance prefab="rex" id="rex12" x="1904" y="370" />
  <qg:instance prefab="rex" id="rex13" x="1968" y="370" />
  <qg:instance prefab="rex" id="rex14" x="2240" y="370" />
  <qg:instance prefab="rex" id="rex15" x="2400" y="370" />
  <qg:instance prefab="rex" id="rex16" x="2528" y="370" />
  <qg:instance prefab="rex" id="rex17" x="2880" y="370" />
  <qg:instance prefab="rex" id="rex18" x="3040" y="370" />

  <!-- ============================================================ -->
  <!-- Banzai Bills (2) — charge from right                        -->
  <!-- ============================================================ -->
  <qg:instance prefab="banzai_bill" id="bb1" x="2000" y="280" />
  <qg:instance prefab="banzai_bill" id="bb2" x="3400" y="300" />

  <!-- ============================================================ -->
  <!-- Piranha Plants (2) — emerge from pipes                      -->
  <!-- ============================================================ -->
  <qg:instance prefab="piranha_plant" id="pp1" x="3408" y="376" />
  <qg:instance prefab="piranha_plant" id="pp2" x="3648" y="376" />

  <!-- ============================================================ -->
  <!-- Flying Qblock (1) — oscillates, drops mushroom              -->
  <!-- ============================================================ -->
  <qg:instance prefab="flying_qblock" id="fqb1" x="1200" y="200" data-content="mushroom" />

  <!-- ============================================================ -->
  <!-- Rotating Blocks (15 + 4 pipe blocks) — cluster at y=264    -->
  <!-- ============================================================ -->
  <qg:instance prefab="rotating_block" id="rb1" x="3384" y="264" />
  <qg:instance prefab="rotating_block" id="rb2" x="3400" y="264" />
  <qg:instance prefab="rotating_block" id="rb3" x="3416" y="264" />
  <qg:instance prefab="rotating_block" id="rb4" x="3432" y="264" />
  <qg:instance prefab="rotating_block" id="rb5" x="3448" y="264" />
  <qg:instance prefab="rotating_block" id="rb6" x="3464" y="264" />
  <qg:instance prefab="rotating_block" id="rb7" x="3480" y="264" />
  <qg:instance prefab="rotating_block" id="rb8" x="3496" y="264" />
  <qg:instance prefab="rotating_block" id="rb9" x="3512" y="264" />
  <qg:instance prefab="rotating_block" id="rb10" x="3528" y="264" />
  <qg:instance prefab="rotating_block" id="rb11" x="3544" y="264" />
  <qg:instance prefab="rotating_block" id="rb12" x="3560" y="264" />
  <qg:instance prefab="rotating_block" id="rb13" x="3576" y="264" />
  <qg:instance prefab="rotating_block" id="rb14" x="3592" y="264" />
  <qg:instance prefab="rotating_block" id="rb15" x="3608" y="264" />

  <!-- ============================================================ -->
  <!-- Yoshi Coins (4)                                              -->
  <!-- ============================================================ -->
  <qg:instance prefab="yoshi_coin" id="ycoin1" x="279" y="271" />
  <qg:instance prefab="yoshi_coin" id="ycoin2" x="1415" y="271" />
  <qg:instance prefab="yoshi_coin" id="ycoin3" x="2871" y="239" />
  <qg:instance prefab="yoshi_coin" id="ycoin4" x="4615" y="271" />

  <!-- ============================================================ -->
  <!-- Checkpoint                                                   -->
  <!-- ============================================================ -->
  <qg:instance prefab="checkpoint" id="checkpoint1" x="2400" y="350" />

  <!-- ============================================================ -->
  <!-- Goal                                                         -->
  <!-- ============================================================ -->
  <qg:sprite id="goal" width="16" height="80" x="4950" y="344"
             color="#00FF00" tag="goal" body="static" sensor="true" />

  <!-- ============================================================ -->
  <!-- Mario — player with SMW physics tuning                      -->
  <!-- ============================================================ -->
  <qg:sprite id="mario" src="assets/sprites/mario_small.png"
             x="80" y="350" tag="player"
             frame-width="16" frame-height="24"
             body="dynamic" controls="arrows" speed="1.5" jump-force="5.3"
             gravity-up="600" gravity-down="1050"
             jump-hold-boost="50" coyote-frames="6" max-fall-speed="240"
             collision-layer="world" collision-mask="world,enemies"
             floor-max-angle="70"
             friction="0.15"
             spin-jump="true">
    <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
    <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
    <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
    <qg:on-collision with-tag="coin" action="emit:coin-collected" />
    <qg:on-collision with-tag="coin" action="destroy-other" />
    <qg:on-collision with-tag="yoshi_coin" action="emit:yoshi-coin-collected" />
    <qg:on-collision with-tag="qblock" action="emit:block-hit" />
    <qg:on-collision with-tag="rotating_block" action="emit:block-hit" />
    <qg:on-collision with-tag="enemy" action="emit:enemy-collision" />
    <qg:on-collision with-tag="hazard" action="emit:enemy-collision" />
    <qg:on-collision with-tag="death" action="emit:fell-in-pit" />
    <qg:on-collision with-tag="goal" action="emit:level-complete" />
    <qg:on-collision with-tag="powerup" action="emit:powerup-collected" />
    <qg:on-collision with-tag="powerup" action="destroy-other" />
  </qg:sprite>

  <!-- ============================================================ -->
  <!-- HUD                                                          -->
  <!-- ============================================================ -->
  <qg:hud sprite-prefix="assets/sprites/hud_">
    <qg:tile sprite="item_box.png" x="112" y="0" />
    <qg:tile sprite="mario_text.png" x="16" y="8" />
    <qg:tile sprite="time_text.png" x="152" y="8" />
    <qg:counter strip="numbers_small.png" align="right" right-edge="232" y="8"
                icon="coin_icon.png" symbol="x_symbol.png"
                bind="{coins}" tint="yellow" intelligent="true" extra-life-at="100" />
    <qg:tile sprite="x_symbol.png" x="24" y="16" />
    <qg:counter strip="numbers_small.png" x="32" y="16" bind="{lives}" tint="yellow" intelligent="true" />
    <qg:collection sprite="coin_icon.png" x="64" y="16" spacing="8" max="5" bind="{yoshi_coins}" />
    <qg:counter strip="numbers_small.png" x="152" y="16" digits="3" bind="{time_left}"
                countdown="true" hurry-at="100" flash="red" tint="yellow" />
    <qg:counter strip="numbers_small.png" align="right" right-edge="232" y="16"
                bind="{score}" tint="yellow" intelligent="true" />
    <qg:hud-behavior target="time_left" event="reach" value="100">
      <qg:action type="emit" event="time-hurry" />
    </qg:hud-behavior>
    <qg:hud-behavior target="time_left" event="reach" value="0">
      <qg:action type="emit" event="time-up" />
    </qg:hud-behavior>
  </qg:hud>

  <!-- ============================================================ -->
  <!-- Death zone                                                   -->
  <!-- ============================================================ -->
  <qg:sprite id="deathzone" width="5120" height="16" x="2560" y="480"
             tag="death" body="static" sensor="true" visible="false" />

  <!-- ============================================================ -->
  <!-- Events                                                       -->
  <!-- ============================================================ -->

  <!-- Coin collection: +10 score, +1 coin counter -->
  <qg:event name="coin-collected">
    <qg:action type="score" amount="10" />
    <qg:action type="set" target="coins" value="{coins+1}" />
  </qg:event>

  <!-- Yoshi coin collection: +50 score, +1 yoshi coin -->
  <qg:event name="yoshi-coin-collected">
    <qg:action type="score" amount="50" />
    <qg:action type="set" target="yoshi_coins" value="{yoshi_coins+1}" />
  </qg:event>

  <!-- Block hit event (sound handled by qg:sound trigger) -->
  <qg:event name="block-hit" handler="onBlockHit" />

  <!-- Enemy collision: stomp detection auto-generated by codegen from rex prefab -->
  <qg:event name="enemy-collision" handler="onEnemyCollision" />

  <!-- Death: handled by death-sequence="smw" on scene -->
  <qg:event name="fell-in-pit" handler="onFellInPit" />

  <!-- Level complete -->
  <qg:event name="level-complete">
    <qg:action type="score" amount="1000" />
    <qg:transition to="world-map" effect="iris-out" duration="1.0" />
  </qg:event>

  <!-- Game over -->
  <qg:event name="game-over">
    <qg:transition to="title" effect="fade" duration="1.0" />
  </qg:event>

</qg:scene>
