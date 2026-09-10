"""
The admin was not in the test suite at all, and it showed.

Exercising all 160 GET routes with a valid token found: the login page could
not log in (its fetch targeted a literal "{URL_PREFIX}" path, 404), two
dashboards answered 500, and most of the API answered 200 with no token while
a handful answered 401 — auth was per route, and most routes forgot.

These are the checks that would have caught each of those.
"""

import os
import pathlib
import re
import sys

import pytest

ADMIN = pathlib.Path(__file__).resolve().parents[2] / "quantum_admin"
for path in (str(ADMIN), str(ADMIN / "backend")):
    if path not in sys.path:
        sys.path.insert(0, path)

pytest.importorskip("fastapi", reason="the admin needs fastapi")
pytest.importorskip("jwt", reason="PyJWT not installed")
from starlette.testclient import TestClient  # noqa: E402

PASSWORD = "uma-senha-de-teste-suficientemente-longa"


@pytest.fixture(scope="module")
def app():
    os.environ["ADMIN_PASSWORD"] = PASSWORD
    os.environ["JWT_SECRET_KEY"] = "a" * 64
    os.environ.pop("QUANTUM_ADMIN_ENV", None)
    os.environ.pop("QUANTUM_ADMIN_ALLOW_ANONYMOUS", None)
    from backend import main
    return main


@pytest.fixture(scope="module")
def client(app):
    # `with` de proposito: o TestClient do Starlette so dispara os eventos de
    # startup quando usado como context manager — e e no startup que o admin
    # roda `init_db()` (create_all) e `seed_db()`.
    #
    # Sem isso o teste dependia de um `quantum_admin.db` que ja existisse no
    # disco. Na maquina de quem desenvolve ele existe (sobrou de alguma
    # execucao real), entao passava; num clone limpo — o CI, ou qualquer
    # pessoa nova — nao existe, nao ha tabelas, e OITENTA E QUATRO rotas
    # respondiam 500. Verde aqui, vermelho la, por estado da maquina.
    with TestClient(app.app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def token(client):
    r = client.post("/auth/login",
                    params={"username": "admin", "password": PASSWORD})
    assert r.status_code == 200, r.text
    # The login also sets the session cookie, and TestClient keeps cookies.
    # Left in the jar, every "no token" request below would quietly be
    # authenticated. Tests that want the cookie log in on their own client.
    client.cookies.clear()
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


def get_routes(app, method="GET"):
    seen = set()
    for route in app.app.routes:
        path = getattr(route, "path", "")
        if method not in (getattr(route, "methods", None) or ()):
            continue
        if path.startswith(("/docs", "/openapi", "/redoc", "/static",
                            "/frontend", "/logout")):
            continue
        if path not in seen:
            seen.add(path)
            yield path


class TestTheApiIsClosedByDefault:
    def test_no_api_route_answers_without_a_token(self, app, client):
        # Auth used to be declared route by route, and most routes did not:
        # /api/projects, /api/dashboard, /api/jobs-list and every
        # /api/resources/* served the admin's data to anyone on the port.
        leaks = [
            p for p in get_routes(app)
            if p.startswith("/api")
            and client.get(re.sub(r"\{[^}]+\}", "1", p)).status_code != 401
        ]
        assert leaks == [], f"{len(leaks)} API routes answer with no token"

    def test_no_data_route_outside_api_answers_without_a_token(self, app, client):
        # The gate treated every GET outside /api as an HTML shell page. 18 of
        # the 90 JSON routes out there had no per-route check and answered 200
        # anonymously — /projects/{id}/environment-variables,
        # /projects/{id}/configuration/history, /datasources/{id}/logs...
        # Only routes that really serve HTML, plus an explicit public list,
        # stay open now.
        # Pages are closed too: an anonymous page request is redirected to the
        # login, a JSON route answers 401. Nothing else is acceptable.
        leaks = []
        for p in get_routes(app):
            if p.startswith("/api") or p in app.PUBLIC_GET_PATHS:
                continue
            if p.endswith(app.PUBLIC_GET_SUFFIXES):
                continue
            url = re.sub(r"\{[^}]+\}", "1", p)
            r = client.get(url, follow_redirects=False)
            redirected_to_login = (r.status_code == 303
                                   and r.headers.get("location", "").endswith("/login"))
            if r.status_code != 401 and not redirected_to_login:
                leaks.append(f"{p} -> {r.status_code}")
        assert leaks == [], f"{len(leaks)} routes answer with no login: {leaks[:8]}"

    def test_the_routes_that_leaked_are_closed(self, client):
        for url in ("/projects/1/environment-variables",
                    "/projects/1/configuration/history",
                    "/datasources/1/logs"):
            assert client.get(url).status_code == 401, url

    def test_no_page_renders_data_to_an_anonymous_visitor(self, app, client, auth):
        # Three pages rendered data server-side with no login — the project
        # detail page put the project's name in its title. Seed markers and
        # look for them in every page an anonymous visitor can reach.
        import uuid
        from fastapi.responses import HTMLResponse

        marker = f"segredo{uuid.uuid4().hex[:10]}"
        project = client.post("/projects", json={"name": f"proj-{marker}",
                                                 "description": marker},
                              headers=auth)
        assert project.status_code == 201, project.text
        project_id = project.json()["id"]
        try:
            client.post(f"/projects/{project_id}/environment-variables",
                        json={"key": f"KEY_{marker}", "value": marker,
                              "is_secret": True}, headers=auth)
            leaking = []
            for route in app.app.router.routes:
                rc = getattr(route, "response_class", None)
                if not (isinstance(rc, type) and issubclass(rc, HTMLResponse)):
                    continue
                if "GET" not in (getattr(route, "methods", None) or ()):
                    continue
                url = re.sub(r"\{[^}]+\}", str(project_id), route.path)
                r = client.get(url)          # follows the redirect to /login
                if marker in r.text:
                    leaking.append(route.path)
            assert leaking == [], f"pages render data with no login: {leaking}"
        finally:
            client.delete(f"/projects/{project_id}", headers=auth)

    def test_the_public_get_list_still_opens(self, client):
        assert client.get("/health").status_code != 401
        assert client.get("/openapi.json").status_code == 200
        assert client.get("/login").status_code == 200
        assert client.get("/health/system").status_code == 401


def test_the_suite_never_touches_the_real_admin_database(app):
    # The database path was fixed at quantum_admin/quantum_admin.db, so every
    # test here created and deleted rows in the file the admin really serves.
    # tests/conftest.py points QUANTUM_ADMIN_DATABASE_URL at a temp file.
    from backend import database
    real = (ADMIN / "quantum_admin.db").resolve()
    assert str(real) not in database.DATABASE_URL, database.DATABASE_URL
    assert "quantum-admin-tests-" in database.DATABASE_URL


class TestTheSessionCookie:
    """Pages are opened by navigation, which cannot send the Bearer token the
    UI keeps in localStorage. The login sets the same token as a cookie."""

    @pytest.fixture
    def browser(self, app):
        # A client of its own: the shared one must stay anonymous.
        with TestClient(app.app, raise_server_exceptions=False) as c:
            yield c

    def test_login_sets_an_httponly_strict_cookie(self, browser):
        r = browser.post("/auth/login",
                         params={"username": "admin", "password": PASSWORD})
        assert r.status_code == 200
        set_cookie = r.headers.get("set-cookie", "").lower()
        assert "token=" in set_cookie
        assert "httponly" in set_cookie
        assert "samesite=strict" in set_cookie

    def test_the_cookie_opens_a_page(self, browser):
        browser.post("/auth/login", params={"username": "admin", "password": PASSWORD})
        r = browser.get("/projects", follow_redirects=False)
        assert r.status_code == 200

    def test_without_it_a_page_redirects_to_login(self, client):
        r = client.get("/projects", follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"].endswith("/login")

    def test_the_cookie_alone_cannot_write(self, browser):
        # Reads only. A write needs the header, which another site cannot
        # make the browser send — so the cookie cannot forge one (CSRF).
        browser.post("/auth/login", params={"username": "admin", "password": PASSWORD})
        r = browser.post("/projects", json={"name": "csrf-attempt", "description": ""})
        assert r.status_code == 401

    def test_logout_clears_it(self, browser):
        browser.post("/auth/login", params={"username": "admin", "password": PASSWORD})
        browser.get("/logout")
        r = browser.get("/projects", follow_redirects=False)
        assert r.status_code == 303

    def test_a_token_opens_them(self, app, client, auth):
        r = client.get("/api/projects", headers=auth)
        assert r.status_code == 200

    def test_a_junk_token_does_not(self, client):
        r = client.get("/api/projects",
                       headers={"Authorization": "Bearer nao-e-um-token"})
        assert r.status_code == 401

    def test_login_itself_stays_reachable(self, client):
        # A gate that blocks the login is a locked door with no key.
        assert client.get("/login").status_code == 200
        assert client.post(
            "/auth/login",
            params={"username": "admin", "password": PASSWORD},
        ).status_code == 200


class TestNenhumaEscritaSemToken:
    """O portao cobria SO `/api`, e a API real do admin vive na raiz.

    37 rotas de ESCRITA ficavam de fora — /settings/connectors,
    /docker/containers/{id}/start, /projects/{id}/deploy. Medido com o
    servidor de pe: `POST /settings/connectors/{id}/test` respondia 200 sem
    token nenhum.
    """

    ESCRITA = ("POST", "PUT", "PATCH", "DELETE")

    def test_nenhuma_rota_de_escrita_responde_sem_token(self, app, client):
        abertas = []
        for route in app.app.routes:
            caminho = getattr(route, "path", "")
            if caminho.startswith(("/docs", "/openapi", "/redoc", "/static",
                                   "/frontend")):
                continue
            for metodo in sorted(set(getattr(route, "methods", None) or ())
                                 & set(self.ESCRITA)):
                if caminho in ("/auth/login", "/auth/logout"):
                    continue
                if caminho.startswith(("/webhooks/", "/health")):
                    continue
                url = re.sub(r"\{[^}]+\}", "1", caminho)
                if client.request(metodo, url).status_code != 401:
                    abertas.append(f"{metodo} {caminho}")
        assert abertas == [], f"{len(abertas)} escritas sem token: {abertas[:6]}"

    def test_o_login_continua_publico(self, client):
        # Um portao que bloqueia o login e porta trancada sem chave.
        assert client.post(
            "/auth/login",
            params={"username": "admin", "password": PASSWORD},
        ).status_code == 200

    def test_o_webhook_chega_ao_proprio_handler(self, client):
        # Webhook nao carrega JWT — quem chama e o GitHub. Ele tem guarda
        # propria por assinatura, e o 401 daqui vem DELA (segredo ausente),
        # nao do portao.
        resposta = client.post("/webhooks/github", json={},
                               headers={"X-GitHub-Event": "push"})
        assert resposta.status_code in (401, 400)

    def test_com_token_a_escrita_passa(self, client, auth):
        criado = client.post("/projects",
                             json={"name": "proj-portao", "description": ""},
                             headers=auth)
        assert criado.status_code == 201, criado.text
        client.delete(f"/projects/{criado.json()['id']}", headers=auth)


class TestTheLoginPageCanActuallyLogIn:
    def test_the_fetch_target_is_a_real_path(self, client):
        body = client.get("/login").text
        assert "{URL_PREFIX}" not in body, (
            "the login page ships an unsubstituted placeholder; its fetch "
            "posts to /%7BURL_PREFIX%7D/auth/login, which is a 404"
        )
        assert "'/auth/login?" in body or '"/auth/login?' in body

    def test_no_page_ships_the_placeholder(self, app, client, auth):
        offenders = []
        for path in get_routes(app):
            r = client.get(re.sub(r"\{[^}]+\}", "1", path), headers=auth)
            ctype = r.headers.get("content-type", "")
            if ctype.startswith("text/html") and "{URL_PREFIX}" in r.text:
                offenders.append(path)
        assert offenders == [], offenders


class TestNoScreenCrashes:
    def test_no_route_answers_500(self, app, client, auth):
        # 503 is allowed: Docker really is absent here, and saying so is
        # correct. 500 means the handler itself is broken — which is how
        # /api/users/dashboard (db.query on a dataclass) and
        # /api/settings/dashboard (a method that does not exist) sat broken
        # behind the one auth check that worked.
        broken = []
        for path in get_routes(app):
            r = client.get(re.sub(r"\{[^}]+\}", "1", path), headers=auth)
            if r.status_code == 500:
                broken.append((path, r.status_code))
        assert broken == [], broken

    def test_the_core_screens_answer(self, client, auth):
        for path in ("/api/dashboard", "/api/projects", "/api/projects-grid",
                     "/api/jobs-list", "/api/jobs/dashboard",
                     "/api/settings/dashboard", "/api/users/dashboard"):
            assert client.get(path, headers=auth).status_code == 200, path


class TestUserManagementDoesTheWork:
    """The Users screen had Add/Edit/Delete buttons that alerted "TODO"."""

    @pytest.fixture
    def cleanup(self, client, auth):
        created = []
        yield created
        for username in created:
            client.delete(f"/auth/users/{username}", headers=auth)

    def test_a_user_can_be_created_and_deleted(self, client, auth, cleanup):
        created = client.post(
            "/auth/users",
            json={"username": "maria", "password": "uma-senha-boa-mesmo",
                  "role": "user"},
            headers=auth,
        )
        assert created.status_code == 200, created.text
        cleanup.append("maria")

        names = [u["username"] for u in client.get("/auth/users", headers=auth).json()]
        assert "maria" in names

        assert client.delete("/auth/users/maria", headers=auth).status_code == 200
        cleanup.clear()
        names = [u["username"] for u in client.get("/auth/users", headers=auth).json()]
        assert "maria" not in names

    def test_the_password_no_longer_has_to_travel_in_the_url(self, client, auth, cleanup):
        # It was query-only, so the password landed in access logs and
        # browser history. The query form still works; JSON is the new way.
        r = client.post("/auth/users",
                        json={"username": "joao", "password": "outra-senha-boa"},
                        headers=auth)
        assert r.status_code == 200
        cleanup.append("joao")

    def test_creating_without_a_password_is_a_400_not_a_crash(self, client, auth):
        r = client.post("/auth/users", json={"username": "sem-senha"},
                        headers=auth)
        assert r.status_code == 400

    def test_you_cannot_delete_the_account_you_are_using(self, client, auth):
        r = client.delete("/auth/users/admin", headers=auth)
        assert r.status_code == 400
        names = [u["username"] for u in client.get("/auth/users", headers=auth).json()]
        assert "admin" in names

    def test_deleting_someone_who_does_not_exist_is_a_404(self, client, auth):
        assert client.delete("/auth/users/fantasma",
                             headers=auth).status_code == 404

    def test_the_endpoints_need_a_token(self, client):
        assert client.post("/auth/users",
                           json={"username": "x", "password": "y"}).status_code == 401
        assert client.delete("/auth/users/x").status_code == 401

    def test_the_screen_no_longer_ships_todo_buttons(self, client, auth):
        body = client.get("/api/users/dashboard", headers=auth).text
        assert "TODO" not in body
        # And it says the store is in memory, because that is what happens
        # to a user created here when the process restarts.
        assert "memory" in body.lower()


class TestTheSettingsScreenTellsTheTruth:
    def test_it_does_not_offer_to_set_the_jwt_secret(self, client, auth):
        # auth_service reads the signing key from the environment only. A
        # field here would accept a value and change nothing.
        body = client.get("/api/settings/dashboard", headers=auth).text
        assert 'name="jwt_secret"' not in body
        assert "JWT_SECRET_KEY" in body

    def test_it_does_not_post_to_routes_that_do_not_exist(self, app, client, auth):
        body = client.get("/api/settings/dashboard", headers=auth).text
        posted = set(re.findall(r'hx-post="([^"]+)"', body))
        known = {p for p in get_routes(app, "POST")}
        for target in posted:
            path = target.split("?")[0]
            assert path in known, f"the settings form posts to {path}, a 404"


class TestDatasourcesCanBeEdited:
    """Dava para criar e excluir um datasource, nunca corrigi-lo.

    Havia criar, excluir, start/stop/restart, testar, logs e setup — e nenhum
    PUT. Errar o host ou a senha significava excluir e recriar, perdendo o
    histórico. O schema DatasourceUpdate já existia; ninguém tinha escrito a
    rota.
    """

    @pytest.fixture
    def datasource(self, client, auth):
        """Cria projeto + datasource, e limpa mesmo se o teste falhar.

        A primeira versao usava um nome fixo e so limpava DEPOIS do yield: um
        teste que falhasse no meio deixava o projeto para tras, e a proxima
        execucao morria no setup com "already exists". Suite que so passa uma
        vez nao e suite — foi o mesmo defeito corrigido em test-query-insert.q,
        cometido de novo aqui.

        Nome unico por execucao, e limpeza em try/finally.
        """
        import uuid

        nome = f"proj-ds-teste-{uuid.uuid4().hex[:8]}"
        project = client.post("/projects",
                              json={"name": nome, "description": ""},
                              headers=auth)
        assert project.status_code == 201, project.text
        project_id = project.json()["id"]

        criado = None
        try:
            criado = client.post(
                f"/projects/{project_id}/datasources",
                json={"name": "db1", "type": "postgres",
                      "connection_type": "direct", "host": "errado",
                      "port": 5432, "database_name": "app",
                      "username": "u", "password": "senha-antiga"},
                headers=auth)
            assert criado.status_code == 201, criado.text
            yield criado.json()["id"]
        finally:
            if criado is not None and criado.status_code == 201:
                client.delete(f"/datasources/{criado.json()['id']}", headers=auth)
            client.delete(f"/projects/{project_id}", headers=auth)

    def test_the_connection_details_can_be_corrected(self, client, auth, datasource):
        response = client.put(f"/datasources/{datasource}",
                              json={"host": "10.0.0.9", "port": 5433},
                              headers=auth)
        assert response.status_code == 200, response.text
        assert response.json()["host"] == "10.0.0.9"
        assert response.json()["port"] == 5433

    def test_the_password_is_stored_encrypted(self, client, auth, datasource):
        from backend import crud
        from backend.database import SessionLocal
        from backend.secret_manager import decrypt_or_legacy

        client.put(f"/datasources/{datasource}",
                   json={"password": "senha-nova"}, headers=auth)

        stored = crud.get_datasource(SessionLocal(), datasource)
        assert stored.password_encrypted != "senha-nova", "senha em texto puro"
        assert decrypt_or_legacy(stored.password_encrypted) == "senha-nova"

    def test_omitting_the_password_keeps_the_one_on_record(self, client, auth,
                                                           datasource):
        from backend import crud
        from backend.database import SessionLocal

        before = crud.get_datasource(SessionLocal(), datasource).password_encrypted
        client.put(f"/datasources/{datasource}", json={"host": "outro"},
                   headers=auth)
        after = crud.get_datasource(SessionLocal(), datasource).password_encrypted
        assert after == before, "alterar o host apagou a senha"

    def test_it_needs_a_token(self, client, datasource):
        assert client.put(f"/datasources/{datasource}",
                          json={"host": "x"}).status_code == 401

    def test_a_datasource_that_does_not_exist_is_a_404(self, client, auth):
        assert client.put("/datasources/999999", json={"host": "x"},
                          headers=auth).status_code == 404

    def test_an_invalid_port_is_refused(self, client, auth, datasource):
        assert client.put(f"/datasources/{datasource}", json={"port": 99999},
                          headers=auth).status_code == 422
