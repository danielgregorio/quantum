"""
Lacunas semânticas conhecidas — o inventário da Fase 0.3, executável.

Cada teste descreve o comportamento PROPOSTO e está marcado
`xfail(strict=True)`: hoje o runtime faz outra coisa. Quando alguém corrigir,
o teste passa inesperadamente e o `strict` derruba a suíte — a lacuna tem de
sair daqui e virar regra com ID na SPEC (Fase 2), com o teste movido para a
seção dela.

O comportamento esperado é PROPOSTA, não decisão. A Fase 2 pode escolher
outra regra; nesse caso o teste muda junto. O que não pode acontecer é a
lacuna sumir sem ninguém decidir.

Todos os casos foram reproduzidos por execução em 2026-09-10.
"""

import pathlib
import tempfile

import pytest

from quantum.core.parser import QuantumParser
from quantum.runtime.component import ComponentRuntime

REPO = pathlib.Path(__file__).resolve().parents[2]


def executar(corpo, params=None):
    caminho = pathlib.Path(tempfile.mkdtemp()) / 'c.q'
    caminho.write_text(
        f'<q:component name="C" xmlns:q="https://quantum.lang/ns">{corpo}</q:component>',
        encoding='utf-8')
    return ComponentRuntime().execute_component(
        QuantumParser().parse_file(str(caminho)), params or {})


def lacuna(reason):
    return pytest.mark.xfail(strict=True, reason=reason)


# Nenhuma lacuna aberta. A proxima entra aqui, com o comportamento proposto e
# @lacuna("Gnn: ...").
