"""The attributes the parser accepts, per q: tag, measured by parsing.

Every attribute a parser reads goes through `element.get` (get_attr and its
siblings call it). While a corpus of pages is parsed, each read is recorded as
(tag, attribute). A read can also be a REFUSAL — the parser looks for
`persist=` only to reject it — so each recorded attribute is parsed once more
on its own: if the parse error names it as unsupported or removed, it is not
part of the language.

Used by test_editor_schemas.py and by scripts/generate-editor-schemas.py.
"""

import re

from quantum.core import xml_lines
from quantum.core.parser import QuantumParser

NS = 'xmlns:q="https://quantum.lang/ns"'
Q = '{https://quantum.lang/ns}'

# Each branch of each Core/AI parser that reads attributes, as a page body.
CORPUS = [
    # structure
    '<q:param name="p" type="integer" required="true" default="1"/><q:return value="{p}"/>',
    '<q:script>console.log(1)</q:script>',
    # control flow
    '<q:set name="a" value="1" type="number"/><q:set name="a" operation="increment" step="2"/>'
    '<q:set name="l" operation="append" value="x"/><q:set name="l" operation="removeAt" index="0"/>'
    '<q:set name="o" value=\'{"a":1}\' type="object"/><q:set name="o" operation="setProperty" key="b" value="1"/>'
    '<q:set name="c" operation="clone" source="o"/>',
    '<q:set name="v" value="a@b.co" required="true" nullable="true" validate="email" pattern=".*" range="1..9" '
    'enum="a" min="1" max="9" minlength="1" maxlength="9" scope="local" default="x"/>',
    '<q:if condition="1"><p>a</p><q:elseif condition="0"><p>b</p></q:elseif><q:else><p>c</p></q:else></q:if>',
    '<q:loop type="range" var="i" from="1" to="3" step="1"><p>{i}</p></q:loop>',
    '<q:loop type="array" var="x" index="k" items="[1]"><p>{x}</p></q:loop>',
    '<q:loop type="list" var="x" items="a,b" delimiter=","><p>{x}</p></q:loop>',
    '<q:query name="r" datasource="db">SELECT 1</q:query><q:loop query="r" var="row"><p>{row}</p></q:loop>',
    '<q:function name="f" returnType="number" description="d" hint="h">'
    '<q:param name="n" type="number" required="true" default="1" min="1" max="9" minlength="1" maxlength="9" '
    'pattern=".*" enum="1" range="1..9" validate="email" description="d"/><q:return value="{n}"/></q:function>',
    # data
    '<q:query name="q" datasource="db" result="qr" paginate="true" page="1" pageSize="10" sortable="true" '
    'onerror="continue">SELECT * FROM t WHERE a = :a<q:param name="a" value="1" type="string" maxLength="5" '
    'scale="2" null="false"/></q:query>',
    '<q:query name="q2" datasource="db" page_size="10" paginate="true">SELECT 1</q:query>',
    '<q:query name="qq" source="q">SELECT * FROM q</q:query>',
    '<q:transaction datasource="db" isolationLevel="SERIALIZABLE"><q:query name="t1">SELECT 1</q:query></q:transaction>',
    '<q:transaction datasource="db" isolation="READ_COMMITTED"><q:query name="t2">SELECT 1</q:query></q:transaction>',
    '<q:invoke name="h" url="http://x" method="POST" timeout="5" contentType="application/json" authType="bearer" '
    'authToken="t" authHeader="X" authUsername="u" authPassword="p" retry="1" retryDelay="10" '
    'responseFormat="auto" cache="false" ttl="5" onerror="continue" result="hr">'
    '<q:header name="X-A" value="1"/><q:param name="a" value="1"/><q:body>x</q:body></q:invoke>',
    '<q:invoke name="s" service="svc.x"><q:param name="a" value="1" type="integer"/></q:invoke>',
    '<q:invoke name="fn" function="f"/>',
    '<q:data name="d" source="d.csv" type="csv" delimiter="," quote="&quot;" header="true" encoding="utf-8" '
    'skip_rows="0" cache="true" ttl="5" result="dr" onerror="continue"><q:column name="c" type="integer"/>'
    '<q:transform><q:filter condition="c &gt; 1"/><q:sort by="c" order="asc"/><q:limit value="1"/>'
    '<q:compute field="z" expression="{c}" type="integer"/></q:transform>'
    '<q:header name="X" value="1"/></q:data>',
    '<q:data name="x" source="d.xml" type="xml" xpath=".//r" namespace="n"><q:field name="i" xpath="@id" type="integer"/></q:data>',
    '<q:data name="j" source="d.json" type="json"><q:field name="i" path="a" type="string"/></q:data>',
    # actions, files, mail
    '<q:action name="a" method="POST"><q:param name="f" type="file" accept=".pdf" maxsize="1MB"/>'
    '<q:file action="upload" file="{f}" destination="d" nameConflict="makeUnique" result="r"/>'
    '<q:flash type="info" message="m"/><q:redirect url="/" flash="ok" status="302"/></q:action><p>x</p>',
    '<q:action name="t" method="POST" table="t" datasource="db" columns="a,b"><q:redirect url="/"/></q:action><p>x</p>',
    '<q:file action="send" file="{f}" name="n.pdf"/>',
    '<q:action name="b" method="POST"><q:redirect to="/"/></q:action><p>x</p>',
    '<q:file action="delete" file="{f}"/>',
    '<q:mail name="m" to="a@b.co" from="c@d.co" cc="e@f.co" bcc="g@h.co" replyTo="i@j.co" subject="s" type="text" '
    'body="b" onerror="continue"><q:attachment file="x.pdf"/></q:mail>',
    # composition
    '<q:import component="Card" from="parts"/><Card title="x"/>',
    '<q:slot name="s"/>',
    # AI
    '<q:llm name="l" model="m" endpoint="http://x" provider="ollama" apiKey="k" temperature="0.1" maxTokens="5" '
    'responseFormat="json" cache="true" ttl="5" timeout="5" knowledge="kb" top="2" minRelevance="0.5" '
    'stream="true" onerror="continue"><q:system>s</q:system><q:message role="user">m</q:message></q:llm>',
    '<q:llm name="l2"><q:prompt>p</q:prompt></q:llm>',
    '<q:knowledge name="kb" embedModel="e" chunkSize="10" chunkOverlap="1" persist="false" persistPath="p" '
    'rebuild="true" onerror="continue"><q:source type="text">t</q:source>'
    '<q:source type="file" path="a.md"/><q:source type="directory" path="d" pattern="*.md"/>'
    '<q:source type="query" datasource="db">SELECT 1</q:source></q:knowledge>',
    '<q:agent name="g" model="m" endpoint="http://x" provider="ollama" apiKey="k" maxIterations="2" timeout="5" '
    'onerror="continue"><q:instruction>i</q:instruction><q:tool name="t" description="d">'
    '<q:param name="a" type="string" required="true" default="x" description="d"/>'
    '<q:function name="f"><q:return value="1"/></q:function></q:tool><q:execute task="t" context="c"/></q:agent>',
]

COMPONENT = ('<q:component name="C" {ns} require_auth="true" require_role="admin" login_url="/in" '
             'require_permission="p" interactive="true" type="pure" port="1">{body}</q:component>')

REFUSAL = re.compile(r'is not supported|was removed|the attribute is|is not a Quantum tag')


def record():
    """{tag: set of attribute names the parser reads} over the corpus."""
    reads = {}
    original = xml_lines._Element.get

    def get(self, key, default=None):
        if isinstance(self.tag, str) and self.tag.startswith(Q):
            reads.setdefault(self.tag[len(Q):], set()).add(key)
        return original(self, key, default)

    xml_lines._Element.get = get
    try:
        for body in CORPUS:
            QuantumParser(use_cache=False).parse(COMPONENT.format(ns=NS, body=body))
    finally:
        xml_lines._Element.get = original
    return reads


# Read only to refuse a VALUE of them (mode="rag", type="url"): not attributes of the language.
READ_TO_REFUSE = {
    ('query', 'mode'): 'IA-3: only mode="rag" is looked for, and it is a parse error',
    ('source', 'url'): 'IA-8: read only for the refused type="url"',
}


def _sources(tag, attribute):
    if tag == 'component':
        yield COMPONENT.replace('<q:component ', f'<q:component {attribute}="1" ').format(ns=NS, body='<p>x</p>')
        return
    for snippet in CORPUS:
        if re.search(rf'<q:{tag}[ >/]', snippet):
            yield COMPONENT.format(ns=NS, body=re.sub(rf'<q:{tag}(?=[ >/])', f'<q:{tag} {attribute}="1"',
                                                     snippet, count=1))


def refused(tag, attribute):
    """Does the parser reject `attribute` on `tag` in any context, saying it is not supported or removed?"""
    if (tag, attribute) in READ_TO_REFUSE:
        return True
    for source in _sources(tag, attribute):
        try:
            QuantumParser(use_cache=False).parse(source)
        except Exception as error:
            message = str(error)
            if REFUSAL.search(message) and f'{attribute}' in message:
                return True
    return False


def accepted():
    """{tag: sorted attribute names} — read by the parser and not refused."""
    return {tag: sorted(a for a in attributes if not refused(tag, a))
            for tag, attributes in record().items()}
