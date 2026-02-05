"""
Build the mario.q file with properly generated tilemap CSV data.
Also generates game.html.

Usage: python scripts/build_mario.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# =============================================================================
# Tilemap Generation
# =============================================================================

COLS = 212
ROWS = 28
# Tile IDs (1-based, matching tileset.png)
EMPTY = 0
GROUND_TOP = 1
GROUND_FILL = 2
BRICK = 3
QBLOCK = 4
USED_BLOCK = 5
PIPE_TL = 6
PIPE_TR = 7
PIPE_BL = 8
PIPE_BR = 9
# 10 = sky (not used, just 0)
CLOUD = 11
BUSH = 12
HILL = 13
STAIR = 14
FLAGPOLE = 15
FLAG = 16


def make_empty_grid():
    return [[EMPTY] * COLS for _ in range(ROWS)]


def generate_background():
    """Generate decorative background layer (no collision)."""
    grid = make_empty_grid()

    cloud_positions = [
        (3, 8), (3, 9),
        (2, 19), (2, 20), (3, 18), (3, 19), (3, 20), (3, 21),
        (3, 48), (3, 49),
        (2, 60), (2, 61), (3, 59), (3, 60), (3, 61), (3, 62),
        (3, 98), (3, 99),
        (2, 110), (2, 111), (3, 109), (3, 110), (3, 111), (3, 112),
        (3, 148), (3, 149),
        (2, 170), (2, 171), (3, 169), (3, 170), (3, 171), (3, 172),
    ]
    for r, c in cloud_positions:
        if 0 <= r < ROWS and 0 <= c < COLS:
            grid[r][c] = CLOUD

    bush_positions = [24, 25, 48, 49, 68, 69, 96, 97, 120, 121, 168, 169]
    for c in bush_positions:
        if 0 <= c < COLS:
            grid[25][c] = BUSH

    return grid


# Block positions: (row, col) - these are NOT in the tilemap, they're individual sprites
QBLOCK_POSITIONS = [
    (20, 20), (20, 77), (20, 79), (20, 101),
]
BRICK_POSITIONS = [
    (20, 16), (20, 17), (20, 18),
    (20, 76), (20, 78), (20, 80),
    (16, 77), (16, 78), (16, 79),
    (20, 100), (20, 102), (20, 103),
]


def generate_terrain():
    """Generate terrain collision layer - ground, pipes, stairs only.
    Bricks and Q-blocks are individual sprites, NOT in tilemap."""
    grid = make_empty_grid()

    # Ground: rows 26-27 with gaps (pits)
    gap1 = set(range(69, 73))
    gap2 = set(range(135, 139))
    gaps = gap1 | gap2

    for c in range(COLS):
        if c not in gaps:
            grid[26][c] = GROUND_TOP
            grid[27][c] = GROUND_FILL

    # Pipes (2 tiles wide, varying heights)
    # Pipe 1: small (2 tall) at cols 28-29
    grid[24][28] = PIPE_TL
    grid[24][29] = PIPE_TR
    grid[25][28] = PIPE_BL
    grid[25][29] = PIPE_BR

    # Pipe 2: medium (3 tall) at cols 38-39
    grid[23][38] = PIPE_TL
    grid[23][39] = PIPE_TR
    grid[24][38] = PIPE_BL
    grid[24][39] = PIPE_BR
    grid[25][38] = PIPE_BL
    grid[25][39] = PIPE_BR

    # Pipe 3: tall (4 tall) at cols 58-59
    grid[22][58] = PIPE_TL
    grid[22][59] = PIPE_TR
    grid[23][58] = PIPE_BL
    grid[23][59] = PIPE_BR
    grid[24][58] = PIPE_BL
    grid[24][59] = PIPE_BR
    grid[25][58] = PIPE_BL
    grid[25][59] = PIPE_BR

    # Staircase at end leading to flagpole (cols 185-193, ascending only)
    for step in range(9):
        col = 185 + step
        for row_offset in range(step + 1):
            r = 25 - row_offset
            if 0 <= r < ROWS and 0 <= col < COLS:
                grid[r][col] = STAIR

    return grid


def grid_to_csv(grid):
    lines = []
    for row in grid:
        lines.append(','.join(str(v) for v in row))
    return '\n'.join(lines)


# =============================================================================
# Sprite generation helpers
# =============================================================================

def _make_enemy_sprite(eid, src, x, y, w, h, fw, fh, behavior, anim_frames="0-1"):
    """Generate XML for an enemy sprite."""
    return f'''    <qg:sprite id="{eid}" src="{src}" x="{x}" y="{y}"
               width="{w}" height="{h}" frame-width="{fw}" frame-height="{fh}"
               body="dynamic" bounce="0" friction="0.3" tag="enemy">
      <qg:animation name="walk" frames="{anim_frames}" speed="0.2" loop="true" auto-play="true" />
      <qg:use behavior="{behavior}"
             on-collision="onWall" collision-tag="tilemap-collision" />
    </qg:sprite>'''


def _generate_block_sprites():
    """Generate all brick and Q-block sprites as individual destroyable sprites."""
    lines = []

    # Q-blocks (with NES texture from qblock_tile.png)
    for i, (row, col) in enumerate(QBLOCK_POSITIONS):
        sid = f"qb{i+1}"
        x = col * 16 + 8
        y = row * 16 + 8
        lines.append(
            f'    <qg:sprite id="{sid}" src="qblock_tile.png" x="{x}" y="{y}" width="16" height="16"'
            f' body="static" tag="qblock">'
        )
        lines.append(
            f'      <qg:use behavior="QBlock"'
            f' on-collision="onHit" collision-tag="player" />'
        )
        lines.append(f'    </qg:sprite>')

    # Bricks (with NES texture from brick_tile.png)
    for i, (row, col) in enumerate(BRICK_POSITIONS):
        sid = f"brick{i+1}"
        x = col * 16 + 8
        y = row * 16 + 8
        lines.append(
            f'    <qg:sprite id="{sid}" src="brick_tile.png" x="{x}" y="{y}" width="16" height="16"'
            f' body="static" tag="brick">'
        )
        lines.append(
            f'      <qg:use behavior="BrickBlock"'
            f' on-collision="onHit" collision-tag="player" />'
        )
        lines.append(f'    </qg:sprite>')

    return '\n'.join(lines)


# =============================================================================
# Mario .q file generation
# =============================================================================

def generate_mario_q():
    bg_csv = grid_to_csv(generate_background())
    terrain_grid = generate_terrain()
    terrain_csv = grid_to_csv(terrain_grid)
    terrain_visual_csv = grid_to_csv(terrain_grid)

    GROUND_Y = 416  # top of ground surface (row 26 * 16)
    MARIO_Y = GROUND_Y - 16  # 400
    GOOMBA_Y = GROUND_Y - 8  # 408
    KOOPA_Y = GROUND_Y - 12  # 404 (koopa is 24px tall, center anchor)

    block_sprites = _generate_block_sprites()

    # Goomba positions (x coords spread across the level)
    goomba_xs = [352, 540, 640, 880, 1200, 1500, 1800, 2400]
    goomba_sprites = '\n'.join(
        _make_enemy_sprite(f"goomba{i+1}", "goomba.png", x, GOOMBA_Y,
                          16, 16, 16, 16, "GoombaAI")
        for i, x in enumerate(goomba_xs)
    )

    # Koopa positions
    koopa_xs = [700, 1100, 1700, 2200]
    koopa_sprites = '\n'.join(
        _make_enemy_sprite(f"koopa{i+1}", "koopa.png", x, KOOPA_Y,
                          16, 24, 16, 24, "KoopaAI")
        for i, x in enumerate(koopa_xs)
    )

    return f'''<q:application id="mario" type="game" engine="2d">

  <!-- === BEHAVIORS === -->

  <qg:behavior name="MarioBehavior">
    <q:function name="onEnemyHit">
      var other = this._other;
      var myBody = this.owner.body;
      var enemyBody = other ? other.body : null;
      var stomped = false;
      if (myBody &amp;&amp; enemyBody) {{
        /* Stomp: Mario's bottom must be above enemy's vertical center */
        var marioBottom = myBody.position.y + 16;
        var enemyCenter = enemyBody.position.y;
        stomped = (marioBottom &lt; enemyCenter + 4) &amp;&amp; (myBody.velocity.y &gt; 0);
      }}
      if (stomped) {{
        Matter.Body.setVelocity(myBody, {{x: myBody.velocity.x, y: -8}});
        game.destroy(other);
        score += 100;
        _updateHUD();
      }} else {{
        lives--;
        if (lives &lt;= 0) {{
          gameOver = true;
          _updateHUD();
        }} else {{
          game.respawn("mario", 40, {MARIO_Y});
          _updateHUD();
        }}
      }}
    </q:function>

    <q:function name="onCoinGet">
      var other = this._other;
      coins++;
      score += 200;
      game.destroy(other);
      game.play('coin_sfx');
      _updateHUD();
    </q:function>

    <q:function name="onBlockHit">
      var other = this._other;
      var myBody = this.owner.body;
      if (myBody &amp;&amp; other &amp;&amp; other.body) {{
        var myY = myBody.position.y;
        var blockY = other.body.position.y;
        /* Only bounce if Mario is below the block */
        if (myY &gt; blockY + 4) {{
          Matter.Body.setVelocity(myBody, {{x: myBody.velocity.x, y: 2}});
        }}
      }}
    </q:function>

    <q:function name="onDeath">
      lives--;
      if (lives &lt;= 0) {{
        gameOver = true;
      }} else {{
        game.respawn("mario", 40, {MARIO_Y});
      }}
      _updateHUD();
    </q:function>

    <q:function name="onWin">
      if (!won) {{
        won = true;
        score += 5000;
        _updateHUD();
        /* Stop theme music and play fanfare */
        game.stop('theme_bgm');
        game.play('fanfare_sfx');
        /* Flagpole slide: disable controls, slide Mario down the pole */
        var marioBody = _sprites["mario"].body;
        var marioSprite = _sprites["mario"].sprite;
        if (marioBody) {{
          Matter.Body.setStatic(marioBody, true);
          Matter.Body.setVelocity(marioBody, {{x: 0, y: 0}});
          /* Slide down to ground level */
          var slideTarget = {GROUND_Y - 16};
          var slideInterval = setInterval(function() {{
            if (marioBody.position.y &lt; slideTarget) {{
              Matter.Body.setPosition(marioBody, {{
                x: marioBody.position.x,
                y: marioBody.position.y + 2
              }});
              marioSprite.y = marioBody.position.y;
            }} else {{
              clearInterval(slideInterval);
              /* Walk right off screen after reaching ground */
              Matter.Body.setStatic(marioBody, false);
              var walkInterval = setInterval(function() {{
                Matter.Body.setVelocity(marioBody, {{x: 3, y: marioBody.velocity.y}});
                marioSprite.scale.x = Math.abs(marioSprite.scale.x);
              }}, 16);
              setTimeout(function() {{ clearInterval(walkInterval); }}, 2000);
            }}
          }}, 16);
        }}
      }}
    </q:function>
  </qg:behavior>

  <qg:behavior name="GoombaAI">
    <q:set name="dir" value="-1" type="integer" />
    <q:set name="spd" value="1" type="float" />

    <q:function name="update">
      var b = this.owner.body;
      if (b) Matter.Body.setVelocity(b, {{x: this.dir * this.spd, y: b.velocity.y}});
    </q:function>

    <q:function name="onWall">
      this.dir *= -1;
    </q:function>
  </qg:behavior>

  <qg:behavior name="KoopaAI">
    <q:set name="dir" value="-1" type="integer" />
    <q:set name="spd" value="0.8" type="float" />

    <q:function name="update">
      var b = this.owner.body;
      if (b) Matter.Body.setVelocity(b, {{x: this.dir * this.spd, y: b.velocity.y}});
    </q:function>

    <q:function name="onWall">
      this.dir *= -1;
    </q:function>
  </qg:behavior>

  <qg:behavior name="QBlock">
    <q:set name="active" value="true" type="boolean" />

    <q:function name="onHit">
      if (!this.active) return;
      var other = this._other;
      if (!other || !other.body) return;
      /* Position-based: player must be BELOW block (hitting from underneath) */
      var playerY = other.body.position.y;
      var blockY = this.owner.body ? this.owner.body.position.y : this.owner.sprite.y;
      if (playerY &gt; blockY + 4) {{
        this.active = false;
        coins++;
        score += 200;
        game.play('powerup_sfx');
        _updateHUD();
        var spr = this.owner.sprite;
        if (spr) {{
          /* Change to used block texture */
          spr.texture = PIXI.Texture.from('used_tile.png');
          /* Bounce animation */
          var origY = spr.y;
          spr.y -= 8;
          setTimeout(function() {{ spr.y = origY; }}, 150);
        }}
      }}
    </q:function>
  </qg:behavior>

  <qg:behavior name="BrickBlock">
    <q:set name="broken" value="false" type="boolean" />

    <q:function name="onHit">
      if (this.broken) return;
      var other = this._other;
      if (!other || !other.body) return;
      /* Position-based: player must be BELOW block (hitting from underneath) */
      var playerY = other.body.position.y;
      var blockY = this.owner.body ? this.owner.body.position.y : this.owner.sprite.y;
      if (playerY &gt; blockY + 4) {{
        this.broken = true;
        score += 50;
        _updateHUD();
        /* Bounce up then destroy */
        var spr = this.owner.sprite;
        var self = this;
        if (spr) {{
          var origY = spr.y;
          spr.y -= 8;
          setTimeout(function() {{
            game.destroy(self.owner);
          }}, 150);
        }} else {{
          game.destroy(this.owner);
        }}
      }}
    </q:function>
  </qg:behavior>

  <!-- === SCENE === -->

  <qg:scene name="world1" width="3392" height="448" background="#5C94FC">

    <qg:physics gravity-y="10" bounds="none" />

    <qg:camera follow="mario" lerp="0.08" bounds="scene" />

    <q:set name="score" value="0" type="integer" />
    <q:set name="coins" value="0" type="integer" />
    <q:set name="lives" value="3" type="integer" />
    <q:set name="gameOver" value="false" type="boolean" />
    <q:set name="won" value="false" type="boolean" />

    <!-- TILEMAP (ground, pipes, stairs - NO bricks/qblocks) -->
    <qg:tilemap id="level" src="tileset.png" tile-width="16" tile-height="16">

      <qg:layer name="background">
{bg_csv}
      </qg:layer>

      <qg:layer name="terrain_visual">
{terrain_visual_csv}
      </qg:layer>

      <qg:layer name="terrain" collision="true">
{terrain_csv}
      </qg:layer>
    </qg:tilemap>

    <!-- Mario (player) -->
    <qg:sprite id="mario" src="player.png" x="40" y="{MARIO_Y}"
               width="16" height="32" frame-width="16" frame-height="32"
               body="dynamic" controls="arrows" speed="6" jump-force="20"
               bounce="0" friction="0.8" tag="player">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1-2" speed="0.15" loop="true" />
      <qg:animation name="jump" frames="3" speed="0.1" loop="false" />
      <qg:use behavior="MarioBehavior"
             on-collision="onEnemyHit" collision-tag="enemy" />
      <qg:use behavior="MarioBehavior"
             on-collision="onCoinGet" collision-tag="coin" />
      <qg:use behavior="MarioBehavior"
             on-collision="onBlockHit" collision-tag="qblock" />
      <qg:use behavior="MarioBehavior"
             on-collision="onBlockHit" collision-tag="brick" />
      <qg:use behavior="MarioBehavior"
             on-collision="onDeath" collision-tag="deathzone" />
      <qg:use behavior="MarioBehavior"
             on-collision="onWin" collision-tag="flagpole" />
    </qg:sprite>

    <!-- Goombas (8 spread across level) -->
{goomba_sprites}

    <!-- Koopa Troopas (4 spread across level) -->
{koopa_sprites}

    <!-- Interactive Blocks (individual destroyable sprites) -->
{block_sprites}

    <!-- Flagpole -->
    <qg:sprite id="flagpole" src="" x="3280" y="{GROUND_Y - 80}"
               width="4" height="160" color="#808080"
               body="static" sensor="true" tag="flagpole" />

    <!-- Death zone (below screen) -->
    <qg:sprite id="deathzone" src="" x="1696" y="480"
               width="3392" height="32" color="#000000"
               body="static" sensor="true" tag="deathzone"
               visible="false" />

    <!-- Sounds -->
    <qg:sound id="theme_bgm" src="theme.wav" channel="bgm" loop="true" trigger="scene.start" volume="0.4" />
    <qg:sound id="jump_sfx" src="jump.wav" channel="sfx" trigger="player.jump" />
    <qg:sound id="coin_sfx" src="coin.wav" channel="sfx" />
    <qg:sound id="powerup_sfx" src="powerup.wav" channel="sfx" />
    <qg:sound id="fanfare_sfx" src="fanfare.wav" channel="bgm" />

    <!-- HUD -->
    <qg:hud position="top-left">
      <text style="font-size:14px; color:#fff; font-family:monospace; text-shadow:1px 1px #000; padding:8px;">
        MARIO  {{score}}
      </text>
    </qg:hud>
    <qg:hud position="top-center">
      <text style="font-size:14px; color:#ffd700; font-family:monospace; text-shadow:1px 1px #000;">
        x{{coins}}
      </text>
    </qg:hud>
    <qg:hud position="top-right">
      <text style="font-size:14px; color:#fff; font-family:monospace; text-shadow:1px 1px #000; padding:8px;">
        WORLD 1-1  LIVES:{{lives}}
      </text>
    </qg:hud>
    <qg:hud position="center">
      <text style="font-size:36px; color:#fff; font-family:monospace; text-shadow:3px 3px #000;">
        {{gameOver ? 'GAME OVER' : (won ? 'STAGE CLEAR!' : '')}}
      </text>
    </qg:hud>

    <!-- Restart -->
    <q:function name="restart">
      game.respawn("mario", 40, {MARIO_Y});
      <q:set name="score" value="{{0}}" />
      <q:set name="coins" value="{{0}}" />
      <q:set name="lives" value="{{3}}" />
      <q:set name="gameOver" value="{{false}}" />
      <q:set name="won" value="{{false}}" />
      _updateHUD();
    </q:function>
    <qg:input key="r" action="restart" type="press" />

  </qg:scene>
</q:application>
'''


# =============================================================================
# Build
# =============================================================================

def main():
    output_dir = PROJECT_ROOT / "projects" / "mario" / "static"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate mario.q
    mario_q_content = generate_mario_q()
    mario_q_path = PROJECT_ROOT / "examples" / "mario.q"
    mario_q_path.write_text(mario_q_content, encoding='utf-8')
    print(f"[1/2] Generated {mario_q_path}")

    # 2. Build game.html
    from core.parser import QuantumParser
    from runtime.game_code_generator import GameCodeGenerator

    parser = QuantumParser()
    ast = parser.parse(mario_q_content)

    gen = GameCodeGenerator()
    html = gen.generate(
        ast.scenes[0],
        behaviors=ast.behaviors,
        prefabs=ast.prefabs,
        title='Super Mario - Quantum',
        source_code=mario_q_content,
    )

    game_html_path = output_dir / "game.html"
    game_html_path.write_text(html, encoding='utf-8')
    print(f"[2/2] Generated {game_html_path} ({len(html)} bytes)")

    # Verify
    checks = {
        'Ground tiles': 'tile_level_26_' in html,
        'Mario sprite': '_spr_mario' in html,
        'Visual tilemap': '_tileData_level_background' in html,
        'Behaviors': all(b in html for b in ['MarioBehavior', 'GoombaAI', 'KoopaAI', 'QBlock', 'BrickBlock']),
        'Goombas (8)': html.count('_spr_goomba') >= 8,
        'Koopas (4)': html.count('_spr_koopa') >= 4,
        'Bricks (12)': html.count('_spr_brick') >= 12,
        'Q-blocks (4)': html.count('_spr_qb') >= 4,
        'Collision handlers': html.count('collisionHandlers.push') >= 4,
    }
    print()
    for name, ok in checks.items():
        print(f"  [{'OK' if ok else 'FAIL'}] {name}")


if __name__ == '__main__':
    main()
