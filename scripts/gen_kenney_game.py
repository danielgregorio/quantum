#!/usr/bin/env python3
"""
Generate the Kenney Pixel Platformer .q file for Quantum game engine.
Outputs: examples/kenney_platformer.q

Tileset: 18x18 tiles, 20 cols x 9 rows (tilemap_packed.png)
Characters: 24x24 tiles, 9 cols x 3 rows (tilemap-characters_packed.png)
Backgrounds: 24x24 tiles, 6 cols x 4 rows (tilemap-backgrounds_packed.png)

Level: 200 cols x 25 rows of 18x18 = 3600x450 pixels
"""

import os

COLS = 200
ROWS = 25
TILE = 18

# Tile indices (0-indexed in tileset, +1 for CSV since 0=empty)
GRASS_TOP_L  = 22  # idx 23
GRASS_TOP_C  = 23  # idx 24
GRASS_TOP_R  = 24  # idx 25 (actually tile 23 is top-center per spec)

# Re-read spec carefully:
# tile 21 (idx 22): Grass ground top-left
# tile 22 (idx 23): Grass ground top-center
# tile 23 (idx 24): Grass ground top-right
# tile 24 (idx 25): Dirt fill interior
# tile 4 (idx 5): Dirt fill plain
# tile 5 (idx 6): Dirt fill variant

T_GRASS_TL = 22  # tile 21
T_GRASS_TC = 23  # tile 22
T_GRASS_TR = 24  # tile 23
T_DIRT     = 25  # tile 24 - dirt fill interior
T_DIRT2    = 5   # tile 4 - dirt fill plain
T_DIRT3    = 6   # tile 5 - dirt fill variant
T_DIRT_INT = 105 # tile 104
T_DIRT_INT2= 121 # tile 120
T_DIRT_DARK= 49  # tile 48

T_PLAT_L   = 41  # tile 40 - platform left edge
T_PLAT_C   = 42  # tile 41 - platform center
T_PLAT_C2  = 43  # tile 42 - platform center variant
T_PLAT_R   = 44  # tile 43 - platform right edge

T_QBLOCK   = 11  # tile 10 - question block
T_QBLOCK2  = 12  # tile 11 - question block variant
T_GOLD_BLK = 10  # tile 9 - gold block

T_COIN     = 152 # tile 151 - gold coin
T_GEM      = 68  # tile 67 - blue diamond
T_CRATE    = 64  # tile 63 - crate
T_BUSH     = 58  # tile 57 - bush
T_SIGN     = 110 # tile 109 - sign post
T_FLAG     = 113 # tile 112 - red flag
T_PIPE     = 38  # tile 37 - pipe body
T_ROCK     = 9   # tile 8 - pebble

T_SOLID    = 25  # Use dirt fill as the generic solid collision tile
T_PLAT_SOLID = 42 # Platform center as solid for floating platforms

EMPTY = 0


def make_grid():
    return [[EMPTY] * COLS for _ in range(ROWS)]


def fill_rect(grid, r1, c1, r2, c2, val):
    """Fill grid[r1..r2][c1..c2] inclusive with val."""
    for r in range(max(0, r1), min(ROWS, r2 + 1)):
        for c in range(max(0, c1), min(COLS, c2 + 1)):
            grid[r][c] = val


def set_tile(grid, r, c, val):
    if 0 <= r < ROWS and 0 <= c < COLS:
        grid[r][c] = val


def build_visual_layer():
    """Build the decorative visual tilemap layer."""
    g = make_grid()

    # === SECTION 1 (cols 0-30): Start area ===
    # Ground: row 21 = grass top, rows 22-24 = dirt
    fill_rect(g, 21, 0, 21, 30, T_GRASS_TC)
    # Left edge
    set_tile(g, 21, 0, T_GRASS_TL)
    fill_rect(g, 22, 0, 24, 30, T_DIRT)
    # Add some dirt variety
    fill_rect(g, 23, 2, 23, 5, T_DIRT2)
    fill_rect(g, 24, 10, 24, 15, T_DIRT3)

    # Bush decorations on ground
    set_tile(g, 20, 3, T_BUSH)
    set_tile(g, 20, 4, T_BUSH)
    set_tile(g, 20, 20, T_BUSH)

    # Coins in air at row 17, cols 8-10
    set_tile(g, 17, 8, T_COIN)
    set_tile(g, 17, 9, T_COIN)
    set_tile(g, 17, 10, T_COIN)

    # Question block at col 15, row 17
    set_tile(g, 17, 15, T_QBLOCK)

    # Small rock decoration
    set_tile(g, 20, 25, T_ROCK)

    # === SECTION 2 (cols 31-55): First challenges ===
    # Ground continues cols 31-34
    fill_rect(g, 21, 31, 21, 34, T_GRASS_TC)
    fill_rect(g, 22, 31, 24, 34, T_DIRT)
    set_tile(g, 21, 34, T_GRASS_TR)

    # GAP at cols 35-37 (no ground)

    # Ground continues cols 38-55
    fill_rect(g, 21, 38, 21, 55, T_GRASS_TC)
    set_tile(g, 21, 38, T_GRASS_TL)
    fill_rect(g, 22, 38, 24, 55, T_DIRT)

    # Floating platform at row 17 (cols 39-43)
    set_tile(g, 17, 39, T_PLAT_L)
    set_tile(g, 17, 40, T_PLAT_C)
    set_tile(g, 17, 41, T_PLAT_C2)
    set_tile(g, 17, 42, T_PLAT_C)
    set_tile(g, 17, 43, T_PLAT_R)

    # Coins in arc over gap
    set_tile(g, 16, 35, T_COIN)
    set_tile(g, 15, 36, T_COIN)
    set_tile(g, 16, 37, T_COIN)

    # Question block higher up
    set_tile(g, 14, 45, T_QBLOCK)

    # Bush
    set_tile(g, 20, 50, T_BUSH)
    set_tile(g, 20, 51, T_BUSH)

    # === SECTION 3 (cols 56-85): Elevated area ===
    # Ground cols 56-59 normal height
    fill_rect(g, 21, 56, 21, 59, T_GRASS_TC)
    fill_rect(g, 22, 56, 24, 59, T_DIRT)

    # Pipe at col 58
    set_tile(g, 19, 58, T_PIPE)
    set_tile(g, 20, 58, T_PIPE)

    # Elevated step cols 60-74 (ground at row 18)
    fill_rect(g, 18, 60, 18, 74, T_GRASS_TC)
    set_tile(g, 18, 60, T_GRASS_TL)
    set_tile(g, 18, 74, T_GRASS_TR)
    fill_rect(g, 19, 60, 24, 74, T_DIRT)
    # Dirt variety
    fill_rect(g, 20, 62, 20, 66, T_DIRT2)
    fill_rect(g, 22, 60, 22, 74, T_DIRT3)

    # Diamond gem at col 65, row 14
    set_tile(g, 14, 65, T_GEM)

    # Coins on elevated area
    set_tile(g, 15, 62, T_COIN)
    set_tile(g, 15, 63, T_COIN)
    set_tile(g, 15, 64, T_COIN)

    # GAP at cols 75-78
    # Ground continues cols 79-85
    fill_rect(g, 21, 79, 21, 85, T_GRASS_TC)
    set_tile(g, 21, 79, T_GRASS_TL)
    fill_rect(g, 22, 79, 24, 85, T_DIRT)

    # Floating platforms at staggered heights
    set_tile(g, 19, 76, T_PLAT_L)
    set_tile(g, 19, 77, T_PLAT_R)
    set_tile(g, 16, 78, T_PLAT_L)
    set_tile(g, 16, 79, T_PLAT_R)

    # Coins near platforms
    set_tile(g, 18, 76, T_COIN)
    set_tile(g, 15, 78, T_COIN)

    # === SECTION 4 (cols 86-120): Underground feel ===
    fill_rect(g, 21, 86, 21, 120, T_GRASS_TC)
    fill_rect(g, 22, 86, 24, 120, T_DIRT)
    fill_rect(g, 23, 90, 24, 110, T_DIRT_DARK)

    # Brown platform "ceiling" at row 10 (cols 90-110)
    fill_rect(g, 10, 90, 10, 110, T_PLAT_C)
    set_tile(g, 10, 90, T_PLAT_L)
    set_tile(g, 10, 110, T_PLAT_R)

    # Question blocks at row 17
    set_tile(g, 17, 95, T_QBLOCK)
    set_tile(g, 17, 100, T_QBLOCK2)
    set_tile(g, 17, 105, T_QBLOCK)

    # Coins between ceiling and ground
    set_tile(g, 14, 93, T_COIN)
    set_tile(g, 14, 97, T_COIN)
    set_tile(g, 14, 102, T_COIN)
    set_tile(g, 14, 107, T_COIN)
    set_tile(g, 16, 92, T_COIN)
    set_tile(g, 16, 98, T_COIN)
    set_tile(g, 16, 108, T_COIN)

    # Crate decorations
    set_tile(g, 20, 88, T_CRATE)
    set_tile(g, 20, 115, T_CRATE)

    # === SECTION 5 (cols 121-155): Platforming gauntlet ===
    # Ground cols 121-124
    fill_rect(g, 21, 121, 21, 124, T_GRASS_TC)
    fill_rect(g, 22, 121, 24, 124, T_DIRT)

    # GAP cols 125-127
    # Floating platform in gap
    set_tile(g, 19, 126, T_PLAT_L)
    set_tile(g, 19, 127, T_PLAT_R)

    # Ground cols 128-134
    fill_rect(g, 21, 128, 21, 134, T_GRASS_TC)
    set_tile(g, 21, 128, T_GRASS_TL)
    fill_rect(g, 22, 128, 24, 134, T_DIRT)

    # GAP cols 135-138
    # Floating platforms
    set_tile(g, 18, 136, T_PLAT_L)
    set_tile(g, 18, 137, T_PLAT_R)

    # Diamond for tough jump
    set_tile(g, 14, 137, T_GEM)

    # Ground cols 139-144
    fill_rect(g, 21, 139, 21, 144, T_GRASS_TC)
    set_tile(g, 21, 139, T_GRASS_TL)
    fill_rect(g, 22, 139, 24, 144, T_DIRT)

    # Flag/checkpoint at col 140
    set_tile(g, 20, 140, T_SIGN)
    set_tile(g, 19, 140, T_FLAG)

    # GAP cols 145-148
    # Floating platform
    set_tile(g, 17, 146, T_PLAT_L)
    set_tile(g, 17, 147, T_PLAT_C)
    set_tile(g, 17, 148, T_PLAT_R)

    # Coins above platforms
    set_tile(g, 16, 146, T_COIN)
    set_tile(g, 16, 147, T_COIN)

    # Ground cols 149-155
    fill_rect(g, 21, 149, 21, 155, T_GRASS_TC)
    set_tile(g, 21, 149, T_GRASS_TL)
    fill_rect(g, 22, 149, 24, 155, T_DIRT)

    # Diamond gem
    set_tile(g, 14, 152, T_GEM)

    # === SECTION 6 (cols 156-199): Final stretch ===
    # Ground cols 156-199
    fill_rect(g, 21, 156, 21, 199, T_GRASS_TC)
    fill_rect(g, 22, 156, 24, 199, T_DIRT)

    # Ascending staircase (cols 160-175)
    # Step 1: row 20, cols 160-161
    fill_rect(g, 20, 160, 20, 161, T_GOLD_BLK)
    # Step 2: row 19, cols 162-163
    fill_rect(g, 19, 162, 20, 163, T_GOLD_BLK)
    # Step 3: row 18, cols 164-165
    fill_rect(g, 18, 164, 20, 165, T_GOLD_BLK)
    # Step 4: row 17, cols 166-167
    fill_rect(g, 17, 166, 20, 167, T_GOLD_BLK)
    # Step 5: row 16, cols 168-169
    fill_rect(g, 16, 168, 20, 169, T_GOLD_BLK)
    # Step 6: row 15, cols 170-171
    fill_rect(g, 15, 170, 20, 171, T_GOLD_BLK)
    # Step 7: row 14, cols 172-173
    fill_rect(g, 14, 172, 20, 173, T_GOLD_BLK)
    # Step 8: row 13, cols 174-175
    fill_rect(g, 13, 174, 20, 175, T_GOLD_BLK)

    # Coins leading to goal
    set_tile(g, 12, 178, T_COIN)
    set_tile(g, 12, 180, T_COIN)
    set_tile(g, 12, 182, T_COIN)

    # Goal area: sign + flag at col 190
    set_tile(g, 20, 190, T_SIGN)
    set_tile(g, 19, 190, T_FLAG)

    # Bush decorations
    set_tile(g, 20, 185, T_BUSH)
    set_tile(g, 20, 186, T_BUSH)
    set_tile(g, 20, 195, T_BUSH)

    # Question block in final area
    set_tile(g, 17, 180, T_QBLOCK2)

    return g


def build_collision_layer():
    """Build the collision tilemap layer. Uses T_SOLID for all collidable ground."""
    g = make_grid()

    # === SECTION 1 (cols 0-30): Full ground ===
    fill_rect(g, 21, 0, 24, 30, T_SOLID)

    # === SECTION 2 (cols 31-55) ===
    fill_rect(g, 21, 31, 24, 34, T_SOLID)
    # GAP at 35-37
    fill_rect(g, 21, 38, 24, 55, T_SOLID)
    # Floating platform at row 17
    fill_rect(g, 17, 39, 17, 43, T_PLAT_SOLID)

    # === SECTION 3 (cols 56-85) ===
    fill_rect(g, 21, 56, 24, 59, T_SOLID)
    # Elevated ground
    fill_rect(g, 18, 60, 24, 74, T_SOLID)
    # GAP 75-78
    fill_rect(g, 21, 79, 24, 85, T_SOLID)
    # Floating platforms
    fill_rect(g, 19, 76, 19, 77, T_PLAT_SOLID)
    fill_rect(g, 16, 78, 16, 79, T_PLAT_SOLID)

    # === SECTION 4 (cols 86-120) ===
    fill_rect(g, 21, 86, 24, 120, T_SOLID)
    # Ceiling platforms
    fill_rect(g, 10, 90, 10, 110, T_PLAT_SOLID)

    # === SECTION 5 (cols 121-155) ===
    fill_rect(g, 21, 121, 24, 124, T_SOLID)
    # Platform in gap
    fill_rect(g, 19, 126, 19, 127, T_PLAT_SOLID)
    fill_rect(g, 21, 128, 24, 134, T_SOLID)
    # Platform in gap
    fill_rect(g, 18, 136, 18, 137, T_PLAT_SOLID)
    fill_rect(g, 21, 139, 24, 144, T_SOLID)
    # Platform in gap
    fill_rect(g, 17, 146, 17, 148, T_PLAT_SOLID)
    fill_rect(g, 21, 149, 24, 155, T_SOLID)

    # === SECTION 6 (cols 156-199) ===
    fill_rect(g, 21, 156, 24, 199, T_SOLID)
    # Staircase collision
    fill_rect(g, 20, 160, 20, 161, T_SOLID)
    fill_rect(g, 19, 162, 20, 163, T_SOLID)
    fill_rect(g, 18, 164, 20, 165, T_SOLID)
    fill_rect(g, 17, 166, 20, 167, T_SOLID)
    fill_rect(g, 16, 168, 20, 169, T_SOLID)
    fill_rect(g, 15, 170, 20, 171, T_SOLID)
    fill_rect(g, 14, 172, 20, 173, T_SOLID)
    fill_rect(g, 13, 174, 20, 175, T_SOLID)

    return g


def grid_to_csv(grid):
    """Convert grid to CSV string with newlines between rows."""
    lines = []
    for row in grid:
        assert len(row) == COLS, f"Row has {len(row)} values, expected {COLS}"
        lines.append(",".join(str(v) for v in row))
    assert len(lines) == ROWS, f"Grid has {len(lines)} rows, expected {ROWS}"
    return "\n".join(lines)


def generate_xml():
    visual = build_visual_layer()
    collision = build_collision_layer()

    visual_csv = grid_to_csv(visual)
    collision_csv = grid_to_csv(collision)

    # Sprite positions (pixel coords): col * 18 for x, row * 18 for y
    # Player starts at col 2, needs to be on ground (row 21 is grass top, so y ~ row 20 * 18 = 360 for feet)
    # Player is 24x24 so center should be slightly above ground
    player_x = 2 * TILE  # 36
    player_y = 20 * TILE - 12  # 348 (above grass at row 21)

    xml = f'''<q:application id="kenney_platformer" type="game" engine="2d">

  <!-- === BEHAVIORS === -->

  <qg:behavior name="PlayerBehavior">
    <q:set name="invulnFrames" value="0" type="number" />
    <q:set name="checkpointX" value="36" type="number" />
    <q:set name="checkpointY" value="348" type="number" />

    <q:function name="onEnemyHit">
      var other = this._other;
      var myBody = this.owner.body;
      var enemyBody = other ? other.body : null;
      if (this.invulnFrames &gt; 0) return;
      var stomped = false;
      if (myBody &amp;&amp; enemyBody) {{
        var myBottom = myBody.position.y + 12;
        var enemyTop = enemyBody.position.y - 12;
        stomped = (myBottom &lt; enemyTop + 14) &amp;&amp; (myBody.velocity.y &gt; 1);
      }}
      if (stomped) {{
        Matter.Body.setVelocity(myBody, {{x: myBody.velocity.x, y: -10}});
        game.destroy(other);
        score += 100;
        game.play('stomp_sfx');
        _updateHUD();
      }} else {{
        lives--;
        this.invulnFrames = 120;
        game.play('hurt_sfx');
        if (lives &lt;= 0) {{
          gameOver = true;
        }} else {{
          game.respawn("player", this.checkpointX, this.checkpointY);
        }}
        _updateHUD();
      }}
    </q:function>

    <q:function name="onCoinGet">
      var other = this._other;
      coins++;
      score += 50;
      game.destroy(other);
      game.play('coin_sfx');
      if (coins &gt;= 100) {{
        coins = 0;
        lives++;
      }}
      _updateHUD();
    </q:function>

    <q:function name="onGemGet">
      var other = this._other;
      score += 500;
      game.destroy(other);
      game.play('powerup_sfx');
      _updateHUD();
    </q:function>

    <q:function name="onBlockHit">
      var other = this._other;
      var myBody = this.owner.body;
      if (myBody &amp;&amp; other &amp;&amp; other.body) {{
        var myY = myBody.position.y;
        var blockY = other.body.position.y;
        if (myY &gt; blockY + 4 &amp;&amp; myBody.velocity.y &lt; 0) {{
          coins++;
          score += 50;
          game.play('block_sfx');
          Matter.Body.setVelocity(myBody, {{x: myBody.velocity.x, y: 2}});
          var spr = other.sprite;
          if (spr) {{
            var origY = spr.y;
            spr.y -= 6;
            setTimeout(function() {{ spr.y = origY; }}, 150);
          }}
          _updateHUD();
        }}
      }}
    </q:function>

    <q:function name="onFlagGet">
      if (!won) {{
        won = true;
        score += 5000;
        game.play('win_sfx');
        _updateHUD();
        var myBody = _sprites["player"].body;
        if (myBody) {{
          Matter.Body.setStatic(myBody, true);
          Matter.Body.setVelocity(myBody, {{x: 0, y: 0}});
        }}
      }}
    </q:function>

    <q:function name="onCheckpoint">
      this.checkpointX = this.owner.body ? this.owner.body.position.x : this.checkpointX;
      this.checkpointY = this.owner.body ? this.owner.body.position.y : this.checkpointY;
    </q:function>

    <q:function name="onDeath">
      lives--;
      if (lives &lt;= 0) {{
        gameOver = true;
      }} else {{
        game.respawn("player", this.checkpointX, this.checkpointY);
      }}
      _updateHUD();
    </q:function>

    <q:function name="update">
      if (this.invulnFrames &gt; 0) {{
        this.invulnFrames--;
        var spr = this.owner.sprite;
        if (spr) {{
          spr.alpha = (this.invulnFrames % 8 &lt; 4) ? 0.3 : 1.0;
        }}
        if (this.invulnFrames === 0 &amp;&amp; spr) {{
          spr.alpha = 1.0;
        }}
      }}
    </q:function>
  </qg:behavior>

  <qg:behavior name="PatrolAI">
    <q:set name="dir" value="-1" type="number" />
    <q:set name="spd" value="1.0" type="number" />

    <q:function name="update">
      var b = this.owner.body;
      if (b) Matter.Body.setVelocity(b, {{x: this.dir * this.spd, y: b.velocity.y}});
    </q:function>

    <q:function name="onWall">
      this.dir *= -1;
    </q:function>
  </qg:behavior>

  <qg:behavior name="SmartPatrolAI">
    <q:set name="dir" value="-1" type="number" />
    <q:set name="spd" value="0.8" type="number" />

    <q:function name="update">
      var b = this.owner.body;
      if (b) Matter.Body.setVelocity(b, {{x: this.dir * this.spd, y: b.velocity.y}});
    </q:function>

    <q:function name="onWall">
      this.dir *= -1;
    </q:function>

    <q:function name="onEdge">
      this.dir *= -1;
    </q:function>
  </qg:behavior>

  <qg:behavior name="FloatingCoin">
    <q:set name="timer" value="0" type="number" />
    <q:set name="baseY" value="0" type="number" />
    <q:set name="initialized" value="false" type="boolean" />

    <q:function name="update">
      if (!this.initialized) {{
        this.baseY = this.owner.sprite ? this.owner.sprite.y : 0;
        this.initialized = true;
      }}
      this.timer += 0.05;
      var spr = this.owner.sprite;
      if (spr) {{
        spr.y = this.baseY + Math.sin(this.timer) * 3;
      }}
    </q:function>
  </qg:behavior>

  <qg:behavior name="QBlockBehavior">
    <q:set name="active" value="true" type="boolean" />

    <q:function name="onHit">
      if (!this.active) return;
      var other = this._other;
      if (!other || !other.body) return;
      var playerY = other.body.position.y;
      var blockY = this.owner.body ? this.owner.body.position.y : this.owner.sprite.y;
      if (playerY &gt; blockY + 4) {{
        this.active = false;
        coins++;
        score += 50;
        game.play('block_sfx');
        _updateHUD();
        var spr = this.owner.sprite;
        if (spr) {{
          var origY = spr.y;
          spr.y -= 6;
          setTimeout(function() {{ spr.y = origY; }}, 150);
        }}
      }}
    </q:function>
  </qg:behavior>

  <!-- === SCENE === -->

  <qg:scene name="level1" width="3600" height="450" background="#92CDDB">

    <qg:physics gravity-y="9.8" bounds="none" />
    <qg:camera follow="player" lerp="0.08" bounds="scene" />

    <!-- State variables -->
    <q:set name="score" value="0" type="number" />
    <q:set name="coins" value="0" type="number" />
    <q:set name="lives" value="3" type="number" />
    <q:set name="gameOver" value="false" type="boolean" />
    <q:set name="won" value="false" type="boolean" />

    <!-- TILEMAP -->
    <qg:tilemap id="level" src="assets/kenney/tilemap_packed.png" tile-width="18" tile-height="18">

      <qg:layer name="terrain_visual">
{visual_csv}
      </qg:layer>

      <qg:layer name="terrain" collision="true">
{collision_csv}
      </qg:layer>

    </qg:tilemap>

    <!-- === PLAYER === -->
    <qg:sprite id="player" src="assets/kenney/tilemap-characters_packed.png" x="{player_x}" y="{player_y}"
               width="24" height="24" frame-width="24" frame-height="24"
               body="dynamic" controls="arrows" speed="4" jump-force="22"
               bounce="0" friction="0.8" tag="player">
      <qg:animation name="idle" frames="0" speed="0.1" loop="true" auto-play="true" />
      <qg:animation name="walk" frames="1,2" speed="0.15" loop="true" />
      <qg:use behavior="PlayerBehavior"
             on-collision="onEnemyHit" collision-tag="enemy" />
      <qg:use behavior="PlayerBehavior"
             on-collision="onCoinGet" collision-tag="coin" />
      <qg:use behavior="PlayerBehavior"
             on-collision="onGemGet" collision-tag="gem" />
      <qg:use behavior="PlayerBehavior"
             on-collision="onBlockHit" collision-tag="qblock" />
      <qg:use behavior="PlayerBehavior"
             on-collision="onFlagGet" collision-tag="flagpole" />
      <qg:use behavior="PlayerBehavior"
             on-collision="onCheckpoint" collision-tag="checkpoint" />
      <qg:use behavior="PlayerBehavior"
             on-collision="onDeath" collision-tag="deathzone" />
    </qg:sprite>

    <!-- === ENEMIES (8 total: 5 blue robots, 3 purple masked) === -->
'''

    enemies = [
        # (id, type, x_col, y_row, behavior)
        # Section 2: 2 enemies after gap
        ("enemy1", "blue",   42, 20, "PatrolAI"),
        ("enemy2", "blue",   48, 20, "PatrolAI"),
        # Section 3: enemies on elevated area
        ("enemy3", "purple", 64, 17, "SmartPatrolAI"),
        ("enemy4", "blue",   70, 17, "SmartPatrolAI"),
        # Section 4: enemies in cave
        ("enemy5", "purple", 96, 20, "PatrolAI"),
        ("enemy6", "blue",  103, 20, "PatrolAI"),
        # Section 5: enemy on platform
        ("enemy7", "purple", 130, 20, "SmartPatrolAI"),
        # Section 6: final enemy on stairs
        ("enemy8", "blue",  165, 17, "PatrolAI"),
    ]

    for eid, etype, col, row, behavior in enemies:
        ex = col * TILE
        ey = row * TILE - 12
        # Blue robot: chars 18,19,20 (row 2 in 9-col grid)
        # Purple masked: chars 24,25,26 (row 2 col 6,7,8... actually row index 2*9+6=24)
        if etype == "blue":
            frames = "18,19,20"
        else:
            frames = "24,25,26"
        xml += f'''    <qg:sprite id="{eid}" src="assets/kenney/tilemap-characters_packed.png" x="{ex}" y="{ey}"
               width="24" height="24" frame-width="24" frame-height="24"
               body="dynamic" bounce="0" friction="0.3" tag="enemy">
      <qg:animation name="walk" frames="{frames}" speed="0.2" loop="true" auto-play="true" />
      <qg:use behavior="{behavior}"
             on-collision="onWall" collision-tag="tilemap-collision" />
    </qg:sprite>
'''

    # === COINS (20 total) ===
    # Coins defined as sprites (not in tilemap) for collectability
    coins = [
        # Section 1: 3 coins
        (8, 17), (9, 17), (10, 17),
        # Section 2: arc over gap + extras
        (35, 16), (36, 15), (37, 16),
        # Section 3: elevated area coins
        (62, 15), (63, 15), (64, 15),
        (76, 18), (78, 15),
        # Section 4: cave coins
        (93, 14), (97, 14), (102, 14), (107, 14),
        (92, 16), (98, 16), (108, 16),
        # Section 6: leading to goal
        (178, 12), (180, 12),
    ]

    for i, (col, row) in enumerate(coins):
        cx = col * TILE + 9  # center in tile
        cy = row * TILE + 9
        xml += f'''    <qg:sprite id="coin{i+1}" src="assets/kenney/tilemap_packed.png" x="{cx}" y="{cy}"
               width="18" height="18" frame-width="18" frame-height="18"
               body="static" sensor="true" tag="coin" frame="{T_COIN - 1}">
      <qg:use behavior="FloatingCoin" />
    </qg:sprite>
'''

    # === GEMS (3 total) ===
    gems = [
        (65, 14),   # Section 3
        (137, 14),  # Section 5
        (152, 14),  # Section 5
    ]

    for i, (col, row) in enumerate(gems):
        gx = col * TILE + 9
        gy = row * TILE + 9
        xml += f'''    <qg:sprite id="gem{i+1}" src="assets/kenney/tilemap_packed.png" x="{gx}" y="{gy}"
               width="18" height="18" frame-width="18" frame-height="18"
               body="static" sensor="true" tag="gem" frame="{T_GEM - 1}">
      <qg:use behavior="FloatingCoin" />
    </qg:sprite>
'''

    # === QUESTION BLOCKS (5 total) ===
    qblocks = [
        (15, 17),   # Section 1
        (45, 14),   # Section 2
        (95, 17),   # Section 4
        (100, 17),  # Section 4
        (105, 17),  # Section 4
    ]

    for i, (col, row) in enumerate(qblocks):
        bx = col * TILE + 9
        by = row * TILE + 9
        xml += f'''    <qg:sprite id="qblock{i+1}" src="assets/kenney/tilemap_packed.png" x="{bx}" y="{by}"
               width="18" height="18" frame-width="18" frame-height="18"
               body="static" tag="qblock" frame="{T_QBLOCK - 1}">
      <qg:use behavior="QBlockBehavior" on-collision="onHit" collision-tag="player" />
    </qg:sprite>
'''

    # === FLAG (goal) ===
    flag_x = 190 * TILE + 9
    flag_y = 18 * TILE  # above ground
    xml += f'''    <!-- Goal flag -->
    <qg:sprite id="goal_flag" src="" x="{flag_x}" y="{flag_y}"
               width="4" height="72" color="#FF4444"
               body="static" sensor="true" tag="flagpole" />

    <!-- Checkpoint at col 140 -->
    <qg:sprite id="checkpoint1" src="" x="{140 * TILE + 9}" y="{19 * TILE}"
               width="18" height="36" color="#00000000"
               body="static" sensor="true" tag="checkpoint"
               visible="false" />

    <!-- Death zone (below screen) -->
    <qg:sprite id="deathzone" src="" x="1800" y="470"
               width="3600" height="32" color="#000000"
               body="static" sensor="true" tag="deathzone"
               visible="false" />

    <!-- === SOUNDS === -->
    <qg:sound id="jump_sfx" src="assets/kenney/audio/jump.ogg" channel="sfx" trigger="player.jump" />
    <qg:sound id="coin_sfx" src="assets/kenney/audio/coin.ogg" channel="sfx" />
    <qg:sound id="powerup_sfx" src="assets/kenney/audio/powerup.ogg" channel="sfx" />
    <qg:sound id="stomp_sfx" src="assets/kenney/audio/stomp.ogg" channel="sfx" />
    <qg:sound id="hurt_sfx" src="assets/kenney/audio/hurt.ogg" channel="sfx" />
    <qg:sound id="win_sfx" src="assets/kenney/audio/win.ogg" channel="sfx" />
    <qg:sound id="block_sfx" src="assets/kenney/audio/block.ogg" channel="sfx" />

    <!-- === HUD === -->
    <qg:hud position="top-left">
      <text style="font-size:14px; color:#fff; font-family:monospace; text-shadow:1px 1px #000; padding:8px;">
        LIVES: {{lives}}
      </text>
    </qg:hud>
    <qg:hud position="top-center">
      <text style="font-size:14px; color:#ffd700; font-family:monospace; text-shadow:1px 1px #000;">
        SCORE: {{score}}
      </text>
    </qg:hud>
    <qg:hud position="top-right">
      <text style="font-size:14px; color:#fff; font-family:monospace; text-shadow:1px 1px #000; padding:8px;">
        COINS: {{coins}}
      </text>
    </qg:hud>
    <qg:hud position="center">
      <text style="font-size:36px; color:#fff; font-family:monospace; text-shadow:3px 3px #000;">
        {{gameOver ? 'GAME OVER' : (won ? 'LEVEL COMPLETE!' : '')}}
      </text>
    </qg:hud>

    <!-- === RESTART === -->
    <q:function name="restart">
      game.respawn("player", 36, 348);
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

    return xml


def main():
    xml = generate_xml()

    # Verify CSV dimensions
    import re
    layers = re.findall(r'<qg:layer[^>]*>(.*?)</qg:layer>', xml, re.DOTALL)
    for i, layer_content in enumerate(layers):
        lines = [l.strip() for l in layer_content.strip().split('\n') if l.strip()]
        print(f"Layer {i+1}: {len(lines)} rows")
        for j, line in enumerate(lines):
            vals = line.split(',')
            if len(vals) != COLS:
                print(f"  ERROR: Row {j} has {len(vals)} values (expected {COLS})")
                return False
        print(f"  All rows have {COLS} values. OK.")

    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "examples", "kenney_platformer.q")
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(xml)

    print(f"\nGenerated: {out_path}")
    print(f"File size: {len(xml)} bytes")
    return True


if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)
