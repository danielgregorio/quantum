---
layout: doc
title: Game Examples
---

<script setup>
import { ref, onMounted } from 'vue'

const examples = ref([])

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/games.json')
    examples.value = data.examples || []
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# Game Examples

Game development with `qg:scene`, sprites, and physics.

<div class="related-links">
  <a href="/features/game-engine" class="related-link">Game Engine Docs</a>
</div>

## All Examples

<ExampleGallery :examples="examples" />

## Game Engine Features

### Scene Setup

```xml
<q:application id="mygame" type="game" engine="2d">
  <qg:scene name="main" width="800" height="600" background="#1a1a2e">
    <!-- Game objects here -->
  </qg:scene>
</q:application>
```

### Sprites

```xml
<qg:sprite id="player"
           src="/assets/player.png"
           x="100" y="300"
           width="32" height="32" />

<qg:sprite id="enemy"
           src=""
           x="400" y="300"
           width="20" height="20"
           color="#ef4444" />
```

### Input Handling

```xml
<qg:input key="ArrowLeft" action="moveLeft" type="hold" />
<qg:input key="ArrowRight" action="moveRight" type="hold" />
<qg:input key="Space" action="jump" type="press" />

<q:function name="moveLeft">
  _sprites["player"].sprite.x -= 5;
</q:function>

<q:function name="moveRight">
  _sprites["player"].sprite.x += 5;
</q:function>
```

### Game Loop Timer

```xml
<qg:timer id="gameLoop" interval="0.016" action="update" auto-start="true" />

<q:function name="update">
  // Update game state at 60fps
  updatePhysics();
  checkCollisions();
  renderFrame();
</q:function>
```

### HUD (Heads-Up Display)

```xml
<qg:hud position="top-left">
  <text style="font-size:24px; color:#fff;">
    Score: {score}
  </text>
</qg:hud>

<qg:hud position="top-right">
  <text style="font-size:18px; color:#f87171;">
    Lives: {lives}
  </text>
</qg:hud>
```

### Collision Detection

```xml
<q:function name="checkCollision">
  var player = _sprites["player"].sprite;
  var coin = _sprites["coin"].sprite;

  if (Math.abs(player.x - coin.x) < 20 &&
      Math.abs(player.y - coin.y) < 20) {
    score += 10;
    respawnCoin();
  }
</q:function>
```

### Prefabs and Spawning

```xml
<qg:prefab name="Bullet">
  <qg:sprite src="" width="4" height="10" color="#ffff00" />
</qg:prefab>

<qg:spawn id="bulletSpawner" prefab="Bullet" pool-size="50" />

<q:function name="fire">
  var bullet = _spawn("bulletSpawner");
  bullet.x = player.x;
  bullet.y = player.y;
</q:function>
```

## Featured Games

| Game | Description |
|------|-------------|
| [snake.q](https://github.com/danielgregorio/quantum/blob/main/examples/snake.q) | Classic Snake game with growing tail |
| [platformer.q](https://github.com/danielgregorio/quantum/blob/main/examples/platformer.q) | Side-scrolling platformer |
| [tictactoe.q](https://github.com/danielgregorio/quantum/blob/main/examples/tictactoe.q) | Two-player Tic-Tac-Toe |
| [tower_defense.q](https://github.com/danielgregorio/quantum/blob/main/examples/tower_defense.q) | Tower defense strategy game |

## Related Categories

- [State Management](/examples/state-management) - Game state
- [Loops](/examples/loops) - Game object iteration
- [Functions](/examples/functions) - Game logic
