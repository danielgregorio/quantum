"""
Compile a Mario phase .q file to HTML with a phase info panel.
Usage: python examples/mario/compile_phase.py 1
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from core.parser import QuantumParser
from runtime.game_code_generator import GameCodeGenerator

PHASES = {
    1: {
        "file": "01_scene.q",
        "title": "Phase 1: PIXI Pipeline",
        "validates": [
            "<b>PIXI.js inicializa</b> — Canvas criado, texturas carregam via Assets.load, sprites renderizam na tela",
        ],
        "expected": "Imagem do level ao fundo. Mario parado no canto inferior esquerdo. Nada se mexe — apenas renderização estática.",
    },
    2: {
        "file": "02_physics.q",
        "title": "Phase 2: Physics + Movement + Camera",
        "validates": [
            "<b>Fisica + Controles + Camera</b> — Mario anda (←→), pula (↑), camera segue suavemente pelo level inteiro",
        ],
        "expected": "Mario anda e pula pelo level completo. Camera acompanha. Sem inimigos, sem coins — apenas exploração livre.",
    },
    3: {
        "file": "03_movement.q",
        "title": "Phase 3: Collision Map",
        "validates": [
            "<b>Collision sprites</b> — ~45 sprites invisíveis (body='static' visible='false') formando hills, plataformas e pipes do level",
        ],
        "expected": "Mario sobe nas colinas, para nos pipes, pisa nas plataformas. Terreno segue a imagem de fundo. ←→ andar, ↑ pular.",
    },
    4: {
        "file": "04_camera.q",
        "title": "Phase 4: Camera + Collision Map",
        "validates": [
            "<b>qg:camera follow</b> — Câmera segue Mario com lerp suave (0.08)",
            "<b>bounds='scene'</b> — Câmera não ultrapassa os limites do mundo",
            "<b>offset-y</b> — Câmera deslocada verticalmente para melhor enquadramento",
            "<b>Collision sprites</b> — ~45 sprites invisíveis formando plataformas e obstáculos",
            "<b>Terrain tag</b> — Todos os blocos de colisão compartilham tag 'terrain'",
        ],
        "expected": "Câmera scroll suave ao andar. Mario sobe em plataformas/hills. Mundo explorável do início ao fim.",
    },
    5: {
        "file": "05_coins.q",
        "title": "Phase 5: Coins + Events + State",
        "validates": [
            "<b>qg:prefab + qg:instance</b> — Template de coin reutilizado 14 vezes",
            "<b>sensor='true'</b> — Coins detectam colisão mas não bloqueiam movimento",
            "<b>qg:on-collision emit:</b> — Colisão dispara evento 'coin-collected'",
            "<b>qg:on-collision destroy-other</b> — Coin destruído ao ser coletado",
            "<b>q:set + qg:event + q:function</b> — Estado (coins/score) + handler JS",
        ],
        "expected": "Coins animados espalhados pelo level. Ao tocar, coin desaparece, contador sobe. Score atualiza.",
    },
    6: {
        "file": "06_blocks.q",
        "title": "Phase 6: Question Blocks",
        "validates": [
            "<b>game.hitBlock()</b> — API do engine para animar e trocar textura do bloco",
            "<b>Texture swap</b> — Bloco ? vira bloco usado após hit",
            "<b>_blockUsed flag</b> — Previne hit duplo no mesmo bloco",
            "<b>Prefab qblock</b> — 7 instâncias com animação 'shine'",
            "<b>Preload texture</b> — Textura do bloco usado pré-carregada via sprite oculto",
        ],
        "expected": "Blocos ? animados no level. Pular embaixo de um bloco troca a textura e dá coins/score. Hit duplo ignorado.",
    },
    7: {
        "file": "07_enemies.q",
        "title": "Phase 7: Rex Enemies + Stomp",
        "validates": [
            "<b>game.setRexAI()</b> — IA de patrulha com inversão de direção em paredes",
            "<b>Stomp detection</b> — Mario acima do Rex + caindo = stomp",
            "<b>2-hit kill</b> — Primeiro stomp achata, segundo destrói",
            "<b>Bounce on stomp</b> — Mario recebe impulso vertical ao stompar",
            "<b>Lateral collision</b> — Se Rex toca Mario de lado = dano",
        ],
        "expected": "12 Rex patrulhando. Pular em cima achata (1° hit) e destrói (2° hit). Tocar de lado = morte do Mario.",
    },
    8: {
        "file": "08_hud.q",
        "title": "Phase 8: HUD Overlay",
        "validates": [
            "<b>qg:hud position</b> — Overlay HTML fixo na tela (top-left, center)",
            "<b>DOM binding</b> — Elementos HTML atualizados via getElementById",
            "<b>q:set lives</b> — Variável de estado 'lives' inicializada em 3",
            "<b>Score/coins display</b> — Contadores visuais sincronizados com estado",
            "<b>Game Over modal</b> — Tela de game over quando lives = 0",
        ],
        "expected": "HUD no topo: 'MARIO x 3 | COINS: 0 | SCORE: 0'. Valores atualizam ao coletar coins, stompar enemies, perder vida.",
    },
    9: {
        "file": "09_death.q",
        "title": "Phase 9: Death + Respawn + Game Over",
        "validates": [
            "<b>game.killPlayer()</b> — Pausa jogo, troca sprite, animação de morte",
            "<b>game.irisIn/Out()</b> — Transições circulares de tela (level start/death)",
            "<b>Death zone sensor</b> — Sprite invisível no fundo do level detecta queda",
            "<b>sessionStorage</b> — Lives e score persistem entre respawns (reload)",
            "<b>Game Over screen</b> — Modal com score final e botão 'Try Again'",
        ],
        "expected": "Cair em buraco ou tocar Rex de lado = morte com animação. Iris out → respawn (se lives > 0) ou Game Over.",
    },
    10: {
        "file": "10_complete.q",
        "title": "Phase 10: Sound + Goal + Polish",
        "validates": [
            "<b>qg:sound trigger</b> — 6 SFX disparados por eventos (jump, coin, stomp, death, clear, block)",
            "<b>qg:sound loop + channel</b> — BGM em loop no canal 'music'",
            "<b>Autoplay workaround</b> — Música inicia no primeiro click/keydown",
            "<b>Goal sensor</b> — Sprite no final do level dispara 'level-complete'",
            "<b>game.pause() + Course Clear</b> — Jogo pausa, iris out, tela de vitória",
        ],
        "expected": "Jogo completo com sons, música, e objetivo. Chegar no goal verde no final = COURSE CLEAR!",
    },
}


def compile_phase(phase_num):
    phase = PHASES[phase_num]
    filepath = os.path.join(os.path.dirname(__file__), phase["file"])

    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()

    parser = QuantumParser()
    ast = parser.parse(source)
    gen = GameCodeGenerator()

    html = gen.generate(
        scene=ast.scenes[0],
        behaviors=getattr(ast, 'behaviors', []),
        prefabs=getattr(ast, 'prefabs', []),
        title=phase["title"],
        source_code=source,
    )

    # Build the info panel HTML
    validates_html = "".join(f"<li>{v}</li>" for v in phase["validates"])

    panel = f'''<div id="phase-info" style="
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        color: #e0e0e0;
        font-family: 'Segoe UI', system-ui, sans-serif;
        padding: 16px 20px;
        margin: 0;
        border-bottom: 3px solid #e94560;
        font-size: 13px;
        line-height: 1.5;
    ">
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 12px;">
            <span style="
                background: #e94560;
                color: #fff;
                padding: 3px 10px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
                white-space: nowrap;
            ">{phase_num}/10</span>
            <span style="font-size: 16px; font-weight: bold; color: #fff;">{phase["title"]}</span>
        </div>
        <div style="color: #e94560; font-weight: bold; margin-bottom: 6px; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">O que esta fase valida</div>
        <ul style="margin: 0 0 12px 0; padding-left: 18px; list-style: '▸ ';">
            {validates_html}
        </ul>
        <div style="color: #4ecca3; font-weight: bold; margin-bottom: 6px; font-size: 11px; text-transform: uppercase; letter-spacing: 1px;">Resultado esperado</div>
        <div style="background: rgba(78, 204, 163, 0.1); border-left: 3px solid #4ecca3; padding: 8px 12px; border-radius: 0 4px 4px 0;">
            {phase["expected"]}
        </div>
    </div>'''

    # Override body layout: stack vertically instead of flex center
    html = html.replace(
        'body { overflow: hidden; background: #111; display: flex; justify-content: center; align-items: center; width: 100vw; height: 100vh; }',
        'body { overflow: auto; background: #111; display: flex; flex-direction: column; align-items: center; width: 100vw; min-height: 100vh; }'
    )
    html = html.replace(
        "canvas { display: block; image-rendering: pixelated; image-rendering: crisp-edges; transform: scale(3); transform-origin: center center; }",
        "canvas { display: block; image-rendering: pixelated; image-rendering: crisp-edges; transform: scale(3); transform-origin: top center; margin-top: 8px; margin-bottom: 450px; }"
    )
    # Make phase-info full width
    html = html.replace('<body>', f'<body>\n{panel}', 1)

    outpath = os.path.join(os.path.dirname(__file__), '..', '..', 'projects', 'mario', 'static', 'game.html')
    with open(outpath, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Phase {phase_num} compiled: {phase['title']}")
    print(f"Output: {os.path.abspath(outpath)}")
    return html


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python compile_phase.py <phase_number>")
        print("  phase_number: 1-10")
        sys.exit(1)

    n = int(sys.argv[1])
    if n not in PHASES:
        print(f"Phase {n} not found. Available: {list(PHASES.keys())}")
        sys.exit(1)

    compile_phase(n)
