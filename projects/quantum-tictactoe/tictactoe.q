<q:application id="tictactoe" type="game" engine="2d">

  <!-- Cell behavior: tracks if cell is empty, X, or O -->
  <qg:behavior name="Cell">
    <q:set name="mark" value="" type="string" />
    <q:function name="onCellClick">
      <q:if condition="{self.mark === '' &amp;&amp; currentTurn === 'X'}">
        <q:set name="self.mark" value="X" />
        <q:set name="moves" value="{moves + 1}" scope="scene" />
        <q:set name="currentTurn" value="O" scope="scene" />
        <q:set name="turnLabel" value="O's turn" scope="scene" />
      </q:if>
      <q:if condition="{self.mark === '' &amp;&amp; currentTurn === 'O'}">
        <q:set name="self.mark" value="O" />
        <q:set name="moves" value="{moves + 1}" scope="scene" />
        <q:set name="currentTurn" value="X" scope="scene" />
        <q:set name="turnLabel" value="X's turn" scope="scene" />
      </q:if>
    </q:function>
  </qg:behavior>

  <qg:scene name="main" width="400" height="480" background="#2c3e50">
    <q:set name="moves" value="0" type="number" />
    <q:set name="currentTurn" value="X" type="string" />
    <q:set name="turnLabel" value="X's turn" type="string" />
    <q:set name="resultText" value="" type="string" />

    <!-- 3x3 Grid of cells (100x100 each, starting at x=50 y=70) -->
    <qg:sprite id="c0" src="" x="50"  y="70"  width="100" height="100" tag="cell">
      <qg:use behavior="Cell" />
      <qg:clickable action="onCellClick" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c1" src="" x="150" y="70"  width="100" height="100" tag="cell">
      <qg:use behavior="Cell" />
      <qg:clickable action="onCellClick" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c2" src="" x="250" y="70"  width="100" height="100" tag="cell">
      <qg:use behavior="Cell" />
      <qg:clickable action="onCellClick" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c3" src="" x="50"  y="170" width="100" height="100" tag="cell">
      <qg:use behavior="Cell" />
      <qg:clickable action="onCellClick" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c4" src="" x="150" y="170" width="100" height="100" tag="cell">
      <qg:use behavior="Cell" />
      <qg:clickable action="onCellClick" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c5" src="" x="250" y="170" width="100" height="100" tag="cell">
      <qg:use behavior="Cell" />
      <qg:clickable action="onCellClick" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c6" src="" x="50"  y="270" width="100" height="100" tag="cell">
      <qg:use behavior="Cell" />
      <qg:clickable action="onCellClick" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c7" src="" x="150" y="270" width="100" height="100" tag="cell">
      <qg:use behavior="Cell" />
      <qg:clickable action="onCellClick" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c8" src="" x="250" y="270" width="100" height="100" tag="cell">
      <qg:use behavior="Cell" />
      <qg:clickable action="onCellClick" cursor="pointer" />
    </qg:sprite>

    <!-- HUD: turn indicator and result -->
    <qg:hud position="top-center">
      <text style="font-size:28px; color:#ecf0f1; font-weight:bold">Tic Tac Toe</text>
      <text style="font-size:20px; color:#f39c12; margin-top:4px">{turnLabel}</text>
    </qg:hud>
    <qg:hud position="bottom-center">
      <text style="font-size:24px; color:#e74c3c; font-weight:bold">{resultText}</text>
    </qg:hud>

    <!-- Restart with R key -->
    <qg:input key="r" action="restartGame" type="press" />
  </qg:scene>

</q:application>
