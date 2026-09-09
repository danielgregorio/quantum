<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 2: Mario Static Test

  Using real SMW Stage 1 tileset + Mario spritesheet
  Tests frame-cutting with frame-width/frame-height
-->
<q:application id="mario-static" type="game" engine="2d">
  <qg:scene name="main" width="256" height="112" background="#5C94FC">
    <qg:tilemap id="ground" src="assets/smw/sprites/stage1_unique.png"
                tile-width="16" tile-height="16">
      <qg:layer name="terrain">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
      </qg:layer>
    </qg:tilemap>

    <!-- Mario with frame-width/height - first frame only (16x16 Small Mario) -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="128" y="44"
               frame-width="16" frame-height="24" />
  </qg:scene>
</q:application>
