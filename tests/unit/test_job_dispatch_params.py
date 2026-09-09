"""q:job action="dispatch" discarded every parameter value.

_parse_param in the monolithic parser read `default=` but never `value=`.
value= is how a CALL SITE passes an argument (q:job dispatch, q:invoke),
while declaration sites (q:function, q:action) use default=. So every
<q:param name="to" value="a@b.c" /> inside a q:job arrived empty and each
dispatched job got nulls — while the dispatch reported success.
"""
import pytest
from quantum.core.parser import QuantumParser


def _job(src_params):
    src = (f'<q:component name="J">'
           f'<q:job name="envio" action="dispatch">{src_params}</q:job>'
           f'</q:component>')
    ast = QuantumParser().parse(src)
    return next(s for s in ast.statements if type(s).__name__ == 'JobNode')


class TestJobParamsCarryTheirValue:
    def test_value_is_parsed(self):
        job = _job('<q:param name="to" value="a@b.c" />')
        assert job.params[0].value == "a@b.c"

    def test_several_params(self):
        job = _job('<q:param name="to" value="a@b.c" /><q:param name="id" value="42" />')
        assert [(p.name, p.value) for p in job.params] == [("to", "a@b.c"), ("id", "42")]

    def test_a_databinding_placeholder_survives_to_the_executor(self):
        job = _job('<q:param name="to" value="{dest}" />')
        assert job.params[0].value == "{dest}"

    def test_default_still_works_for_declaration_sites(self):
        src = ('<q:component name="F"><q:function name="f">'
               '<q:param name="n" type="number" default="7" />'
               '<q:return value="{n}" /></q:function></q:component>')
        ast = QuantumParser().parse(src)
        fn = next(s for s in ast.statements if type(s).__name__ == 'FunctionNode')
        assert fn.params[0].default == "7"
        assert fn.params[0].value is None
