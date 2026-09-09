<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 5: Animated Sprites with Prefabs

  Demonstrates the prefab system:
  - Define a coin prefab once with all properties
  - Instantiate multiple times with just position

  This is how real games work - templates for repeated objects.
-->
<q:application id="animated-coins" type="game" engine="2d">
  <qg:scene name="main" width="256" height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />

    <!-- PREFAB DEFINITION (once) -->
    <qg:prefab name="coin">
      <qg:sprite src="assets/smw/sprites/coin_animated.png"
                 frame-width="16" frame-height="16">
        <qg:animation name="spin" frames="0,1,2,3,2,1" speed="0.12" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <!-- TILEMAP -->
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

    <!-- COIN INSTANCES (just position!) -->
    <qg:instance prefab="coin" x="48" y="32" />
    <qg:instance prefab="coin" x="96" y="32" />
    <qg:instance prefab="coin" x="144" y="32" />
    <qg:instance prefab="coin" x="192" y="32" />
    <qg:instance prefab="coin" x="72" y="56" />
    <qg:instance prefab="coin" x="120" y="56" />
    <qg:instance prefab="coin" x="168" y="56" />

    <!-- Mario -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="48" y="60"
               frame-width="16" frame-height="24"
               body="dynamic" controls="arrows" speed="0.4" jump-force="1.2" friction="0">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-3" speed="0.18" loop="true" />
      <qg:animation name="jump" frames="4" speed="0.1" loop="false" />
    </qg:sprite>
  </qg:scene>
</q:application>
