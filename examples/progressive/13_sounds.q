<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 13: Sounds

  Tests:
  - Sound effects (jump, coin)
  - Background music
  - Sound triggers

  Note: Requires audio files in assets folder
-->
<q:application id="sounds" type="game" engine="2d">
  <qg:scene name="main" width="256" height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />

    <!-- Sound definitions -->
    <qg:sound id="jump" src="assets/smw/sounds/jump.wav" />
    <qg:sound id="coin" src="assets/smw/sounds/coin.wav" />
    <qg:sound id="bgm" src="assets/smw/sounds/overworld.mp3" loop="true" volume="0.5" />

    <!-- Coin prefab -->
    <qg:prefab name="coin">
      <qg:sprite src="assets/smw/sprites/coin_animated.png"
                 frame-width="16" frame-height="16"
                 tag="coin" body="static" sensor="true">
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

    <!-- Coins -->
    <qg:instance prefab="coin" x="80" y="56" />
    <qg:instance prefab="coin" x="128" y="56" />
    <qg:instance prefab="coin" x="176" y="56" />

    <!-- Mario with coin collection -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="32" y="60" tag="player"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="0.4" jump-force="1.2" friction="0">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
      <qg:on-collision with-tag="coin" action="destroy-other" />
    </qg:sprite>

    <!-- HUD note about sounds -->
    <qg:hud position="top-left">
      <div style="color: #FFD700; font-family: monospace; font-size: 8px; text-shadow: 1px 1px #000;">
        Sound test (audio files needed)
      </div>
    </qg:hud>
  </qg:scene>
</q:application>
