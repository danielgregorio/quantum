"""O `value=` inicial de um `ui:calendar` era apagado no carregamento.

O servidor renderiza a selecao certa nos tres modos — `_calendar_settings`
divide o `value` por virgula e monta `range_start`/`range_end`/`multiple`.
Mas o `init` do CALENDAR_JS montava o estado assim:

    selected: options.value ? parseDate(options.value) : null,
    rangeStart: null,
    rangeEnd: null,
    multiple: [],

e chamava `render()`, que reescreve o `innerHTML` do calendario. Ou seja:
com `mode="range" value="2026-01-05,2026-01-10"` a pagina aparecia por um
instante com as datas marcadas e ficava vazia. `parseDate` ainda recebia a
string INTEIRA, `"2026-01-05,2026-01-10"`, que vira Invalid Date.

E `parseDate` lia "2026-01-05" como meia-noite UTC enquanto o resto do
modulo usa os getters LOCAIS: a oeste de Greenwich o calendario marcava um
dia antes do que o servidor tinha renderizado.

O JS aqui roda de verdade, no node, contra um DOM minimo - nao e uma
assercao sobre o texto do arquivo.
"""

import json
import shutil
import subprocess

import pytest

from quantum.runtime.ui_html_templates import CALENDAR_JS

NODE = shutil.which('node')
pytestmark = pytest.mark.skipif(NODE is None, reason="node is not installed")


def _estado(opcoes):
    """Roda o init de verdade e devolve o estado resultante."""
    corpo = CALENDAR_JS.replace('<script>', '').replace('</script>', '')
    programa = f"""
const window = globalThis;
const elemento = {{ innerHTML: '', querySelector: () => null,
                    querySelectorAll: () => [] }};
globalThis.document = {{ getElementById: () => elemento }};

{corpo}

__quantumCalendar.init('cal', {json.dumps(opcoes)});
const s = __quantumCalendar.get('cal');
const iso = (d) => d ? d.getFullYear() + '-' +
    String(d.getMonth() + 1).padStart(2, '0') + '-' +
    String(d.getDate()).padStart(2, '0') : null;
console.log(JSON.stringify({{
    mode: s.mode,
    selected: iso(s.selected),
    rangeStart: iso(s.rangeStart),
    rangeEnd: iso(s.rangeEnd),
    multiple: s.multiple.map(iso),
    viewMonth: s.viewMonth,
    viewYear: s.viewYear,
    html: elemento.innerHTML,
}}));
"""
    saida = subprocess.run([NODE, '--input-type=module', '-e', programa],
                           capture_output=True, text=True, timeout=60)
    assert saida.returncode == 0, saida.stderr
    return json.loads(saida.stdout.strip().split('\n')[-1])


class TestModoRange:
    def test_as_duas_pontas_do_intervalo_sobrevivem_ao_init(self):
        s = _estado({'mode': 'range', 'value': '2026-01-05,2026-01-10'})
        assert s['rangeStart'] == '2026-01-05'
        assert s['rangeEnd'] == '2026-01-10'

    def test_o_grid_renderizado_marca_o_intervalo(self):
        s = _estado({'mode': 'range', 'value': '2026-01-05,2026-01-10'})
        assert 'range-start' in s['html'], s['html'][:400]
        assert 'range-end' in s['html']
        assert 'in-range' in s['html']

    def test_so_o_inicio_tambem_funciona(self):
        s = _estado({'mode': 'range', 'value': '2026-01-05'})
        assert s['rangeStart'] == '2026-01-05'
        assert s['rangeEnd'] is None

    def test_selected_nao_recebe_a_string_inteira(self):
        """parseDate("2026-01-05,2026-01-10") e Invalid Date."""
        s = _estado({'mode': 'range', 'value': '2026-01-05,2026-01-10'})
        assert s['selected'] is None


class TestModoMultiple:
    def test_todas_as_datas_sobrevivem_ao_init(self):
        s = _estado({'mode': 'multiple',
                     'value': '2026-01-05,2026-01-10,2026-01-20'})
        assert s['multiple'] == ['2026-01-05', '2026-01-10', '2026-01-20']

    def test_o_grid_marca_todas(self):
        s = _estado({'mode': 'multiple', 'value': '2026-01-05,2026-01-10'})
        assert s['html'].count('selected') >= 2, s['html'][:400]

    def test_espacos_em_volta_das_virgulas_nao_atrapalham(self):
        s = _estado({'mode': 'multiple', 'value': '2026-01-05 , 2026-01-10'})
        assert s['multiple'] == ['2026-01-05', '2026-01-10']


class TestModoSingle:
    def test_continua_funcionando(self):
        s = _estado({'mode': 'single', 'value': '2026-01-05'})
        assert s['selected'] == '2026-01-05'
        assert s['rangeStart'] is None and s['multiple'] == []

    def test_a_vista_abre_no_mes_da_data_escolhida(self):
        """Abria sempre no mes ATUAL, entao a selecao ficava invisivel."""
        s = _estado({'mode': 'single', 'value': '2020-03-15'})
        assert (s['viewYear'], s['viewMonth']) == (2020, 2)   # 2 = marco

    def test_sem_value_a_vista_e_o_mes_de_hoje(self):
        import datetime
        hoje = datetime.date.today()
        s = _estado({'mode': 'single'})
        assert (s['viewYear'], s['viewMonth']) == (hoje.year, hoje.month - 1)

    def test_um_value_invalido_nao_quebra_o_calendario(self):
        s = _estado({'mode': 'single', 'value': 'nao-e-data'})
        assert s['selected'] is None
        assert s['html'], "o calendario nem renderizou"


class TestFusoHorario:
    """`new Date("2026-01-05")` e meia-noite UTC; formatDate usa getters
    locais. A oeste de Greenwich a data voltava um dia — e o servidor, que
    usa date.fromisoformat, nao volta. Os dois discordavam."""

    def test_a_data_lida_e_a_data_escrita(self):
        s = _estado({'mode': 'single', 'value': '2026-01-05'})
        assert s['selected'] == '2026-01-05'

    def test_primeiro_dia_do_ano_nao_cai_no_ano_anterior(self):
        s = _estado({'mode': 'single', 'value': '2026-01-01'})
        assert s['selected'] == '2026-01-01'
        assert (s['viewYear'], s['viewMonth']) == (2026, 0)

    def test_uma_data_com_hora_continua_sendo_aceita(self):
        s = _estado({'mode': 'single', 'value': '2026-01-05T12:00:00'})
        assert s['selected'] == '2026-01-05'


class TestOServidorEOClienteConcordam:
    """O HTML do servidor e o estado do JS tem de marcar as mesmas datas."""

    def _servidor(self, fonte):
        from quantum.core.parser import QuantumParser
        from quantum.runtime.ui_html_adapter import UIHtmlAdapter
        app = QuantumParser(use_cache=False).parse(fonte)
        return UIHtmlAdapter().generate(app.ui_windows, app.ui_children, 'T')

    def test_range(self):
        html = self._servidor(
            '<q:application id="a" type="ui"><ui:window>'
            '<ui:calendar mode="range" value="2026-01-05,2026-01-10" />'
            '</ui:window></q:application>')
        assert 'range-start' in html and 'range-end' in html

        s = _estado({'mode': 'range', 'value': '2026-01-05,2026-01-10'})
        assert 'range-start' in s['html'] and 'range-end' in s['html']

    def test_multiple(self):
        html = self._servidor(
            '<q:application id="a" type="ui"><ui:window>'
            '<ui:calendar mode="multiple" value="2026-01-05,2026-01-10" />'
            '</ui:window></q:application>')
        assert html.count('selected') >= 2

        s = _estado({'mode': 'multiple', 'value': '2026-01-05,2026-01-10'})
        assert s['html'].count('selected') >= 2
