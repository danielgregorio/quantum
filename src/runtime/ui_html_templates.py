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

body { background: var(--q-bg); color: var(--q-text); min-height: 100vh; }

/* Window */
.q-window { width: 100%; min-height: 100vh; display: flex; flex-direction: column; }

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

/* Responsive Layout */
.q-window > header, .q-window > .q-header { flex-shrink: 0; }
.q-window > footer, .q-window > .q-footer { flex-shrink: 0; margin-top: auto; }
.q-window > div:not(.q-header):not(.q-footer) { flex: 1; overflow: auto; }
.q-panel { flex-shrink: 0; }

/* Media Queries for smaller screens */
@media (max-width: 900px) {
  .q-window > div[style*="flex-direction: row"] { flex-direction: column !important; }
  .q-window > div > div[style*="width: 280px"] { width: 100% !important; }
  .q-window > div > div[style*="width: 50%"] { width: 100% !important; }
}

/* ============================================
   Component Library Styles
   ============================================ */

/* Card */
.q-card { background: var(--q-bg); border: 1px solid var(--q-border); border-radius: var(--q-radius); box-shadow: var(--q-shadow); overflow: hidden; }
.q-card-elevated { box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
.q-card-outlined { box-shadow: none; border-width: 2px; }
.q-card-image { width: 100%; }
.q-card-image img { width: 100%; height: auto; display: block; }
.q-card-header { padding: 16px; border-bottom: 1px solid var(--q-border); }
.q-card-title { font-size: var(--q-font-lg); font-weight: 600; margin: 0; }
.q-card-subtitle { font-size: var(--q-font-sm); color: var(--q-secondary); margin-top: 4px; }
.q-card-body { padding: 16px; }
.q-card-footer { padding: 12px 16px; background: var(--q-light); border-top: 1px solid var(--q-border); display: flex; gap: 8px; justify-content: flex-end; }

/* Modal */
.q-modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: none; justify-content: center; align-items: center; z-index: 1000; }
.q-modal-overlay.q-modal-open { display: flex; }
.q-modal { background: var(--q-bg); border-radius: var(--q-radius); box-shadow: 0 8px 32px rgba(0,0,0,0.2); max-width: 500px; width: 90%; max-height: 90vh; overflow: auto; }
.q-modal-sm { max-width: 300px; }
.q-modal-lg { max-width: 800px; }
.q-modal-xl { max-width: 1100px; }
.q-modal-full { max-width: 95vw; max-height: 95vh; }
.q-modal-header { display: flex; justify-content: space-between; align-items: center; padding: 16px; border-bottom: 1px solid var(--q-border); }
.q-modal-title { font-size: var(--q-font-lg); font-weight: 600; margin: 0; }
.q-modal-close { background: none; border: none; font-size: 20px; cursor: pointer; padding: 4px 8px; color: var(--q-secondary); }
.q-modal-close:hover { color: var(--q-text); }
.q-modal-body { padding: 16px; }

/* Chart */
.q-chart { padding: 16px; }
.q-chart-title { font-size: var(--q-font-lg); font-weight: 600; margin-bottom: 16px; }
.q-chart-container { display: flex; flex-direction: column; gap: 8px; }
.q-chart-bar-group { display: flex; align-items: center; gap: 12px; }
.q-chart-label { min-width: 80px; font-size: var(--q-font-sm); }
.q-chart-bar { height: 24px; border-radius: 4px; display: flex; align-items: center; padding: 0 8px; min-width: 30px; transition: width 0.3s ease; }
.q-chart-value { font-size: var(--q-font-xs); color: white; font-weight: 600; }

/* Avatar */
.q-avatar { position: relative; display: inline-flex; align-items: center; justify-content: center; width: 40px; height: 40px; border-radius: 50%; background: var(--q-primary); color: white; font-weight: 600; overflow: hidden; }
.q-avatar-xs { width: 24px; height: 24px; font-size: var(--q-font-xs); }
.q-avatar-sm { width: 32px; height: 32px; font-size: var(--q-font-sm); }
.q-avatar-lg { width: 56px; height: 56px; font-size: var(--q-font-lg); }
.q-avatar-xl { width: 72px; height: 72px; font-size: var(--q-font-xl); }
.q-avatar-square { border-radius: var(--q-radius); }
.q-avatar img { width: 100%; height: 100%; object-fit: cover; }
.q-avatar-initials { text-transform: uppercase; }
.q-avatar-status { position: absolute; bottom: 0; right: 0; width: 12px; height: 12px; border-radius: 50%; border: 2px solid var(--q-bg); }
.q-avatar-status-online { background: var(--q-success); }
.q-avatar-status-offline { background: var(--q-secondary); }
.q-avatar-status-away { background: var(--q-warning); }
.q-avatar-status-busy { background: var(--q-danger); }

/* Tooltip */
.q-tooltip-wrapper { position: relative; display: inline-block; }
.q-tooltip-text { visibility: hidden; position: absolute; z-index: 100; padding: 6px 10px; background: var(--q-dark); color: white; font-size: var(--q-font-sm); border-radius: var(--q-radius); white-space: nowrap; opacity: 0; transition: opacity 0.2s; }
.q-tooltip-wrapper:hover .q-tooltip-text { visibility: visible; opacity: 1; }
.q-tooltip-top .q-tooltip-text { bottom: 100%; left: 50%; transform: translateX(-50%); margin-bottom: 8px; }
.q-tooltip-bottom .q-tooltip-text { top: 100%; left: 50%; transform: translateX(-50%); margin-top: 8px; }
.q-tooltip-left .q-tooltip-text { right: 100%; top: 50%; transform: translateY(-50%); margin-right: 8px; }
.q-tooltip-right .q-tooltip-text { left: 100%; top: 50%; transform: translateY(-50%); margin-left: 8px; }

/* Dropdown */
.q-dropdown { position: relative; display: inline-block; }
.q-dropdown-trigger { display: inline-flex; align-items: center; gap: 4px; padding: 8px 12px; background: var(--q-bg); border: 1px solid var(--q-border); border-radius: var(--q-radius); cursor: pointer; }
.q-dropdown-arrow { font-size: var(--q-font-xs); }
.q-dropdown-menu { position: absolute; top: 100%; left: 0; min-width: 160px; background: var(--q-bg); border: 1px solid var(--q-border); border-radius: var(--q-radius); box-shadow: var(--q-shadow); z-index: 100; display: none; margin-top: 4px; }
.q-dropdown-right .q-dropdown-menu { left: auto; right: 0; }
.q-dropdown:focus-within .q-dropdown-menu,
.q-dropdown-hover:hover .q-dropdown-menu { display: block; }
.q-dropdown-menu .q-menu-item { display: block; width: 100%; padding: 8px 12px; text-align: left; }

/* Alert */
.q-alert { display: flex; align-items: flex-start; gap: 12px; padding: 12px 16px; border-radius: var(--q-radius); margin-bottom: 8px; }
.q-alert-info { background: rgba(6,182,212,0.1); border: 1px solid var(--q-info); color: var(--q-info); }
.q-alert-success { background: rgba(34,197,94,0.1); border: 1px solid var(--q-success); color: var(--q-success); }
.q-alert-warning { background: rgba(245,158,11,0.1); border: 1px solid var(--q-warning); color: var(--q-warning); }
.q-alert-danger { background: rgba(239,68,68,0.1); border: 1px solid var(--q-danger); color: var(--q-danger); }
.q-alert-icon { flex-shrink: 0; font-size: var(--q-font-lg); }
.q-alert-content { flex: 1; }
.q-alert-title { font-weight: 600; margin-bottom: 4px; }
.q-alert-message { font-size: var(--q-font-sm); opacity: 0.9; }
.q-alert-dismiss { background: none; border: none; cursor: pointer; padding: 0 4px; font-size: var(--q-font-lg); opacity: 0.6; }
.q-alert-dismiss:hover { opacity: 1; }

/* Breadcrumb */
.q-breadcrumb { padding: 8px 0; }
.q-breadcrumb-list { display: flex; align-items: center; list-style: none; gap: 0; flex-wrap: wrap; }
.q-breadcrumb-item { display: flex; align-items: center; }
.q-breadcrumb-link { color: var(--q-primary); text-decoration: none; }
.q-breadcrumb-link:hover { text-decoration: underline; }
.q-breadcrumb-text { color: var(--q-text); }
.q-breadcrumb-current .q-breadcrumb-text { font-weight: 500; }
.q-breadcrumb-separator { margin: 0 8px; color: var(--q-secondary); }
.q-breadcrumb-icon { margin-right: 4px; }

/* Pagination */
.q-pagination { display: flex; align-items: center; gap: 16px; padding: 8px 0; }
.q-pagination-total { font-size: var(--q-font-sm); color: var(--q-secondary); }
.q-pagination-controls { display: flex; align-items: center; gap: 8px; }
.q-pagination-prev, .q-pagination-next { padding: 6px 12px; background: var(--q-bg); border: 1px solid var(--q-border); border-radius: var(--q-radius); cursor: pointer; }
.q-pagination-prev:hover, .q-pagination-next:hover { background: var(--q-light); }
.q-pagination-pages { padding: 0 12px; font-weight: 500; }
.q-pagination-jump { display: flex; align-items: center; gap: 8px; font-size: var(--q-font-sm); }
.q-pagination-input { width: 60px; padding: 4px 8px; border: 1px solid var(--q-border); border-radius: var(--q-radius); }

/* Skeleton */
.q-skeleton { background: linear-gradient(90deg, var(--q-light) 25%, #e2e8f0 50%, var(--q-light) 75%); background-size: 200% 100%; border-radius: var(--q-radius); }
.q-skeleton-animated { animation: q-skeleton-loading 1.5s infinite; }
@keyframes q-skeleton-loading { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }
.q-skeleton-text { height: 16px; margin-bottom: 8px; }
.q-skeleton-text:last-child { width: 60%; }
.q-skeleton-circle { width: 48px; height: 48px; border-radius: 50%; }
.q-skeleton-rect { height: 100px; }
.q-skeleton-card { border: 1px solid var(--q-border); border-radius: var(--q-radius); padding: 16px; }

/* ============================================
   Toast Notifications
   ============================================ */

/* Toast Container */
.q-toast-container { position: fixed; z-index: 9999; display: flex; flex-direction: column; gap: 8px; pointer-events: none; max-width: 400px; }
.q-toast-container.q-toast-top-right { top: 16px; right: 16px; }
.q-toast-container.q-toast-top-left { top: 16px; left: 16px; }
.q-toast-container.q-toast-bottom-right { bottom: 16px; right: 16px; }
.q-toast-container.q-toast-bottom-left { bottom: 16px; left: 16px; }
.q-toast-container.q-toast-top-center { top: 16px; left: 50%; transform: translateX(-50%); }
.q-toast-container.q-toast-bottom-center { bottom: 16px; left: 50%; transform: translateX(-50%); }

/* Toast */
.q-toast { display: flex; align-items: flex-start; gap: 12px; padding: 12px 16px; border-radius: var(--q-radius); box-shadow: 0 4px 12px rgba(0,0,0,0.15); pointer-events: auto; animation: q-toast-in 0.3s ease; background: var(--q-bg); border: 1px solid var(--q-border); }
.q-toast.q-toast-out { animation: q-toast-out 0.3s ease forwards; }
.q-toast-info { border-left: 4px solid var(--q-info); }
.q-toast-success { border-left: 4px solid var(--q-success); }
.q-toast-warning { border-left: 4px solid var(--q-warning); }
.q-toast-danger { border-left: 4px solid var(--q-danger); }
.q-toast-icon { flex-shrink: 0; font-size: var(--q-font-lg); }
.q-toast-info .q-toast-icon { color: var(--q-info); }
.q-toast-success .q-toast-icon { color: var(--q-success); }
.q-toast-warning .q-toast-icon { color: var(--q-warning); }
.q-toast-danger .q-toast-icon { color: var(--q-danger); }
.q-toast-content { flex: 1; min-width: 0; }
.q-toast-title { font-weight: 600; margin-bottom: 2px; }
.q-toast-message { font-size: var(--q-font-sm); color: var(--q-secondary); }
.q-toast-close { flex-shrink: 0; background: none; border: none; cursor: pointer; padding: 0; font-size: var(--q-font-lg); color: var(--q-secondary); opacity: 0.6; }
.q-toast-close:hover { opacity: 1; }
@keyframes q-toast-in { from { opacity: 0; transform: translateX(100%); } to { opacity: 1; transform: translateX(0); } }
@keyframes q-toast-out { from { opacity: 1; transform: translateX(0); } to { opacity: 0; transform: translateX(100%); } }

/* ============================================
   Carousel / Slider
   ============================================ */

.q-carousel { position: relative; overflow: hidden; border-radius: var(--q-radius); }
.q-carousel-track { display: flex; transition: transform 0.5s ease; }
.q-carousel.q-carousel-fade .q-carousel-track { display: block; }
.q-carousel-slide { flex: 0 0 100%; min-width: 100%; }
.q-carousel.q-carousel-fade .q-carousel-slide { position: absolute; top: 0; left: 0; width: 100%; opacity: 0; transition: opacity 0.5s ease; }
.q-carousel.q-carousel-fade .q-carousel-slide.active { position: relative; opacity: 1; }

/* Carousel Arrows */
.q-carousel-arrow { position: absolute; top: 50%; transform: translateY(-50%); background: rgba(0,0,0,0.5); color: white; border: none; width: 40px; height: 40px; border-radius: 50%; cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: var(--q-font-lg); z-index: 10; transition: background 0.2s; }
.q-carousel-arrow:hover { background: rgba(0,0,0,0.7); }
.q-carousel-arrow:disabled { opacity: 0.3; cursor: not-allowed; }
.q-carousel-prev { left: 12px; }
.q-carousel-next { right: 12px; }

/* Carousel Indicators */
.q-carousel-indicators { position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%); display: flex; gap: 8px; z-index: 10; }
.q-carousel-indicator { width: 10px; height: 10px; border-radius: 50%; background: rgba(255,255,255,0.5); border: none; cursor: pointer; transition: background 0.2s; }
.q-carousel-indicator.active { background: white; }
.q-carousel-indicator:hover { background: rgba(255,255,255,0.8); }

/* ============================================
   Stepper / Wizard
   ============================================ */

.q-stepper { display: flex; flex-direction: column; }
.q-stepper-horizontal .q-stepper-header { flex-direction: row; }
.q-stepper-vertical { flex-direction: row; }
.q-stepper-vertical .q-stepper-header { flex-direction: column; width: 200px; }
.q-stepper-vertical .q-stepper-content { flex: 1; }

/* Stepper Header */
.q-stepper-header { display: flex; gap: 0; margin-bottom: 24px; }
.q-stepper-horizontal .q-stepper-header { align-items: center; }

/* Step Item */
.q-step-item { display: flex; align-items: center; flex: 1; }
.q-stepper-vertical .q-step-item { flex-direction: column; align-items: flex-start; padding: 16px 0; }

/* Step Indicator */
.q-step-indicator { width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 600; font-size: var(--q-font-sm); background: var(--q-light); color: var(--q-secondary); border: 2px solid var(--q-border); flex-shrink: 0; transition: all 0.3s; }
.q-step-item.active .q-step-indicator { background: var(--q-primary); color: white; border-color: var(--q-primary); }
.q-step-item.completed .q-step-indicator { background: var(--q-success); color: white; border-color: var(--q-success); }
.q-step-item.error .q-step-indicator { background: var(--q-danger); color: white; border-color: var(--q-danger); }

/* Step Labels */
.q-step-labels { margin-left: 12px; }
.q-stepper-vertical .q-step-labels { margin-left: 0; margin-top: 8px; }
.q-step-title { font-weight: 500; color: var(--q-text); }
.q-step-item.active .q-step-title { color: var(--q-primary); }
.q-step-description { font-size: var(--q-font-sm); color: var(--q-secondary); margin-top: 2px; }
.q-step-optional { font-size: var(--q-font-xs); color: var(--q-secondary); font-style: italic; }

/* Step Connector */
.q-step-connector { flex: 1; height: 2px; background: var(--q-border); margin: 0 8px; }
.q-stepper-vertical .q-step-connector { width: 2px; height: 100%; min-height: 40px; margin: 0; margin-left: 15px; }
.q-step-item.completed + .q-step-item .q-step-connector,
.q-step-item.completed .q-step-connector { background: var(--q-success); }

/* Stepper Content */
.q-stepper-content { padding: 16px 0; }
.q-step-content { display: none; }
.q-step-content.active { display: block; animation: q-fade-in 0.3s ease; }

/* Stepper Actions */
.q-stepper-actions { display: flex; gap: 12px; justify-content: flex-end; padding-top: 16px; border-top: 1px solid var(--q-border); margin-top: 16px; }

/* ============================================
   Calendar / Date Picker
   ============================================ */

.q-calendar { background: var(--q-bg); border: 1px solid var(--q-border); border-radius: var(--q-radius); padding: 16px; width: 300px; }

/* Calendar Header */
.q-calendar-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.q-calendar-title { font-weight: 600; font-size: var(--q-font-md); }
.q-calendar-nav { display: flex; gap: 8px; }
.q-calendar-nav button { background: none; border: 1px solid var(--q-border); border-radius: var(--q-radius); width: 28px; height: 28px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.q-calendar-nav button:hover { background: var(--q-light); }

/* Calendar Grid */
.q-calendar-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 2px; }
.q-calendar-weekday { text-align: center; font-size: var(--q-font-xs); font-weight: 600; color: var(--q-secondary); padding: 8px 0; }

/* Calendar Days */
.q-calendar-day { text-align: center; padding: 8px 0; font-size: var(--q-font-sm); border-radius: var(--q-radius); cursor: pointer; transition: all 0.15s; }
.q-calendar-day:hover { background: var(--q-light); }
.q-calendar-day.today { font-weight: 600; color: var(--q-primary); }
.q-calendar-day.selected { background: var(--q-primary); color: white; }
.q-calendar-day.in-range { background: rgba(59,130,246,0.15); }
.q-calendar-day.range-start { background: var(--q-primary); color: white; border-radius: var(--q-radius) 0 0 var(--q-radius); }
.q-calendar-day.range-end { background: var(--q-primary); color: white; border-radius: 0 var(--q-radius) var(--q-radius) 0; }
.q-calendar-day.other-month { color: var(--q-secondary); opacity: 0.5; }
.q-calendar-day.disabled { color: var(--q-secondary); opacity: 0.3; cursor: not-allowed; pointer-events: none; }
.q-calendar-day.week-number { font-size: var(--q-font-xs); color: var(--q-secondary); cursor: default; }
.q-calendar-day.week-number:hover { background: none; }

/* Date Picker (Input + Calendar popup) */
.q-date-picker { position: relative; }
.q-date-picker-input { width: 100%; padding: 8px 12px; padding-right: 36px; border: 1px solid var(--q-border); border-radius: var(--q-radius); }
.q-date-picker-input:focus { border-color: var(--q-primary); outline: none; box-shadow: 0 0 0 3px rgba(59,130,246,0.15); }
.q-date-picker-icon { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); color: var(--q-secondary); pointer-events: none; }
.q-date-picker-clear { position: absolute; right: 32px; top: 50%; transform: translateY(-50%); background: none; border: none; color: var(--q-secondary); cursor: pointer; padding: 4px; }
.q-date-picker-clear:hover { color: var(--q-text); }
.q-date-picker-dropdown { position: absolute; top: 100%; left: 0; margin-top: 4px; z-index: 100; box-shadow: 0 4px 12px rgba(0,0,0,0.15); display: none; }
.q-date-picker-dropdown.open { display: block; animation: q-fade-in 0.2s ease; }
"""


# ==========================================================================
# CSS Animations
# ==========================================================================

CSS_ANIMATIONS = """\
/* ============================================
   Quantum UI Animation System
   ============================================ */

/* Animation container base */
.q-animate {
  will-change: transform, opacity;
}

/* Animation variables (customizable via inline styles) */
.q-animate {
  --q-anim-duration: 300ms;
  --q-anim-delay: 0ms;
  --q-anim-easing: ease;
  --q-anim-repeat: 1;
  --q-anim-direction: normal;
}

/* ----------------------------------------
   Fade Animations
   ---------------------------------------- */
@keyframes q-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes q-fade-out {
  from { opacity: 1; }
  to { opacity: 0; }
}

.q-anim-fade-in,
.q-anim-fade {
  animation: q-fade-in var(--q-anim-duration) var(--q-anim-easing) var(--q-anim-delay) var(--q-anim-repeat) var(--q-anim-direction) both;
}

.q-anim-fade-out {
  animation: q-fade-out var(--q-anim-duration) var(--q-anim-easing) var(--q-anim-delay) var(--q-anim-repeat) var(--q-anim-direction) both;
}

/* ----------------------------------------
   Slide Animations
   ---------------------------------------- */
@keyframes q-slide-in-left {
  from { transform: translateX(-100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes q-slide-in-right {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}

@keyframes q-slide-in-up {
  from { transform: translateY(100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

@keyframes q-slide-in-down {
  from { transform: translateY(-100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

.q-anim-slide,
.q-anim-slide-left,
.q-anim-slide-in-left {
  animation: q-slide-in-left var(--q-anim-duration) var(--q-anim-easing) var(--q-anim-delay) var(--q-anim-repeat) var(--q-anim-direction) both;
}

.q-anim-slide-right,
.q-anim-slide-in-right {
  animation: q-slide-in-right var(--q-anim-duration) var(--q-anim-easing) var(--q-anim-delay) var(--q-anim-repeat) var(--q-anim-direction) both;
}

.q-anim-slide-up,
.q-anim-slide-in-up {
  animation: q-slide-in-up var(--q-anim-duration) var(--q-anim-easing) var(--q-anim-delay) var(--q-anim-repeat) var(--q-anim-direction) both;
}

.q-anim-slide-down,
.q-anim-slide-in-down {
  animation: q-slide-in-down var(--q-anim-duration) var(--q-anim-easing) var(--q-anim-delay) var(--q-anim-repeat) var(--q-anim-direction) both;
}

/* ----------------------------------------
   Scale Animations
   ---------------------------------------- */
@keyframes q-scale-in {
  from { transform: scale(0); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}

@keyframes q-scale-out {
  from { transform: scale(1); opacity: 1; }
  to { transform: scale(0); opacity: 0; }
}

.q-anim-scale,
.q-anim-scale-in {
  animation: q-scale-in var(--q-anim-duration) var(--q-anim-easing) var(--q-anim-delay) var(--q-anim-repeat) var(--q-anim-direction) both;
}

.q-anim-scale-out {
  animation: q-scale-out var(--q-anim-duration) var(--q-anim-easing) var(--q-anim-delay) var(--q-anim-repeat) var(--q-anim-direction) both;
}

/* ----------------------------------------
   Rotate Animations
   ---------------------------------------- */
@keyframes q-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@keyframes q-rotate-in {
  from { transform: rotate(-180deg); opacity: 0; }
  to { transform: rotate(0deg); opacity: 1; }
}

.q-anim-rotate {
  animation: q-rotate var(--q-anim-duration) var(--q-anim-easing) var(--q-anim-delay) var(--q-anim-repeat) var(--q-anim-direction) both;
}

.q-anim-rotate-in {
  animation: q-rotate-in var(--q-anim-duration) var(--q-anim-easing) var(--q-anim-delay) var(--q-anim-repeat) var(--q-anim-direction) both;
}

/* ----------------------------------------
   Bounce Animation
   ---------------------------------------- */
@keyframes q-bounce {
  0%, 20%, 53%, 100% {
    animation-timing-function: cubic-bezier(0.215, 0.61, 0.355, 1);
    transform: translateY(0);
  }
  40%, 43% {
    animation-timing-function: cubic-bezier(0.755, 0.05, 0.855, 0.06);
    transform: translateY(-30px);
  }
  70% {
    animation-timing-function: cubic-bezier(0.755, 0.05, 0.855, 0.06);
    transform: translateY(-15px);
  }
  80% {
    transform: translateY(0);
  }
  90% {
    transform: translateY(-4px);
  }
}

.q-anim-bounce {
  animation: q-bounce var(--q-anim-duration) var(--q-anim-easing) var(--q-anim-delay) var(--q-anim-repeat) var(--q-anim-direction) both;
  transform-origin: center bottom;
}

/* ----------------------------------------
   Pulse Animation
   ---------------------------------------- */
@keyframes q-pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

.q-anim-pulse {
  animation: q-pulse var(--q-anim-duration) var(--q-anim-easing) var(--q-anim-delay) var(--q-anim-repeat) var(--q-anim-direction) both;
}

/* ----------------------------------------
   Shake Animation
   ---------------------------------------- */
@keyframes q-shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-5px); }
  20%, 40%, 60%, 80% { transform: translateX(5px); }
}

.q-anim-shake {
  animation: q-shake var(--q-anim-duration) var(--q-anim-easing) var(--q-anim-delay) var(--q-anim-repeat) var(--q-anim-direction) both;
}

/* ----------------------------------------
   Trigger States
   ---------------------------------------- */
/* on-load: Play immediately (default) */
.q-trigger-on-load {
  /* Animation plays on page load by default */
}

/* on-hover: Play on mouse hover */
.q-trigger-on-hover {
  animation-play-state: paused;
}
.q-trigger-on-hover:hover {
  animation-play-state: running;
}

/* on-click: Play on click (requires JS) */
.q-trigger-on-click {
  animation-play-state: paused;
}
.q-trigger-on-click.q-anim-active {
  animation-play-state: running;
}

/* on-visible: Play when visible (requires IntersectionObserver JS) */
.q-trigger-on-visible {
  animation-play-state: paused;
}
.q-trigger-on-visible.q-anim-visible {
  animation-play-state: running;
}

/* ----------------------------------------
   Transition Effects (for inline use)
   ---------------------------------------- */
.q-transition {
  transition-property: transform, opacity;
  transition-duration: var(--q-anim-duration);
  transition-timing-function: var(--q-anim-easing);
  transition-delay: var(--q-anim-delay);
}

/* Common transition presets */
.q-transition-scale:hover {
  transform: scale(var(--q-transition-scale, 1.05));
}

.q-transition-scale:active {
  transform: scale(var(--q-transition-scale-active, 0.95));
}

.q-transition-fade:hover {
  opacity: var(--q-transition-opacity, 0.8);
}

.q-transition-lift:hover {
  transform: translateY(var(--q-transition-lift, -2px));
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

/* ----------------------------------------
   Easing Functions
   ---------------------------------------- */
.q-easing-linear { --q-anim-easing: linear; }
.q-easing-ease { --q-anim-easing: ease; }
.q-easing-ease-in { --q-anim-easing: ease-in; }
.q-easing-ease-out { --q-anim-easing: ease-out; }
.q-easing-ease-in-out { --q-anim-easing: ease-in-out; }
.q-easing-spring { --q-anim-easing: cubic-bezier(0.175, 0.885, 0.32, 1.275); }
.q-easing-bounce { --q-anim-easing: cubic-bezier(0.68, -0.55, 0.265, 1.55); }

/* ----------------------------------------
   Reduced Motion Support
   ---------------------------------------- */
@media (prefers-reduced-motion: reduce) {
  .q-animate,
  .q-transition,
  [class*="q-anim-"] {
    animation: none !important;
    transition: none !important;
  }
}
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


# ==========================================================================
# Animation JS
# ==========================================================================

ANIMATION_JS = """\
<script>
// Quantum UI Animation Manager
window.__quantumAnimate = (function() {
    'use strict';

    // IntersectionObserver for on-visible trigger
    var visibilityObserver = null;

    function initVisibilityObserver() {
        if (visibilityObserver) return;
        if (typeof IntersectionObserver === 'undefined') {
            console.warn('IntersectionObserver not supported; on-visible trigger disabled');
            return;
        }

        visibilityObserver = new IntersectionObserver(function(entries) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('q-anim-visible');
                    // Optionally unobserve after first trigger
                    if (entry.target.dataset.animOnce !== 'false') {
                        visibilityObserver.unobserve(entry.target);
                    }
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });
    }

    function setupClickTriggers() {
        document.querySelectorAll('.q-trigger-on-click').forEach(function(el) {
            el.addEventListener('click', function() {
                // Remove and re-add animation class to restart
                var classes = this.className.match(/q-anim-[\\w-]+/g) || [];
                var self = this;
                classes.forEach(function(cls) {
                    self.classList.remove(cls);
                });
                // Force reflow
                void this.offsetWidth;
                classes.forEach(function(cls) {
                    self.classList.add(cls);
                });
                this.classList.add('q-anim-active');
            });

            // Remove active class when animation ends
            el.addEventListener('animationend', function() {
                this.classList.remove('q-anim-active');
            });
        });
    }

    function setupVisibilityTriggers() {
        initVisibilityObserver();
        if (!visibilityObserver) return;

        document.querySelectorAll('.q-trigger-on-visible').forEach(function(el) {
            visibilityObserver.observe(el);
        });
    }

    function parseTransition(transitionStr) {
        // Parse transition shorthand: "scale:0.95:100ms" or "scale:0.95"
        if (!transitionStr) return null;
        var parts = transitionStr.split(':');
        return {
            type: parts[0] || 'scale',
            value: parts[1] || '0.95',
            duration: parts[2] || '150ms'
        };
    }

    function applyTransition(el, transitionStr) {
        var t = parseTransition(transitionStr);
        if (!t) return;

        el.classList.add('q-transition');
        el.style.setProperty('--q-anim-duration', t.duration);

        if (t.type === 'scale') {
            el.style.setProperty('--q-transition-scale', t.value);
            el.classList.add('q-transition-scale');
        } else if (t.type === 'fade') {
            el.style.setProperty('--q-transition-opacity', t.value);
            el.classList.add('q-transition-fade');
        } else if (t.type === 'lift') {
            el.style.setProperty('--q-transition-lift', t.value);
            el.classList.add('q-transition-lift');
        }
    }

    function setupTransitions() {
        document.querySelectorAll('[data-transition]').forEach(function(el) {
            applyTransition(el, el.dataset.transition);
        });
    }

    // Initialize all animation triggers
    function init() {
        setupClickTriggers();
        setupVisibilityTriggers();
        setupTransitions();
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Public API
    return {
        init: init,
        parseTransition: parseTransition,
        applyTransition: applyTransition,

        // Programmatically trigger animation on element
        trigger: function(el, animationType) {
            if (typeof el === 'string') {
                el = document.querySelector(el);
            }
            if (!el) return;

            // Remove existing animation classes
            var classes = el.className.match(/q-anim-[\\w-]+/g) || [];
            classes.forEach(function(cls) {
                el.classList.remove(cls);
            });

            // Force reflow
            void el.offsetWidth;

            // Add new animation
            if (animationType) {
                el.classList.add('q-anim-' + animationType);
            }
        },

        // Reset animation (for replay)
        reset: function(el) {
            if (typeof el === 'string') {
                el = document.querySelector(el);
            }
            if (!el) return;

            var classes = el.className.match(/q-anim-[\\w-]+/g) || [];
            classes.forEach(function(cls) {
                el.classList.remove(cls);
            });
            el.classList.remove('q-anim-active', 'q-anim-visible');
            void el.offsetWidth; // Force reflow
        }
    };
})();
</script>
"""


# ==========================================================================
# State Persistence JS
# ==========================================================================

PERSISTENCE_JS = """\
<script>
// Quantum State Persistence Manager
window.__quantumPersist = (function() {
    'use strict';

    // Storage backends
    var backends = {
        local: {
            get: function(key) {
                try {
                    var item = localStorage.getItem(key);
                    if (item) {
                        var data = JSON.parse(item);
                        // Check TTL expiration
                        if (data._ttl && Date.now() > data._ttl) {
                            localStorage.removeItem(key);
                            return null;
                        }
                        return data.value;
                    }
                } catch (e) { console.warn('Persist local get error:', e); }
                return null;
            },
            set: function(key, value, options) {
                try {
                    var data = { value: value };
                    if (options && options.ttl) {
                        data._ttl = Date.now() + (options.ttl * 1000);
                    }
                    localStorage.setItem(key, JSON.stringify(data));
                    return true;
                } catch (e) { console.warn('Persist local set error:', e); }
                return false;
            },
            remove: function(key) {
                try {
                    localStorage.removeItem(key);
                    return true;
                } catch (e) { return false; }
            }
        },
        session: {
            get: function(key) {
                try {
                    var item = sessionStorage.getItem(key);
                    if (item) {
                        var data = JSON.parse(item);
                        return data.value;
                    }
                } catch (e) { console.warn('Persist session get error:', e); }
                return null;
            },
            set: function(key, value, options) {
                try {
                    sessionStorage.setItem(key, JSON.stringify({ value: value }));
                    return true;
                } catch (e) { console.warn('Persist session set error:', e); }
                return false;
            },
            remove: function(key) {
                try {
                    sessionStorage.removeItem(key);
                    return true;
                } catch (e) { return false; }
            }
        },
        sync: {
            // Cross-tab synchronization using localStorage + BroadcastChannel
            _channel: null,
            _listeners: {},
            _init: function() {
                if (this._channel) return;
                if (typeof BroadcastChannel !== 'undefined') {
                    this._channel = new BroadcastChannel('quantum_persist_sync');
                    var self = this;
                    this._channel.onmessage = function(e) {
                        if (e.data && e.data.type === 'sync' && self._listeners[e.data.key]) {
                            self._listeners[e.data.key].forEach(function(cb) {
                                cb(e.data.value);
                            });
                        }
                    };
                }
            },
            get: function(key) {
                return backends.local.get('__qsync_' + key);
            },
            set: function(key, value, options) {
                this._init();
                var result = backends.local.set('__qsync_' + key, value, options);
                if (result && this._channel) {
                    this._channel.postMessage({ type: 'sync', key: key, value: value });
                }
                return result;
            },
            remove: function(key) {
                return backends.local.remove('__qsync_' + key);
            },
            subscribe: function(key, callback) {
                this._init();
                if (!this._listeners[key]) {
                    this._listeners[key] = [];
                }
                this._listeners[key].push(callback);
            }
        }
    };

    // Registered persisted variables
    var registry = {};

    return {
        // Register a variable for persistence
        register: function(name, scope, options) {
            options = options || {};
            registry[name] = {
                scope: scope || 'local',
                key: options.key || name,
                encrypt: options.encrypt || false,
                ttl: options.ttl || null,
                prefix: options.prefix || '__qp_'
            };
        },

        // Get storage key for a variable
        getKey: function(name) {
            var reg = registry[name];
            if (!reg) return '__qp_' + name;
            return reg.prefix + reg.key;
        },

        // Save value to persistent storage
        save: function(name, value) {
            var reg = registry[name];
            if (!reg) return false;
            var backend = backends[reg.scope] || backends.local;
            var key = this.getKey(name);
            return backend.set(key, value, { ttl: reg.ttl });
        },

        // Load value from persistent storage
        load: function(name) {
            var reg = registry[name];
            if (!reg) return null;
            var backend = backends[reg.scope] || backends.local;
            var key = this.getKey(name);
            return backend.get(key);
        },

        // Remove persisted value
        remove: function(name) {
            var reg = registry[name];
            if (!reg) return false;
            var backend = backends[reg.scope] || backends.local;
            var key = this.getKey(name);
            return backend.remove(key);
        },

        // Subscribe to sync updates (for sync scope)
        subscribe: function(name, callback) {
            var reg = registry[name];
            if (reg && reg.scope === 'sync') {
                backends.sync.subscribe(reg.key, callback);
            }
        },

        // Check if variable is registered for persistence
        isPersisted: function(name) {
            return !!registry[name];
        },

        // Get all registered variables
        getRegistry: function() {
            return Object.assign({}, registry);
        }
    };
})();

// Integration with QuantumState (if available)
if (typeof window.__quantumStateUpdate !== 'undefined') {
    var originalUpdate = window.__quantumStateUpdate;
    window.__quantumStateUpdate = function(name, value) {
        // Call original handler
        originalUpdate(name, value);
        // Auto-persist if registered
        if (window.__quantumPersist.isPersisted(name)) {
            window.__quantumPersist.save(name, value);
        }
    };
}
</script>
"""


# ==========================================================================
# Persistence Registration Helper
# ==========================================================================

def generate_persistence_registration(persisted_vars: list) -> str:
    """Generate JS code to register persisted variables.

    Args:
        persisted_vars: List of dicts with keys: name, scope, key, ttl, encrypt, prefix

    Returns:
        JavaScript code to register variables for persistence.
    """
    if not persisted_vars:
        return ''

    lines = ['<script>', 'document.addEventListener("DOMContentLoaded", function() {']

    for var in persisted_vars:
        name = var.get('name', '')
        scope = var.get('scope', 'local')
        key = var.get('key') or name
        ttl = var.get('ttl')
        encrypt = 'true' if var.get('encrypt') else 'false'
        prefix = var.get('prefix', '__qp_')

        options_parts = [
            f"key: '{key}'",
            f"encrypt: {encrypt}",
            f"prefix: '{prefix}'"
        ]
        if ttl:
            options_parts.append(f"ttl: {ttl}")

        options_str = ', '.join(options_parts)
        lines.append(f"  window.__quantumPersist.register('{name}', '{scope}', {{{options_str}}});")

        # Restore persisted value on load
        lines.append(f"  var __pv_{name} = window.__quantumPersist.load('{name}');")
        lines.append(f"  if (__pv_{name} !== null && typeof window.__quantumStateUpdate === 'function') {{")
        lines.append(f"    window.__quantumStateUpdate('{name}', __pv_{name});")
        lines.append(f"  }}")

    lines.append('});')
    lines.append('</script>')
    return '\n'.join(lines)


# ==========================================================================
# Form Validation CSS
# ==========================================================================

VALIDATION_CSS = """\
/* ============================================
   Quantum UI Form Validation Styles
   ============================================ */

/* Input wrapper for validation */
.q-input-wrapper {
  position: relative;
  width: 100%;
}

/* Error message display */
.q-error-message {
  color: var(--q-danger);
  font-size: var(--q-font-sm);
  margin-top: 4px;
  min-height: 1.2em;
}

/* Validation summary */
.q-validation-summary {
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid var(--q-danger);
  border-radius: var(--q-radius);
  padding: 12px 16px;
  margin-bottom: 16px;
}

.q-validation-summary ul {
  margin: 0;
  padding-left: 20px;
}

.q-validation-summary li {
  color: var(--q-danger);
  font-size: var(--q-font-sm);
}

/* Input states */
.q-input.q-invalid,
.q-input:invalid:not(:placeholder-shown) {
  border-color: var(--q-danger);
}

.q-input.q-invalid:focus,
.q-input:invalid:not(:placeholder-shown):focus {
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15);
}

.q-input.q-valid,
.q-input:valid:not(:placeholder-shown) {
  border-color: var(--q-success);
}

.q-input.q-valid:focus,
.q-input:valid:not(:placeholder-shown):focus {
  box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.15);
}

/* Required field indicator */
.q-formitem-label.q-required::after {
  content: " *";
  color: var(--q-danger);
}

/* Shake animation for invalid fields */
@keyframes q-shake-invalid {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-4px); }
  20%, 40%, 60%, 80% { transform: translateX(4px); }
}

.q-input.q-shake {
  animation: q-shake-invalid 0.4s ease-in-out;
}
"""


# ==========================================================================
# Form Validation JS
# ==========================================================================

VALIDATION_JS = """\
<script>
// Quantum UI Form Validation System
window.__qValidation = (function() {
    'use strict';

    // Registered custom validators per form
    var formValidators = {};

    // Built-in validation types
    var builtInTypes = {
        email: /^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$/,
        url: /^https?:\\/\\/[\\w\\-]+(\\.[\\w\\-]+)+[/#?]?.*$/,
        phone: /^[\\+]?[(]?[0-9]{1,3}[)]?[-\\s\\.]?[0-9]{1,4}[-\\s\\.]?[0-9]{4,6}$/,
        alphanumeric: /^[a-zA-Z0-9]+$/,
        alpha: /^[a-zA-Z]+$/,
        numeric: /^[0-9]+$/,
        integer: /^-?[0-9]+$/,
        decimal: /^-?[0-9]+(\\.[0-9]+)?$/
    };

    // Default error messages
    var defaultMessages = {
        required: 'This field is required',
        email: 'Please enter a valid email address',
        url: 'Please enter a valid URL',
        phone: 'Please enter a valid phone number',
        pattern: 'Please match the required format',
        minlength: 'Please enter at least {0} characters',
        maxlength: 'Please enter no more than {0} characters',
        min: 'Please enter a value greater than or equal to {0}',
        max: 'Please enter a value less than or equal to {0}',
        match: 'Fields do not match'
    };

    // Format message with parameters
    function formatMessage(template, params) {
        if (!params) return template;
        if (!Array.isArray(params)) params = [params];
        return template.replace(/\\{(\\d+)\\}/g, function(match, index) {
            return typeof params[index] !== 'undefined' ? params[index] : match;
        });
    }

    // Show error for an input
    function showError(input, message) {
        input.classList.add('q-invalid');
        input.classList.remove('q-valid');

        var errorEl = document.getElementById(input.id + '-error');
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }

        // Shake animation
        input.classList.add('q-shake');
        setTimeout(function() {
            input.classList.remove('q-shake');
        }, 400);
    }

    // Clear error for an input
    function clearError(input) {
        input.classList.remove('q-invalid');
        input.classList.add('q-valid');

        var errorEl = document.getElementById(input.id + '-error');
        if (errorEl) {
            errorEl.style.display = 'none';
        }
    }

    // Validate a single input
    function validateInput(input, form) {
        var value = input.value;
        var customMessage = input.dataset.errorMessage;

        // Required validation
        if (input.hasAttribute('required') && !value.trim()) {
            showError(input, customMessage || defaultMessages.required);
            return false;
        }

        // Skip other validations if empty and not required
        if (!value.trim()) {
            clearError(input);
            return true;
        }

        // Type validation
        var inputType = input.type;
        if (inputType === 'email' && builtInTypes.email && !builtInTypes.email.test(value)) {
            showError(input, customMessage || defaultMessages.email);
            return false;
        }

        if (inputType === 'url' && builtInTypes.url && !builtInTypes.url.test(value)) {
            showError(input, customMessage || defaultMessages.url);
            return false;
        }

        // Pattern validation
        var pattern = input.getAttribute('pattern');
        if (pattern) {
            var regex = new RegExp('^' + pattern + '$');
            if (!regex.test(value)) {
                showError(input, customMessage || defaultMessages.pattern);
                return false;
            }
        }

        // Min/Max length validation
        var minlength = input.getAttribute('minlength');
        if (minlength && value.length < parseInt(minlength, 10)) {
            showError(input, customMessage || formatMessage(defaultMessages.minlength, minlength));
            return false;
        }

        var maxlength = input.getAttribute('maxlength');
        if (maxlength && value.length > parseInt(maxlength, 10)) {
            showError(input, customMessage || formatMessage(defaultMessages.maxlength, maxlength));
            return false;
        }

        // Min/Max value validation (for number inputs)
        if (inputType === 'number') {
            var numValue = parseFloat(value);
            var min = input.getAttribute('min');
            if (min !== null && numValue < parseFloat(min)) {
                showError(input, customMessage || formatMessage(defaultMessages.min, min));
                return false;
            }

            var max = input.getAttribute('max');
            if (max !== null && numValue > parseFloat(max)) {
                showError(input, customMessage || formatMessage(defaultMessages.max, max));
                return false;
            }
        }

        // Custom validators
        var customValidators = input.dataset.validators;
        if (customValidators && form) {
            var formId = form.id;
            var validators = formValidators[formId] || [];
            var validatorNames = customValidators.split(',').map(function(s) { return s.trim(); });

            for (var i = 0; i < validatorNames.length; i++) {
                var validatorName = validatorNames[i];
                var validator = validators.find(function(v) { return v.name === validatorName; });
                if (validator) {
                    var result = runValidator(validator, value, form);
                    if (!result.valid) {
                        showError(input, result.message || customMessage || 'Validation failed');
                        return false;
                    }
                }
            }
        }

        clearError(input);
        return true;
    }

    // Run a custom validator
    function runValidator(validator, value, form) {
        // Pattern validation
        if (validator.pattern) {
            var regex = new RegExp(validator.pattern);
            if (!regex.test(value)) {
                return { valid: false, message: validator.message };
            }
        }

        // Type-based validation
        if (validator.type && builtInTypes[validator.type]) {
            if (!builtInTypes[validator.type].test(value)) {
                return { valid: false, message: validator.message || defaultMessages[validator.type] };
            }
        }

        // Match validation (compare to another field)
        if (validator.match && form) {
            var otherInput = form.querySelector('[name="' + validator.match + '"]');
            if (otherInput && value !== otherInput.value) {
                return { valid: false, message: validator.message || defaultMessages.match };
            }
        }

        // Min/Max validation
        if (validator.minlength && value.length < validator.minlength) {
            return { valid: false, message: validator.message || formatMessage(defaultMessages.minlength, validator.minlength) };
        }
        if (validator.maxlength && value.length > validator.maxlength) {
            return { valid: false, message: validator.message || formatMessage(defaultMessages.maxlength, validator.maxlength) };
        }

        // Custom expression
        if (typeof validator.expression === 'function') {
            try {
                var result = validator.expression(value, form);
                if (!result) {
                    return { valid: false, message: validator.message };
                }
            } catch (e) {
                console.warn('Validator expression error:', e);
                return { valid: false, message: 'Validation error' };
            }
        }

        return { valid: true };
    }

    // Validate entire form
    function validateForm(formId) {
        var form = document.getElementById(formId);
        if (!form) return true;

        var inputs = form.querySelectorAll('input, select, textarea');
        var allValid = true;
        var errors = [];

        inputs.forEach(function(input) {
            if (input.id && !validateInput(input, form)) {
                allValid = false;
                var errorEl = document.getElementById(input.id + '-error');
                if (errorEl) {
                    errors.push(errorEl.textContent);
                }
            }
        });

        // Form-level validators (not tied to specific fields)
        var formLevelValidators = (formValidators[formId] || []).filter(function(v) {
            return v.field;
        });

        formLevelValidators.forEach(function(validator) {
            var targetInput = form.querySelector('[name="' + validator.field + '"]');
            if (targetInput) {
                var result = runValidator(validator, targetInput.value, form);
                if (!result.valid) {
                    showError(targetInput, result.message);
                    allValid = false;
                    errors.push(result.message);
                }
            }
        });

        // Update validation summary if present
        var summaryEl = document.getElementById(formId + '-summary');
        if (summaryEl) {
            if (errors.length > 0) {
                var ul = '<ul>' + errors.map(function(e) { return '<li>' + e + '</li>'; }).join('') + '</ul>';
                summaryEl.innerHTML = ul;
                summaryEl.style.display = 'block';
            } else {
                summaryEl.style.display = 'none';
            }
        }

        return allValid;
    }

    // Setup real-time validation on blur/input
    function setupRealtimeValidation() {
        document.addEventListener('blur', function(e) {
            var input = e.target;
            if (input.matches && input.matches('input, select, textarea')) {
                var form = input.closest('form');
                if (form && form.dataset.validation) {
                    validateInput(input, form);
                }
            }
        }, true);

        document.addEventListener('input', function(e) {
            var input = e.target;
            if (input.matches && input.matches('input, select, textarea') && input.classList.contains('q-invalid')) {
                var form = input.closest('form');
                if (form && form.dataset.validation) {
                    validateInput(input, form);
                }
            }
        }, true);
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setupRealtimeValidation);
    } else {
        setupRealtimeValidation();
    }

    // Public API
    return {
        validateForm: validateForm,
        validateInput: validateInput,
        showError: showError,
        clearError: clearError,
        registerValidator: function(formId, validator) {
            if (!formValidators[formId]) {
                formValidators[formId] = [];
            }
            formValidators[formId].push(validator);
        },
        addValidationType: function(name, regex, defaultMessage) {
            builtInTypes[name] = regex;
            if (defaultMessage) {
                defaultMessages[name] = defaultMessage;
            }
        }
    };
})();
</script>
"""


# ==========================================================================
# Toast Notification JS
# ==========================================================================

TOAST_JS = """\
<script>
// Quantum UI Toast Notification System
window.__quantumToast = (function() {
    'use strict';

    var containers = {};
    var toastId = 0;

    // Icons for variants
    var icons = {
        info: '&#9432;',
        success: '&#10003;',
        warning: '&#9888;',
        danger: '&#10007;'
    };

    // Get or create container for position
    function getContainer(position) {
        if (containers[position]) return containers[position];

        var container = document.createElement('div');
        container.className = 'q-toast-container q-toast-' + position;
        document.body.appendChild(container);
        containers[position] = container;
        return container;
    }

    // Create toast element
    function createToast(options) {
        var id = 'toast-' + (++toastId);
        var toast = document.createElement('div');
        toast.id = id;
        toast.className = 'q-toast q-toast-' + (options.variant || 'info');

        var html = '';

        // Icon
        if (options.icon !== false) {
            html += '<span class="q-toast-icon">' + (options.icon || icons[options.variant] || icons.info) + '</span>';
        }

        // Content
        html += '<div class="q-toast-content">';
        if (options.title) {
            html += '<div class="q-toast-title">' + options.title + '</div>';
        }
        html += '<div class="q-toast-message">' + (options.message || '') + '</div>';
        html += '</div>';

        // Close button
        if (options.dismissible !== false) {
            html += '<button class="q-toast-close" onclick="__quantumToast.dismiss(\'' + id + '\')">&times;</button>';
        }

        toast.innerHTML = html;
        return toast;
    }

    // Show toast
    function show(options) {
        var position = options.position || 'top-right';
        var container = getContainer(position);
        var toast = createToast(options);

        container.appendChild(toast);

        // Auto dismiss
        var duration = options.duration !== undefined ? options.duration : 3000;
        if (duration > 0) {
            setTimeout(function() {
                dismiss(toast.id);
            }, duration);
        }

        return toast.id;
    }

    // Dismiss toast
    function dismiss(id) {
        var toast = document.getElementById(id);
        if (!toast) return;

        toast.classList.add('q-toast-out');
        setTimeout(function() {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    // Dismiss all toasts
    function dismissAll() {
        Object.keys(containers).forEach(function(pos) {
            var container = containers[pos];
            var toasts = container.querySelectorAll('.q-toast');
            toasts.forEach(function(t) { dismiss(t.id); });
        });
    }

    // Shorthand methods
    function info(message, options) {
        return show(Object.assign({ message: message, variant: 'info' }, options || {}));
    }

    function success(message, options) {
        return show(Object.assign({ message: message, variant: 'success' }, options || {}));
    }

    function warning(message, options) {
        return show(Object.assign({ message: message, variant: 'warning' }, options || {}));
    }

    function danger(message, options) {
        return show(Object.assign({ message: message, variant: 'danger' }, options || {}));
    }

    return {
        show: show,
        dismiss: dismiss,
        dismissAll: dismissAll,
        info: info,
        success: success,
        warning: warning,
        danger: danger,
        error: danger  // alias
    };
})();
</script>
"""


# ==========================================================================
# Carousel JS
# ==========================================================================

CAROUSEL_JS = """\
<script>
// Quantum UI Carousel System
window.__quantumCarousel = (function() {
    'use strict';

    var carousels = {};

    function init(id, options) {
        var carousel = document.getElementById(id);
        if (!carousel) return;

        options = options || {};
        var track = carousel.querySelector('.q-carousel-track');
        var slides = carousel.querySelectorAll('.q-carousel-slide');
        var indicators = carousel.querySelectorAll('.q-carousel-indicator');
        var prevBtn = carousel.querySelector('.q-carousel-prev');
        var nextBtn = carousel.querySelector('.q-carousel-next');

        var state = {
            current: options.current || 0,
            total: slides.length,
            autoPlay: options.autoPlay || false,
            interval: options.interval || 5000,
            loop: options.loop !== false,
            animation: options.animation || 'slide',
            timer: null
        };

        carousels[id] = state;

        function goTo(index) {
            if (index < 0) {
                index = state.loop ? state.total - 1 : 0;
            } else if (index >= state.total) {
                index = state.loop ? 0 : state.total - 1;
            }

            state.current = index;

            if (state.animation === 'slide') {
                track.style.transform = 'translateX(-' + (index * 100) + '%)';
            } else {
                // Fade animation
                slides.forEach(function(s, i) {
                    s.classList.toggle('active', i === index);
                });
            }

            // Update indicators
            indicators.forEach(function(ind, i) {
                ind.classList.toggle('active', i === index);
            });

            // Update arrow states if not looping
            if (!state.loop) {
                if (prevBtn) prevBtn.disabled = index === 0;
                if (nextBtn) nextBtn.disabled = index === state.total - 1;
            }

            // Callback
            if (options.onChange) {
                options.onChange(index);
            }
        }

        function next() {
            goTo(state.current + 1);
        }

        function prev() {
            goTo(state.current - 1);
        }

        function startAutoPlay() {
            if (state.timer) clearInterval(state.timer);
            state.timer = setInterval(next, state.interval);
        }

        function stopAutoPlay() {
            if (state.timer) {
                clearInterval(state.timer);
                state.timer = null;
            }
        }

        // Event listeners
        if (prevBtn) prevBtn.addEventListener('click', prev);
        if (nextBtn) nextBtn.addEventListener('click', next);

        indicators.forEach(function(ind, i) {
            ind.addEventListener('click', function() { goTo(i); });
        });

        // Pause on hover
        carousel.addEventListener('mouseenter', stopAutoPlay);
        carousel.addEventListener('mouseleave', function() {
            if (state.autoPlay) startAutoPlay();
        });

        // Initialize
        goTo(state.current);
        if (state.autoPlay) startAutoPlay();

        return {
            goTo: goTo,
            next: next,
            prev: prev,
            startAutoPlay: startAutoPlay,
            stopAutoPlay: stopAutoPlay,
            getCurrent: function() { return state.current; }
        };
    }

    return { init: init, get: function(id) { return carousels[id]; } };
})();
</script>
"""


# ==========================================================================
# Stepper JS
# ==========================================================================

STEPPER_JS = """\
<script>
// Quantum UI Stepper System
window.__quantumStepper = (function() {
    'use strict';

    var steppers = {};

    function init(id, options) {
        var stepper = document.getElementById(id);
        if (!stepper) return;

        options = options || {};
        var steps = stepper.querySelectorAll('.q-step-item');
        var contents = stepper.querySelectorAll('.q-step-content');

        var state = {
            current: options.current || 0,
            total: steps.length,
            linear: options.linear !== false,
            completed: []
        };

        steppers[id] = state;

        function updateUI() {
            steps.forEach(function(step, i) {
                step.classList.remove('active', 'completed');
                if (i === state.current) {
                    step.classList.add('active');
                } else if (state.completed.indexOf(i) !== -1) {
                    step.classList.add('completed');
                }
            });

            contents.forEach(function(content, i) {
                content.classList.toggle('active', i === state.current);
            });
        }

        function canGoTo(index) {
            if (!state.linear) return true;
            // In linear mode, can only go to completed steps or current+1
            if (index <= state.current) return true;
            if (index === state.current + 1 && state.completed.indexOf(state.current) !== -1) return true;
            return false;
        }

        function goTo(index) {
            if (index < 0 || index >= state.total) return false;
            if (!canGoTo(index)) return false;

            state.current = index;
            updateUI();

            if (options.onChange) {
                options.onChange(index);
            }

            return true;
        }

        function next() {
            return goTo(state.current + 1);
        }

        function prev() {
            return goTo(state.current - 1);
        }

        function complete(index) {
            if (index === undefined) index = state.current;
            if (state.completed.indexOf(index) === -1) {
                state.completed.push(index);
            }
            updateUI();

            // Check if all completed
            if (state.completed.length === state.total && options.onComplete) {
                options.onComplete();
            }
        }

        function setError(index, message) {
            if (index === undefined) index = state.current;
            var step = steps[index];
            if (step) {
                step.classList.add('error');
                // Remove from completed if present
                var ci = state.completed.indexOf(index);
                if (ci !== -1) state.completed.splice(ci, 1);
            }
        }

        function clearError(index) {
            if (index === undefined) index = state.current;
            var step = steps[index];
            if (step) {
                step.classList.remove('error');
            }
        }

        // Click handlers for clickable steps
        if (options.clickable) {
            steps.forEach(function(step, i) {
                step.style.cursor = 'pointer';
                step.addEventListener('click', function() {
                    goTo(i);
                });
            });
        }

        // Initialize
        updateUI();

        return {
            goTo: goTo,
            next: next,
            prev: prev,
            complete: complete,
            setError: setError,
            clearError: clearError,
            getCurrent: function() { return state.current; },
            isCompleted: function(i) { return state.completed.indexOf(i) !== -1; }
        };
    }

    return { init: init, get: function(id) { return steppers[id]; } };
})();
</script>
"""


# ==========================================================================
# Calendar JS
# ==========================================================================

CALENDAR_JS = """\
<script>
// Quantum UI Calendar System
window.__quantumCalendar = (function() {
    'use strict';

    var calendars = {};

    var monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                      'July', 'August', 'September', 'October', 'November', 'December'];
    var dayNames = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];

    function init(id, options) {
        var container = document.getElementById(id);
        if (!container) return;

        options = options || {};
        var state = {
            mode: options.mode || 'single',
            selected: options.value ? parseDate(options.value) : null,
            rangeStart: null,
            rangeEnd: null,
            multiple: [],
            viewMonth: new Date().getMonth(),
            viewYear: new Date().getFullYear(),
            minDate: options.minDate ? parseDate(options.minDate) : null,
            maxDate: options.maxDate ? parseDate(options.maxDate) : null,
            disabledDates: (options.disabledDates || '').split(',').filter(Boolean).map(parseDate),
            disabledDays: (options.disabledDays || '').split(',').filter(Boolean).map(Number),
            firstDayOfWeek: options.firstDayOfWeek || 0,
            showWeekNumbers: options.showWeekNumbers || false
        };

        calendars[id] = state;

        function parseDate(str) {
            if (!str) return null;
            var d = new Date(str);
            return isNaN(d.getTime()) ? null : d;
        }

        function formatDate(d) {
            if (!d) return '';
            return d.getFullYear() + '-' +
                   String(d.getMonth() + 1).padStart(2, '0') + '-' +
                   String(d.getDate()).padStart(2, '0');
        }

        function isSameDay(d1, d2) {
            if (!d1 || !d2) return false;
            return d1.getFullYear() === d2.getFullYear() &&
                   d1.getMonth() === d2.getMonth() &&
                   d1.getDate() === d2.getDate();
        }

        function isDisabled(date) {
            if (state.minDate && date < state.minDate) return true;
            if (state.maxDate && date > state.maxDate) return true;
            if (state.disabledDays.indexOf(date.getDay()) !== -1) return true;
            return state.disabledDates.some(function(d) { return isSameDay(d, date); });
        }

        function render() {
            var html = '';

            // Header
            html += '<div class="q-calendar-header">';
            html += '<button class="q-calendar-nav" onclick="__quantumCalendar.prevMonth(\'' + id + '\')">&lt;</button>';
            html += '<span class="q-calendar-title">' + monthNames[state.viewMonth] + ' ' + state.viewYear + '</span>';
            html += '<button class="q-calendar-nav" onclick="__quantumCalendar.nextMonth(\'' + id + '\')">&gt;</button>';
            html += '</div>';

            // Grid
            html += '<div class="q-calendar-grid">';

            // Weekday headers
            var orderedDays = dayNames.slice(state.firstDayOfWeek).concat(dayNames.slice(0, state.firstDayOfWeek));
            if (state.showWeekNumbers) html += '<div class="q-calendar-weekday"></div>';
            orderedDays.forEach(function(d) {
                html += '<div class="q-calendar-weekday">' + d + '</div>';
            });

            // Days
            var firstDay = new Date(state.viewYear, state.viewMonth, 1);
            var lastDay = new Date(state.viewYear, state.viewMonth + 1, 0);
            var startDay = (firstDay.getDay() - state.firstDayOfWeek + 7) % 7;

            // Previous month days
            var prevMonth = new Date(state.viewYear, state.viewMonth, 0);
            for (var i = startDay - 1; i >= 0; i--) {
                var day = prevMonth.getDate() - i;
                html += '<div class="q-calendar-day other-month">' + day + '</div>';
            }

            // Current month days
            var today = new Date();
            for (var d = 1; d <= lastDay.getDate(); d++) {
                var date = new Date(state.viewYear, state.viewMonth, d);
                var classes = ['q-calendar-day'];

                if (isSameDay(date, today)) classes.push('today');
                if (isDisabled(date)) classes.push('disabled');

                if (state.mode === 'single' && isSameDay(date, state.selected)) {
                    classes.push('selected');
                } else if (state.mode === 'range') {
                    if (isSameDay(date, state.rangeStart)) classes.push('range-start', 'selected');
                    if (isSameDay(date, state.rangeEnd)) classes.push('range-end', 'selected');
                    if (state.rangeStart && state.rangeEnd && date > state.rangeStart && date < state.rangeEnd) {
                        classes.push('in-range');
                    }
                } else if (state.mode === 'multiple') {
                    if (state.multiple.some(function(s) { return isSameDay(s, date); })) {
                        classes.push('selected');
                    }
                }

                html += '<div class="' + classes.join(' ') + '" onclick="__quantumCalendar.selectDate(\'' + id + '\', ' + d + ')">' + d + '</div>';
            }

            // Next month days
            var remaining = (7 - ((startDay + lastDay.getDate()) % 7)) % 7;
            for (var n = 1; n <= remaining; n++) {
                html += '<div class="q-calendar-day other-month">' + n + '</div>';
            }

            html += '</div>';

            container.innerHTML = html;
        }

        function selectDate(day) {
            var date = new Date(state.viewYear, state.viewMonth, day);
            if (isDisabled(date)) return;

            if (state.mode === 'single') {
                state.selected = date;
            } else if (state.mode === 'range') {
                if (!state.rangeStart || state.rangeEnd) {
                    state.rangeStart = date;
                    state.rangeEnd = null;
                } else {
                    if (date < state.rangeStart) {
                        state.rangeEnd = state.rangeStart;
                        state.rangeStart = date;
                    } else {
                        state.rangeEnd = date;
                    }
                }
            } else if (state.mode === 'multiple') {
                var idx = state.multiple.findIndex(function(d) { return isSameDay(d, date); });
                if (idx === -1) {
                    state.multiple.push(date);
                } else {
                    state.multiple.splice(idx, 1);
                }
            }

            render();

            if (options.onChange) {
                options.onChange(getValue());
            }
        }

        function getValue() {
            if (state.mode === 'single') return state.selected ? formatDate(state.selected) : null;
            if (state.mode === 'range') return { start: formatDate(state.rangeStart), end: formatDate(state.rangeEnd) };
            if (state.mode === 'multiple') return state.multiple.map(formatDate);
        }

        function prevMonth() {
            state.viewMonth--;
            if (state.viewMonth < 0) {
                state.viewMonth = 11;
                state.viewYear--;
            }
            render();
        }

        function nextMonth() {
            state.viewMonth++;
            if (state.viewMonth > 11) {
                state.viewMonth = 0;
                state.viewYear++;
            }
            render();
        }

        // Initialize
        render();

        return {
            getValue: getValue,
            selectDate: selectDate,
            prevMonth: prevMonth,
            nextMonth: nextMonth,
            render: render
        };
    }

    return {
        init: init,
        get: function(id) { return calendars[id]; },
        selectDate: function(id, day) {
            var cal = calendars[id];
            if (cal && cal.selectDate) cal.selectDate(day);
        },
        prevMonth: function(id) {
            var cal = calendars[id];
            if (cal && cal.prevMonth) cal.prevMonth();
        },
        nextMonth: function(id) {
            var cal = calendars[id];
            if (cal && cal.nextMonth) cal.nextMonth();
        }
    };
})();
</script>
"""
