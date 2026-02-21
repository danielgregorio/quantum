<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 3: Full Tilemap with Collision

  Tests physics and collision with real SMW tileset
  - Mario falls with gravity
  - Mario lands on ground (collision)
-->
<q:application id="tilemap-full" type="game" engine="2d">
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

    <!-- Mario with physics - should fall and land on ground (16x16 Small Mario) -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="48" y="28"
               frame-width="16" frame-height="24"
               body="dynamic" bounce="0" friction="0.8" />
  </qg:scene>
</q:application>
