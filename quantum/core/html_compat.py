"""
Accept the HTML people actually write.

A `.q` file is XML, but its body is HTML, and two things every HTML author
writes are invalid XML:

  1. **Boolean attributes** — `<input required autofocus />`. HTML5 allows a
     bare attribute name; XML demands `required="required"`.
  2. **A bare ampersand in text** — `Forms & Actions`. Browsers tolerate it;
     XML does not.

Ten of the forty-eight components SHIPPED WITH THE FRAMEWORK failed to parse
for exactly these two reasons, which meant they returned HTTP 400 — including
`login.q`, the login screen. The error message told the author to escape the
character, which is true and useless: the file was written the way HTML is
written.

This normalises both before the XML parser sees the source. It is deliberately
narrow:

- Only known boolean attribute names are expanded, and only inside a start
  tag, never in text.
- Only an `&` that does not already begin a valid entity is escaped.
- `<script>`, `<style>`, comments and CDATA sections are left untouched —
  their contents are not XML and rewriting them would corrupt real code.
"""

import re

# HTML5 boolean attributes. A closed list: expanding an arbitrary bare word
# would turn a typo into a silently accepted attribute.
BOOLEAN_ATTRS = frozenset({
    'allowfullscreen', 'async', 'autofocus', 'autoplay', 'checked', 'controls',
    'default', 'defer', 'disabled', 'formnovalidate', 'hidden', 'inert',
    'ismap', 'itemscope', 'loop', 'multiple', 'muted', 'nomodule', 'novalidate',
    'open', 'playsinline', 'readonly', 'required', 'reversed', 'selected',
    'shadowrootclonable', 'shadowrootdelegatesfocus', 'shadowrootserializable',
})

# HTML void elements. `<br>` and `<meta charset="utf-8">` are correct HTML and
# unclosed tags to an XML parser, which then reports the error far away — at
# the `</head>` or `</div>` that no longer matches. components/login.q and
# components/products.q both failed this way, and the reported line was
# nowhere near the real cause.
VOID_ELEMENTS = frozenset({
    'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
    'meta', 'param', 'source', 'track', 'wbr',
})

# Regions whose contents must not be rewritten.
_PROTECTED = re.compile(
    r'(<!\[CDATA\[.*?\]\]>'
    r'|<!--.*?-->'
    r'|<script\b[^>]*>.*?</script\s*>'
    r'|<style\b[^>]*>.*?</style\s*>)',
    re.DOTALL | re.IGNORECASE,
)

# Tags whose body is Python source, not markup. HTML gives <script> exactly
# this treatment; XML gives it to nothing, so a perfectly ordinary line like
#
#     pattern = re.compile(r'<q:agent\s+([^>]*?)/?>')
#
# ended the parse with "not well-formed (invalid token)" pointing at the
# regex. components/admin/agents.q and components/admin/components.q were
# both unparseable — HTTP 400 from the server — for that reason, and the
# author's only recourse was to know to write CDATA by hand.
#
# `script` and `style` are here for the SAME reason. HTML treats the body of
# both as raw text; XML treats nothing that way. A template literal with markup
# inside —
#
#     list.innerHTML = todos.map(t => `<div class="item">${t.task}</div>`)
#
# — is not XML: `${t.completed ? 'checked' : ''}` inside a tag is an invalid
# token. components/islands_demo.q, shipped in the repository, returned HTTP
# 400 because of it, and there was nothing the author could do but write
# CDATA by hand around their own JavaScript.
#
# Measured before the change: of the 47 .q files with <script>/<style>, 46
# render byte for byte the same and 1 (islands_demo) stops being a parse
# error. None gets worse.
_RAW_TEXT_TAGS = ('q:python', 'q:class', 'q:pyclass', 'script', 'style')
_RAW_TEXT = re.compile(
    r'(<(' + '|'.join(_RAW_TEXT_TAGS) + r')\b[^>]*>)(.*?)(</\2\s*>)',
    re.DOTALL | re.IGNORECASE,
)


def wrap_raw_text_tags(source: str) -> str:
    """Put the body of the scripting tags in CDATA when it needs it."""
    def wrap(match):
        open_tag, _name, body, close_tag = match.groups()
        if '<' not in body and '&' not in body:
            return match.group(0)
        if '<![CDATA[' in body:
            return match.group(0)

        # Inside CDATA nothing is decoded, so the entity has to be undone
        # HERE. Without this, `if a &lt; 10:` reached exec() with the literal
        # `&lt;` — a SyntaxError. Before this wrapping the XML parser decoded
        # it; wrapping turned the decoding off and broke 6 .q files shipped in
        # the repository, which used the escaped form because it was the only
        # one that worked.
        #
        # `&amp;` last: undoing it first would turn `&amp;lt;` into `<`.
        for entity, char in (('&lt;', '<'), ('&gt;', '>'),
                                    ('&quot;', '"'), ('&apos;', "'"),
                                    ('&amp;', '&')):
            body = body.replace(entity, char)
        # ]]> cannot appear inside a CDATA section; split it across two.
        body = body.replace(']]>', ']]]]><![CDATA[>')
        return f'{open_tag}<![CDATA[{body}]]>{close_tag}'

    return _RAW_TEXT.sub(wrap, source)

# A start tag: <name ...attrs...> or <name ... />
#
# The attribute part must understand QUOTED VALUES, because `>` is legal inside
# one: `<q:validator expression="parseInt(value) >= 18" />`. A pattern of
# `[^<>]*` stopped at that `>` and mangled the tag — it silently turned
# `parseInt(value) >= 18` into `parseInt(value)>= 18`, which a test caught.
#
# The trailing `/` is NOT matched separately: a greedy attribute run would
# swallow it anyway (`<meta ... />` came back as `<meta ... / />`, breaking
# files that were previously fine). fix_tag strips it from the end instead,
# which leaves interior whitespace exactly as written.
_TAG = re.compile(
    r'<([A-Za-z_][\w:.-]*)((?:\s(?:[^<>"\']|"[^"]*"|\'[^\']*\')*)?)>',
    re.DOTALL,
)

# A bare attribute name sitting on its own inside a tag's attribute list.
_BARE_ATTR = re.compile(r'(^|\s)([A-Za-z_][\w:-]*)(?=\s|$)')

# `&` that already starts a well-formed entity.
_GOOD_ENTITY = re.compile(r'&(#\d+|#x[0-9A-Fa-f]+|[A-Za-z][A-Za-z0-9]*);')


def _expand_boolean_attrs(attrs: str) -> str:
    """`required autofocus` -> `required="required" autofocus="autofocus"`."""
    if not attrs.strip():
        return attrs

    # Split on quoted values so a bare word inside a value is never touched.
    parts = re.split(r'("[^"]*"|\'[^\']*\')', attrs)
    for i in range(0, len(parts), 2):          # even indexes are outside quotes
        segment = parts[i]

        def repl(m):
            lead, name = m.group(1), m.group(2)
            # `foo=` is a normal attribute whose value follows; leave it.
            after = segment[m.end():]
            if after.lstrip().startswith('='):
                return m.group(0)
            if name.lower() in BOOLEAN_ATTRS:
                return f'{lead}{name}="{name}"'
            return m.group(0)

        parts[i] = _BARE_ATTR.sub(repl, segment)
    return ''.join(parts)


_QUOTED_VALUE = re.compile(r'"([^"]*)"|\'([^\']*)\'')


def _escape_bare_lt_in_values(attrs: str) -> str:
    """Escapes `<` inside an attribute's VALUE.

    XML forbids `<` in an attribute value; tolerant HTML and people do not.
    These two lines are natural to write and did not parse:

        <q:if condition="n < 0">
        <q:return value="<h1>Hi</h1>" />

    Ten examples in the documentation — the quick-start among them — were
    exactly that. A raw `&` and a boolean attribute were already tolerated
    here; `<` followed the same logic and was missing.

    Escaping keeps the value: the XML parser undoes `&lt;` when reading, so the
    author gets back the `<` they wrote. Only the quoted value is touched; the
    `<` that OPENS the tag is outside this piece.
    """
    def swap(m):
        quote = '"' if m.group(1) is not None else "'"
        value = m.group(1) if m.group(1) is not None else m.group(2)
        return f'{quote}{value.replace("<", "&lt;")}{quote}'

    return _QUOTED_VALUE.sub(swap, attrs)


# XML predefines FIVE entities; HTML defines more than two thousand. `&nbsp;`
# — the most used of all — does not exist in XML, so a file with it gave
# "undefined entity" and HTTP 400. This module exists to accept the HTML people
# write, and stopped one step short of its own mission.
#
# The translation is to a NUMERIC reference, which XML accepts: `&nbsp;` ->
# `&#160;`. The final character is the same; only the spelling changes.
def _named_entities_to_numeric(text: str) -> str:
    if '&' not in text:
        return text

    from html.entities import html5

    def swap(m):
        name = m.group(1)
        # The five XML ones stay as they are: they are valid and readable.
        if name in ('lt', 'gt', 'amp', 'quot', 'apos'):
            return m.group(0)
        char = html5.get(name + ';')
        if char is None:
            return m.group(0)
        return ''.join(f'&#{ord(c)};' for c in char)

    return re.sub(r'&([A-Za-z][A-Za-z0-9]*);', swap, text)


def _escape_bare_ampersands(text: str) -> str:
    """`Forms & Actions` -> `Forms &amp; Actions`, leaving real entities."""
    if '&' not in text:
        return text
    out = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch != '&':
            out.append(ch)
            i += 1
            continue
        m = _GOOD_ENTITY.match(text, i)
        if m:
            out.append(m.group(0))
            i = m.end()
        else:
            out.append('&amp;')
            i += 1
    return ''.join(out)


def normalise_html(source: str) -> str:
    """Make ordinary HTML parseable as XML, without touching code regions."""
    # First, because it CREATES protected regions: Python inside q:python is
    # not markup, and wrapping it in CDATA both makes it parse and keeps the
    # rewrites below away from it.
    source = wrap_raw_text_tags(source)

    pieces = _PROTECTED.split(source)
    # split() with one capturing group alternates: text, protected, text, ...
    for i in range(0, len(pieces), 2):
        chunk = pieces[i]

        # 1. boolean attributes, inside start tags only
        def fix_tag(m):
            name, attrs = m.group(1), m.group(2)

            # Closing tags (</div>) and declarations are not start tags.
            if name.startswith('/'):
                return m.group(0)

            # Peel a trailing self-closing slash off the attribute run, leaving
            # every other character — including interior whitespace — alone.
            self_closing = attrs.rstrip().endswith('/')
            if self_closing:
                stripped = attrs.rstrip()
                attrs = stripped[:-1]

            attrs = _expand_boolean_attrs(attrs)
            # A bare & inside an attribute VALUE is invalid XML too, and query
            # strings are full of them: href="/x?a=1&b=2".
            attrs = _escape_bare_ampersands(attrs)
            attrs = _named_entities_to_numeric(attrs)
            # And a raw `<` inside the value too: `condition="n < 0"` and
            # `value="<h1>Hi</h1>"` are what people write — and what the
            # documentation itself taught in ten examples that did not
            # parse.
            attrs = _escape_bare_lt_in_values(attrs)

            # Close void elements the author left open (<br>, <meta ...>).
            # `name.lower()` matched a PascalCase component with a void
            # element: <Link>, <Input>, <Source>, <Meta> became
            # `<Link ... />content</Link>` — self-closed, with an orphan
            # closing tag. A void element is an HTML concept, and HTML is
            # written in lowercase; a component call is PascalCase by
            # convention and is not HTML.
            if self_closing or (name.islower() and name in VOID_ELEMENTS):
                sep = '' if (not attrs or attrs.endswith(' ')) else ' '
                return f'<{name}{attrs}{sep}/>'
            return f'<{name}{attrs}>'

        chunk = _TAG.sub(fix_tag, chunk)

        # 2. bare ampersands, in the text between tags only
        segments = re.split(r'(<[^>]*>)', chunk)
        for j in range(0, len(segments), 2):   # even indexes are text
            segments[j] = _escape_bare_ampersands(segments[j])
            segments[j] = _named_entities_to_numeric(segments[j])
        pieces[i] = ''.join(segments)

    return ''.join(pieces)
