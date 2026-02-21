<?xml version="1.0" encoding="UTF-8"?>
<!--
  DEBUG: Super Simple Test
  Single-frame sprites ONLY, no animations, no frame cutting
-->
<q:application id="debug-simple" type="game" engine="2d">
  <qg:scene name="main" width="256" height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />

    <!-- Ground - simple brown rectangle -->
    <qg:sprite id="ground" x="128" y="136" width="256" height="16" color="#8B4513" body="static" />

    <!-- Test 1: ? Block single frame (16x16) -->
    <qg:sprite id="qblock1" src="assets/smw/sprites/qblock_single.png"
               x="48" y="56" width="16" height="16" body="static" />

    <!-- Test 2: Another ? Block -->
    <qg:sprite id="qblock2" src="assets/smw/sprites/qblock_single.png"
               x="80" y="56" width="16" height="16" body="static" />

    <!-- Test 3: Mushroom (16x16) -->
    <qg:sprite id="mush" src="assets/smw/sprites/mushroom.png"
               x="112" y="56" width="16" height="16" body="static" />

    <!-- Test 4: Goomba single frame -->
    <qg:sprite id="goomba" src="assets/smw/sprites/goomba_single.png"
               x="180" y="120" width="16" height="16" body="static" />

    <!-- Mario using idle single frame (16x32) -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_idle.png"
               x="32" y="100" width="16" height="32"
               body="dynamic" controls="arrows" speed="0.4" jump-force="1.2" />

    <qg:hud position="top-left">
      <div style="color:white;font-family:monospace;font-size:10px;">
        DEBUG: ?block | ?block | mushroom | goomba
      </div>
    </qg:hud>
  </qg:scene>
</q:application>
