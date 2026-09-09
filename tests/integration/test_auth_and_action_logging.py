"""
Two failures that made the framework's own login unusable and undebuggable.

1. require_auth never authenticated anyone.

   is_authenticated was `session_data.get('authenticated', False) is True`,
   which demands the Python boolean. A .q attribute is a string:
   components/login.q line 19 — the framework's OWN login — writes

       <q:set name="session.authenticated" value="true" />

   storing "true", and "true" is not True. So a user who had just logged in
   successfully was bounced back to /login forever.

2. A failed q:action logged nothing.

   The 500 page says "check server logs for details" and the logs recorded
   absolutely nothing; the failure existed only as a flash message.
"""

import contextlib
import io
import logging

import pytest
from flask import Flask

from quantum.core.parser import QuantumParser
from quantum.runtime.action_handler import ActionHandler
from quantum.runtime.auth_service import AuthService
from quantum.runtime.component import ComponentRuntime


class TestAuthAcceptsWhatTheEngineStores:
    @pytest.mark.parametrize("value", [True, "true", "True", " TRUE ", "1", "yes", "on"])
    def test_written_truthy_forms_authenticate(self, value):
        assert AuthService.is_authenticated({"authenticated": value}) is True

    @pytest.mark.parametrize("value", [
        False, "false", "False", "no", "off", "0", "", None,
        "sim", "banana", "yes please", 1, 0, [], {}, [1],
    ])
    def test_everything_else_is_false(self, value):
        """Closed list — the fix must not widen what counts as authenticated.

        Note 1 (the integer) is deliberately NOT authenticated: only the
        written string forms and the real boolean count.
        """
        assert AuthService.is_authenticated({"authenticated": value}) is False

    def test_a_missing_flag_is_false(self):
        assert AuthService.is_authenticated({}) is False

    def test_the_frameworks_own_login_value_works(self):
        """components/login.q writes value="true" with no type attribute."""
        assert AuthService.is_authenticated({"authenticated": "true"}) is True

    def test_user_id_and_role_follow_the_same_rule(self):
        # Keys as components/login.q writes them: userId / userRole.
        s = {"authenticated": "true", "userId": 7, "userRole": "admin"}
        assert AuthService.get_user_id(s) == 7
        assert AuthService.get_user_role(s) == "admin"

    def test_user_id_is_none_when_not_authenticated(self):
        assert AuthService.get_user_id({"authenticated": "false", "userId": 7}) is None


class TestActionFailureIsLogged:
    def test_the_traceback_reaches_the_log(self, caplog):
        src = (
            '<q:component name="F">'
            '<q:action name="quebra" method="POST">'
            '<q:query name="q" datasource="inexistente">SELECT 1</q:query>'
            '</q:action></q:component>'
        )
        ast = QuantumParser().parse(src)
        action = next(s for s in ast.statements if type(s).__name__ == "ActionNode")

        app = Flask(__name__)
        app.secret_key = "t"
        rt = ComponentRuntime()

        with app.test_request_context("/quebra", method="POST"):
            with caplog.at_level(logging.ERROR, logger="quantum.action"):
                with contextlib.redirect_stdout(io.StringIO()):
                    url, status = ActionHandler(rt).handle_action(action)

        assert status == 500
        assert url is None, "a 500 must not carry a Location header"
        assert caplog.records, "the action failed and the log said nothing"
        assert "quebra" in caplog.text, "the log should name the action"
