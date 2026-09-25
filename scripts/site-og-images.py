"""Write the site's Open Graph images: docs/public/og/<lang>.png, 1200x630.

    python scripts/site-og-images.py

One image per language (en, pt, es, zh): the logo, the name and the sentence,
rendered by Chromium (Playwright) from an HTML card with the system's fonts —
no web font, no CDN. docs/.vitepress/config.js points og:image at them.
Run it again when the sentence or the logo changes, and commit the PNGs.
"""

import html
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / 'docs' / 'public' / 'og'

SENTENCES = {
    'en': ('Declarative web applications in XML, with AI and RAG built into the language.',
           'No build chain, no JavaScript, no front-end framework.'),
    'pt': ('Aplicações web declarativas em XML, com IA e RAG na própria linguagem.',
           'Sem cadeia de build, sem JavaScript, sem framework de front-end.'),
    'es': ('Aplicaciones web declarativas en XML, con IA y RAG en el propio lenguaje.',
           'Sin cadena de build, sin JavaScript, sin framework de front-end.'),
    'zh': ('用 XML 编写的声明式 Web 应用，语言内置 AI 与 RAG。',
           '无需构建工具链，无需 JavaScript，无需前端框架。'),
}

CARD = '''<!doctype html><html><head><meta charset="utf-8"><style>
html, body {{ margin: 0; width: 1200px; height: 630px; }}
body {{ background: #1b1b1f; color: #dfdfd6; display: flex; flex-direction: column; justify-content: center;
        padding: 0 96px; box-sizing: border-box;
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei",
                     "Noto Sans CJK SC", sans-serif; }}
.mark {{ display: flex; align-items: center; gap: 28px; margin-bottom: 48px; }}
.mark svg {{ width: 112px; height: 112px; }}
.name {{ font-size: 88px; font-weight: 700; color: #fff; letter-spacing: -1px; }}
.one {{ font-size: 44px; line-height: 1.3; color: #fff; margin: 0 0 24px; }}
.two {{ font-size: 32px; line-height: 1.35; color: #a8b1ff; margin: 0; }}
.url {{ position: absolute; bottom: 48px; left: 96px; font-size: 26px; color: #98989f; }}
</style></head><body>
<div class="mark">{logo}<div class="name">Quantum</div></div>
<p class="one">{one}</p><p class="two">{two}</p>
<div class="url">quantumframework.net</div>
</body></html>'''


def main() -> int:
    from playwright.sync_api import sync_playwright
    logo = (REPO / 'docs' / 'public' / 'logo.svg').read_text(encoding='utf-8')
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page(viewport={'width': 1200, 'height': 630})
        for lang, (one, two) in SENTENCES.items():
            page.set_content(CARD.format(logo=logo, one=html.escape(one), two=html.escape(two)))
            page.screenshot(path=str(OUT / f'{lang}.png'))
            print(f'wrote {(OUT / f"{lang}.png").relative_to(REPO).as_posix()}')
        browser.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
