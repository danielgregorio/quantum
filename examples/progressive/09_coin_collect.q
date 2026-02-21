<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 9: Coin Collection

  Tests:
  - Collision events (Mario + Coin)
  - Coin disappears when collected
  - Using tag system and sensor bodies

  Note: Coins use sensor="true" so they detect overlap without physical collision
-->
<q:application id="coin-collect" type="game" engine="2d">
  <qg:scene name="main" width="256" height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />

    <!-- Coin prefab with sensor body for overlap detection -->
    <qg:prefab name="coin">
      <qg:sprite src="assets/smw/sprites/coin_animated.png"
                 frame-width="16" frame-height="16"
                 tag="coin"
                 body="static" sensor="true">
        <qg:animation name="spin" frames="0,1,2,3,2,1" speed="0.12" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <qg:tilemap id="level" src="assets/smw/sprites/stage1_unique.png"
                tile-width="16" tile-height="16">
      <qg:layer name="terrain" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
      </qg:layer>
    </qg:tilemap>

    <!-- Coins to collect -->
    <qg:instance prefab="coin" x="64" y="56" />
    <qg:instance prefab="coin" x="96" y="56" />
    <qg:instance prefab="coin" x="128" y="56" />
    <qg:instance prefab="coin" x="160" y="56" />
    <qg:instance prefab="coin" x="192" y="56" />

    <!-- Mario with coin collection -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="32" y="60"
               frame-width="16" frame-height="24"
               tag="player"
               body="dynamic" controls="arrows" speed="0.4" jump-force="1.2" friction="0">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
      <!-- Collision handler: when touching a coin, destroy the coin -->
      <qg:on-collision with-tag="coin" action="destroy-other" />
    </qg:sprite>
  </qg:scene>
</q:application>
