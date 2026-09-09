#!/bin/bash
# PreToolUse hook: Blocks Write tool on critical Godot files
# These files are manually tuned and must NEVER be overwritten by codegen.
#
# Exit codes:
#   0 = allow
#   2 = block (shows stderr message to user)

# Read JSON from stdin
INPUT=$(cat)

# Extract tool name
TOOL_NAME=$(echo "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null)

# Only check Write tool (Edit is fine - small targeted changes)
if [ "$TOOL_NAME" != "Write" ]; then
    exit 0
fi

# Extract file path
FILE_PATH=$(echo "$INPUT" | python -c "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" 2>/dev/null)

# Normalize path separators
FILE_PATH=$(echo "$FILE_PATH" | sed 's|\\|/|g')

# Check if it's a protected Godot file
PROTECTED_FILES=(
    "projects/mario/godot/main.tscn"
    "projects/mario/godot/scripts/player_controller.gd"
    "projects/mario/godot/scripts/prefab_rex.gd"
    "projects/mario/godot/scripts/scene_main.gd"
    "projects/mario/godot/scripts/hud_manager.gd"
    "projects/mario/godot/scripts/tilemap_loader.gd"
    "projects/mario/godot/scripts/quantum_bridge.gd"
    "projects/mario/godot/scripts/quantum_event_bus.gd"
    "projects/mario/godot/scripts/camera_follow.gd"
    "projects/mario/godot/scripts/prefab_qblock.gd"
    "projects/mario/godot/scripts/prefab_coin.gd"
    "projects/mario/godot/scripts/prefab_checkpoint.gd"
    "projects/mario/godot/scripts/prefab_rotating_block.gd"
    "projects/mario/godot/scripts/prefab_yoshi_coin.gd"
)

for PROTECTED in "${PROTECTED_FILES[@]}"; do
    if echo "$FILE_PATH" | grep -q "$PROTECTED"; then
        echo "BLOQUEADO: Write em arquivo Godot protegido: $PROTECTED" >&2
        echo "Estes arquivos foram tunados manualmente. Use Edit (nao Write) para fazer alteracoes pontuais." >&2
        echo "Se realmente precisa reescrever o arquivo inteiro, peca autorizacao explicita ao usuario." >&2
        exit 2
    fi
done

exit 0
