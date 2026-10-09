<q:application id="pong" type="game">

  <!-- Pong: Godot's own "Pong with GDScript" demo (godotengine/godot-demo-projects,
       2d/pong, MIT), transcribed into the game language node for node and line
       for line. README.md next to this file maps each piece of the original to
       its tag, and lists what the language had to grow to say it. The sprites
       are the demo's (assets/LICENSE.md). -->

  <qg:spritesheet name="paddle" src="assets/paddle.png" tile="8x32" />
  <qg:spritesheet name="ball" src="assets/ball.png" tile="8" />
  <qg:spritesheet name="separator" src="assets/separator.png" tile="2x400" />

  <!-- The left paddle is player 1 on W/S, the right one player 2 on the arrows —
       on one keyboard. Over the network each peer is one player: one hosts
       (q-host=7777), the other joins (q-join=HOST:7777), and the game runs
       in lockstep, the same on both (README.md). -->
  <qg:input player="1" action="up" keys="W" />
  <qg:input player="1" action="down" keys="S" />
  <qg:input player="2" action="up" keys="Up" />
  <qg:input player="2" action="down" keys="Down" />
  <qg:multiplayer players="2" delay="3" />

  <!-- The ball flies left at 100 px/s, 2 px/s faster every second; it bounces
       off the ceiling and the floor, and goes back to its start, as it was,
       when it passes a paddle. -->
  <qg:prefab name="Ball" tag="ball" sheet="ball" hitbox="8x8" ai="fly" heading="left" speed="100" accel="2">
    <qg:on-collision with="edge">
      <qg:deflect target="me" axis="y" />
    </qg:on-collision>
    <qg:on-collision with="wall">
      <qg:respawn target="me" />
    </qg:on-collision>
  </qg:prefab>

  <qg:scene name="court" width="640" height="400" background="#24272a" seed="1">
    <qg:sprite sheet="separator" x="320" y="200" />

    <!-- A paddle moves up and down at 100 px/s, kept on the screen; the ball
         it touches leaves towards the other side, at a random slant. -->
    <qg:character id="left" controller="ship" player="1" axis="vertical" speed="100"
                  sheet="paddle" x="67.6285" y="192.594" hitbox="8x32" gd:modulate="#00ffff">
      <qg:on-collision with="ball">
        <qg:deflect target="other" dx="1" dy="{random(-1, 1)}" />
      </qg:on-collision>
    </qg:character>
    <qg:character id="right" controller="ship" player="2" axis="vertical" speed="100"
                  sheet="paddle" x="563.815" y="188.919" hitbox="8x32" gd:modulate="#ff00ff">
      <qg:on-collision with="ball">
        <qg:deflect target="other" dx="-1" dy="{random(-1, 1)}" />
      </qg:on-collision>
    </qg:character>

    <qg:instance prefab="Ball" name="ball" x="320.5" y="191.124" />

    <qg:zone name="ceiling" tag="edge" x="0" y="-20" width="640" height="20" />
    <qg:zone name="floor" tag="edge" x="0" y="400" width="640" height="20" />
    <qg:zone name="left-wall" tag="wall" x="-20" y="0" width="20" height="400" />
    <qg:zone name="right-wall" tag="wall" x="640" y="0" width="20" height="400" />
  </qg:scene>

</q:application>
