<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 5: Coins

  Adds coin prefab, 14 coin instances, state variables,
  coin collection events, and minimal HUD for coin counter.
-->
<q:application id="yoshi-island-1" type="game" engine="2d">
  <qg:scene name="main" width="5120" height="432" viewport-width="256" viewport-height="224" background="#5C94FC">
    <qg:physics gravity-y="1.5" />
    <qg:camera follow="mario" lerp="0.08" bounds="scene" offset-y="-80" />

    <!-- Game state -->
    <q:set name="coins" value="0" type="number" />
    <q:set name="score" value="0" type="number" />

    <!-- Prefabs -->
    <qg:prefab name="coin">
      <qg:sprite src="assets/smw/sprites/coin_animated.png"
                 frame-width="16" frame-height="16"
                 tag="coin" body="static" sensor="true">
        <qg:animation name="spin" frames="0,1,2,3,2,1" speed="0.12" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <!-- Full level background image -->
    <qg:sprite id="level-bg" src="assets/smw/sprites/yoshi-island-1.png"
               x="2560" y="216" width="5120" height="432" />

    <!-- Main ground collision -->
    <qg:sprite id="ground-main" width="5120" height="16" x="2560" y="392"
               tag="terrain" body="static" visible="false" />

    <!-- Collision data -->
    <qg:sprite id="block0" width="16" height="16" x="1912" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block1" width="16" height="16" x="1960" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block2" width="16" height="16" x="2120" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block3" width="32" height="16" x="2240" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block4" width="32" height="16" x="4560" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block5" width="16" height="16" x="4664" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block6" width="32" height="16" x="1824" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block7" width="16" height="16" x="1912" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block8" width="16" height="16" x="1960" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block9" width="32" height="16" x="2112" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block10" width="32" height="16" x="2240" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block11" width="32" height="16" x="4560" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block12" width="32" height="16" x="1824" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block13" width="16" height="16" x="1912" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block14" width="16" height="16" x="1960" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block15" width="32" height="16" x="2112" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block16" width="32" height="16" x="2240" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block17" width="32" height="16" x="4560" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block18" width="32" height="16" x="1824" y="376" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block19" width="16" height="16" x="1912" y="376" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block20" width="16" height="16" x="1960" y="376" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block21" width="32" height="16" x="2112" y="376" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block22" width="32" height="16" x="2240" y="376" tag="terrain" body="static" visible="false" />
    <qg:sprite id="block23" width="32" height="16" x="4560" y="376" tag="terrain" body="static" visible="false" />

    <qg:sprite id="plat2" width="16" height="16" x="216" y="296" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat3" width="32" height="16" x="912" y="296" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat4" width="16" height="16" x="1240" y="296" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat5" width="16" height="16" x="1304" y="296" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat6" width="16" height="16" x="1368" y="296" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat7" width="32" height="16" x="2080" y="296" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat10" width="16" height="16" x="200" y="312" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat11" width="16" height="16" x="888" y="312" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat12" width="16" height="16" x="936" y="312" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat13" width="16" height="16" x="1224" y="312" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat14" width="16" height="16" x="1288" y="312" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat15" width="16" height="16" x="1352" y="312" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat19" width="16" height="16" x="184" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat20" width="16" height="16" x="872" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat21" width="16" height="16" x="1208" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat22" width="16" height="16" x="1272" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat23" width="16" height="16" x="1336" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat27" width="144" height="16" x="4376" y="328" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat28" width="16" height="16" x="856" y="344" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat32" width="16" height="16" x="840" y="360" tag="terrain" body="static" visible="false" />
    <qg:sprite id="plat35" width="16" height="16" x="824" y="376" tag="terrain" body="static" visible="false" />

    <!-- Coins -->
    <qg:instance prefab="coin" x="160" y="288" />
    <qg:instance prefab="coin" x="528" y="224" />
    <qg:instance prefab="coin" x="560" y="224" />
    <qg:instance prefab="coin" x="1600" y="288" />
    <qg:instance prefab="coin" x="2656" y="176" />
    <qg:instance prefab="coin" x="2672" y="176" />
    <qg:instance prefab="coin" x="2688" y="176" />
    <qg:instance prefab="coin" x="2704" y="176" />
    <qg:instance prefab="coin" x="2720" y="176" />
    <qg:instance prefab="coin" x="3600" y="272" />
    <qg:instance prefab="coin" x="3616" y="272" />
    <qg:instance prefab="coin" x="4080" y="288" />
    <qg:instance prefab="coin" x="4096" y="288" />
    <qg:instance prefab="coin" x="4112" y="288" />

    <!-- Mario -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="80" y="350" tag="player"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="1.5" jump-force="5.3" friction="0.15">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
      <qg:on-collision with-tag="coin" action="emit:coin-collected" />
      <qg:on-collision with-tag="coin" action="destroy-other" />
    </qg:sprite>

    <!-- Minimal HUD -->
    <qg:hud position="top-left">
      <div style="color: #FFD700; font-family: monospace; font-size: 14px; text-shadow: 1px 1px #000;">
        COINS: <span id="coin-display">0</span>
      </div>
    </qg:hud>

    <!-- Events -->
    <qg:event name="coin-collected" handler="onCoinCollected" />

    <q:function name="onCoinCollected">
      coins = coins + 1
      score = score + 10
      document.getElementById('coin-display').textContent = coins
    </q:function>

  </qg:scene>
</q:application>
