"""Conformidade: SPEC.md seção 7a (Serviços declarados)."""

import sys
import textwrap

import pytest

from quantum import services


@pytest.fixture
def modulo(tmp_path, monkeypatch):
    """Um modulo Python do projeto com servicos declarados."""
    services._reset()
    (tmp_path / 'meus_servicos.py').write_text(textwrap.dedent('''
        from quantum.services import service

        @service("projetos.listar")
        def listar(status="ativo", limite=10):
            itens = [{"nome": "a", "status": "ativo"}, {"nome": "b", "status": "parado"}]
            return [i for i in itens if i["status"] == status][:limite]

        @service("contas.dobro")
        def dobro(n):
            return n * 2

        @service("falha")
        def falha():
            raise RuntimeError("disco cheio")
    '''), encoding='utf-8')
    # Sem syspath_prepend: o modulo tem de ser achado a partir do diretorio do
    # projeto, como no `quantum start` (o script nao poe o cwd no sys.path).
    monkeypatch.chdir(tmp_path)
    caminho_antes = list(sys.path)
    yield 'services:\n  - meus_servicos\n'
    sys.path[:] = caminho_antes
    sys.modules.pop('meus_servicos', None)
    services._reset()


def pagina(nome, corpo):
    return f'<q:component name="{nome}" xmlns:q="https://quantum.lang/ns">{corpo}</q:component>'


class TestServicos:
    def test_pagina_chama_servico_declarado(self, servidor, modulo):
        # SVC-1 / SVC-3
        cliente = servidor(datasources_yaml=modulo, p=pagina('p',
            '<q:invoke name="ps" service="projetos.listar"><q:param name="status" value="ativo"/></q:invoke>'
            '<q:loop items="{ps}" var="x"><p>PROJETO {x.nome}</p></q:loop>'))
        html = cliente.get('/p').get_data(as_text=True)
        assert 'PROJETO a' in html and 'PROJETO b' not in html

    def test_param_convertido_pelo_type(self, servidor, modulo):
        # SVC-3
        cliente = servidor(datasources_yaml=modulo, p=pagina('p',
            '<q:invoke name="d" service="contas.dobro"><q:param name="n" value="21" type="integer"/></q:invoke>'
            '<p>R={d}</p>'))
        assert 'R=42' in cliente.get('/p').get_data(as_text=True)

    def test_servico_inexistente_lista_os_registrados(self, executar, modulo, monkeypatch):
        # SVC-3
        import yaml
        from quantum.runtime import service_container
        monkeypatch.setattr(service_container.ServiceContainer, 'config',
                            property(lambda self: yaml.safe_load(modulo)))
        with pytest.raises(Exception, match="no service named 'projetos.lista'.*projetos.listar"):
            executar('<q:invoke name="x" service="projetos.lista"/>')

    def test_falha_do_servico_segue_inv2(self, executar, modulo, monkeypatch):
        # SVC-3 / INV-2
        import yaml
        from quantum.runtime import service_container
        monkeypatch.setattr(service_container.ServiceContainer, 'config',
                            property(lambda self: yaml.safe_load(modulo)))
        with pytest.raises(Exception, match="service 'falha' failed: disco cheio"):
            executar('<q:invoke name="x" service="falha"/>')
        r = executar('<q:invoke name="x" service="falha" onerror="continue"/><q:return value="{x_result}"/>')
        assert r['success'] is False and 'disco cheio' in r['error']['message']

    def test_modulo_so_carrega_se_listado(self, executar, modulo):
        # SVC-2: sem services: na config, nada e importado
        with pytest.raises(Exception, match="no service named 'contas.dobro'"):
            executar('<q:invoke name="x" service="contas.dobro"><q:param name="n" value="1"/></q:invoke>')

    def test_modulo_listado_que_nao_existe_e_erro(self, executar, monkeypatch):
        # SVC-2
        services._reset()
        from quantum.runtime import service_container
        monkeypatch.setattr(service_container.ServiceContainer, 'config',
                            property(lambda self: {'services': ['nao_existe_modulo']}))
        with pytest.raises(Exception, match="service module 'nao_existe_modulo'"):
            executar('<q:invoke name="x" service="a.b"/>')

    def test_nome_duplicado_de_outra_funcao_e_erro(self):
        # SVC-1
        services._reset()

        @services.service('dup.x')
        def um():
            return 1

        with pytest.raises(services.ServiceError, match="already registered"):
            @services.service('dup.x')
            def dois():
                return 2
        services._reset()

    def test_endpoint_em_invoke_e_erro_de_parse(self):
        # SVC-3
        from quantum.core.parser import QuantumParser, QuantumParseError
        with pytest.raises(QuantumParseError, match='endpoint= is not supported'):
            QuantumParser().parse(pagina('p', '<q:invoke name="x" endpoint="/graphql"/>'))
