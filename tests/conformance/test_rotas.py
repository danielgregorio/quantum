"""Conformidade: SPEC.md seção 3a (Páginas e rotas)."""

import pytest


def pagina(nome, corpo):
    return f'<q:component name="{nome}" xmlns:q="https://quantum.lang/ns">{corpo}</q:component>'


@pytest.fixture
def site(servidor, tmp_path):
    pasta = tmp_path / 'components'
    (pasta / 'loja').mkdir(parents=True)
    (pasta / 'loja' / 'index.q').write_text(pagina('loja', '<p>VITRINE</p>'), encoding='utf-8')
    (pasta / 'loja' / '[id].q').write_text(
        pagina('produto', '<q:param name="id" type="integer"/><p>PRODUTO {id + 1}</p>'), encoding='utf-8')
    return servidor(index=pagina('index', '<p>INICIO</p>'), sobre=pagina('sobre', '<p>SOBRE</p>'))


class TestRotas:
    @pytest.mark.parametrize('url,texto', [
        ('/', 'INICIO'), ('/sobre', 'SOBRE'), ('/loja', 'VITRINE'), ('/loja/41', 'PRODUTO 42')])
    def test_arquivo_vira_rota(self, site, url, texto):
        # ROUTE-1
        r = site.get(url)
        assert r.status_code == 200 and texto in r.get_data(as_text=True)

    def test_sem_arquivo_e_404(self, site):
        # ROUTE-1
        assert site.get('/nao-existe').status_code == 404

    def test_fora_de_components_e_404(self, site):
        # ROUTE-1
        assert site.get('/../quantum.config.yaml').status_code == 404

    def test_segmento_pega_o_resto_do_caminho(self, servidor, tmp_path):
        # ROUTE-1: [...caminho]
        (tmp_path / 'components' / 'docs').mkdir(parents=True)
        (tmp_path / 'components' / 'docs' / '[...caminho].q').write_text(
            pagina('doc', '<p>DOC={caminho}</p>'), encoding='utf-8')
        c = servidor()
        assert 'DOC=guia/rotas.md' in c.get('/docs/guia/rotas.md').get_data(as_text=True)


class TestRotaNaAction:
    FONTE = pagina('item', '<q:action name="salvar" method="POST"><q:param name="nota" type="string"/>'
                           '<q:redirect url="/fim" flash="{nome}:{nota}"/></q:action>'
                           '<p>F={flash}</p>')

    def test_action_ve_o_segmento_da_rota(self, servidor, tmp_path):
        # ROUTE-2 (antes: "Variable 'nome' not found" e 500)
        (tmp_path / 'components' / 'item').mkdir(parents=True)
        (tmp_path / 'components' / 'item' / '[nome].q').write_text(self.FONTE, encoding='utf-8')
        c = servidor(fim=pagina('fim', '<p>F={flash}</p>'))
        r = c.post('/item/loja', data={'action': 'salvar', 'nota': 'ok'})
        assert r.status_code == 302
        assert 'F=loja:ok' in c.get('/fim').get_data(as_text=True)

    def test_campo_do_formulario_nao_troca_o_segmento(self, servidor, tmp_path):
        # ROUTE-2
        (tmp_path / 'components' / 'item').mkdir(parents=True)
        (tmp_path / 'components' / 'item' / '[nome].q').write_text(self.FONTE, encoding='utf-8')
        c = servidor(fim=pagina('fim', '<p>F={flash}</p>'))
        c.post('/item/loja', data={'action': 'salvar', 'nota': 'ok', 'nome': 'outra'})
        assert 'F=loja:ok' in c.get('/fim').get_data(as_text=True)


class TestPrivados:
    @pytest.mark.parametrize('url', ['/_layout/Moldura', '/loja/_parte', '/_layout/Moldura.q'])
    def test_nome_com_sublinhado_nao_e_servido(self, servidor, tmp_path, url):
        # ROUTE-3 (antes: o layout respondia na URL dele, com 500 por faltar a prop)
        (tmp_path / 'components' / '_layout').mkdir(parents=True)
        (tmp_path / 'components' / 'loja').mkdir(parents=True)
        (tmp_path / 'components' / '_layout' / 'Moldura.q').write_text(
            pagina('Moldura', '<q:param name="titulo" required="true"/><h1>{titulo}</h1>'), encoding='utf-8')
        (tmp_path / 'components' / 'loja' / '_parte.q').write_text(pagina('parte', '<p>PARTE</p>'), encoding='utf-8')
        c = servidor(p=pagina('p', '<q:import component="Moldura" from="_layout"/><Moldura titulo="USADO"/>'))
        assert c.get(url).status_code == 404
        assert 'USADO' in c.get('/p').get_data(as_text=True)
