"""
Game Engine 2D - HTML/JS Templates and JS Builder

Provides:
  - JsBuilder: Structured JS code emitter with proper indentation and escaping
  - HTML shell template
  - Runtime JS subsystems (animation, particles, tweens, audio, etc.)
"""

import json
import re
from html import escape as html_escape


PIXI_CDN = "https://cdn.jsdelivr.net/npm/pixi.js@8/dist/pixi.min.js"
MATTER_CDN = "https://cdn.jsdelivr.net/npm/matter-js@0.20/build/matter.min.js"


# ==========================================================================
# JsBuilder - Structured JS code emitter
# ==========================================================================

class JsBuilder:
    """Builds syntactically valid JavaScript code with proper indentation.

    Every append method returns self for chaining.
    """

    def __init__(self, indent_size: int = 2):
        self._lines: list[str] = []
        self._indent: int = 0
        self._indent_size: int = indent_size

    # -- core --

    @property
    def _pad(self) -> str:
        return ' ' * (self._indent * self._indent_size)

    def line(self, code: str = '') -> 'JsBuilder':
        """Emit a single line at current indent."""
        self._lines.append(f"{self._pad}{code}" if code else '')
        return self

    def raw(self, code: str) -> 'JsBuilder':
        """Emit raw code without indentation changes (for pre-formatted blocks)."""
        for ln in code.split('\n'):
            self._lines.append(f"{self._pad}{ln}")
        return self

    def blank(self) -> 'JsBuilder':
        self._lines.append('')
        return self

    def comment(self, text: str) -> 'JsBuilder':
        return self.line(f"// {text}")

    def section(self, title: str) -> 'JsBuilder':
        return self.blank().line(f"// === {title} ===")

    def indent(self) -> 'JsBuilder':
        self._indent += 1
        return self

    def dedent(self) -> 'JsBuilder':
        self._indent = max(0, self._indent - 1)
        return self

    # -- variables --

    def const(self, name: str, value: str) -> 'JsBuilder':
        return self.line(f"const {name} = {value};")

    def let(self, name: str, value: str) -> 'JsBuilder':
        return self.line(f"let {name} = {value};")

    def assign(self, target: str, value: str) -> 'JsBuilder':
        return self.line(f"{target} = {value};")

    # -- blocks --

    def block_open(self, header: str) -> 'JsBuilder':
        """Open a block: `header {`"""
        self.line(f"{header} {{")
        self._indent += 1
        return self

    def block_close(self, suffix: str = '') -> 'JsBuilder':
        self._indent = max(0, self._indent - 1)
        self.line(f"}}{suffix}")
        return self

    def func(self, name: str, params: str = '') -> 'JsBuilder':
        return self.block_open(f"function {name}({params})")

    def method(self, name: str, params: str = '') -> 'JsBuilder':
        return self.block_open(f"{name}({params})")

    def if_block(self, condition: str) -> 'JsBuilder':
        return self.block_open(f"if ({condition})")

    def else_if_block(self, condition: str) -> 'JsBuilder':
        self._indent = max(0, self._indent - 1)
        self.line(f"}} else if ({condition}) {{")
        self._indent += 1
        return self

    def else_block(self) -> 'JsBuilder':
        self._indent = max(0, self._indent - 1)
        self.line("} else {")
        self._indent += 1
        return self

    def for_of(self, item: str, iterable: str) -> 'JsBuilder':
        return self.block_open(f"for (const {item} of {iterable})")

    def for_entries(self, key: str, val: str, obj: str) -> 'JsBuilder':
        return self.block_open(f"for (const [{key}, {val}] of Object.entries({obj}))")

    def for_range(self, var: str, start: str, end: str, step: str = '1') -> 'JsBuilder':
        return self.block_open(f"for (let {var} = {start}; {var} <= {end}; {var} += {step})")

    # -- classes --

    def class_open(self, name: str) -> 'JsBuilder':
        return self.block_open(f"class {name}")

    def class_close(self) -> 'JsBuilder':
        return self.block_close()

    # -- statements --

    def call(self, fn: str, *args: str) -> 'JsBuilder':
        return self.line(f"{fn}({', '.join(args)});")

    def ret(self, value: str = '') -> 'JsBuilder':
        return self.line(f"return {value};") if value else self.line("return;")

    # -- output --

    def build(self) -> str:
        return '\n'.join(self._lines)

    def __str__(self) -> str:
        return self.build()


# ==========================================================================
# Safe value helpers
# ==========================================================================

def js_string(val: str) -> str:
    """Safely encode a string as a JS string literal using JSON encoding."""
    return json.dumps(val)


def js_id(name: str) -> str:
    """Sanitize a string to be a valid JS identifier."""
    s = re.sub(r'[^a-zA-Z0-9_$]', '_', name)
    if s and s[0].isdigit():
        s = '_' + s
    return s or '_unnamed'


def js_number(val) -> str:
    """Safely format a number for JS."""
    if isinstance(val, bool):
        return 'true' if val else 'false'
    if isinstance(val, (int, float)):
        if isinstance(val, float) and val == int(val):
            return str(int(val))
        return str(val)
    try:
        f = float(val)
        if f == int(f):
            return str(int(f))
        return str(f)
    except (ValueError, TypeError):
        return '0'


def js_bool(val) -> str:
    if isinstance(val, bool):
        return 'true' if val else 'false'
    if isinstance(val, str):
        return 'true' if val.lower() in ('true', '1', 'yes') else 'false'
    return 'true' if val else 'false'


def is_number(val: str) -> bool:
    try:
        float(val)
        return True
    except (ValueError, TypeError):
        return False


def js_safe_value(val: str, val_type: str = 'string') -> str:
    """Convert a Quantum value to a safe JS literal based on declared type."""
    if val_type == 'integer':
        return val if val.lstrip('-').isdigit() else '0'
    elif val_type == 'boolean':
        return js_bool(val)
    elif val_type in ('float', 'number', 'decimal'):
        try:
            float(val)
            return val
        except ValueError:
            return '0'
    elif val_type == 'array':
        # Return array literals as-is (e.g., "[]", "[1,2,3]")
        if val.startswith('[') and val.endswith(']'):
            return val
        return '[]'
    elif val_type == 'object':
        # Return object literals as-is (e.g., "{}", "{a:1}")
        if val.startswith('{') and val.endswith('}'):
            return val
        return '{}'
    else:
        if val in ('true', 'false'):
            return val
        if is_number(val):
            return val
        return json.dumps(val)


def sanitize_hud_text(text: str) -> str:
    """Escape HTML in HUD text content, preserving {binding} expressions."""
    # Split on {bindings}, escape the non-binding parts
    parts = re.split(r'(\{[^}]+\})', text)
    result = []
    for part in parts:
        if part.startswith('{') and part.endswith('}'):
            result.append(part)  # keep binding as-is
        else:
            result.append(html_escape(part))
    return ''.join(result)


def compile_binding_to_js(text: str) -> str:
    """Convert HUD text with {bindings} to a safe JS template expression.

    Instead of innerHTML with template literals (XSS risk), generates a
    function that builds text content safely using only whitelisted variables.

    Input:  "Score: {score}"
    Output: "'Score: ' + String(score)"
    """
    parts = re.split(r'(\{[^}]+\})', text)
    js_parts = []
    for part in parts:
        if part.startswith('{') and part.endswith('}'):
            expr = part[1:-1].strip()
            # Whitelist: only allow identifiers, basic math, dots, arrays, ternary
            if re.match(r'^[a-zA-Z_$0-9][a-zA-Z0-9_$.\s+\-*/()%<>=!&|,\[\]?:\'"]*$', expr):
                js_parts.append(f"String({expr})")
            else:
                js_parts.append(json.dumps(part))  # escape the raw binding
        elif part:
            js_parts.append(json.dumps(part))
    return ' + '.join(js_parts) if js_parts else '""'


# ==========================================================================
# HTML Template
# ==========================================================================

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ overflow: hidden; background: #111; display: flex; justify-content: center; align-items: center; width: 100vw; height: 100vh; }}
    canvas {{ display: block; }}
    .qg-hud {{ position: absolute; pointer-events: none; padding: 8px; font-family: sans-serif; z-index: 10; }}
    .qg-hud-top-left {{ top: 0; left: 0; }}
    .qg-hud-top-right {{ top: 0; right: 0; }}
    .qg-hud-top-center {{ top: 0; left: 50%; transform: translateX(-50%); }}
    .qg-hud-bottom-left {{ bottom: 0; left: 0; }}
    .qg-hud-bottom-right {{ bottom: 0; right: 0; }}
    .qg-hud-bottom-center {{ bottom: 0; left: 50%; transform: translateX(-50%); }}
    .qg-hud-center {{ top: 50%; left: 50%; transform: translate(-50%, -50%); }}

    /* Source Code Viewer */
    #qg-source-btn {{
      position: fixed;
      bottom: 16px;
      right: 16px;
      z-index: 1000;
      background: rgba(255, 255, 255, 0.1);
      color: rgba(255, 255, 255, 0.5);
      border: 1px solid rgba(255, 255, 255, 0.15);
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      font-family: monospace;
      font-size: 12px;
      transition: all 0.2s;
    }}
    #qg-source-btn:hover {{
      background: rgba(255, 255, 255, 0.2);
      color: rgba(255, 255, 255, 0.9);
    }}
    #qg-source-modal {{
      display: none;
      position: fixed;
      top: 0;
      left: 0;
      width: 100%;
      height: 100%;
      background: rgba(0, 0, 0, 0.92);
      z-index: 999;
      overflow: auto;
    }}
    #qg-source-modal.visible {{
      display: flex;
      flex-direction: column;
    }}
    #qg-source-close {{
      position: fixed;
      top: 16px;
      right: 16px;
      background: rgba(255, 255, 255, 0.1);
      color: #fff;
      border: 1px solid rgba(255, 255, 255, 0.2);
      padding: 8px 16px;
      border-radius: 6px;
      cursor: pointer;
      font-family: monospace;
      font-size: 13px;
      z-index: 1001;
    }}
    #qg-source-close:hover {{
      background: rgba(255, 255, 255, 0.2);
    }}
    #qg-source-content {{
      flex: 1;
      overflow: auto;
      padding: 48px 24px 24px;
    }}
    #qg-source-content pre {{
      background: #1e1e2e;
      color: #cdd6f4;
      padding: 24px;
      border-radius: 12px;
      font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', 'Monaco', monospace;
      font-size: 14px;
      line-height: 1.7;
      overflow-x: auto;
      white-space: pre;
      tab-size: 2;
      border: 1px solid #313244;
      max-width: 900px;
      margin: 0 auto;
    }}
  </style>
</head>
<body>
{hud_html}
  <button id="qg-source-btn" onclick="toggleSource()">source</button>
  <div id="qg-source-modal">
    <button id="qg-source-close" onclick="toggleSource()">ESC</button>
    <div id="qg-source-content">
      <pre id="qg-source-code">{source_code}</pre>
    </div>
  </div>
  <script src="{pixi_cdn}"></script>
  <script src="{matter_cdn}"></script>
  <script>
function toggleSource() {{
  var modal = document.getElementById('qg-source-modal');
  modal.classList.toggle('visible');
}}
document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') {{
    document.getElementById('qg-source-modal').classList.remove('visible');
  }}
}});
{game_js}
  </script>
</body>
</html>
"""


# ==========================================================================
# Runtime JS subsystems (emitted as pre-validated blocks)
# ==========================================================================

def emit_physics_sync(js: JsBuilder):
    """Emit the syncPhysics function."""
    js.func('syncPhysics')
    js.for_entries('id', 'info', '_sprites')
    js.if_block('info.body && !info.body.isStatic')
    js.assign('info.sprite.x', 'info.body.position.x')
    js.assign('info.sprite.y', 'info.body.position.y')
    js.assign('info.sprite.rotation', 'info.body.angle')
    js.block_close()  # if
    js.block_close()  # for
    js.block_close()  # function


def emit_input_system(js: JsBuilder):
    """Emit keyboard input tracking."""
    js.const('_keys', '{}')
    js.const('_justPressed', '{}')
    js.line("window.addEventListener('keydown', (e) => {")
    js.indent()
    js.line("if (!_keys[e.key]) _justPressed[e.key] = true;")
    js.assign('_keys[e.key]', 'true')
    js.dedent()
    js.line("});")
    js.line("window.addEventListener('keyup', (e) => {")
    js.indent()
    js.assign('_keys[e.key]', 'false')
    js.dedent()
    js.line("});")
    js.func('_clearJustPressed')
    js.line("for (const k in _justPressed) delete _justPressed[k];")
    js.block_close()


def emit_animation_system(js: JsBuilder):
    """Emit the spritesheet animation runtime.

    Manages frame-based animations on sprites with spritesheets.
    Supports named animations, auto-play, speed, loop, and control-based switching.
    """
    js.comment("Animation System")
    js.const('_animatedSprites', '{}')
    js.blank()

    # parseFrames: "0-3" => [0,1,2,3], "0,2,4" => [0,2,4]
    js.func('_parseFrames', 'spec')
    js.if_block("spec.includes('-')")
    js.const('parts', "spec.split('-').map(Number)")
    js.const('result', '[]')
    js.for_range('i', 'parts[0]', 'parts[1]')
    js.line('result.push(i);')
    js.block_close()  # for
    js.ret('result')
    js.block_close()  # if
    js.ret("spec.split(',').map(s => parseInt(s.trim(), 10))")
    js.block_close()  # function
    js.blank()

    # registerAnimation
    js.func('_registerAnimation', 'spriteId, texture, frameW, frameH, anims')
    js.if_block('!texture || !frameW || !frameH')
    js.ret()
    js.block_close()
    js.const('baseTexture', 'texture.source || texture.baseTexture || texture')
    js.const('texW', 'baseTexture.width || texture.width')
    js.const('texH', 'baseTexture.height || texture.height')
    js.const('cols', 'Math.floor(texW / frameW)')
    js.const('rows', 'Math.floor(texH / frameH)')
    js.const('totalFrames', 'cols * rows')
    js.blank()
    js.comment('Build frame textures')
    js.const('frameTextures', '[]')
    js.for_range('i', '0', 'totalFrames - 1')
    js.const('fx', 'i % cols')
    js.const('fy', 'Math.floor(i / cols)')
    js.const('rect', 'new PIXI.Rectangle(fx * frameW, fy * frameH, frameW, frameH)')
    js.const('frameTex', 'new PIXI.Texture({ source: baseTexture, frame: rect })')
    js.line('frameTextures.push(frameTex);')
    js.block_close()  # for
    js.blank()
    js.comment('Parse named animations')
    js.const('animDefs', '{}')
    js.let('defaultAnim', 'null')
    js.for_of('[name, cfg]', 'Object.entries(anims)')
    js.const('frames', '_parseFrames(cfg.frames)')
    js.const('textures', 'frames.filter(f => f < frameTextures.length).map(f => frameTextures[f])')
    js.if_block('textures.length > 0')
    js.line("animDefs[name] = { textures: textures, speed: cfg.speed || 0.1, loop: cfg.loop !== false };")
    js.if_block('cfg.autoPlay')
    js.assign('defaultAnim', 'name')
    js.block_close()
    js.block_close()
    js.block_close()  # for
    js.blank()
    js.if_block('Object.keys(animDefs).length === 0')
    js.ret()
    js.block_close()
    js.blank()
    js.if_block('!defaultAnim')
    js.assign('defaultAnim', 'Object.keys(animDefs)[0]')
    js.block_close()
    js.blank()
    js.comment('Create animated sprite')
    js.const('firstAnim', 'animDefs[defaultAnim]')
    js.const('animSprite', 'new PIXI.AnimatedSprite(firstAnim.textures)')
    js.assign('animSprite.animationSpeed', 'firstAnim.speed')
    js.if_block('firstAnim.loop !== false')
    js.assign('animSprite.loop', 'true')
    js.block_close()
    js.line('animSprite.play();')
    js.blank()
    js.comment('Copy transform from static sprite')
    js.const('info', '_sprites[spriteId]')
    js.if_block('info')
    js.const('oldSprite', 'info.sprite')
    js.assign('animSprite.x', 'oldSprite.x')
    js.assign('animSprite.y', 'oldSprite.y')
    js.assign('animSprite.anchor.x', 'oldSprite.anchor ? oldSprite.anchor.x : 0.5')
    js.assign('animSprite.anchor.y', 'oldSprite.anchor ? oldSprite.anchor.y : 0.5')
    js.if_block('oldSprite.width')
    js.assign('animSprite.width', 'oldSprite.width')
    js.block_close()
    js.if_block('oldSprite.height')
    js.assign('animSprite.height', 'oldSprite.height')
    js.block_close()
    js.assign('animSprite.alpha', 'oldSprite.alpha')
    js.assign('animSprite.visible', 'oldSprite.visible')
    js.blank()
    js.comment('Replace in container')
    js.const('parent', 'oldSprite.parent')
    js.if_block('parent')
    js.const('idx', 'parent.getChildIndex(oldSprite)')
    js.line('parent.removeChild(oldSprite);')
    js.line('parent.addChildAt(animSprite, idx);')
    js.block_close()
    js.assign('info.sprite', 'animSprite')
    js.line("_animatedSprites[spriteId] = { anims: animDefs, current: defaultAnim, sprite: animSprite };")
    js.block_close()
    js.block_close()  # function
    js.blank()

    # switchAnimation
    js.func('_switchAnimation', 'spriteId, animName')
    js.const('entry', '_animatedSprites[spriteId]')
    js.if_block('!entry || entry.current === animName || !entry.anims[animName]')
    js.ret()
    js.block_close()
    js.const('anim', 'entry.anims[animName]')
    js.assign('entry.sprite.textures', 'anim.textures')
    js.assign('entry.sprite.animationSpeed', 'anim.speed')
    js.assign('entry.sprite.loop', 'anim.loop !== false')
    js.line('entry.sprite.gotoAndPlay(0);')
    js.assign('entry.current', 'animName')
    js.block_close()  # function
    js.blank()

    # updateControlAnimations - auto-switch based on input
    js.func('_updateControlAnimations')
    js.for_entries('spriteId', 'ctrl', '_controlledSprites')
    js.const('entry', '_animatedSprites[spriteId]')
    js.if_block('!entry')
    js.line('continue;')
    js.block_close()
    js.const('info', '_sprites[spriteId]')
    js.if_block('!info || !info.body')
    js.line('continue;')
    js.block_close()
    js.const('vx', 'Math.abs(info.body.velocity.x)')
    js.const('vy', 'info.body.velocity.y')
    js.blank()
    js.comment('Priority: jump > walk > idle')
    js.if_block("Math.abs(vy) > 5 && entry.anims['jump']")
    js.line("_switchAnimation(spriteId, 'jump');")
    js.else_if_block("vx > 0.5 && _keys[ctrl.right] && entry.anims['walk-right']")
    js.line("_switchAnimation(spriteId, 'walk-right');")
    js.else_if_block("vx > 0.5 && _keys[ctrl.left] && entry.anims['walk-left']")
    js.line("_switchAnimation(spriteId, 'walk-left');")
    js.else_if_block("vx > 0.5 && (entry.anims['walk'] || entry.anims['walk-right'])")
    js.line("_switchAnimation(spriteId, entry.anims['walk'] ? 'walk' : 'walk-right');")
    js.else_if_block("entry.anims['idle']")
    js.line("_switchAnimation(spriteId, 'idle');")
    js.block_close()  # if chain
    js.block_close()  # for
    js.block_close()  # function


def emit_easing_functions(js: JsBuilder):
    """Emit a comprehensive set of easing functions."""
    js.comment("Easing Functions")
    js.line('const _easing = {')
    js.indent()
    js.line("linear: t => t,")
    js.line("easeIn: t => t * t,")
    js.line("easeOut: t => t * (2 - t),")
    js.line("easeInOut: t => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t,")
    js.line("easeInCubic: t => t * t * t,")
    js.line("easeOutCubic: t => (--t) * t * t + 1,")
    js.line("easeInOutCubic: t => t < 0.5 ? 4 * t * t * t : (t - 1) * (2 * t - 2) * (2 * t - 2) + 1,")
    js.line("easeInQuart: t => t * t * t * t,")
    js.line("easeOutQuart: t => 1 - (--t) * t * t * t,")
    js.line("easeInOutQuart: t => t < 0.5 ? 8 * t * t * t * t : 1 - 8 * (--t) * t * t * t,")
    js.line("easeOutBounce: t => {")
    js.indent()
    js.line("if (t < 1/2.75) return 7.5625 * t * t;")
    js.line("if (t < 2/2.75) return 7.5625 * (t -= 1.5/2.75) * t + 0.75;")
    js.line("if (t < 2.5/2.75) return 7.5625 * (t -= 2.25/2.75) * t + 0.9375;")
    js.line("return 7.5625 * (t -= 2.625/2.75) * t + 0.984375;")
    js.dedent()
    js.line("},")
    js.line("easeInBounce: t => 1 - _easing.easeOutBounce(1 - t),")
    js.line("easeOutElastic: t => {")
    js.indent()
    js.line("if (t === 0 || t === 1) return t;")
    js.line("return Math.pow(2, -10 * t) * Math.sin((t - 0.075) * (2 * Math.PI) / 0.3) + 1;")
    js.dedent()
    js.line("},")
    js.line("easeInElastic: t => {")
    js.indent()
    js.line("if (t === 0 || t === 1) return t;")
    js.line("return -Math.pow(2, 10 * (t - 1)) * Math.sin((t - 1.075) * (2 * Math.PI) / 0.3);")
    js.dedent()
    js.line("},")
    js.dedent()
    js.line("};")


def emit_tween_system(js: JsBuilder):
    """Emit the tween runtime with real easing."""
    emit_easing_functions(js)
    js.blank()
    js.const('_tweens', '{}')
    js.let('_tweenIdCounter', '0')
    js.blank()

    js.func('_createTween', 'config')
    js.const('id', "config.id || ('tween_' + _tweenIdCounter++)")
    js.line("_tweens[id] = {")
    js.indent()
    js.line("target: config.target,")
    js.line("prop: config.prop,")
    js.line("from: null,")
    js.line("to: config.to,")
    js.line("duration: config.duration || 1,")
    js.line("easing: config.easing || 'linear',")
    js.line("loop: !!config.loop,")
    js.line("yoyo: !!config.yoyo,")
    js.line("delay: config.delay || 0,")
    js.line("elapsed: 0,")
    js.line("delayElapsed: 0,")
    js.line("active: config.active !== false,")
    js.line("started: false,")
    js.dedent()
    js.line("};")
    js.ret('id')
    js.block_close()
    js.blank()

    js.func('_updateTweens', 'dt')
    js.for_entries('tid', 'tw', '_tweens')
    js.if_block('!tw.active')
    js.line('continue;')
    js.block_close()
    js.comment('Handle delay')
    js.if_block('tw.delayElapsed < tw.delay')
    js.line('tw.delayElapsed += dt / 60;')
    js.line('continue;')
    js.block_close()
    js.comment('Init start value on first frame')
    js.if_block('!tw.started')
    js.const('info', '_sprites[tw.target]')
    js.if_block('!info')
    js.line('continue;')
    js.block_close()
    js.assign('tw.from', 'info.sprite[tw.prop]')
    js.assign('tw.started', 'true')
    js.block_close()
    js.line('tw.elapsed += dt / 60;')
    js.const('rawT', 'Math.min(tw.elapsed / tw.duration, 1)')
    js.const('easeFn', "_easing[tw.easing] || _easing.linear")
    js.const('t', 'easeFn(rawT)')
    js.const('info', '_sprites[tw.target]')
    js.if_block('info')
    js.assign('info.sprite[tw.prop]', 'tw.from + (tw.to - tw.from) * t')
    js.block_close()
    js.if_block('rawT >= 1')
    js.if_block('tw.loop')
    js.assign('tw.elapsed', '0')
    js.if_block('tw.yoyo')
    js.const('tmp', 'tw.from')
    js.assign('tw.from', 'tw.to')
    js.assign('tw.to', 'tmp')
    js.block_close()
    js.else_block()
    js.assign('tw.active', 'false')
    js.block_close()
    js.block_close()  # rawT >= 1
    js.block_close()  # for
    js.block_close()  # function


def emit_particle_system(js: JsBuilder):
    """Emit a real particle system with pooling, velocity, lifetime, alpha fade."""
    js.comment("Particle System")
    js.const('_particleSystems', '{}')
    js.blank()

    js.func('_createParticleSystem', 'config')
    js.line('const ps = {')
    js.indent()
    js.line("id: config.id,")
    js.line("follow: config.follow || null,")
    js.line("trigger: config.trigger || null,")
    js.line("count: config.count || 20,")
    js.line("emitRate: config.emitRate || 10,")
    js.line("lifetime: config.lifetime || 1,")
    js.line("speedMin: config.speedMin || 1,")
    js.line("speedMax: config.speedMax || 3,")
    js.line("angleMin: (config.angleMin || 0) * Math.PI / 180,")
    js.line("angleMax: (config.angleMax || 360) * Math.PI / 180,")
    js.line("alphaStart: config.alphaStart !== undefined ? config.alphaStart : 1,")
    js.line("alphaEnd: config.alphaEnd !== undefined ? config.alphaEnd : 0,")
    js.line("active: false,")
    js.line("emitTimer: 0,")
    js.line("pool: [],")
    js.line("container: new PIXI.Container(),")
    js.dedent()
    js.line("};")
    js.blank()
    js.comment('Pre-allocate particle pool')
    js.for_range('i', '0', 'ps.count - 1')
    js.const('p', 'new PIXI.Graphics()')
    js.line("p.circle(0, 0, 3);")
    js.line("p.fill({ color: 0xffffff });")
    js.assign('p.visible', 'false')
    js.line("p._life = 0; p._maxLife = 0; p._vx = 0; p._vy = 0;")
    js.line("p._alphaStart = 1; p._alphaEnd = 0;")
    js.line('ps.container.addChild(p);')
    js.line('ps.pool.push(p);')
    js.block_close()
    js.blank()
    js.line('_cameraContainer.addChild(ps.container);')
    js.line('_particleSystems[config.id] = ps;')
    js.ret('ps')
    js.block_close()  # function
    js.blank()

    js.func('_emitParticle', 'ps, x, y')
    js.for_of('p', 'ps.pool')
    js.if_block('!p.visible')
    js.assign('p.x', 'x')
    js.assign('p.y', 'y')
    js.const('angle', 'ps.angleMin + Math.random() * (ps.angleMax - ps.angleMin)')
    js.const('speed', 'ps.speedMin + Math.random() * (ps.speedMax - ps.speedMin)')
    js.assign('p._vx', 'Math.cos(angle) * speed')
    js.assign('p._vy', 'Math.sin(angle) * speed')
    js.assign('p._life', '0')
    js.assign('p._maxLife', 'ps.lifetime')
    js.assign('p._alphaStart', 'ps.alphaStart')
    js.assign('p._alphaEnd', 'ps.alphaEnd')
    js.assign('p.alpha', 'ps.alphaStart')
    js.assign('p.visible', 'true')
    js.ret()
    js.block_close()  # if
    js.block_close()  # for
    js.block_close()  # function
    js.blank()

    js.func('_activateParticles', 'psId')
    js.const('ps', '_particleSystems[psId]')
    js.if_block('ps')
    js.assign('ps.active', 'true')
    js.block_close()
    js.block_close()
    js.blank()

    js.func('_deactivateParticles', 'psId')
    js.const('ps', '_particleSystems[psId]')
    js.if_block('ps')
    js.assign('ps.active', 'false')
    js.block_close()
    js.block_close()
    js.blank()

    js.func('_updateParticles', 'dt')
    js.for_entries('id', 'ps', '_particleSystems')
    js.comment('Emit new particles if active')
    js.if_block('ps.active')
    js.line('ps.emitTimer += dt / 60;')
    js.const('interval', '1 / ps.emitRate')
    js.block_open('while (ps.emitTimer >= interval)')
    js.line('ps.emitTimer -= interval;')
    js.let('ex', '0')
    js.let('ey', '0')
    js.if_block('ps.follow')
    js.const('info', '_sprites[ps.follow]')
    js.if_block('info')
    js.assign('ex', 'info.sprite.x')
    js.assign('ey', 'info.sprite.y')
    js.block_close()
    js.block_close()
    js.line('_emitParticle(ps, ex, ey);')
    js.block_close()  # while
    js.block_close()  # if active
    js.blank()
    js.comment('Update living particles')
    js.for_of('p', 'ps.pool')
    js.if_block('!p.visible')
    js.line('continue;')
    js.block_close()
    js.line('p._life += dt / 60;')
    js.if_block('p._life >= p._maxLife')
    js.assign('p.visible', 'false')
    js.line('continue;')
    js.block_close()
    js.const('lifeT', 'p._life / p._maxLife')
    js.assign('p.x', 'p.x + p._vx')
    js.assign('p.y', 'p.y + p._vy')
    js.assign('p.alpha', 'p._alphaStart + (p._alphaEnd - p._alphaStart) * lifeT')
    js.block_close()  # for particles
    js.block_close()  # for systems
    js.block_close()  # function


def emit_audio_system(js: JsBuilder):
    """Emit robust audio system with proper autoplay handling."""
    js.comment("Audio System")
    js.const('_sounds', '{}')
    js.let('_audioCtx', 'null')
    js.let('_audioUnlocked', 'false')
    js.const('_pendingSounds', '[]')
    js.blank()

    js.func('_initAudio')
    js.if_block('_audioCtx')
    js.ret()
    js.block_close()
    js.line("_audioCtx = new (window.AudioContext || window.webkitAudioContext)();")
    js.blank()
    js.comment('Unlock audio on any user interaction')
    js.const('unlockEvents', "['click', 'keydown', 'touchstart', 'pointerdown']")
    js.func('_unlock')
    js.if_block('_audioUnlocked')
    js.ret()
    js.block_close()
    js.if_block("_audioCtx.state === 'suspended'")
    js.line("_audioCtx.resume().then(() => {")
    js.indent()
    js.assign('_audioUnlocked', 'true')
    js.comment('Play any queued sounds')
    js.block_open('while (_pendingSounds.length > 0)')
    js.const('pending', '_pendingSounds.shift()')
    js.const('_psrc', '_doPlaySound(pending.id, pending.opts)')
    js.if_block('_psrc')
    js.assign('_activeSources[pending.id]', '_psrc')
    js.line("_psrc.onended = function() { if (_activeSources[pending.id] === _psrc) delete _activeSources[pending.id]; };")
    js.block_close()
    js.block_close()
    js.dedent()
    js.line("});")
    js.else_block()
    js.assign('_audioUnlocked', 'true')
    js.block_close()
    js.for_of('evt', 'unlockEvents')
    js.line("document.removeEventListener(evt, _unlock);")
    js.block_close()
    js.block_close()  # _unlock
    js.blank()
    js.for_of('evt', 'unlockEvents')
    js.line("document.addEventListener(evt, _unlock, { once: false });")
    js.block_close()
    js.block_close()  # _initAudio
    js.blank()

    js.block_open('async function _loadSound(id, url)')
    js.line('_initAudio();')
    js.block_open('try')
    js.const('resp', 'await fetch(url)')
    js.const('buf', 'await resp.arrayBuffer()')
    js.assign('_sounds[id]', 'await _audioCtx.decodeAudioData(buf)')
    js.block_close()
    js.block_open('catch(e)')
    js.line("console.warn('Sound load failed:', id, e);")
    js.block_close()
    js.block_close()  # function
    js.blank()

    js.func('_doPlaySound', 'id, opts')
    js.assign('opts', 'opts || {}')
    js.const('buf', '_sounds[id]')
    js.if_block('!buf')
    js.ret()
    js.block_close()
    js.const('src', '_audioCtx.createBufferSource()')
    js.assign('src.buffer', 'buf')
    js.const('gain', '_audioCtx.createGain()')
    js.assign('gain.gain.value', 'opts.volume !== undefined ? opts.volume : 1')
    js.line('src.connect(gain).connect(_audioCtx.destination);')
    js.assign('src.loop', '!!opts.loop')
    js.line('src.start(0);')
    js.ret('src')
    js.block_close()
    js.blank()

    js.const('_activeSources', '{}')
    js.blank()
    js.func('_playSound', 'id, opts')
    js.if_block('!_audioUnlocked')
    js.line('_pendingSounds.push({ id: id, opts: opts });')
    js.ret()
    js.block_close()
    js.const('src', '_doPlaySound(id, opts)')
    js.if_block('src')
    js.assign('_activeSources[id]', 'src')
    js.line("src.onended = function() { if (_activeSources[id] === src) delete _activeSources[id]; };")
    js.block_close()
    js.ret('src')
    js.block_close()
    js.blank()
    js.func('_stopSound', 'id')
    js.const('src', '_activeSources[id]')
    js.if_block('src')
    js.block_open('try')
    js.line('src.stop();')
    js.block_close()
    js.block_open('catch(e)')
    js.block_close()
    js.line('delete _activeSources[id];')
    js.block_close()
    js.block_close()


def emit_timer_system(js: JsBuilder):
    """Emit timer system without eval."""
    js.comment("Timer System")
    js.const('_timers', '{}')
    js.const('_timerActions', '{}')
    js.blank()

    js.func('_createTimer', 'id, interval, repeat, autoStart, actionFn')
    js.line("_timers[id] = { elapsed: 0, interval: interval, repeat: repeat, count: 0, active: autoStart };")
    js.assign('_timerActions[id]', 'actionFn')
    js.block_close()
    js.blank()

    js.func('_updateTimers', 'dt')
    js.for_entries('tid', 't', '_timers')
    js.if_block('!t.active')
    js.line('continue;')
    js.block_close()
    js.line('t.elapsed += dt / 60;')
    js.if_block('t.elapsed >= t.interval')
    js.assign('t.elapsed', '0')
    js.if_block('_timerActions[tid]')
    js.line('_timerActions[tid]();')
    js.block_close()
    js.line('t.count++;')
    js.if_block('t.repeat >= 0 && t.count >= t.repeat')
    js.assign('t.active', 'false')
    js.block_close()
    js.block_close()  # elapsed >= interval
    js.block_close()  # for
    js.block_close()  # function


def emit_event_bus(js: JsBuilder):
    """Emit a lightweight pub/sub event bus for game events."""
    js.comment("Event Bus")
    js.const('_gameEvents', '{ _listeners: {} }')
    js.line("_gameEvents.on = function(event, cb) {")
    js.indent()
    js.if_block('!this._listeners[event]')
    js.assign('this._listeners[event]', '[]')
    js.block_close()
    js.line('this._listeners[event].push(cb);')
    js.dedent()
    js.line("};")
    js.line("_gameEvents.off = function(event, cb) {")
    js.indent()
    js.if_block('this._listeners[event]')
    js.assign('this._listeners[event]', 'this._listeners[event].filter(fn => fn !== cb)')
    js.block_close()
    js.dedent()
    js.line("};")
    js.line("_gameEvents.emit = function(event, data) {")
    js.indent()
    js.if_block('this._listeners[event]')
    js.for_of('cb', 'this._listeners[event]')
    js.line('cb(data);')
    js.block_close()
    js.block_close()
    js.dedent()
    js.line("};")


def emit_game_api(js: JsBuilder):
    """Emit the game API object with utility methods."""
    js.comment("Game API")
    js.const('game', '{ camera: {} }')
    js.blank()

    # game.destroy(info)
    js.line("game.destroy = function(info) {")
    js.indent()
    js.if_block('!info')
    js.ret()
    js.block_close()
    js.comment('Find sprite id')
    js.let('spriteId', 'null')
    js.for_entries('id', 'entry', '_sprites')
    js.if_block('entry === info || entry.sprite === info')
    js.assign('spriteId', 'id')
    js.line('break;')
    js.block_close()
    js.block_close()
    js.if_block('!spriteId')
    js.ret()
    js.block_close()
    js.const('entry', '_sprites[spriteId]')
    js.if_block('entry.sprite && entry.sprite.parent')
    js.line('entry.sprite.parent.removeChild(entry.sprite);')
    js.block_close()
    js.if_block('entry.body')
    js.line('Matter.Composite.remove(mWorld, entry.body);')
    js.block_close()
    js.line('delete _sprites[spriteId];')
    js.dedent()
    js.line("};")
    js.blank()

    # game.play(soundId, opts)
    js.line("game.play = function(soundId, opts) {")
    js.indent()
    js.if_block("typeof _playSound === 'function'")
    js.ret('_playSound(soundId, opts)')
    js.block_close()
    js.dedent()
    js.line("};")
    js.blank()

    # game.stop(soundId)
    js.line("game.stop = function(soundId) {")
    js.indent()
    js.if_block("typeof _stopSound === 'function'")
    js.line('_stopSound(soundId);')
    js.block_close()
    js.dedent()
    js.line("};")
    js.blank()

    # game.emit(info, event)
    js.line("game.emit = function(info, event) {")
    js.indent()
    js.line('_gameEvents.emit(event, info);')
    js.if_block('info && info.tag')
    js.line("_gameEvents.emit(info.tag + '.' + event, info);")
    js.block_close()
    js.dedent()
    js.line("};")
    js.blank()

    # game.loadScene(name)
    js.line("game.loadScene = function(name) {")
    js.indent()
    js.if_block("typeof _loadScene === 'function'")
    js.line('_loadScene(name);')
    js.block_close()
    js.dedent()
    js.line("};")
    js.blank()

    # game.respawn(id, x, y)
    js.line("game.respawn = function(id, x, y) {")
    js.indent()
    js.const('info', '_sprites[id]')
    js.if_block('!info')
    js.ret()
    js.block_close()
    js.if_block('info.sprite')
    js.assign('info.sprite.x', 'x')
    js.assign('info.sprite.y', 'y')
    js.assign('info.sprite.visible', 'true')
    js.block_close()
    js.if_block('info.body')
    js.line('Matter.Body.setPosition(info.body, { x: x, y: y });')
    js.line('Matter.Body.setVelocity(info.body, { x: 0, y: 0 });')
    js.block_close()
    js.dedent()
    js.line("};")
    js.blank()

    # game.destroyGroup(name)
    js.line("game.destroyGroup = function(groupName) {")
    js.indent()
    js.const('toRemove', '[]')
    js.for_entries('id', 'info', '_sprites')
    js.if_block('info.group === groupName')
    js.line('toRemove.push(info);')
    js.block_close()
    js.block_close()
    js.for_of('info', 'toRemove')
    js.line('game.destroy(info);')
    js.block_close()
    js.dedent()
    js.line("};")
    js.blank()

    # game.moveX(info, dx)
    js.line("game.moveX = function(info, dx) {")
    js.indent()
    js.if_block('info && info.body')
    js.line("Matter.Body.setVelocity(info.body, { x: dx, y: info.body.velocity.y });")
    js.block_close()
    js.dedent()
    js.line("};")
    js.blank()

    # game.moveToward(info, targetId, speed)
    js.line("game.moveToward = function(info, targetId, speed) {")
    js.indent()
    js.if_block('!info || !info.body')
    js.ret()
    js.block_close()
    js.const('target', '_sprites[targetId]')
    js.if_block('!target')
    js.ret()
    js.block_close()
    js.const('dx', 'target.sprite.x - info.sprite.x')
    js.const('dy', 'target.sprite.y - info.sprite.y')
    js.const('dist', 'Math.sqrt(dx * dx + dy * dy)')
    js.if_block('dist < 1')
    js.ret()
    js.block_close()
    js.line("Matter.Body.setVelocity(info.body, { x: (dx / dist) * speed, y: (dy / dist) * speed });")
    js.dedent()
    js.line("};")
    js.blank()

    # game.patrol(info, speed)
    js.line("game.patrol = function(info, speed) {")
    js.indent()
    js.line('game.moveX(info, speed);')
    js.dedent()
    js.line("};")
    js.blank()

    # game.camera.shake(intensity, duration)
    js.line("game.camera.shake = function(intensity, duration) {")
    js.indent()
    js.let('_shakeFrames', 'Math.floor((duration || 0.3) * 60)')
    js.const('_shakeIntensity', 'intensity || 5')
    js.const('origX', '_cameraContainer.x')
    js.const('origY', '_cameraContainer.y')
    js.line("const _shakeTick = () => {")
    js.indent()
    js.if_block('_shakeFrames <= 0')
    js.assign('_cameraContainer.x', 'origX')
    js.assign('_cameraContainer.y', 'origY')
    js.ret()
    js.block_close()
    js.line('_cameraContainer.x = origX + (Math.random() - 0.5) * _shakeIntensity * 2;')
    js.line('_cameraContainer.y = origY + (Math.random() - 0.5) * _shakeIntensity * 2;')
    js.line('_shakeFrames--;')
    js.line('requestAnimationFrame(_shakeTick);')
    js.dedent()
    js.line("};")
    js.line('_shakeTick();')
    js.dedent()
    js.line("};")
    js.blank()

    # game.spawn(id)
    js.line("game.spawn = function(id) {")
    js.indent()
    js.if_block("typeof _spawn === 'function'")
    js.line('_spawn(id);')
    js.block_close()
    js.dedent()
    js.line("};")


def emit_spawn_system(js: JsBuilder):
    """Emit the spawn/pool system."""
    js.comment("Spawn System")
    js.const('_spawners', '{}')
    js.const('_prefabConfigs', '{}')
    js.blank()

    js.func('_registerPrefab', 'name, config')
    js.assign('_prefabConfigs[name]', 'config')
    js.block_close()
    js.blank()

    js.func('_createSpawner', 'config')
    js.line("_spawners[config.id] = {")
    js.indent()
    js.line("id: config.id,")
    js.line("prefab: config.prefab,")
    js.line("poolSize: config.poolSize || 10,")
    js.line("spawnX: config.x || 0,")
    js.line("spawnY: config.y || 0,")
    js.line("interval: config.interval || null,")
    js.line("pool: [],")
    js.line("active: 0,")
    js.dedent()
    js.line("};")
    js.block_close()
    js.blank()

    # Helper to create a sprite from prefab config
    js.func('_createPrefabSprite', 'prefabName, x, y')
    js.const('config', '_prefabConfigs[prefabName]')
    js.if_block('!config')
    js.line("console.warn('Unknown prefab:', prefabName);")
    js.ret('null')
    js.block_close()
    js.const('w', 'config.width || 20')
    js.const('h', 'config.height || 20')
    js.const('spr', 'new PIXI.Graphics()')
    js.comment('Center the rectangle like main sprites')
    js.line('spr.rect(-w/2, -h/2, w, h);')
    js.if_block('config.color')
    js.line("spr.fill({ color: parseInt(config.color.replace('#',''), 16) });")
    js.else_block()
    js.line("spr.fill({ color: 0x22c55e });")
    js.block_close()
    js.assign('spr.x', 'x')
    js.assign('spr.y', 'y')
    js.line('_cameraContainer.addChild(spr);')
    js.ret('spr')
    js.block_close()
    js.blank()

    js.func('_spawn', 'spawnerId')
    js.const('sp', '_spawners[spawnerId]')
    js.if_block('!sp')
    js.ret('null')
    js.block_close()
    js.comment('Find an inactive pool member')
    js.for_of('item', 'sp.pool')
    js.if_block('!item.active')
    js.assign('item.active', 'true')
    js.if_block('item.sprite')
    js.assign('item.sprite.visible', 'true')
    js.assign('item.sprite.x', 'sp.spawnX')
    js.assign('item.sprite.y', 'sp.spawnY')
    js.block_close()
    js.if_block('item.body')
    js.line('Matter.Body.setPosition(item.body, { x: sp.spawnX, y: sp.spawnY });')
    js.block_close()
    js.ret('item.sprite')
    js.block_close()
    js.block_close()
    js.comment('No inactive items, create new if under pool limit')
    js.if_block('sp.pool.length < sp.poolSize')
    js.const('newSprite', '_createPrefabSprite(sp.prefab, sp.spawnX, sp.spawnY)')
    js.if_block('newSprite')
    js.const('newItem', '{ sprite: newSprite, active: true, body: null }')
    js.line('sp.pool.push(newItem);')
    js.ret('newSprite')
    js.block_close()
    js.block_close()
    js.ret('null')
    js.block_close()


def emit_mouse_system(js: JsBuilder):
    """Emit global mouse position tracking and coordinate conversion."""
    js.comment("Mouse System")
    js.let('_mouseX', '0')
    js.let('_mouseY', '0')
    js.let('_mouseWorldX', '0')
    js.let('_mouseWorldY', '0')
    js.line("app.canvas.addEventListener('pointermove', (e) => {")
    js.indent()
    js.const('rect', 'app.canvas.getBoundingClientRect()')
    js.assign('_mouseX', 'e.clientX - rect.left')
    js.assign('_mouseY', 'e.clientY - rect.top')
    js.comment('Convert to world coordinates (accounting for camera)')
    js.assign('_mouseWorldX', '_mouseX - _cameraContainer.x')
    js.assign('_mouseWorldY', '_mouseY - _cameraContainer.y')
    js.dedent()
    js.line("});")


# HUD element template (HTML)
HUD_DIV_TEMPLATE = '<div class="qg-hud qg-hud-{position}" id="qg-hud-{index}">{content}</div>'
