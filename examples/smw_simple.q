<q:application id="smw-simple" type="game" engine="2d">

  <qg:scene name="main" width="800" height="400" background="#5CA0FF">

    <qg:physics gravity-y="20" bounds="none" />
    <qg:camera follow="mario" lerp="0.1" bounds="scene" />

    <!-- Game State -->
    <q:set name="score" value="0" type="integer" />
    <q:set name="coins" value="0" type="integer" />

    <!-- Ground -->
    <qg:sprite id="ground" color="#8B4513"
               x="400" y="380" width="800" height="40"
               body="static" tag="solid" />

    <!-- Platform -->
    <qg:sprite id="platform" color="#228B22"
               x="300" y="280" width="100" height="20"
               body="static" tag="solid" />

    <!-- Mario -->
    <qg:sprite id="mario" src="assets/smw/sprites/mario.png"
               x="100" y="300" width="16" height="32"
               frame-width="16" frame-height="32"
               body="dynamic" controls="arrows" speed="5" jump-force="12"
               bounce="0" friction="0.8" tag="player">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-2" speed="0.12" loop="true" />
    </qg:sprite>

    <!-- Coins -->
    <qg:sprite id="coin1" src="assets/smw/sprites/objects.png"
               x="200" y="300" width="16" height="16"
               frame-x="0" frame-y="96"
               body="static" sensor="true" tag="coin">
      <qg:animation name="spin" frames="0-3" speed="0.1" loop="true" auto-play="true" />
    </qg:sprite>

    <qg:sprite id="coin2" src="assets/smw/sprites/objects.png"
               x="300" y="220" width="16" height="16"
               frame-x="0" frame-y="96"
               body="static" sensor="true" tag="coin">
      <qg:animation name="spin" frames="0-3" speed="0.1" loop="true" auto-play="true" />
    </qg:sprite>

    <qg:sprite id="coin3" src="assets/smw/sprites/objects.png"
               x="400" y="300" width="16" height="16"
               frame-x="0" frame-y="96"
               body="static" sensor="true" tag="coin">
      <qg:animation name="spin" frames="0-3" speed="0.1" loop="true" auto-play="true" />
    </qg:sprite>

    <!-- Enemy -->
    <qg:sprite id="koopa" src="assets/smw/sprites/koopas.png"
               x="500" y="340" width="16" height="24"
               frame-x="64" frame-y="0"
               body="dynamic" bounce="0" friction="0.3" tag="enemy">
      <qg:animation name="walk" frames="0-1" speed="0.15" loop="true" auto-play="true" />
    </qg:sprite>

    <!-- Event Handlers -->
    <q:function name="onCoinCollected">
      coins++;
      score += 200;
      game.play('coin_sfx');
      _updateHUD();
    </q:function>

    <!-- Register Events -->
    <qg:event name="coinCollected" handler="onCoinCollected" />

    <!-- Sounds -->
    <qg:sound id="coin_sfx" src="assets/smw/sounds/smw_coin.wav" channel="sfx" />
    <qg:sound id="jump_sfx" src="assets/smw/sounds/smw_jump.wav" channel="sfx" trigger="player.jump" />

    <!-- HUD -->
    <qg:hud position="top-left">
      <div style="padding:10px; font-family:monospace; font-size:16px; color:#fff;">
        SCORE: {score} | COINS: {coins}
      </div>
    </qg:hud>

  </qg:scene>

</q:application>
