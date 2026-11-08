"""The application's API described (SPEC.md API-7): /api/openapi.json, read from the components, and what
`quantum check` says of the endpoints and the routes (DEV-3)."""

import json
import subprocess
import sys

import pytest

CARDS = '''<q:component name="cards" require_auth="true">
  <q:endpoint method="GET" description="The cards">
    <q:param name="column" default="" maxlength="60" description="Of this column only" />
    <q:param name="page" type="integer" min="1" default="1" />
    <q:respond json="{ {'cards': [], 'page': page} }" />
  </q:endpoint>
  <q:endpoint method="POST" require_role="admin,member" limit="10/minute" maxsize="16kb"
              origins="https://game.example">
    <q:param name="title" required="true" minlength="3" maxlength="120" />
    <q:param name="stars" type="number" range="1..5" />
    <q:param name="due" type="date" default="" />
    <q:param name="kind" enum="task, bug" default="task" />
    <q:param name="mail" type="email" pattern="@example[.]com$" />
    <q:if condition="{title == 'nope'}">
      <q:respond status="409" json="{ {'error': 'taken', 'message': 'Taken.'} }" />
    </q:if>
    <q:respond status="201" json="{ {'id': 1, 'title': title} }" />
  </q:endpoint>
  <q:endpoint method="DELETE">
    <q:param name="hard" type="boolean" default="false" />
  </q:endpoint>
</q:component>'''

PAGE = '<q:component name="home"><p>Hello</p></q:component>'


@pytest.fixture
def app(tmp_path):
    """app({'api/boards/[id]/cards.q': source, ...}, config='') -> a Flask test client of those files."""
    from quantum.runtime.web_server import QuantumWebServer

    def build(files, config=''):
        for name, source in files.items():
            path = tmp_path / 'components' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding='utf-8')
        (tmp_path / 'quantum.config.yaml').write_text(
            f"server:\n  debug: false\npaths:\n  components: {(tmp_path / 'components').as_posix()}\n"
            "logging:\n  level: ERROR\n  console: false\n  file: false\n" + config, encoding='utf-8')
        server = QuantumWebServer(str(tmp_path / 'quantum.config.yaml'))
        server.app.config['TESTING'] = True
        return server.app.test_client()
    return build


def the_document(client):
    response = client.get('/api/openapi.json')
    assert response.status_code == 200 and response.mimetype == 'application/json'
    return response.get_json()


class TestTheDocument:
    """API-7: every endpoint, at its route, with its parameters, answers and refusals."""

    def test_it_is_a_valid_openapi_document(self, app):
        validator = pytest.importorskip('openapi_spec_validator')
        doc = the_document(app({'index.q': PAGE, 'api/boards/[id]/cards.q': CARDS}))
        validator.validate(doc)
        assert doc['openapi'] == '3.1.0' and list(doc['paths']) == ['/api/boards/{id}/cards']   # pages are not
        assert set(doc['paths']['/api/boards/{id}/cards']) == {'get', 'post', 'delete'}

    def test_a_route_segment_is_a_path_parameter(self, app):
        op = the_document(app({'api/boards/[id]/cards.q': CARDS}))['paths']['/api/boards/{id}/cards']['get']
        assert op['parameters'][0] == {'name': 'id', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}
        assert op['summary'] == 'The cards' and op['operationId'] == 'getApiBoardsIdCards'

    def test_get_and_delete_take_query_parameters(self, app):
        paths = the_document(app({'cards.q': CARDS}))['paths']['/cards']
        assert paths['get']['parameters'] == [
            {'name': 'column', 'in': 'query', 'required': False,
             'schema': {'type': 'string', 'maxLength': 60, 'description': 'Of this column only'}},
            {'name': 'page', 'in': 'query', 'required': False,
             'schema': {'type': 'integer', 'minimum': 1, 'default': 1}}]
        assert paths['delete']['parameters'][0]['schema'] == {'type': 'boolean', 'default': False}
        assert 'requestBody' not in paths['get']

    def test_the_others_take_a_json_body_with_the_rules_of_act_2(self, app):
        body = the_document(app({'cards.q': CARDS}))['paths']['/cards']['post']['requestBody']
        schema = body['content']['application/json']['schema']
        assert body['required'] is True and schema['required'] == ['title']
        assert schema['properties'] == {
            'title': {'type': 'string', 'minLength': 3, 'maxLength': 120},
            'stars': {'type': 'number', 'minimum': 1, 'maximum': 5},
            'due': {'type': 'string', 'format': 'date'},
            'kind': {'type': 'string', 'enum': ['task', 'bug'], 'default': 'task'},
            'mail': {'type': 'string', 'format': 'email', 'pattern': '@example[.]com$'}}
        assert 'application/x-www-form-urlencoded' in body['content']          # a form's fields too (API-1)

    def test_the_answers_and_the_refusals(self, app):
        ops = the_document(app({'cards.q': CARDS}))['paths']['/cards']
        post = ops['post']['responses']
        assert set(post) == {'201', '400', '401', '403', '409', '413', '415', '422', '429', '500'}
        assert post['201']['content']['application/json']['schema'] == {
            'type': 'object', 'properties': {'id': {}, 'title': {}}, 'required': ['id', 'title']}
        assert post['201']['description'] == 'Created' and post['409']['description'] == 'Conflict'
        assert 'Retry-After' in post['429']['headers']
        assert post['422']['content']['application/json']['schema'] == {'$ref': '#/components/schemas/Error'}
        # an endpoint that may end without q:respond answers 204 (API-2); one that always ends with it does not
        assert '204' in ops['delete']['responses'] and '204' not in ops['get']['responses']
        assert '403' not in ops['get']['responses'] and '429' not in ops['get']['responses']

    def test_who_may_call_it(self, app):
        doc = the_document(app({'cards.q': CARDS}))
        ops = doc['paths']['/cards']
        assert ops['get']['security'] == [{'session': []}]                    # whoever is signed in
        assert ops['post']['security'] == [{'session': ['admin', 'member']}]
        assert doc['components']['securitySchemes']['session'] == {
            'type': 'apiKey', 'in': 'cookie', 'name': 'session',
            'description': "The session of whoever signed in; its roles are the ones an operation lists."}
        assert ops['post']['x-origins'] == ['https://game.example']
        assert ops['post']['x-limit'] == '10/minute' and ops['post']['x-maxsize'] == 16384

    def test_an_open_endpoint_has_no_security(self, app):
        source = '<q:component name="ping"><q:endpoint method="GET"><q:respond json="{1}" /></q:endpoint></q:component>'
        doc = the_document(app({'ping.q': source}))
        assert 'security' not in doc['paths']['/ping']['get'] and 'securitySchemes' not in doc['components']

    def test_its_title_and_version_and_who_may_read_it(self, app):
        client = app({'cards.q': CARDS}, config='api:\n  title: Kanban\n  version: "2.1"\n')
        response = client.get('/api/openapi.json')
        assert response.get_json()['info']['title'] == 'Kanban' and response.get_json()['info']['version'] == '2.1'
        assert response.headers['Access-Control-Allow-Origin'] == '*'

    def test_without_an_endpoint_or_when_hidden_it_is_404(self, app, tmp_path):
        assert app({'index.q': PAGE}).get('/api/openapi.json').status_code == 404
        hidden = app({'cards.q': CARDS}, config='api:\n  openapi: false\n')
        assert hidden.get('/api/openapi.json').status_code == 404
        assert hidden.get('/cards').status_code == 401                        # the API itself still answers

    def test_what_is_never_served_is_not_described(self, app):
        ping = '<q:component name="p"><q:endpoint method="GET"><q:respond json="{1}" /></q:endpoint></q:component>'
        doc = the_document(app({'ping.q': ping, '_shared/hidden.q': ping, 'api/index.q': ping}))
        assert list(doc['paths']) == ['/api', '/ping']                        # ROUTE-1, ROUTE-3

    def test_it_follows_the_components_as_they_change(self, app, tmp_path):
        client = app({'cards.q': CARDS})
        assert list(the_document(client)['paths']) == ['/cards']
        (tmp_path / 'components' / 'notes.q').write_text(
            '<q:component name="n"><q:endpoint method="GET"><q:respond json="{1}" /></q:endpoint></q:component>')
        assert list(the_document(client)['paths']) == ['/cards', '/notes']


class TestQuantumCheck:
    """DEV-3: what quantum check says of the endpoints and the routes; --openapi writes the document."""

    @pytest.fixture
    def check(self, tmp_path):
        (tmp_path / 'quantum.config.yaml').write_text('paths:\n  components: ./components\n', encoding='utf-8')

        def run(files):
            for name, source in files.items():
                path = tmp_path / 'components' / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source, encoding='utf-8')
            from quantum.cli.check import ProjectChecker
            checker = ProjectChecker(tmp_path, tmp_path / 'quantum.config.yaml')
            return [str(p) for p in checker.run()], checker
        return run

    def test_the_endpoints_are_listed(self, check):
        problems, checker = check({'api/boards/[id]/cards.q': CARDS})
        assert problems == []
        assert checker.endpoints == ['GET /api/boards/{id}/cards', 'POST /api/boards/{id}/cards',
                                     'DELETE /api/boards/{id}/cards']

    def test_a_parameter_the_route_replaces(self, check):
        source = '''<q:component name="c"><q:endpoint method="POST">
          <q:param name="id" type="integer" /><q:respond json="{id}" /></q:endpoint></q:component>'''
        problems, _ = check({'cards/[id].q': source})
        assert problems == ['components/cards/[id].q:1: <q:endpoint method="POST"> <q:param name="id">: '
                            "the route's segment [id] is set last and replaces it (ROUTE-2); rename one"]

    def test_a_body_with_a_status_that_has_none(self, check):
        source = '''<q:component name="c"><q:endpoint method="DELETE">
          <q:respond status="204" json="{ {'gone': true} }" /></q:endpoint></q:component>'''
        problems, _ = check({'gone.q': source})
        assert len(problems) == 1 and 'a 204 answer has no body (API-2)' in problems[0]

    def test_an_endpoint_never_served(self, check):
        source = '<q:component name="c"><q:endpoint method="GET"><q:respond json="{1}" /></q:endpoint></q:component>'
        problems, _ = check({'_lib/ping.q': source})
        assert problems == ['components/_lib/ping.q:1: q:endpoint in a file that is never served (ROUTE-3, ROUTE-4)']

    def test_two_files_at_one_path(self, check):
        problems, _ = check({'shop.q': PAGE, 'shop/index.q': PAGE, 'item/[id].q': PAGE, 'item/[slug].q': PAGE,
                             'item/new.q': PAGE})
        assert problems == [
            'components/item/[slug].q:?: the same path as item/[id].q (/item/{slug}): which one answers is '
            'not defined (ROUTE-1); rename one',
            'components/shop/index.q:?: never served: shop.q answers /shop first (ROUTE-1)',
        ]

    def test_the_command_writes_the_document(self, tmp_path):
        (tmp_path / 'components').mkdir()
        (tmp_path / 'components' / 'cards.q').write_text(CARDS, encoding='utf-8')
        (tmp_path / 'quantum.config.yaml').write_text('paths:\n  components: ./components\napi:\n  title: Cards\n',
                                                      encoding='utf-8')
        done = subprocess.run([sys.executable, '-m', 'quantum.cli.runner', 'check', '--openapi', 'openapi.json'],
                              cwd=tmp_path, capture_output=True, text=True, timeout=120)
        assert done.returncode == 0, done.stdout + done.stderr
        assert 'OpenAPI document written to openapi.json.' in done.stdout
        assert '3 endpoint(s): GET /cards, POST /cards, DELETE /cards' in done.stdout
        doc = json.loads((tmp_path / 'openapi.json').read_text(encoding='utf-8'))
        assert doc['info']['title'] == 'Cards' and set(doc['paths']['/cards']) == {'get', 'post', 'delete'}
