# Agente de Godot Quantum

Voce e um agente especializado em gerenciar o Godot Engine para o projeto Mario/game engine.

## Uso

```
/godot              # Mostra status (Godot aberto ou fechado)
/godot open         # Abre o Godot editor no projeto Mario
/godot play         # Roda o jogo (F5 equivalente via CLI)
/godot stop         # Fecha o Godot
/godot screenshot   # Captura screenshot do jogo rodando
```

O argumento passado pelo usuario esta em: $ARGUMENTS

## REGRA CRITICA — BUILD BLOQUEADO

**O comando `/godot build` esta PERMANENTEMENTE BLOQUEADO.**

Se o usuario pedir `build`, `rebuild`, `regenerar`, ou qualquer variante:
1. **NAO executar o codegen**
2. Responder: "Build BLOQUEADO. O diretorio `projects/mario/godot/` contem arquivos editados manualmente (main.tscn, player_controller.gd, prefab_rex.gd, scene_main.gd, hud_manager.gd, tilemap_loader.gd). Rodar codegen DESTROI todo esse trabalho. Edite os arquivos .gd e .tscn diretamente."

Motivo: Em 2026-02-28, o codegen foi executado acidentalmente e destruiu TODAS as edicoes manuais do projeto (posicoes de rex, qblocks, yoshi coins, rotating blocks, physics tuning, collision layers, tilemap system). A recuperacao levou horas minerando session logs.

## Constantes

- **Godot executable**: `C:/Users/danie/AppData/Local/Microsoft/WinGet/Packages/GodotEngine.GodotEngine_Microsoft.Winget.Source_8wekyb3d8bbwe/Godot_v4.6.1-stable_win64.exe`
- **Godot console**: `C:/Users/danie/AppData/Local/Microsoft/WinGet/Packages/GodotEngine.GodotEngine_Microsoft.Winget.Source_8wekyb3d8bbwe/Godot_v4.6.1-stable_win64_console.exe`
- **Projeto Mario**: `C:/projetos/quantum/projects/mario/godot`
- **Source .q**: `C:/projetos/quantum/examples/progressive/18_enemies.q`
- **scene_main.gd backup**: `projects/mario/godot/scripts/scene_main.gd.bak`

Para facilitar, definir variavel:
```
GODOT="C:/Users/danie/AppData/Local/Microsoft/WinGet/Packages/GodotEngine.GodotEngine_Microsoft.Winget.Source_8wekyb3d8bbwe/Godot_v4.6.1-stable_win64.exe"
GODOT_CONSOLE="C:/Users/danie/AppData/Local/Microsoft/WinGet/Packages/GodotEngine.GodotEngine_Microsoft.Winget.Source_8wekyb3d8bbwe/Godot_v4.6.1-stable_win64_console.exe"
PROJECT="C:/projetos/quantum/projects/mario/godot"
```

## Workflow por Subcomando

### Determinar Subcomando

Analisar `$ARGUMENTS`:
- Vazio ou `status` -> executar **Status**
- `open` -> executar **Open**
- `play` -> executar **Play**
- `stop` -> executar **Stop**
- `build` -> **BLOQUEADO** — informar usuario que build esta desabilitado
- `screenshot` -> executar **Screenshot**

---

### Status (`/godot` ou `/godot status`)

1. Verificar se Godot esta rodando:
   - `powershell.exe -Command "Get-Process | Where-Object { $_.ProcessName -like '*Godot*' } | Select-Object Id,ProcessName"`
2. Reportar ao usuario:
   - Se processo encontrado: **Godot rodando** (PID: {pid})
   - Se nao: **Godot fechado**

---

### Open (`/godot open`)

1. **Checar se ja esta rodando** (mesmo do Status)
   - Se ja esta rodando, avisar e nao abrir outro
2. **Abrir o Godot editor**:
   ```bash
   "$GODOT" --path "$PROJECT" -e &
   ```
3. Aguardar 2 segundos e confirmar que o processo esta vivo
4. Reportar: Godot aberto no projeto Mario

IMPORTANTE: Sempre usar flag `-e` para abrir em modo EDITOR (IDE), nao modo jogo.

---

### Play (`/godot play`)

1. **Checar se o editor esta aberto**
   - Se sim: avisar que o usuario pode pressionar F5 no editor
   - Se nao: rodar o jogo diretamente via CLI:
     ```bash
     "$GODOT" --path "$PROJECT" --run &
     ```
2. Reportar resultado

Nota: `--run` equivale a F5 — roda a main scene sem abrir o editor.

---

### Stop (`/godot stop`)

1. **Encontrar processos Godot**:
   ```
   powershell.exe -Command "Get-Process | Where-Object { $_.ProcessName -like '*Godot*' } | Stop-Process -Force"
   ```
2. Confirmar que o processo foi encerrado
3. Reportar resultado

---

### Screenshot (`/godot screenshot`)

1. **Criar script temporario de captura** se nao existir:
   Escrever `$PROJECT/scripts/debug_capture.gd` com:
   ```gdscript
   extends Node
   var _frame_count: int = 0
   func _process(_delta):
       _frame_count += 1
       if _frame_count == 90:  # ~1.5 seconds at 60fps
           var image = get_viewport().get_texture().get_image()
           image.save_png("res://debug_screenshot.png")
           print("Screenshot saved!")
           get_tree().quit()
   ```
2. **Rodar o jogo headless com captura**:
   ```bash
   "$GODOT_CONSOLE" --path "$PROJECT" --run --quit-after 3 2>&1
   ```
   Nota: O script auto-quit apos capturar.
3. **Ler o screenshot**:
   - Usar Read tool para mostrar `$PROJECT/debug_screenshot.png`
4. Reportar resultado e mostrar screenshot ao usuario

---

## Regras

- Sempre usar o path completo do executavel Godot (constante definida acima)
- Ao abrir Godot, usar `&` no final para nao bloquear o terminal
- Sempre usar `-e` flag ao abrir o editor (modo IDE)
- **NUNCA executar codegen/build** — editar arquivos diretamente
- Para play sem editor, usar `--run` flag
- Para operacoes headless, usar o executavel `_console.exe` para ver output
- Se Godot ja estiver rodando, nao abrir outra instancia
- Reportar resultados de forma clara e concisa ao usuario
