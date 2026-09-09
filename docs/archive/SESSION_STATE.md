# Estado da Sessao - Mario Game (Phase 18)

## Data: 2026-02-24

---

## RESUMO DO QUE FOI FEITO

### 1. Collision Editor (Concluido)
- Arquivo: `examples/progressive/20_collision_editor.q`
- Ferramenta visual para definir tiles de colisao
- Scroll horizontal/vertical com setas
- Shift+setas para scroll rapido
- Tecla E para exportar dados de colisao

### 2. Fix Double Jump (CONCLUIDO AGORA)
- **Problema**: Mario podia pular infinitamente no ar
- **Causa**: Check `Math.abs(velocity.y) < 0.5` era true no pico do pulo e quando encostado em paredes
- **Solucao**: Sistema de cooldown
- **Arquivo modificado**: `src/runtime/game_code_generator.py` (linhas ~1831-1843)

```python
# Mudanca feita:
# Can jump if (grounded OR within coyote time) AND cooldown expired
js.const(f'_canJump_{sid_js}', f'({grounded_var} || {sprite_ref}._coyoteFrames > 0) && {sprite_ref}._jumpCooldown === 0')

# Quando pula, seta cooldown de 8 frames:
js.line(f"{sprite_ref}._jumpCooldown = 8;")
```

### 3. Rex Stomp Detection (Concluido)
- Deteccao mais generosa (8px threshold, qualquer velocidade descendente)
- Mario so morre se colidir lateralmente com Rex

### 4. Jump Height Adjustment (Concluido)
- `jump-force="5.3"` (75% do original 7)

### 5. Mushroom Power-up (Parcial)
- Tentativa de spawnar cogumelo no primeiro bloco de interrogacao
- `game.spawnPrefab` nao existe
- Simplificado para dar power-up direto ao bater no bloco

### 6. Music on Death (Pendente - Nao Funcionou)
- Tentativas: `game.stopSound`, `game.stopAllSounds`, `_audioCtx.suspend()`
- Problema: BGM continua tocando junto com som de morte
- **PRECISA INVESTIGAR**: Sistema de audio em `game_templates.py`

### 7. Slope System (DESABILITADO)
- Sistema SNES-style implementado mas coordenadas estavam erradas
- Mario flutuava no ar em posicoes incorretas
- Codigo comentado ate obter coordenadas corretas do usuario

---

## ARQUIVOS PRINCIPAIS

| Arquivo | Descricao |
|---------|-----------|
| `examples/progressive/18_enemies.q` | Game principal (Mario Yoshi's Island 1) |
| `examples/progressive/20_collision_editor.q` | Editor de colisao |
| `src/runtime/game_code_generator.py` | Gerador de codigo JS (fisica, controles, pulo) |
| `src/runtime/game_templates.py` | Templates JS (audio, animacao, _registerAnimation) |
| `18_enemies.html` | Game compilado (pronto para testar) |

---

## CONFIGURACOES ATUAIS DO MARIO

```xml
<qg:sprite id="mario" src="assets/smw/sprites/mario_small.png"
           x="48" y="350" tag="player"
           frame-width="16" frame-height="24"
           body="dynamic" controls="arrows"
           speed="1.5"
           jump-force="5.3"
           friction="0.15">
```

---

## TAREFAS PENDENTES

### Alta Prioridade
1. **Testar fix do double jump** - Acabou de ser aplicado, precisa validar
2. **Fix musica na morte** - BGM precisa parar antes do som de morte tocar

### Media Prioridade
3. **Sistema de slopes** - Precisa das coordenadas X corretas do usuario para:
   - Cano diagonal (onde Mario deve poder subir andando)
   - Colina triangular

### Baixa Prioridade
4. **Cogumelo fisico** - Implementar `game.spawnPrefab` ou sistema alternativo

---

## COMANDOS UTEIS

```bash
# Compilar o jogo
python compile_game.py examples/progressive/18_enemies.q 18_enemies.html

# Rodar servidor local (para debug no DevTools)
python -m http.server 8000
# Abrir http://localhost:8000/18_enemies.html

# Compilar collision editor
python compile_game.py examples/progressive/20_collision_editor.q collision_editor.html
```

---

## CODIGO RELEVANTE - Double Jump Fix

### Localizacao: `src/runtime/game_code_generator.py` (~linha 1806-1843)

```python
# Initialize tracking variables if not present
js.if_block(f'{sprite_ref}._coyoteFrames === undefined')
js.line(f'{sprite_ref}._coyoteFrames = 0;')
js.line(f'{sprite_ref}._jumpHeld = false;')
js.line(f'{sprite_ref}._wasGrounded = false;')
js.line(f'{sprite_ref}._jumpCooldown = 0;')
js.block_close()

# Decrease jump cooldown
js.if_block(f'{sprite_ref}._jumpCooldown > 0')
js.line(f'{sprite_ref}._jumpCooldown--;')
js.block_close()

# Check if grounded (small vertical velocity)
js.const(f'_isGrounded_{sid_js}', f'{body_ref} && Math.abs({body_ref}.velocity.y) < 0.5')
grounded_var = f'_isGrounded_{sid_js}'

# Update coyote time
js.if_block(grounded_var)
js.line(f'{sprite_ref}._coyoteFrames = {coyote_frames};')
js.line(f'{sprite_ref}._wasGrounded = true;')
js.else_if_block(f'{sprite_ref}._coyoteFrames > 0')
js.line(f'{sprite_ref}._coyoteFrames--;')
js.block_close()

# Can jump if (grounded OR within coyote time) AND cooldown expired
js.const(f'_canJump_{sid_js}', f'({grounded_var} || {sprite_ref}._coyoteFrames > 0) && {sprite_ref}._jumpCooldown === 0')
can_jump_var = f'_canJump_{sid_js}'

# Initiate jump
js.if_block(f'{jump_just} && {body_ref} && {can_jump_var}')
js.line(f"Matter.Body.setVelocity({body_ref}, {{ x: {body_ref}.velocity.x, y: -{jf} }});")
js.line(f"{sprite_ref}._jumpHeld = true;")
js.line(f"{sprite_ref}._coyoteFrames = 0;")  # Consume coyote time
js.line(f"{sprite_ref}._jumpCooldown = 8;")  # Must wait 8 frames before next jump
js.line(f"_gameEvents.emit('player.jump', {sprite_ref});")
js.block_close()
```

---

## PROXIMOS PASSOS AO RETORNAR

1. Abrir `18_enemies.html` no navegador
2. Testar se Mario:
   - Pula normalmente quando no chao
   - NAO pula no ar (double jump corrigido)
   - Consegue pular apos encostar no cano e cair
3. Se funcionar, seguir para fix da musica na morte
4. Obter coordenadas X para slopes do usuario

---

## CONTEXTO TECNICO

- **Engine grafica**: PIXI.js v8
- **Engine fisica**: Matter.js
- **Audio**: Web Audio API (AudioContext, AudioBufferSourceNode)
- **Linguagem**: Quantum XML (.q) -> JavaScript compilado
