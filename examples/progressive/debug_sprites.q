<?xml version="1.0" encoding="UTF-8"?>
<!--
  Debug: Simple Sprites Test
  NO animations, NO frame cutting - just basic sprites
-->
<q:application id="debug-sprites" type="game" engine="2d">
  <qg:scene name="main" width="256" height="144" background="#5C94FC">
    <qg:physics gravity-y="0.8" />

    <!-- Ground using simple colored rectangles -->
    <qg:sprite id="ground" x="128" y="136" width="256" height="16"
               color="#8B4513" body="static" />

    <!-- Test sprites - single frame, no animation -->
    <qg:sprite id="qblock1" src="assets/smw/sprites/qblock_single.png"
               x="64" y="56" width="16" height="16" body="static" />

    <qg:sprite id="qblock2" src="assets/smw/sprites/qblock_single.png"
               x="96" y="56" width="16" height="16" body="static" />

    <qg:sprite id="coin1" src="assets/smw/sprites/coin_single.png"
               x="128" y="56" width="16" height="16" body="static" />

    <qg:sprite id="mushroom1" src="assets/smw/sprites/mushroom.png"
               x="160" y="56" width="16" height="16" body="static" />

    <qg:sprite id="goomba1" src="assets/smw/sprites/goomba_single.png"
               x="192" y="120" width="16" height="16" body="static" tag="enemy" />

    <!-- Mario - also single frame for testing -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_idle.png"
               x="32" y="96" width="16" height="16"
               body="dynamic" controls="arrows" speed="0.4" jump-force="1.2" />

    <!-- HUD -->
    <qg:hud position="top-left">
      <div style="color: white; font-family: monospace; font-size: 10px;">
        DEBUG: qblock | qblock | coin | mushroom | goomba
      </div>
    </qg:hud>
  </qg:scene>
</q:application>
