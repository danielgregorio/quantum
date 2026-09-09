"""SQL correto era recusado no parse por causa de `:` dentro de aspas.

O parser exige que todo `:nome` no SQL tenha um `<q:param>` correspondente —
uma boa regra, que existe para pegar o parametro esquecido. Mas a varredura
era um `re.findall(r':([a-zA-Z_]\\w*)', sql)` sobre o SQL CRU, e portanto
tambem sobre o que esta dentro de literais de texto e de comentarios:

    TO_CHAR(c.created_at, 'YYYY-MM-DD HH24:MI')   ->  achava `:MI`
    SELECT x::text FROM t                         ->  achava `:text`

As duas formas sao SQL comum. A primeira aparece em
projects/blog/components/post.q, que por causa disso nao parseava: o arquivo
era recusado com "SQL parameter(s) :MI declared in SQL but no matching
<q:param> element provided" — e nao havia parametro nenhum para declarar.
Nao havia o que fazer a nao ser reescrever o SQL.
"""

import pytest

from quantum.core.parser import QuantumParser, QuantumParseError
from quantum.core.parsers.data.query_parser import QueryParser


class TestAVarredura:
    @pytest.mark.parametrize("sql,esperado", [
        # o que E parametro
        ("SELECT * FROM t WHERE id = :id", {'id'}),
        ("INSERT INTO t (a, b) VALUES (:a, :b)", {'a', 'b'}),
        ("SELECT * FROM t WHERE a = :a AND b = :b", {'a', 'b'}),
        # o que NAO e
        ("SELECT TO_CHAR(x, 'HH24:MI') FROM t", set()),
        ("SELECT TO_CHAR(x, 'YYYY-MM-DD HH24:MI:SS') FROM t", set()),
        ("SELECT x::text FROM t", set()),
        ("SELECT x::int, y::text FROM t", set()),
        ("SELECT 1 -- comentario com :naoeh\n", set()),
        ("SELECT 1 /* bloco com :naoeh */", set()),
        ('SELECT "coluna:estranha" FROM t', set()),
        ("SELECT 'literal com ''aspas'' e :naoeh' FROM t", set()),
        # misturado
        ("SELECT TO_CHAR(x, 'HH24:MI') FROM t WHERE id = :id", {'id'}),
        ("SELECT x::text FROM t WHERE a = :a", {'a'}),
        ("SELECT 1 /* :nao */ WHERE a = :a -- :nao2\n", {'a'}),
    ])
    def test_so_os_parametros_de_verdade(self, sql, esperado):
        assert QueryParser._named_params(sql) == esperado


class TestPeloParserDeVerdade:
    def _parse(self, sql, params=''):
        fonte = (f'<q:component name="C">'
                 f'<q:query name="q" datasource="db">{sql}{params}</q:query>'
                 f'</q:component>')
        return QuantumParser(use_cache=False).parse(fonte)

    def test_um_formato_de_data_com_dois_pontos_e_aceito(self):
        self._parse("SELECT TO_CHAR(c.created_at, 'YYYY-MM-DD HH24:MI') "
                    "as created_at FROM comments")

    def test_um_cast_do_postgres_e_aceito(self):
        self._parse("SELECT id::text FROM users")

    def test_um_parametro_de_verdade_sem_q_param_CONTINUA_sendo_recusado(self):
        """A regra existe para pegar o parametro esquecido; nao pode sumir."""
        with pytest.raises(QuantumParseError, match=":id"):
            self._parse("SELECT * FROM t WHERE id = :id")

    def test_com_o_q_param_declarado_passa(self):
        self._parse("SELECT * FROM t WHERE id = :id",
                    '<q:param name="id" value="1" />')

    def test_um_parametro_esquecido_ao_lado_de_um_formato_de_data(self):
        """O caso misto: a data nao pode mascarar o parametro que falta."""
        with pytest.raises(QuantumParseError, match=":user_id"):
            self._parse("SELECT TO_CHAR(x, 'HH24:MI') FROM t "
                        "WHERE user_id = :user_id")


class TestOArquivoQueNaoParseava:
    def test_projects_blog_components_post_q(self):
        import pathlib
        raiz = pathlib.Path(__file__).resolve().parents[2]
        alvo = raiz / 'projects' / 'blog' / 'components' / 'post.q'
        if not alvo.exists():
            pytest.skip("o arquivo nao esta neste checkout")
        QuantumParser(use_cache=False).parse_file(str(alvo))
