<q:application id="snake" type="game" engine="2d">

  <!-- Snake game with proper tail following and food collision -->

  <qg:prefab name="SnakeSegment">
    <qg:sprite src="" width="20" height="20" color="#22c55e" />
  </qg:prefab>

  <qg:scene name="game" width="800" height="600" background="#1a1a2e">
    <!-- Game state -->
    <q:set name="score" value="0" type="integer" />
    <q:set name="gameOver" value="false" type="boolean" />
    <q:set name="gridSize" value="20" type="integer" />
    <q:set name="dx" value="1" type="integer" />
    <q:set name="dy" value="0" type="integer" />
    <q:set name="nextDx" value="1" type="integer" />
    <q:set name="nextDy" value="0" type="integer" />

    <!-- Tail positions array and segments array -->
    <q:set name="tailPositions" value="[]" type="array" />
    <q:set name="tailSegments" value="[]" type="array" />
    <q:set name="tailLength" value="3" type="integer" />

    <!-- Snake head -->
    <qg:sprite id="head" src="" x="200" y="300" width="20" height="20" color="#4ade80" />

    <!-- Food -->
    <qg:sprite id="food" src="" x="400" y="300" width="20" height="20" color="#f87171" />

    <!-- Spawner for tail segments -->
    <qg:spawn id="segSpawner" prefab="SnakeSegment" pool-size="100" x="-100" y="-100" />

    <!-- Input handlers - Arrow keys -->
    <qg:input key="ArrowUp" action="setDirUp" type="press" />
    <qg:input key="ArrowDown" action="setDirDown" type="press" />
    <qg:input key="ArrowLeft" action="setDirLeft" type="press" />
    <qg:input key="ArrowRight" action="setDirRight" type="press" />

    <!-- Input handlers - WASD -->
    <qg:input key="w" action="setDirUp" type="press" />
    <qg:input key="W" action="setDirUp" type="press" />
    <qg:input key="s" action="setDirDown" type="press" />
    <qg:input key="S" action="setDirDown" type="press" />
    <qg:input key="a" action="setDirLeft" type="press" />
    <qg:input key="A" action="setDirLeft" type="press" />
    <qg:input key="d" action="setDirRight" type="press" />
    <qg:input key="D" action="setDirRight" type="press" />

    <q:function name="setDirUp">
      if (dy !== 1) { nextDx = 0; nextDy = -1; }
    </q:function>

    <q:function name="setDirDown">
      if (dy !== -1) { nextDx = 0; nextDy = 1; }
    </q:function>

    <q:function name="setDirLeft">
      if (dx !== 1) { nextDx = -1; nextDy = 0; }
    </q:function>

    <q:function name="setDirRight">
      if (dx !== -1) { nextDx = 1; nextDy = 0; }
    </q:function>

    <q:function name="moveSnake">
      if (gameOver) return;

      var headSprite = _sprites["head"].sprite;
      var foodSprite = _sprites["food"].sprite;

      // Apply direction change (prevent 180 turn)
      dx = nextDx;
      dy = nextDy;

      // Store current head position in tail
      tailPositions.unshift({ x: headSprite.x, y: headSprite.y });

      // Move head
      headSprite.x += dx * gridSize;
      headSprite.y += dy * gridSize;

      // Wrap around screen
      if (headSprite.x >= 800) headSprite.x = 0;
      if (headSprite.x &lt; 0) headSprite.x = 780;
      if (headSprite.y >= 600) headSprite.y = 0;
      if (headSprite.y &lt; 0) headSprite.y = 580;

      // Check food collision
      if (headSprite.x === foodSprite.x &amp;&amp; headSprite.y === foodSprite.y) {
        score += 10;
        tailLength += 1;

        // Spawn new segment
        var newSeg = _spawn("segSpawner");
        if (newSeg) {
          tailSegments.push(newSeg);
        }

        // Reposition food randomly (aligned to grid)
        var newFoodX = Math.floor(Math.random() * 40) * gridSize;
        var newFoodY = Math.floor(Math.random() * 30) * gridSize;
        foodSprite.x = newFoodX;
        foodSprite.y = newFoodY;

        // Speed up the game (minimum 0.04s interval)
        if (_timers["gameTick"].interval > 0.04) {
          _timers["gameTick"].interval -= 0.005;
        }

        _updateHUD();
      }

      // Trim tail positions to current length
      while (tailPositions.length > tailLength) {
        tailPositions.pop();
      }

      // Update segment positions
      for (var i = 0; i &lt; tailSegments.length; i++) {
        if (tailPositions[i]) {
          tailSegments[i].x = tailPositions[i].x;
          tailSegments[i].y = tailPositions[i].y;
        }
      }

      // Check self collision (head hits tail)
      for (var j = 0; j &lt; tailPositions.length; j++) {
        if (headSprite.x === tailPositions[j].x &amp;&amp; headSprite.y === tailPositions[j].y) {
          gameOver = true;
          _updateHUD();
          break;
        }
      }
    </q:function>

    <!-- Game tick timer -->
    <qg:timer id="gameTick" interval="0.12" action="moveSnake" auto-start="true" />

    <!-- HUD -->
    <qg:hud position="top-left">
      <text style="font-size:24px; color:#ffffff; font-family:monospace; text-shadow: 2px 2px #000;">Score: {score}</text>
    </qg:hud>

    <qg:hud position="center">
      <text style="font-size:48px; color:#ef4444; font-family:monospace; text-shadow: 3px 3px #000;">{gameOver ? 'GAME OVER' : ''}</text>
    </qg:hud>
  </qg:scene>

</q:application>
