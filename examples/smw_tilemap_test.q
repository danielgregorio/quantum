<q:application id="smw-tilemap-test" type="game" engine="2d">

  <qg:scene name="main" width="512" height="256" background="#5CA0FF">

    <qg:physics gravity-y="20" bounds="none" />

    <!-- Tilemap test with tileset_yi1_minimal_transparent.png -->
    <!-- Tile mapping:
         1=corner_tl, 2=edge_top, 3=corner_tr
         17=edge_left, 18=fill, 19=edge_right
         33=corner_bl, 34=edge_bottom, 35=corner_br
         225-227=hill (left, mid, right) - row 14
    -->
    <qg:tilemap id="level" src="assets/smw/sprites/tileset_yi1_minimal_transparent.png"
                tile-width="16" tile-height="16">

      <!-- Visual layer to test tile rendering -->
      <qg:layer name="terrain" collision="true">
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,225,226,227,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
1,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,3
17,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,19
17,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,18,19
33,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,34,35
      </qg:layer>
    </qg:tilemap>

    <!-- Small Mario with animations -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="50" y="150" width="16" height="32"
               frame-width="16" frame-height="32"
               body="dynamic" controls="arrows" speed="5" jump-force="12"
               bounce="0" friction="0.8" tag="player">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-2" speed="0.12" loop="true" />
    </qg:sprite>

    <!-- HUD -->
    <qg:hud position="top-left">
      <div style="padding:10px; font-family:monospace; font-size:14px; color:#fff; background:rgba(0,0,0,0.5);">
        Tilemap Test - Using tileset_yi1_minimal_transparent.png<br/>
        Tiles: 1-3=top row, 17-19=middle, 33-35=bottom, 225-227=hills
      </div>
    </qg:hud>

  </qg:scene>

</q:application>
