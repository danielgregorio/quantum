"""Conformance: SPEC.md section 3a (Pages and routes)."""

import pytest


def page(name, body):
    return f'<q:component name="{name}" xmlns:q="https://quantum.lang/ns">{body}</q:component>'


@pytest.fixture
def site(serve_pages, tmp_path):
    folder = tmp_path / 'components'
    (folder / 'shop').mkdir(parents=True)
    (folder / 'shop' / 'index.q').write_text(page('shop', '<p>STOREFRONT</p>'), encoding='utf-8')
    (folder / 'shop' / '[id].q').write_text(
        page('product', '<q:param name="id" type="integer"/><p>PRODUCT {id + 1}</p>'), encoding='utf-8')
    return serve_pages(index=page('index', '<p>HOME</p>'), about=page('about', '<p>ABOUT</p>'))


class TestRoutes:
    @pytest.mark.parametrize('url,text', [
        ('/', 'HOME'), ('/about', 'ABOUT'), ('/shop', 'STOREFRONT'), ('/shop/41', 'PRODUCT 42')])
    def test_a_file_becomes_a_route(self, site, url, text):
        # ROUTE-1
        r = site.get(url)
        assert r.status_code == 200 and text in r.get_data(as_text=True)

    def test_no_file_is_404(self, site):
        # ROUTE-1
        assert site.get('/does-not-exist').status_code == 404

    def test_outside_components_is_404(self, site):
        # ROUTE-1
        assert site.get('/../quantum.config.yaml').status_code == 404

    def test_a_segment_takes_the_rest_of_the_path(self, serve_pages, tmp_path):
        # ROUTE-1: [...path]
        (tmp_path / 'components' / 'docs').mkdir(parents=True)
        (tmp_path / 'components' / 'docs' / '[...path].q').write_text(
            page('doc', '<p>DOC={path}</p>'), encoding='utf-8')
        c = serve_pages()
        assert 'DOC=guide/routes.md' in c.get('/docs/guide/routes.md').get_data(as_text=True)


class TestRouteInAnAction:
    SOURCE = page('item', '<q:action name="save" method="POST"><q:param name="note" type="string"/>'
                          '<q:redirect url="/end" flash="{name}:{note}"/></q:action>'
                          '<p>F={flash}</p>')

    def test_the_action_sees_the_route_segment(self, serve_pages, tmp_path):
        # ROUTE-2 (before: "Variable 'name' not found" and a 500)
        (tmp_path / 'components' / 'item').mkdir(parents=True)
        (tmp_path / 'components' / 'item' / '[name].q').write_text(self.SOURCE, encoding='utf-8')
        c = serve_pages(end=page('end', '<p>F={flash}</p>'))
        r = c.post('/item/shop', data={'action': 'save', 'note': 'ok'})
        assert r.status_code == 302
        assert 'F=shop:ok' in c.get('/end').get_data(as_text=True)

    def test_a_form_field_does_not_replace_the_segment(self, serve_pages, tmp_path):
        # ROUTE-2
        (tmp_path / 'components' / 'item').mkdir(parents=True)
        (tmp_path / 'components' / 'item' / '[name].q').write_text(self.SOURCE, encoding='utf-8')
        c = serve_pages(end=page('end', '<p>F={flash}</p>'))
        c.post('/item/shop', data={'action': 'save', 'note': 'ok', 'name': 'other'})
        assert 'F=shop:ok' in c.get('/end').get_data(as_text=True)


class TestPrivate:
    @pytest.mark.parametrize('url', ['/_layout/Frame', '/shop/_part', '/_layout/Frame.q'])
    def test_a_name_with_an_underscore_is_not_served(self, serve_pages, tmp_path, url):
        # ROUTE-3 (before: the layout answered at its own URL, with a 500 for the missing prop)
        (tmp_path / 'components' / '_layout').mkdir(parents=True)
        (tmp_path / 'components' / 'shop').mkdir(parents=True)
        (tmp_path / 'components' / '_layout' / 'Frame.q').write_text(
            page('Frame', '<q:param name="title" required="true"/><h1>{title}</h1>'), encoding='utf-8')
        (tmp_path / 'components' / 'shop' / '_part.q').write_text(page('part', '<p>PART</p>'), encoding='utf-8')
        c = serve_pages(p=page('p', '<q:import component="Frame" from="_layout"/><Frame title="USED"/>'))
        assert c.get(url).status_code == 404
        assert 'USED' in c.get('/p').get_data(as_text=True)
