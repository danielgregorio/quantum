<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 4: Mario Animated

  Full test with:
  - Real SMW tileset
  - Physics and collision
  - Arrow key controls
  - Walk animation
-->
<q:application id="mario-animated" type="game" engine="2d">
  <qg:scene name="main" width="256" height="144" background="#5C94FC">
    <qg:physics gravity-y="20" />

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

    <!-- Mario with controls and animations (16x16 Small Mario) -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="48" y="44"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="3" jump-force="12">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.15" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
    </qg:sprite>
  </qg:scene>
</q:application>
