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
