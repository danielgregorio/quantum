"""The site talks about Quantum as it is now.

Every removed or renamed thing in CHANGELOG.md (each Removed and Breaking
entry, from 0.10 to 1.0), the retired tier names, the laboratory's game names
and the pre-1.0 wording have a pattern here. A page that shows one of them as
current fails. A page may still NAME one to say it is gone or refused ("is a
parse error", "was removed", "used to") — that is how the Reference and the
guide explain errors — and the changelog, the blog and the roadmap's history
talk about the past on purpose.

When something new is removed or renamed, add its pattern here with the
replacement to point to.
"""

import re
from pathlib import Path



REPO = Path(__file__).resolve().parents[2]
DOCS = REPO / 'docs'
# The repository's front door: what GitHub and PyPI show before the site.
FRONT_DOOR = ('README.md', 'CONTRIBUTING.md', 'SECURITY.md', 'SUPPORT_TIERS.md', 'CODE_OF_CONDUCT.md')

# Pages about the past, by design.
HISTORY = ('changelog/', 'blog/')

# (id, pattern, what to write instead). Patterns match the page's text,
# code blocks included: a code sample is the most copied part of a page.
DEPRECATED = [
    # 0.22 — the qtest: engine and type="testing"
    ('qtest', r'<qtest:|\bqtest:', '`quantum test` and `*.test.q` files (TEST-1)'),
    # A removed value is also presented as current when a table or a list names
    # it: the q:application page listed `testing` in its table of types, and
    # "(`--target html`, `desktop` or `mobile`)", and both slipped past.
    ('type-testing', r'type="testing"|^\|\s*`testing`\s*\|', '`quantum test` (APP-2)'),
    # 0.22 — RAG through q:query
    ('mode-rag', r'mode="rag"', '`q:llm knowledge="..."` (IA-3)'),
    # 0.22 — the phi3 default; llm.default_model as the spelling
    ('phi3-default', r'default[^.\n]{0,40}\bphi3\b|\bphi3\b[^.\n]{0,30}\bdefault',
     'a model from `llm.model` or `QUANTUM_LLM_DEFAULT_MODEL`: there is no default (IA-1)'),
    ('default-model', r'\bdefault_model\s*:', '`llm.model:` (IA-1)'),
    # 0.21 — mail
    ('email-mock', r'EMAIL_MOCK', '`mail:` in quantum.config.yaml (CFG-1)'),
    ('mail-result', r'_mail_result', '`<name>_result`, `mail_result` by default'),
    ('maxSize', r'\bmaxSize=', '`maxsize=`'),
    # 0.21 / 1.0 — CLI commands that do not exist
    ('old-cli', r'\bquantum (dev|new|build|serve|lint|docs|deploy|apps)\b',
     'the commands in `quantum --help`: run, start, stop, console, check, test, desktop, '
     'admin, pkg, jobs, mq, migrate'),
    # 0.16 — the desktop target and browser persistence
    ('target-desktop', r'--target desktop|--target[^\n|]{0,60}`desktop`', '`quantum desktop` (UI-8)'),
    ('persist', r'<q:persist\b|<q:set\b[^>]*\bpersist(Key|Ttl|Encrypt)?=|`persist="local"`',
     '`session.x` or the database (SET-2)'),
    # 0.14 / 0.20 / 1.0 — attributes that never did anything, or were renamed
    ('set-unique', r'<q:set\b[^>]*\bunique=', '`operation="unique"`'),
    ('knowledge-model', r'<q:knowledge\b[^>]*\bmodel=', '`model=` on the `q:llm` that reads it (IA-2)'),
    ('max-iterations', r'\bmax_iterations=', '`maxIterations=`'),
    ('source-url', r'<q:source\b[^>]*type="url"', 'a file, directory or query source (IA-8)'),
    ('query-attrs', r'<q:query\b[^>]*\b(cache|ttl|reactive|interval|timeout|maxrows|batch)=',
     'nothing: these never did anything (DB-5)'),
    ('function-attrs', r'<q:function\b[^>]*\b(cache|memoize|pure|async|retry|timeout|access|scope|validate|endpoint)=',
     'nothing: these never did anything (FN-2)'),
    ('invoke-attrs', r'<q:invoke\b[^>]*\b(endpoint|transform)=', '`url=` and `q:param` (INV-1)'),
    ('action-attrs', r'<q:action\b[^>]*\b(require_auth|csrf|rate_limit)=', 'a guard on the page (AUTH-7)'),
    ('component-attrs', r'<q:component\b[^>]*\b(basePath|health|metrics|trace)=', 'nothing (PARSE-3)'),
    ('q-html', r'<q:(html|div|span|body|head)\b', 'plain HTML elements (PARSE-1)'),
    ('never-existed', r'<q:(fetch|try|storedproc|include|throw)\b', 'the tags in the Reference (PARSE-1)'),
    # pagination by hand, before paginate="true" and ui:pager
    ('hand-pagination', r'\(page\s*-\s*1\)\s*\*|OFFSET\s*\(',
     '`paginate="true"` on the q:query and a `ui:pager` (UI-11)'),
    # 0.11 — q:application types
    ('app-types', r'<q:application\b[^>]*type="(html|api|microservices)"|^\|\s*`(api|microservices)`\s*\|',
     'pages in `components/` (APP-1)'),
    # 1.0 / 0.14 / 0.11 — more attributes that never did anything (PARSE-3, PARSE-5)
    ('column-attrs', r'<q:column\b[^>]*\b(required|default|validate|pattern|min|max|minlength|maxlength|range|enum)=',
     '`q:transform` to filter rows; `q:column` takes only `name` and `type` (PARSE-3)'),
    ('set-types', r'<q:set\b[^>]*\btype="(date|datetime|struct|null)"', 'a `q:set` type from the Reference (PARSE-5)'),
    ('set-mask', r'<q:set\b[^>]*\bmask=', 'nothing: it never did anything (PARSE-3)'),
    ('param-validation', r'<q:param\b[^>]*\bvalidation=', 'the `q:param` rules (PARSE-3)'),
    # 0.22 — a slice with a step is an error (EXPR-13)
    ('slice-step', r'\{[^}\n]*\[[^\]\n]*:[^\]\n]*:[^\]\n]*\][^}\n]*\}', 'a slice without a step (EXPR-13)'),
    # 0.21 — mail that pretended to send; an upload URL that was never served
    ('mail-mock', r'\[MOCK\] Email sent', '`host: log` in the `mail:` section (MAIL-1)'),
    ('uploads-url', r'(href|src)="/uploads/|_result\.url\b', 'a page that sends the file (`q:file action="send"`, FILE-2)'),
    # 1.0 — projects that were removed, and the admin's deploy feature
    ('removed-projects', r'projects/(quantum-landing|llm-demo|quantum-rag|quantum-fighter|quantum-tower)\b|tower_defense\.q',
     'the apps in the Showcase'),
    ('admin-deploy', r'\bDeployService\b|\bauto-deploy\b|one-command deploy', '`quantum start` behind your own server'),
    # 0.10 — an AI failure is an error, not the text of the answer
    ('rag-error-text', r'Error generating answer', 'an error the page can handle with `onerror` (IA-5)'),
    # tiers, renamed for 1.0
    ('tier-names', r'\bDiferencial\b', 'the tiers Core, AI, Experimental, Laboratory'),
    ('tier-laboratorio', r'\bLaboratório\b', 'the tiers Core, AI, Experimental, Laboratory'),
    # the laboratory's game, which is not in the public repository
    ('smw', r'\bSuper Mario\b|\bMario\b|\bSMW\b|\bYoshi\b|\bNintendo\b|\bKoopa\b|\bGoomba\b',
     'the neutral names of the game examples'),
    # pre-1.0 wording and numbers that age
    ('pre-1', r'\bpre-1\.0\b|\bin beta\b|\bbeta release\b|\(beta\)|\bis beta\b',
     'Quantum 1.0 is released'),
    ('old-version', r'\b(?:v|version |Quantum )0\.\d+(?:\.\d+)?\b', 'the current version, or none'),
    ('test-count', r'\b\d{1,2}[,.]?\d{3} (?:tests|passing)\b|\b\d+(?:\.\d+)?k (?:tests|passing)\b',
     'no count (it changes with every commit)'),
]

# Saying it is gone, refused or old is not presenting it as current.
PAST = re.compile(
    r'\b(removed|no longer|parse error|is (also )?an error|are errors|is refused|refuses|was |were |'
    r'used to|replaced|instead of|deprecated|renamed|never (did|ran|existed|worked)|old\b|until \d|'
    r'up\s+to\s+(quantum\s+)?0\.|'
    # the same markers on the Spanish pages (docs/es/)
    r'se eliminó|eliminad[oa]s?|ya no|es un error de análisis|renombrad[oa]s?|reemplazad[oa]s?|antes eran|'
    # ... and on the Portuguese ones (docs/pt/)
    r'foi |foram |era |eram |removid[oa]s?|não (é |são )?mais|substituíd[oa]s?|renomead[oa]s?|'
    r'é um erro de (análise|parse)|obsolet[oa]s?|até\s+o\s+quantum\s+0\.)'
    # ... and on the Chinese ones (docs/zh/): no \b between CJK characters
    r'|已移除|已删除|已被|曾经|曾是|以前|原为|不再|改名|取代|解析错误',
    re.I)

# The label that says a block is refused code, in each language of the site.
ERROR_MARK = re.compile(r'\*\*(Error|Erro|错误)[:：]\*\*')

# Mentions that stay, each with why: (page, pattern id).
ALLOWED = {
    ('reference/spec.md', 'qtest'): 'APP-2: a qtest: tag is a parse error that names quantum test',
    ('targets/desktop.md', 'target-desktop'): 'its "What happened to --target desktop" section',
}
FENCE = '`' * 3


def unpublished():
    """The pages srcExclude keeps off the site (docs/.vitepress/config.js)."""
    config = (DOCS / '.vitepress' / 'config.js').read_text(encoding='utf-8')
    block = re.search(r'srcExclude:\s*\[(.*?)\]', config, re.S)
    return set(re.findall(r"'([^']+\.md)'", block.group(1))) if block else set()


UNPUBLISHED = unpublished()


def pages():
    """The published pages, and the repository's front door: what a reader sees.
    A front-door file's name starts with / (/README.md)."""
    for name in FRONT_DOOR:
        yield f'/{name}', (REPO / name).read_text(encoding='utf-8')
    for path in sorted(DOCS.rglob('*.md')):
        rel = path.relative_to(DOCS).as_posix()
        if ('node_modules' in path.parts or '.vitepress' in path.parts
                or rel.startswith(HISTORY) or rel in UNPUBLISHED):
            continue
        yield rel, path.read_text(encoding='utf-8')


# An old name that is the right word in a translation: Laboratório is how the
# pt-BR pages say Laboratory (docs/.vitepress/i18n/glossary.pt.md).
NATIVE = {('pt/', 'tier-laboratorio')}


def sentence_around(text, start, end):
    """The sentence (or line of code) the match is in."""
    left = max(text.rfind('\n\n', 0, start), text.rfind('. ', 0, start), text.rfind('\n```', 0, start))
    right_candidates = [i for i in (text.find('\n\n', end), text.find('. ', end), text.find('\n```', end)) if i != -1]
    right = min(right_candidates) if right_candidates else len(text)
    return text[left + 1:right]


def fenced_context(text, start):
    """For a match inside a code block: the paragraph before the block, the
    block and the paragraph after it. The guide shows refused code as a block
    followed by **Error:**, or introduced by a sentence that says it is gone.
    None when the match is not inside a block."""
    if text.count('\n' + FENCE, 0, start) % 2 == 0:
        return None
    opening = text.rfind('\n' + FENCE, 0, start)
    closing = text.find('\n' + FENCE, start)
    before = text.rfind('\n\n', 0, opening)
    gap = text.find('\n\n', closing + 4)                 # the blank line after the block
    after = text.find('\n\n', gap + 2) if gap != -1 else -1
    return text[before + 1: after if after != -1 else len(text)]


def hits():
    for rel, text in pages():
        for pid, pattern, instead in DEPRECATED:
            if (rel, pid) in ALLOWED or any(rel.startswith(lang) and pid == rule for lang, rule in NATIVE):
                continue
            for m in re.finditer(pattern, text, re.M):
                block = fenced_context(text, m.start())
                if block is not None and (ERROR_MARK.search(block) or PAST.search(block)):
                    continue
                sentence = sentence_around(text, m.start(), m.end())
                if PAST.search(sentence) or ERROR_MARK.search(sentence):
                    continue
                line = text.count('\n', 0, m.start()) + 1
                yield rel, line, pid, m.group(0), instead


HITS = list(hits())


def where(rel):
    return rel[1:] if rel.startswith('/') else f'docs/{rel}'


def test_no_page_presents_a_removed_thing_as_current():
    assert not HITS, '\n'.join(
        f'{where(rel)}:{line}: {found!r} is gone or renamed; write {instead}'
        for rel, line, pid, found, instead in HITS)


def test_the_unpublished_pages_exist():
    # srcExclude names real files: a typo would publish the page it meant to hide
    assert UNPUBLISHED and all((DOCS / page).is_file() for page in UNPUBLISHED)


def test_the_allowlist_only_shrinks():
    for (rel, pid), why in ALLOWED.items():
        assert why, (rel, pid)
        text = (REPO / rel[1:] if rel.startswith('/') else DOCS / rel).read_text(encoding='utf-8')
        pattern = next(p for i, p, _ in DEPRECATED if i == pid)
        assert re.search(pattern, text), f'{rel}: no {pid} left — take it off ALLOWED'


# What each pattern must catch, as a page once wrote it — a pattern that
# matches nothing (a missing flag, a typo) would pass every page in silence.
SAMPLES = {
    'type-testing': ['| `testing` | Experimental | generates browser tests |', '<q:application type="testing">'],
    'target-desktop': ['(`--target html`, `desktop` or `mobile`)', 'quantum run app.q --target desktop'],
    'app-types': ['| `api` | Experimental |', '<q:application id="x" type="api">'],
    'query-attrs': ['<q:query name="q" datasource="db" timeout="30">'],
    'function-attrs': ['<q:function name="f" scope="global">'],
    'column-attrs': ['<q:column name="age" type="integer" min="0" />'],
    'set-types': ['<q:set name="d" type="date" value="2026-01-01" />'],
    'set-mask': ['<q:set name="p" value="123" mask="###" />'],
    'param-validation': ['<q:param name="x" validation="email" />'],
    'slice-step': ['<q:return value="{items[::-1]}" />'],
    'mail-mock': ['[MOCK] Email sent to ana@example.com'],
    'uploads-url': ['<a href="/uploads/{saved.filename}">', '{saved_result.url}'],
    'removed-projects': ['projects/quantum-landing', 'examples/tower_defense.q'],
    'admin-deploy': ['one-command deploy to the cloud'],
    'rag-error-text': ['Error generating answer: timeout'],
}


def test_each_pattern_catches_what_it_is_for():
    patterns = {pid: pattern for pid, pattern, _ in DEPRECATED}
    for pid, samples in SAMPLES.items():
        for sample in samples:
            assert re.search(patterns[pid], sample, re.M), f'{pid} does not catch {sample!r}'
