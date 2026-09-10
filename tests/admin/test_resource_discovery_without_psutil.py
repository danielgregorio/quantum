"""
Sem psutil, o admin varria as portas 1-9999 do localhost, uma por vez.

`ResourceDiscovery._scan_ports_socket` fazia connect_ex com timeout de 0,1 s
em cada porta. No Linux uma porta fechada recusa na hora e ninguem notou; no
Windows cada tentativa espera o timeout — medido: ~109 ms por porta, cerca de
18 MINUTOS para uma unica requisicao a /api/resources/overview.

Achado rodando a suite num clone novo: psutil nao estava declarado em lugar
nenhum, a maquina de desenvolvimento o tinha por acaso, e no clone limpo o
teste de fumaca do admin ficou pendurado ate ser morto.
"""

import pathlib
import sys

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
for path in (str(ADMIN), str(ADMIN / "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.resource_manager import ResourceDiscovery  # noqa: E402


def test_sem_psutil_nao_varre_portas(monkeypatch):
    # Socket falso que so conta: contra o codigo antigo este teste falha em
    # milissegundos (10 mil tentativas) em vez de pendurar por 18 minutos.
    import backend.resource_manager as rm

    tentativas = []

    class SocketQueSoConta:
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def settimeout(self, _):
            pass

        def connect_ex(self, endereco):
            tentativas.append(endereco)
            return 1

    monkeypatch.setattr(rm.socket, "socket", SocketQueSoConta)
    descoberta = ResourceDiscovery()
    descoberta._psutil_available = False

    assert descoberta.scan_ports_in_use() == []
    assert tentativas == [], f"varreu {len(tentativas)} portas"


def test_psutil_e_dependencia_declarada_do_admin():
    requisitos = (ADMIN / "backend" / "requirements.txt").read_text(encoding="utf-8")
    assert any(l.strip().startswith("psutil") for l in requisitos.splitlines())
