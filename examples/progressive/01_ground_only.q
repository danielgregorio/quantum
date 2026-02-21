<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 1: Ground Only Test - Using REAL SMW Stage 1 tileset

  Tile IDs from TileFactory:
  - 9 = grass top
  - 14 = dirt/ground fill
-->
<q:application id="ground-test" type="game" engine="2d">
  <qg:scene name="main" width="256" height="80" background="#5C94FC">
    <qg:tilemap id="test" src="assets/smw/sprites/stage1_unique.png"
                tile-width="16" tile-height="16">
      <qg:layer name="ground">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
9,9,9,9,9,9,9,9,9,9,9,9,9,9,9,9
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
14,14,14,14,14,14,14,14,14,14,14,14,14,14,14,14
      </qg:layer>
    </qg:tilemap>
  </qg:scene>
</q:application>
