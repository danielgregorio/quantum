<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 8: Full SMW Map

  Authentic SMW-style level with:
  - Hills (decorative background)
  - Ground with proper tiles
  - Platforms at different heights
  - Gaps to jump over
  - Multiple sections

  Tileset reference (stage1_unique.png):
  - Tile 0-2: Hill tops
  - Tile 9: Grass surface
  - Tile 14: Underground solid
  - Other tiles: Various platforms and decorations
-->
<q:application id="full-map" type="game" engine="2d">
  <qg:scene name="main" width="768" height="144" viewport-width="256" viewport-height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />
    <qg:camera follow="mario" lerp="0.08" bounds="scene" />

    <!-- Prefabs -->
    <qg:prefab name="coin">
      <qg:sprite src="assets/smw/sprites/coin_animated.png"
                 frame-width="16" frame-height="16">
        <qg:animation name="spin" frames="0,1,2,3,2,1" speed="0.12" loop="true" auto-play="true" />
      </qg:sprite>
    </qg:prefab>

    <qg:tilemap id="level" src="assets/smw/sprites/stage1_unique.png"
                tile-width="16" tile-height="16">
      <!-- Main terrain layer -->
      <qg:layer name="terrain" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,9,9,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,9,9,0,0,0,0,0,0,0,0,0,0,0,0,0,9,9,9,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,9,9,9,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,9,9,9,9
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,0,0,0,9,9,9,9,9,9,9,9,9,9,9,0,0,0,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14,14,14,14,0,0,0,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
      </qg:layer>
    </qg:tilemap>

    <!-- Coins placed strategically -->
    <qg:instance prefab="coin" x="80" y="72" />
    <qg:instance prefab="coin" x="112" y="72" />
    <qg:instance prefab="coin" x="176" y="56" />
    <qg:instance prefab="coin" x="256" y="40" />
    <qg:instance prefab="coin" x="368" y="56" />
    <qg:instance prefab="coin" x="400" y="56" />
    <qg:instance prefab="coin" x="480" y="24" />
    <qg:instance prefab="coin" x="512" y="24" />
    <qg:instance prefab="coin" x="608" y="56" />
    <qg:instance prefab="coin" x="640" y="56" />
    <qg:instance prefab="coin" x="720" y="56" />

    <!-- Mario -->
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
