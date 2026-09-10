"""
Toda regra do SPEC.md tem teste, e todo teste que cita uma regra cita uma que existe.

A especificação só vale se cada regra for travada por execução. Uma regra sem
teste é uma promessa que ninguém confere — foi exatamente assim que a
documentação do Quantum passou meses ensinando saídas que o código nunca
produzia.

Um teste declara a regra que cobre citando o ID num comentário ou docstring
(`# RET-1`). Os IDs são procurados em todos os arquivos de tests/.
"""

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
ID = re.compile(r'\b(RET|LOOP|IF|FN|ACT|AUTH|DATA|IA|EXPR|INV|RUN|SCOPE|ERR|CFG|APP|SVC)-(\d+)\b')


def ids_da_spec():
    texto = (REPO / 'SPEC.md').read_text(encoding='utf-8')
    return {f'{a}-{n}' for a, n in re.findall(r'\*\*([A-Z]+)-(\d+)\*\*', texto)}


def ids_citados_nos_testes():
    citados = {}
    for arquivo in (REPO / 'tests').rglob('*.py'):
        if arquivo.name == 'test_spec_ids.py':
            continue
        for a, n in ID.findall(arquivo.read_text(encoding='utf-8', errors='ignore')):
            citados.setdefault(f'{a}-{n}', set()).add(arquivo.relative_to(REPO).as_posix())
    return citados


def test_a_spec_tem_regras():
    assert len(ids_da_spec()) >= 10


def test_toda_regra_tem_teste():
    sem_teste = sorted(ids_da_spec() - set(ids_citados_nos_testes()))
    assert sem_teste == [], f'regras do SPEC.md sem nenhum teste que as cite: {sem_teste}'


def test_todo_id_citado_existe_na_spec():
    fantasmas = {i: sorted(arqs) for i, arqs in ids_citados_nos_testes().items()
                 if i not in ids_da_spec()}
    assert fantasmas == {}, f'testes citam regras que não existem no SPEC.md: {fantasmas}'
