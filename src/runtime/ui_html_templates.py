"""
UI Engine - HTML Templates and HtmlBuilder

Provides:
  - HtmlBuilder: Structured HTML code emitter with proper indentation
  - HTML_TEMPLATE: Shell HTML5 document template
  - CSS_RESET: Basic CSS reset
  - CSS_THEME: Default theme variables and base styles
"""


# ==========================================================================
# HtmlBuilder - Structured HTML code emitter
# ==========================================================================

class HtmlBuilder:
    """Builds well-formatted HTML with proper indentation."""

    def __init__(self, indent_size: int = 2):
        self._lines: list[str] = []
        self._indent: int = 0
        self._indent_size: int = indent_size

    @property
    def _pad(self) -> str:
        return ' ' * (self._indent * self._indent_size)

    def line(self, code: str = '') -> 'HtmlBuilder':
        self._lines.append(f"{self._pad}{code}" if code else '')
        return self

    def raw(self, code: str) -> 'HtmlBuilder':
        for ln in code.split('\n'):
            self._lines.append(f"{self._pad}{ln}")
        return self

    def blank(self) -> 'HtmlBuilder':
        self._lines.append('')
        return self

    def indent(self) -> 'HtmlBuilder':
        self._indent += 1
        return self

    def dedent(self) -> 'HtmlBuilder':
        self._indent = max(0, self._indent - 1)
        return self

    def open_tag(self, tag: str, attrs: dict = None, self_closing: bool = False) -> 'HtmlBuilder':
        attr_str = ''
        if attrs:
            parts = []
            for k, v in attrs.items():
                if v is True:
                    parts.append(k)
                elif v is not None and v is not False:
                    parts.append(f'{k}="{v}"')
            if parts:
                attr_str = ' ' + ' '.join(parts)
        if self_closing:
            self.line(f'<{tag}{attr_str} />')
        else:
            self.line(f'<{tag}{attr_str}>')
        return self

    def close_tag(self, tag: str) -> 'HtmlBuilder':
        self.line(f'</{tag}>')
        return self

    def text(self, content: str) -> 'HtmlBuilder':
        self.line(content)
        return self

    def comment(self, text: str) -> 'HtmlBuilder':
        self.line(f'<!-- {text} -->')
        return self

    def build(self) -> str:
        return '\n'.join(self._lines)


# ==========================================================================
# CSS Reset
# ==========================================================================

CSS_RESET = """\
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 16px; line-height: 1.5; -webkit-font-smoothing: antialiased; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
img, picture, video, canvas, svg { display: block; max-width: 100%; }
input, button, textarea, select { font: inherit; }
"""


# ==========================================================================
# CSS Theme
# ==========================================================================

CSS_THEME = """\
:root {
  --q-primary: #3b82f6;
  --q-secondary: #64748b;
  --q-success: #22c55e;
  --q-danger: #ef4444;
  --q-warning: #f59e0b;
  --q-info: #06b6d4;
  --q-light: #f8fafc;
  --q-dark: #1e293b;
  --q-bg: #ffffff;
  --q-text: #1e293b;
  --q-border: #e2e8f0;
  --q-radius: 6px;
  --q-shadow: 0 1px 3px rgba(0,0,0,0.1);
  --q-font-xs: 0.75rem;
  --q-font-sm: 0.875rem;
  --q-font-md: 1rem;
  --q-font-lg: 1.25rem;
  --q-font-xl: 1.5rem;
  --q-font-2xl: 2rem;
}

body { background: var(--q-bg); color: var(--q-text); }

/* Window */
.q-window { max-width: 1200px; margin: 0 auto; padding: 16px; }

/* Panel */
.q-panel { border: 1px solid var(--q-border); border-radius: var(--q-radius); padding: 16px; box-shadow: var(--q-shadow); }
.q-panel-title { font-weight: 600; margin-bottom: 12px; font-size: var(--q-font-lg); border-bottom: 1px solid var(--q-border); padding-bottom: 8px; }

/* Buttons */
.q-btn { display: inline-flex; align-items: center; justify-content: center; padding: 8px 16px; border: 1px solid var(--q-border); border-radius: var(--q-radius); cursor: pointer; font-weight: 500; transition: all 0.15s; background: var(--q-bg); }
.q-btn:hover { opacity: 0.9; }
.q-btn-primary { background: var(--q-primary); color: white; border-color: var(--q-primary); }
.q-btn-secondary { background: var(--q-secondary); color: white; border-color: var(--q-secondary); }
.q-btn-danger { background: var(--q-danger); color: white; border-color: var(--q-danger); }
.q-btn-success { background: var(--q-success); color: white; border-color: var(--q-success); }
.q-btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* Inputs */
.q-input { width: 100%; padding: 8px 12px; border: 1px solid var(--q-border); border-radius: var(--q-radius); outline: none; transition: border-color 0.15s; }
.q-input:focus { border-color: var(--q-primary); box-shadow: 0 0 0 3px rgba(59,130,246,0.15); }

/* Checkbox / Switch */
.q-checkbox { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.q-switch { position: relative; display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }
.q-switch input { display: none; }
.q-switch-track { width: 40px; height: 22px; background: var(--q-border); border-radius: 11px; position: relative; transition: background 0.2s; }
.q-switch input:checked + .q-switch-track { background: var(--q-primary); }
.q-switch-thumb { width: 18px; height: 18px; background: white; border-radius: 50%; position: absolute; top: 2px; left: 2px; transition: transform 0.2s; }
.q-switch input:checked + .q-switch-track .q-switch-thumb { transform: translateX(18px); }

/* Table */
.q-table { width: 100%; border-collapse: collapse; }
.q-table th, .q-table td { padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--q-border); }
.q-table th { font-weight: 600; background: var(--q-light); }
.q-table tr:hover { background: var(--q-light); }

/* Tabs */
.q-tabs { display: flex; flex-direction: column; }
.q-tab-headers { display: flex; border-bottom: 2px solid var(--q-border); gap: 0; }
.q-tab-header { padding: 10px 20px; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; font-weight: 500; color: var(--q-secondary); transition: all 0.15s; background: none; border-top: none; border-left: none; border-right: none; }
.q-tab-header.active { color: var(--q-primary); border-bottom-color: var(--q-primary); }
.q-tab-content { display: none; padding: 16px 0; }
.q-tab-content.active { display: block; }

/* Form */
.q-form { display: flex; flex-direction: column; gap: 16px; }
.q-formitem { display: flex; flex-direction: row; align-items: center; gap: 12px; }
.q-formitem-label { min-width: 120px; font-weight: 500; }

/* Badge */
.q-badge { display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 12px; font-size: var(--q-font-xs); font-weight: 600; background: var(--q-light); color: var(--q-text); }
.q-badge-primary { background: var(--q-primary); color: white; }
.q-badge-secondary { background: var(--q-secondary); color: white; }
.q-badge-success { background: var(--q-success); color: white; }
.q-badge-danger { background: var(--q-danger); color: white; }
.q-badge-warning { background: var(--q-warning); color: white; }

/* Loading */
.q-loading { display: flex; align-items: center; gap: 8px; color: var(--q-secondary); }
.q-spinner { width: 20px; height: 20px; border: 2px solid var(--q-border); border-top-color: var(--q-primary); border-radius: 50%; animation: q-spin 0.6s linear infinite; }
@keyframes q-spin { to { transform: rotate(360deg); } }

/* Log */
.q-log { font-family: 'SF Mono', 'Fira Code', monospace; font-size: var(--q-font-sm); background: var(--q-dark); color: #e2e8f0; padding: 12px; border-radius: var(--q-radius); overflow-y: auto; max-height: 400px; }

/* Progress */
progress { width: 100%; height: 8px; border-radius: 4px; overflow: hidden; appearance: none; }
progress::-webkit-progress-bar { background: var(--q-light); border-radius: 4px; }
progress::-webkit-progress-value { background: var(--q-primary); border-radius: 4px; }

/* Header / Footer */
.q-header { padding: 12px 16px; background: var(--q-dark); color: white; font-weight: 600; font-size: var(--q-font-lg); }
.q-footer { padding: 12px 16px; background: var(--q-light); color: var(--q-secondary); border-top: 1px solid var(--q-border); font-size: var(--q-font-sm); }

/* Scrollbox */
.q-scrollbox { overflow: auto; }

/* Accordion / Section */
details.q-section { border: 1px solid var(--q-border); border-radius: var(--q-radius); margin-bottom: 4px; }
details.q-section summary { padding: 10px 16px; cursor: pointer; font-weight: 500; }
details.q-section .q-section-content { padding: 12px 16px; border-top: 1px solid var(--q-border); }

/* Spacer */
.q-spacer { flex: 1; }

/* Select */
.q-select { width: 100%; padding: 8px 12px; border: 1px solid var(--q-border); border-radius: var(--q-radius); outline: none; background: var(--q-bg); }
.q-select:focus { border-color: var(--q-primary); }

/* Menu */
.q-menu { display: flex; gap: 4px; }
.q-menu-item { padding: 8px 16px; cursor: pointer; border-radius: var(--q-radius); transition: background 0.15s; }
.q-menu-item:hover { background: var(--q-light); }

/* DividedBox */
.q-dividedbox { display: flex; gap: 0; }
.q-dividedbox-h { flex-direction: row; }
.q-dividedbox-v { flex-direction: column; }
.q-divider { background: var(--q-border); flex-shrink: 0; }
.q-dividedbox-h > .q-divider { width: 4px; cursor: col-resize; }
.q-dividedbox-v > .q-divider { height: 4px; cursor: row-resize; }
"""


# ==========================================================================
# HTML Template
# ==========================================================================

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <style>
{css}
  </style>
</head>
<body>
{body}
{js}
</body>
</html>
"""


# ==========================================================================
# Tab JS
# ==========================================================================

TAB_JS = """\
<script>
document.querySelectorAll('.q-tab-header').forEach(function(btn) {
  btn.addEventListener('click', function() {
    var group = this.dataset.tabGroup;
    var target = this.dataset.tab;
    document.querySelectorAll('.q-tab-header[data-tab-group="' + group + '"]').forEach(function(b) { b.classList.remove('active'); });
    document.querySelectorAll('.q-tab-content[data-tab-group="' + group + '"]').forEach(function(c) { c.classList.remove('active'); });
    this.classList.add('active');
    document.getElementById(target).classList.add('active');
  });
});
</script>
"""
