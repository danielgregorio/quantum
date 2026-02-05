<q:application id="tictactoe" type="game" engine="2d">

  <qg:scene name="main" width="400" height="450" background="#1a1a2e">

    <!-- State -->
    <q:set name="turn" value="X" type="string" />
    <q:set name="status" value="X's turn" type="string" />
    <q:set name="active" value="true" type="boolean" />
    <q:set name="b0" value="" type="string" />
    <q:set name="b1" value="" type="string" />
    <q:set name="b2" value="" type="string" />
    <q:set name="b3" value="" type="string" />
    <q:set name="b4" value="" type="string" />
    <q:set name="b5" value="" type="string" />
    <q:set name="b6" value="" type="string" />
    <q:set name="b7" value="" type="string" />
    <q:set name="b8" value="" type="string" />
    <q:set name="marks" value="[]" type="array" />

    <!-- Grid lines -->
    <qg:sprite id="v1" src="" x="167" y="225" width="3" height="300" color="#334155" />
    <qg:sprite id="v2" src="" x="267" y="225" width="3" height="300" color="#334155" />
    <qg:sprite id="h1" src="" x="200" y="175" width="300" height="3" color="#334155" />
    <qg:sprite id="h2" src="" x="200" y="275" width="300" height="3" color="#334155" />

    <!-- Cells -->
    <qg:sprite id="c0" src="" x="100" y="125" width="96" height="96" color="#16213e">
      <qg:clickable action="play0" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c1" src="" x="200" y="125" width="96" height="96" color="#16213e">
      <qg:clickable action="play1" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c2" src="" x="300" y="125" width="96" height="96" color="#16213e">
      <qg:clickable action="play2" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c3" src="" x="100" y="225" width="96" height="96" color="#16213e">
      <qg:clickable action="play3" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c4" src="" x="200" y="225" width="96" height="96" color="#16213e">
      <qg:clickable action="play4" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c5" src="" x="300" y="225" width="96" height="96" color="#16213e">
      <qg:clickable action="play5" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c6" src="" x="100" y="325" width="96" height="96" color="#16213e">
      <qg:clickable action="play6" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c7" src="" x="200" y="325" width="96" height="96" color="#16213e">
      <qg:clickable action="play7" cursor="pointer" />
    </qg:sprite>
    <qg:sprite id="c8" src="" x="300" y="325" width="96" height="96" color="#16213e">
      <qg:clickable action="play8" cursor="pointer" />
    </qg:sprite>

    <!-- Cell actions -->
    <q:function name="play0">if (b0 === '' &amp;&amp; active) place(0);</q:function>
    <q:function name="play1">if (b1 === '' &amp;&amp; active) place(1);</q:function>
    <q:function name="play2">if (b2 === '' &amp;&amp; active) place(2);</q:function>
    <q:function name="play3">if (b3 === '' &amp;&amp; active) place(3);</q:function>
    <q:function name="play4">if (b4 === '' &amp;&amp; active) place(4);</q:function>
    <q:function name="play5">if (b5 === '' &amp;&amp; active) place(5);</q:function>
    <q:function name="play6">if (b6 === '' &amp;&amp; active) place(6);</q:function>
    <q:function name="play7">if (b7 === '' &amp;&amp; active) place(7);</q:function>
    <q:function name="play8">if (b8 === '' &amp;&amp; active) place(8);</q:function>

    <!-- Core game logic -->
    <q:function name="place">
      var i = arguments[0];
      var cells = [b0,b1,b2,b3,b4,b5,b6,b7,b8];
      var setters = [
        function(v){b0=v}, function(v){b1=v}, function(v){b2=v},
        function(v){b3=v}, function(v){b4=v}, function(v){b5=v},
        function(v){b6=v}, function(v){b7=v}, function(v){b8=v}
      ];
      setters[i](turn);

      <!-- Draw mark on cell -->
      var t = new PIXI.Text({ text: turn, style: {
        fontFamily: 'Arial', fontSize: 56, fontWeight: 'bold',
        fill: turn === 'X' ? 0x60a5fa : 0xf87171
      }});
      t.anchor.set(0.5);
      t.x = _sprites['c'+i].sprite.x;
      t.y = _sprites['c'+i].sprite.y;
      _cameraContainer.addChild(t);
      marks.push(t);

      <!-- Check winner -->
      var b = [b0,b1,b2,b3,b4,b5,b6,b7,b8];
      b[i] = turn;
      var W = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
      for (var k = 0; k &lt; W.length; k++) {
        if (b[W[k][0]] !== '' &amp;&amp; b[W[k][0]] === b[W[k][1]] &amp;&amp; b[W[k][1]] === b[W[k][2]]) {
          status = turn + ' wins!';
          active = false;
          _updateHUD();
          return;
        }
      }

      <!-- Check draw -->
      var full = b.every(function(c){ return c !== ''; });
      if (full) { status = 'Draw!'; active = false; _updateHUD(); return; }

      turn = turn === 'X' ? 'O' : 'X';
      status = turn + "'s turn";
      _updateHUD();
    </q:function>

    <!-- Restart -->
    <q:function name="restart">
      for (var i = 0; i &lt; marks.length; i++) { _cameraContainer.removeChild(marks[i]); }
      marks = [];
      b0=''; b1=''; b2=''; b3=''; b4=''; b5=''; b6=''; b7=''; b8='';
      turn = 'X'; status = "X's turn"; active = true;
      _updateHUD();
    </q:function>

    <qg:input key="r" action="restart" type="press" />
    <qg:input key="R" action="restart" type="press" />

    <!-- HUD -->
    <qg:hud position="top-center">
      <text style="font-size:22px; color:#fbbf24; font-family:monospace;">{status}</text>
    </qg:hud>
    <qg:hud position="bottom-center">
      <text style="font-size:13px; color:#475569; font-family:monospace;">{active ? '' : 'R to restart'}</text>
    </qg:hud>

  </qg:scene>

</q:application>
