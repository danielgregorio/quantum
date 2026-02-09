<q:application id="snake" type="game" engine="2d">

  <!-- Snake movement behavior: grid-based step driven by timer -->
  <qg:behavior name="SnakeMovement">
    <q:set name="dx" value="1" type="number" />
    <q:set name="dy" value="0" type="number" />
    <q:set name="nextDx" value="1" type="number" />
    <q:set name="nextDy" value="0" type="number" />
    <q:set name="gridSize" value="20" type="number" />
    <q:set name="tailLength" value="3" type="number" />

    <q:function name="changeDir">
      <q:if condition="{self.nextDx !== -self.dx || self.nextDy !== -self.dy}">
        <q:set name="self.dx" value="{self.nextDx}" />
        <q:set name="self.dy" value="{self.nextDy}" />
      </q:if>
    </q:function>

    <q:function name="moveSnake">
      <q:if condition="{gameOver}">
        <q:set name="self.dx" value="0" />
        <q:set name="self.dy" value="0" />
      </q:if>

      self.changeDir();

      <q:set name="self.x" value="{self.x + self.dx * self.gridSize}" />
      <q:set name="self.y" value="{self.y + self.dy * self.gridSize}" />

      <q:if condition="{self.x >= 800}">
        <q:set name="self.x" value="0" />
      </q:if>
      <q:if condition="{self.x &lt; 0}">
        <q:set name="self.x" value="780" />
      </q:if>
      <q:if condition="{self.y >= 600}">
        <q:set name="self.y" value="0" />
      </q:if>
      <q:if condition="{self.y &lt; 0}">
        <q:set name="self.y" value="580" />
      </q:if>
    </q:function>
  </qg:behavior>

  <qg:prefab name="SnakeSegment">
    <qg:sprite id="segment" src="" width="20" height="20" />
  </qg:prefab>

  <qg:prefab name="Food">
    <qg:sprite id="foodItem" src="" width="20" height="20" />
  </qg:prefab>

  <qg:scene name="game" width="800" height="600" background="#1a1a2e">
    <q:set name="score" value="0" type="number" />
    <q:set name="gameOver" value="false" type="boolean" />
    <q:set name="direction" value="right" type="string" />

    <qg:sprite id="head" src="" x="200" y="300" width="20" height="20">
      <qg:use behavior="SnakeMovement" />
    </qg:sprite>

    <qg:sprite id="food" src="" x="400" y="300" width="20" height="20" tag="food" />

    <qg:input key="ArrowUp" action="setDirUp" type="press" />
    <qg:input key="ArrowDown" action="setDirDown" type="press" />
    <qg:input key="ArrowLeft" action="setDirLeft" type="press" />
    <qg:input key="ArrowRight" action="setDirRight" type="press" />

    <q:function name="setDirUp">
      <q:set name="direction" value="up" />
    </q:function>
    <q:function name="setDirDown">
      <q:set name="direction" value="down" />
    </q:function>
    <q:function name="setDirLeft">
      <q:set name="direction" value="left" />
    </q:function>
    <q:function name="setDirRight">
      <q:set name="direction" value="right" />
    </q:function>

    <qg:timer id="gameTick" interval="0.15" action="moveSnake" auto-start="true" />

    <qg:spawn id="segSpawner" prefab="SnakeSegment" pool-size="100" x="0" y="0" />

    <qg:hud position="top-left">
      <text style="font-size:22px; color:#ffffff; font-family:monospace;">Score: {score}</text>
    </qg:hud>

    <qg:hud position="center">
      <text style="font-size:40px; color:#FF5252; font-family:monospace;">{gameOver ? 'GAME OVER' : ''}</text>
    </qg:hud>
  </qg:scene>

</q:application>
