<?xml version="1.0" encoding="UTF-8"?>
<!--
  Phase 20: Collision Editor

  Interactive tool to define collision tiles:
  - Click tile to cycle: passable -> block -> platform -> passable
  - Visual feedback with colors
  - Export collision data when done
-->
<q:application id="collision-editor" type="game" engine="2d">
  <qg:scene name="main" width="5120" height="432" viewport-width="512" viewport-height="300" background="#5C94FC">

    <!-- Full level background image -->
    <qg:sprite id="level-bg" src="assets/smw/sprites/yoshi-island-1.png"
               x="2560" y="216" width="5120" height="432" />

    <!-- Events -->
    <qg:event name="game-init" handler="onGameInit" />

    <q:function name="onGameInit">
      const TILE_W = 16
      const TILE_H = 16
      const LEVEL_W = 5120
      const LEVEL_H = 432
      const VIEWPORT_W = 512
      const COLS = Math.ceil(LEVEL_W / TILE_W)  // 320 tiles
      const ROWS = Math.ceil(LEVEL_H / TILE_H)  // 27 tiles

      // Collision states: 0=passable, 1=block, 2=platform (one-way)
      const collisionData = []
      for (let r = 0; r &lt; ROWS; r++) {
        collisionData.push(new Array(COLS).fill(0))
      }

      // Colors for each state
      const COLORS = {
        0: null,           // passable - no overlay
        1: 0xFF0000,       // block - red
        2: 0x00FF00        // platform - green
      }
      const ALPHA = 0.4

      // Use existing camera container for scrolling
      _cameraContainer.sortableChildren = true

      // Create tile overlay container
      const tileContainer = new PIXI.Container()
      tileContainer.zIndex = 100
      _cameraContainer.addChild(tileContainer)

      // Create clickable tiles
      const tileSprites = []
      for (let row = 0; row &lt; ROWS; row++) {
        tileSprites[row] = []
        for (let col = 0; col &lt; COLS; col++) {
          const tile = new PIXI.Graphics()
          tile.rect(0, 0, TILE_W, TILE_H)
          tile.stroke({ color: 0xFFFFFF, width: 1, alpha: 0.1 })
          tile.x = col * TILE_W
          tile.y = row * TILE_H
          tile.eventMode = 'static'
          tile.cursor = 'pointer'

          // Store tile position
          tile._col = col
          tile._row = row

          // Click handler
          tile.on('pointerdown', (e) => {
            const r = tile._row
            const c = tile._col
            // Cycle state: 0 -> 1 -> 2 -> 0
            collisionData[r][c] = (collisionData[r][c] + 1) % 3

            // Update visual
            updateTileVisual(tile, collisionData[r][c])

            // Log for debugging
            console.log(`Tile [${r},${c}] = ${collisionData[r][c]} (${['passable','block','platform'][collisionData[r][c]]})`)
          })

          tileSprites[row][col] = tile
          tileContainer.addChild(tile)
        }
      }

      function updateTileVisual(tile, state) {
        tile.clear()
        if (state === 0) {
          // Passable - just outline
          tile.rect(0, 0, TILE_W, TILE_H)
          tile.stroke({ color: 0xFFFFFF, width: 1, alpha: 0.1 })
        } else if (state === 1) {
          // Block - red fill
          tile.rect(0, 0, TILE_W, TILE_H)
          tile.fill({ color: 0xFF0000, alpha: ALPHA })
          tile.stroke({ color: 0xFF0000, width: 1, alpha: 0.8 })
        } else if (state === 2) {
          // Platform - green fill
          tile.rect(0, 0, TILE_W, TILE_H)
          tile.fill({ color: 0x00FF00, alpha: ALPHA })
          tile.stroke({ color: 0x00FF00, width: 1, alpha: 0.8 })
        }
      }

      // Camera controls - arrow keys to scroll
      let camX = 0
      let camY = 0
      const CAM_SPEED = 64  // Faster scroll (4 tiles at a time)
      const CAM_SPEED_FAST = 256  // Even faster with Shift
      const VIEWPORT_H = 300  // Visible area height (smaller to allow vertical scroll)

      document.addEventListener('keydown', (e) => {
        const speed = e.shiftKey ? CAM_SPEED_FAST : CAM_SPEED

        if (e.key === 'ArrowRight') {
          camX = Math.min(camX + speed, LEVEL_W - VIEWPORT_W)
          _cameraContainer.x = -camX
          e.preventDefault()
        } else if (e.key === 'ArrowLeft') {
          camX = Math.max(camX - speed, 0)
          _cameraContainer.x = -camX
          e.preventDefault()
        } else if (e.key === 'ArrowDown') {
          camY = Math.min(camY + speed, LEVEL_H - VIEWPORT_H)
          _cameraContainer.y = -camY
          e.preventDefault()
        } else if (e.key === 'ArrowUp') {
          camY = Math.max(camY - speed, 0)
          _cameraContainer.y = -camY
          e.preventDefault()
        } else if (e.key === 'Home') {
          camX = 0
          camY = 0
          _cameraContainer.x = 0
          _cameraContainer.y = 0
          e.preventDefault()
        } else if (e.key === 'End') {
          camX = LEVEL_W - VIEWPORT_W
          _cameraContainer.x = -camX
          e.preventDefault()
        } else if (e.key === 'e' || e.key === 'E') {
          exportCollisionData()
        }
      })

      // Mouse wheel to scroll horizontally
      document.addEventListener('wheel', (e) => {
        camX = Math.max(0, Math.min(camX + e.deltaY, LEVEL_W - VIEWPORT_W))
        _cameraContainer.x = -camX
        e.preventDefault()
      }, { passive: false })

      // Export function
      function exportCollisionData() {
        // Find all non-zero tiles
        const blocks = []
        const platforms = []
        for (let r = 0; r &lt; ROWS; r++) {
          for (let c = 0; c &lt; COLS; c++) {
            if (collisionData[r][c] === 1) {
              blocks.push({x: c * TILE_W, y: r * TILE_H})
            } else if (collisionData[r][c] === 2) {
              platforms.push({x: c * TILE_W, y: r * TILE_H})
            }
          }
        }

        // Merge adjacent horizontal blocks
        const mergedBlocks = mergeHorizontal(blocks)
        const mergedPlatforms = mergeHorizontal(platforms)

        console.log('=== COLLISION DATA ===')
        console.log('Blocks:', JSON.stringify(mergedBlocks))
        console.log('Platforms:', JSON.stringify(mergedPlatforms))

        // Also create XML-friendly output
        let xml = '&lt;!-- Collision sprites --&gt;\\n'
        mergedBlocks.forEach((b, i) => {
          xml += `&lt;qg:sprite id="block${i}" width="${b.w}" height="${b.h}" x="${b.x + b.w/2}" y="${b.y + b.h/2}" tag="terrain" body="static" visible="false" /&gt;\\n`
        })
        console.log('\\n=== XML OUTPUT ===')
        console.log(xml)

        alert('Collision data exported to console! Press F12 to view.')
      }

      function mergeHorizontal(tiles) {
        if (tiles.length === 0) return []

        // Sort by y, then x
        tiles.sort((a, b) => a.y === b.y ? a.x - b.x : a.y - b.y)

        const merged = []
        let current = { x: tiles[0].x, y: tiles[0].y, w: TILE_W, h: TILE_H }

        for (let i = 1; i &lt; tiles.length; i++) {
          const t = tiles[i]
          // Same row and adjacent?
          if (t.y === current.y &amp;&amp; t.x === current.x + current.w) {
            current.w += TILE_W
          } else {
            merged.push(current)
            current = { x: t.x, y: t.y, w: TILE_W, h: TILE_H }
          }
        }
        merged.push(current)
        return merged
      }

      // Instructions
      console.log('=== COLLISION EDITOR ===')
      console.log('Click tiles to cycle: passable -> block (red) -> platform (green)')
      console.log('Arrow keys: scroll level in all 4 directions')
      console.log('Shift + Arrow keys: fast scroll')
      console.log('Home: reset to start position')
      console.log('E key: export collision data')
    </q:function>

    <!-- HUD with instructions -->
    <qg:hud position="top-left">
      <div style="color: #FFF; font-family: monospace; font-size: 12px; background: rgba(0,0,0,0.7); padding: 8px;">
        COLLISION EDITOR<br/>
        Click: cycle tile<br/>
        Arrows: scroll (all 4 directions)<br/>
        Shift+Arrows: fast scroll<br/>
        Home: reset position<br/>
        E: export data
      </div>
    </qg:hud>

  </qg:scene>
</q:application>
