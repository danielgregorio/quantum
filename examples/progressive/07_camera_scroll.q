<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 7: Camera and Scrolling

  Tests:
  - Map larger than screen (512x144)
  - Camera follows Mario smoothly
  - Camera bounds (doesn't show beyond map)
-->
<q:application id="camera-scroll" type="game" engine="2d">
  <qg:scene name="main" width="512" height="144" viewport-width="256" viewport-height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />
    <qg:camera follow="mario" lerp="0.08" bounds="scene" />

    <!-- Coin prefab -->
    <qg:prefab name="coin">
      <qg:sprite src="assets/smw/sprites/coin_animated.png"
                 frame-width="16" frame-height="16">
        <qg:animation name="spin" frames="0,1,2,3,2,1" speed="0.12" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <qg:tilemap id="level" src="assets/smw/sprites/stage1_unique.png"
                tile-width="16" tile-height="16">
      <qg:layer name="terrain" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,9,9,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,9,9,9,0,0,0,0,0,0,9,9,9,0,0,0,0,0,0,0,0,9,9,9,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
      </qg:layer>
    </qg:tilemap>

    <!-- Coins spread across the level -->
    <qg:instance prefab="coin" x="80" y="72" />
    <qg:instance prefab="coin" x="144" y="56" />
    <qg:instance prefab="coin" x="208" y="72" />
    <qg:instance prefab="coin" x="272" y="56" />
    <qg:instance prefab="coin" x="336" y="72" />
    <qg:instance prefab="coin" x="400" y="24" />
    <qg:instance prefab="coin" x="464" y="56" />

    <!-- Mario starts on the left -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="32" y="60"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="0.4" jump-force="1.2" friction="0">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
    </qg:sprite>
  </qg:scene>
</q:application>
