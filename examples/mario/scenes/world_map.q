<?xml version="1.0" encoding="UTF-8"?>
<!--
  World Map - SMW-style path-based navigation

  Mario moves between nodes on the map.
  D-pad navigates, Enter enters a level.
  Levels unlock after clearing the previous one.
-->
<qg:scene name="world-map" type="map"
          width="512" height="512"
          viewport-width="256" viewport-height="224"
          background="#4488CC">

  <!-- Map background -->
  <qg:sprite id="map-bg" src="assets/smw/sprites/world1_map.png"
             x="256" y="256" width="512" height="512" />

  <!-- Mario sprite on map -->
  <qg:sprite id="mario" src="assets/smw/sprites/mario_map.png"
             x="32" y="180" width="16" height="16" />

  <!-- Background music -->
  <qg:sound id="bgm-map" src="assets/smw/sounds/music/music-map1.wav"
            trigger="scene-start" loop="true" volume="0.5" channel="music" />

  <!-- Map nodes -->
  <qg:map-node id="start" x="32" y="180" />
  <qg:map-node id="yoshi-island-1" x="80" y="180" scene="yoshi-island-1"
               icon="assets/smw/sprites/level_dot.png" />
  <qg:map-node id="yoshi-island-2" x="128" y="160" scene="yoshi-island-2"
               locked="true" icon="assets/smw/sprites/level_dot.png" />
  <qg:map-node id="castle-1" x="200" y="140" scene="castle-1"
               locked="true" icon="assets/smw/sprites/castle_icon.png" />

  <!-- Map paths -->
  <qg:map-path from="start" to="yoshi-island-1" />
  <qg:map-path from="yoshi-island-1" to="yoshi-island-2" unlock="yoshi-island-1-cleared" />
  <qg:map-path from="yoshi-island-2" to="castle-1" unlock="yoshi-island-2-cleared" />

  <!-- HUD: lives counter -->
  <qg:hud sprite-prefix="assets/smw/sprites/hud_">
    <qg:tile sprite="mario_text.png" x="16" y="8" />
    <qg:counter strip="numbers_small.png" x="32" y="16" bind="{lives}" tint="yellow" />
  </qg:hud>

</qg:scene>
