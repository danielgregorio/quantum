<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 6: SMW-Style Jump Physics

  Tests Mario jump with:
  - Asymmetric gravity (floaty rise, snappy fall)
  - Variable jump height (hold to jump higher)
  - Coyote time (jump shortly after leaving platform)
  - Max fall speed (terminal velocity)
  - Camera following the player

  Controls: Arrow keys to move, Up/Space to jump
  Hold jump to go higher, tap for short hop
-->
<q:application id="smw-physics" type="game" engine="2d">
  <qg:scene name="main" width="256" height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />
    <qg:camera follow="mario" lerp="0.1" bounds="scene" />

    <qg:tilemap id="level" src="assets/smw/sprites/stage1_unique.png"
                tile-width="16" tile-height="16">
      <qg:layer name="terrain" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,9,9,9,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,9,9,9,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
      </qg:layer>
    </qg:tilemap>

    <!-- Mario with SMW-style physics (tuned for natural speed) -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="32" y="44"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="0.4"
               friction="0"
               jump-force="1.2"
               gravity-up="0.8"
               gravity-down="1.15"
               jump-hold-boost="0.15"
               coyote-frames="5"
               max-fall-speed="4">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
    </qg:sprite>
  </qg:scene>
</q:application>
