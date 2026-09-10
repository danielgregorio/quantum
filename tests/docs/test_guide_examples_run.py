"""
Cada exemplo do guia que mostra um resultado tem de produzir esse resultado.

Os outputs de docs/guide/loops.md eram fabricados — nenhum saía do runtime — e
docs/guide/conditionals.md ensinava `a && b`, que parseava como erro e fazia a
condição ser falsa para qualquer entrada. Ler a doc não pega isso; executar
pega.

Formato reconhecido, logo depois de um bloco ```xml:

    **Output:** `["json", "na mesma linha"]`

    **Output:**
    ```
    ["ou", "num bloco"]
    ```

    **Error:** `trecho da mensagem de erro`

**Resultado:** e **Erro:** (páginas em português) valem o mesmo. Um resultado
que não é JSON é comparado com o texto do valor.

Um bloco sem `<q:component>` é executado como corpo de um componente.
`q:application` é experimental (SUPPORT_TIERS.md) e fica de fora.
"""

import contextlib
import io
import json
import pathlib
import re
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime

GUIDE = pathlib.Path(__file__).resolve().parents[2] / 'docs' / 'guide'
F = '`' * 3

EXEMPLO = re.compile(
    F + r'xml\n(?P<xml>(?:(?!' + F + r').)*)' + F + r'\s*\n'
    r'\*\*(?P<tipo>Output|Error|Resultado|Erro):\*\*[ \t]*'
    r'(?:`(?P<inline>[^`\n]+)`|\n' + F + r'[a-z]*\n(?P<bloco>.*?)' + F + r')',
    re.S)


def exemplos():
    for doc in sorted(GUIDE.glob('*.md')):
        texto = doc.read_text(encoding='utf-8')
        for n, m in enumerate(EXEMPLO.finditer(texto)):
            if '<q:application' in m['xml'] or '<q:route' in m['xml']:
                continue
            linha = texto[:m.start()].count('\n') + 1
            esperado = (m['inline'] if m['inline'] is not None else m['bloco']).strip()
            yield pytest.param(m['xml'], m['tipo'], esperado, id=f'{doc.name}:{linha}')


TODOS = list(exemplos())


def executar(xml):
    if '<q:component' not in xml:
        xml = f'<q:component name="Doc" xmlns:q="https://quantum.lang/ns">{xml}</q:component>'
    caminho = pathlib.Path(tempfile.mkdtemp()) / 'doc.q'
    caminho.write_text(xml, encoding='utf-8')
    with contextlib.redirect_stdout(io.StringIO()):
        return ComponentRuntime(config={}).execute_component(
            QuantumParser().parse_file(str(caminho)), {})


@pytest.mark.parametrize('xml,tipo,esperado', TODOS)
def test_o_exemplo_produz_o_que_a_doc_mostra(xml, tipo, esperado):
    if tipo in ('Error', 'Erro'):
        with pytest.raises(Exception) as erro:
            executar(xml)
        assert esperado in str(erro.value)
        return
    resultado = executar(xml)
    try:
        assert resultado == json.loads(esperado)
    except json.JSONDecodeError:
        # **Resultado:** `x = 10` — o texto como aparece, sem aspas de JSON
        assert str(resultado) == esperado


def test_a_extracao_encontra_os_exemplos():
    # Se o formato do markdown mudar, o parametrize vira zero casos e passa
    # em silêncio.
    por_pagina = {}
    for p in TODOS:
        pagina = p.id.split(':')[0]
        por_pagina[pagina] = por_pagina.get(pagina, 0) + 1
    assert por_pagina.get('loops.md', 0) >= 8
    assert por_pagina.get('databinding.md', 0) >= 8
