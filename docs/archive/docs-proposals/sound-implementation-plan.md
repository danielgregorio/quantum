# Plano de Implementacao de Sons - SMW Yoshi's Island 1

## Inventario de Sons Disponiveis

### Efeitos Sonoros (assets/smw/sounds/)
| Arquivo | Uso | Trigger/Evento |
|---------|-----|----------------|
| `smw_jump.wav` | Mario pula | `player.jump` |
| `smw_stomp.wav` | Mario pisa em inimigo | `enemy-stomped` |
| `smw_coin.wav` | Coleta moeda | `coin-collected` |
| `smw_1-up.wav` | Ganha vida extra | `1up-collected` |
| `smw_course_clear.wav` | Completa fase | `level-complete` |
| `smw_lost_a_life.wav` | Mario morre | `mario-died` |
| `smw_power-up.wav` | Coleta power-up | `powerup-collected` |
| `smw_kick.wav` | Chuta casco | `shell-kick` |
| `smw_spin_jump.wav` | Spin jump | `player.spin-jump` |
| `smw_message_block.wav` | Bloco de mensagem | `message-block-hit` |
| `smw_goal_iris-out.wav` | Iris out no goal | `goal-iris-out` |

### Musicas (assets/smw/sounds/music/)
| Arquivo | Uso | Trigger |
|---------|-----|---------|
| `music-map1.wav` | Musica do nivel (normal) | `scene.start` |
| `music-map1-turbo.wav` | Musica (tempo acabando) | `time-warning` |
| `beggining.wav` | Jingle inicial | `game-start` |

---

## Implementacao

### Fase 1: Adicionar game.playSound()

Adicionar funcao helper em `game_templates.py`:

```javascript
game.playSound = function(soundId, opts) {
  _playSound(soundId, opts || {});
};

game.stopSound = function(soundId) {
  // Para sons em loop (musica)
  if (_activeSources[soundId]) {
    _activeSources[soundId].stop();
    delete _activeSources[soundId];
  }
};
```

### Fase 2: Definir Sons na Cena (18_enemies.q)

```xml
<!-- Efeitos Sonoros -->
<qg:sound id="sfx-jump" src="assets/smw/sounds/smw_jump.wav" trigger="player.jump" />
<qg:sound id="sfx-coin" src="assets/smw/sounds/smw_coin.wav" trigger="coin-collected" />
<qg:sound id="sfx-stomp" src="assets/smw/sounds/smw_stomp.wav" trigger="enemy-stomped" />
<qg:sound id="sfx-death" src="assets/smw/sounds/smw_lost_a_life.wav" trigger="mario-died" />
<qg:sound id="sfx-powerup" src="assets/smw/sounds/smw_power-up.wav" trigger="powerup-collected" />
<qg:sound id="sfx-1up" src="assets/smw/sounds/smw_1-up.wav" trigger="1up-collected" />
<qg:sound id="sfx-clear" src="assets/smw/sounds/smw_course_clear.wav" trigger="level-complete" />
<qg:sound id="sfx-block" src="assets/smw/sounds/smw_message_block.wav" trigger="block-hit" />

<!-- Musica de Fundo -->
<qg:sound id="bgm-level" src="assets/smw/sounds/music/music-map1.wav"
          trigger="scene.start" loop="true" volume="0.6" channel="music" />
```

### Fase 3: Emitir Eventos nos Momentos Certos

#### Eventos ja existentes que precisam emitir som:
- `coin-collected` - ja existe
- `block-hit` - ja existe
- `level-complete` - ja existe
- `enemy-collision` (quando stomp) - precisa emitir `enemy-stomped`
- `mario-died` - precisa criar e emitir

#### Eventos novos necessarios:
1. `enemy-stomped` - quando pisa em inimigo
2. `mario-died` - quando morre (separado de death-animation-complete)

### Fase 4: Modificar Handlers de Eventos

```javascript
// Em onEnemyCollision, quando stomp:
if (isStomping) {
  _gameEvents.emit('enemy-stomped', { enemy: enemy.id });
  // ... resto do codigo
}

// Antes de chamar game.killPlayer:
_gameEvents.emit('mario-died', {});
game.killPlayer('mario');
```

### Fase 5: Pausar Musica na Morte

Modificar `game.killPlayer()`:
```javascript
game.killPlayer = function(playerId) {
  // Parar musica de fundo
  game.stopSound('bgm-level');
  // ... resto do codigo
}
```

### Fase 6: Resumir Musica no Respawn

```javascript
function onDeathAnimationComplete() {
  if (lives > 0) {
    // Respawn
    game.playSound('bgm-level', { loop: true, volume: 0.6 });
    // ...
  }
}
```

---

## Codigo Final para 18_enemies.q

```xml
<!-- Sons -->
<qg:sound id="sfx-jump" src="assets/smw/sounds/smw_jump.wav" trigger="player.jump" />
<qg:sound id="sfx-coin" src="assets/smw/sounds/smw_coin.wav" trigger="coin-collected" />
<qg:sound id="sfx-stomp" src="assets/smw/sounds/smw_stomp.wav" trigger="enemy-stomped" />
<qg:sound id="sfx-death" src="assets/smw/sounds/smw_lost_a_life.wav" trigger="mario-died" />
<qg:sound id="sfx-clear" src="assets/smw/sounds/smw_course_clear.wav" trigger="level-complete" />
<qg:sound id="sfx-block" src="assets/smw/sounds/smw_message_block.wav" trigger="block-hit" />
<qg:sound id="bgm-level" src="assets/smw/sounds/music/music-map1.wav"
          trigger="scene.start" loop="true" volume="0.5" channel="music" />
```

---

## Verificacao

- [ ] Som de pulo funciona ao pressionar espaco/seta cima
- [ ] Som de moeda ao coletar
- [ ] Som de stomp ao pisar em Rex
- [ ] Som de morte ao morrer
- [ ] Som de course clear ao terminar
- [ ] Musica toca no inicio e para na morte
- [ ] Musica retoma no respawn

---

## Ordem de Implementacao

1. Adicionar `game.playSound()` e `game.stopSound()` em game_templates.py
2. Adicionar `<qg:sound>` tags em 18_enemies.q
3. Emitir eventos `enemy-stomped` e `mario-died` nos handlers
4. Parar musica na morte, retomar no respawn
5. Testar todos os sons
