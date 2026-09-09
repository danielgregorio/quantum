<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 1: Scene + Background

  Minimal setup: PIXI scene, background image, static Mario sprite.
  No physics, no controls - just rendering validation.
-->
<q:application id="yoshi-island-1" type="game" engine="2d">
  <qg:scene name="main" width="5120" height="432" viewport-width="256" viewport-height="224" background="#5C94FC">

    <!-- Full level background image -->
    <qg:sprite id="level-bg" src="assets/smw/sprites/yoshi-island-1.png"
               x="2560" y="216" width="5120" height="432" />

    <!-- Mario - static, no physics, no controls -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
               x="80" y="368" tag="player"
               frame-width="16" frame-height="24">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
    </qg:sprite>

    <!-- Position viewport to show ground level (no camera in this phase) -->
    <qg:event name="game-init" handler="onGameInit" />
    <q:function name="onGameInit">
      _cameraContainer.y = -180;
    </q:function>

  </qg:scene>
</q:application>
