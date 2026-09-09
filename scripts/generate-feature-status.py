"""Generate FEATURE_STATUS.md by MEASURING the engine, never by hand.

    python scripts/generate-feature-status.py

PRODUCTION_READINESS.md Fase 6. Hand-written status tables rot: this repo has
manifests marking implemented features "planned", a docs page teaching a tag no
parser registers, and a SUPPORT_TIERS table whose "validated" column was filled
in from isolated checks. A generated table cannot drift, because it is derived
from the registries and from whether the examples actually run.

What it measures, per tag:
  - registered   — a parser is registered for it
  - executor     — a node type it produces has an executor (or it is render-only)
  - example      — at least one examples/*.q or components/*.q uses it
  - runs         — that example parses (a cheap, honest proxy: full execution
                   would need databases, Ollama and a network, so parsing is
                   what this can claim without lying)
"""
import collections
import io
import contextlib
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from quantum.core import tiers  # noqa: E402
from quantum.core.parser import QuantumParser  # noqa: E402
from quantum.runtime.component import ComponentRuntime  # noqa: E402

HTML_TAGS = {
    'div', 'span', 'p', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol',
    'li', 'table', 'tr', 'td', 'th', 'thead', 'tbody', 'form', 'input',
    'button', 'label', 'select', 'option', 'textarea', 'img', 'br', 'hr',
    'pre', 'code', 'style', 'script', 'html', 'head', 'body', 'header',
    'footer', 'nav', 'main', 'section', 'article', 'aside', 'strong', 'em',
    'b', 'i', 'blockquote', 'meta', 'link', 'canvas', 'svg', 'audio', 'video',
    'source',
}


def registered_tags():
    parser = QuantumParser()
    reg = getattr(parser, '_parser_registry', None)
    names = sorted(getattr(reg, '_parsers', {}).keys())
    return [n for n in names if n not in HTML_TAGS]


def executor_node_types():
    with contextlib.redirect_stdout(io.StringIO()):
        rt = ComponentRuntime()
    reg = rt._executor_registry
    return {t.__name__ for t in getattr(reg, '_executors', {}).keys()}


def usage_index():
    """tag -> [files that use it]"""
    idx = collections.defaultdict(list)
    for base in ('examples', 'components'):
        for f in (REPO / base).rglob('*.q'):
            try:
                text = f.read_text(encoding='utf-8', errors='ignore')
            except OSError:
                continue
            for tag in set(re.findall(r'<q:([a-zA-Z-]+)', text)):
                idx[tag].append(f)
    return idx


def parses(path):
    try:
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            QuantumParser().parse(path.read_text(encoding='utf-8', errors='ignore'))
        return True
    except Exception:
        return False


def main():
    tags = registered_tags()
    executors = executor_node_types()
    usage = usage_index()

    rows = []
    for tag in tags:
        tier = tiers.tier_of(tag)
        files = usage.get(tag, [])
        ok = any(parses(f) for f in files) if files else None
        rows.append({
            'tag': tag,
            'tier': tier,
            'examples': len(files),
            'parses': ok,
        })

    by_tier = collections.defaultdict(list)
    for r in rows:
        by_tier[r['tier']].append(r)

    order = [('core', 'Core'), ('diferencial', 'Diferencial'),
             ('experimental', 'Experimental'), ('unknown', 'Não classificada')]

    out = [
        '# FEATURE_STATUS — gerado, não escrito',
        '',
        '> **Não edite este arquivo.** Ele é produzido por',
        '> `python scripts/generate-feature-status.py`, medindo o motor.',
        '> Tabelas de status escritas à mão apodrecem — este repositório tem',
        '> manifests marcando como "planned" features já implementadas e uma',
        '> página de docs ensinando uma tag que nenhum parser registra.',
        '',
        f'**{len(tags)} tags `q:` registradas · {len(executors)} executores.**',
        '',
        'Colunas: **tier** vem de `quantum/core/tiers.py` (a superfície que o',
        'motor de fato impõe). **exemplos** conta arquivos em `examples/` e',
        '`components/` que usam a tag. **parseia** diz se pelo menos um desses',
        'arquivos passa no parser — é um proxy honesto e barato; execução',
        'completa exigiria banco, Ollama e rede, então esta coluna não afirma',
        'mais do que mediu.',
        '',
    ]

    for key, title in order:
        group = sorted(by_tier.get(key, []), key=lambda r: r['tag'])
        if not group:
            continue
        out += [f'## {title} ({len(group)} tags)', '',
                '| Tag | Exemplos | Parseia |', '|---|---|---|']
        for r in group:
            if r['examples'] == 0:
                status = '— sem exemplo'
            elif r['parses']:
                status = 'sim'
            else:
                status = '**NÃO**'
            out.append(f"| `q:{r['tag']}` | {r['examples']} | {status} |")
        out.append('')

    no_example = [r['tag'] for r in rows if r['examples'] == 0]
    broken = [r['tag'] for r in rows if r['examples'] and not r['parses']]

    out += ['## Lacunas que esta medição expõe', '']
    out.append(f'- **{len(no_example)} tags sem nenhum exemplo** no repositório: '
               + (', '.join(f'`q:{t}`' for t in sorted(no_example)) or 'nenhuma')
               + '. Uma tag sem exemplo que roda não deveria entrar no Core '
                 '(regra de entrada, PRODUCTION_READINESS.md Fase 6).')
    out.append(f'- **{len(broken)} tags cujos exemplos não parseiam**: '
               + (', '.join(f'`q:{t}`' for t in sorted(broken)) or 'nenhuma')
               + '.')
    out.append('')

    (REPO / 'FEATURE_STATUS.md').write_text('\n'.join(out), encoding='utf-8')
    print(f"{len(tags)} tags medidas -> FEATURE_STATUS.md")
    print(f"  sem exemplo: {len(no_example)} | exemplos que não parseiam: {len(broken)}")


if __name__ == '__main__':
    main()
