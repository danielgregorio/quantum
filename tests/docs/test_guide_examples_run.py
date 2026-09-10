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


# O banco que docs/guide/query.md descreve em "The example database". Um bloco
# com datasource="db" roda contra uma copia nova dele.
ESQUEMA = """
create table users (id integer primary key, name text, email text, status text);
insert into users (name, email, status) values
  ('Ana', 'ana@example.com', 'active'),
  ('Bruno', 'bruno@example.com', 'active'),
  ('Carla', 'carla@example.com', 'inactive');
create table products (id integer primary key, name text, price real, stock integer);
insert into products (name, price, stock) values
  ('Notebook', 3500.0, 5), ('Mouse', 80.0, 40), ('Monitor', 1200.0, 0);
create table orders (id integer primary key, user_id integer, total real);
"""


def executar(xml):
    if '<q:component' not in xml:
        xml = f'<q:component name="Doc" xmlns:q="https://quantum.lang/ns">{xml}</q:component>'
    pasta = pathlib.Path(tempfile.mkdtemp())
    caminho = pasta / 'doc.q'
    caminho.write_text(xml, encoding='utf-8')
    config = {}
    if 'datasource="db"' in xml:
        import sqlite3
        banco = pasta / 'app.db'
        conexao = sqlite3.connect(banco)
        conexao.executescript(ESQUEMA)
        conexao.commit()
        conexao.close()
        config = {'datasources': {'db': {'driver': 'sqlite', 'database': str(banco)}}}
    with contextlib.redirect_stdout(io.StringIO()):
        return ComponentRuntime(config=config).execute_component(
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
    minimos = {'loops.md': 8, 'databinding.md': 8, 'conditionals.md': 6, 'functions.md': 6,
               'query.md': 9, 'state-management.md': 10, 'components.md': 4}
    faltando = {p: (por_pagina.get(p, 0), n) for p, n in minimos.items() if por_pagina.get(p, 0) < n}
    assert not faltando, f"paginas com menos exemplos executados que o esperado: {faltando}"
