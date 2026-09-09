"""f-string com expressao em varias linhas quebra no Python 3.11.

O pyproject promete 3.11 e 3.12, e o CI roda a matriz nas duas. Mas quem
desenvolve roda UMA versao — aqui 3.12 — e sintaxe nova passa despercebida.

Foi o que aconteceu com `quantum/runtime/renderer.py`: uma f-string de aspas
simples com a expressao quebrada em varias linhas DENTRO das chaves. Isso e
PEP 701, valido so no 3.12+; no 3.11 vira `SyntaxError: unterminated string
literal`. Como o renderer e importado por meio mundo, a coleta do pytest
morria com 16 erros — a suite inteira parava, verde local e vermelha no CI.

**O que este teste NAO e:** um verificador geral de compatibilidade com 3.11.
`ast.parse(feature_version=(3,11))` NAO serve para isso — foi a primeira coisa
que tentei e ele aceita a f-string multi-linha alegremente, porque
`feature_version` nao afeta o tokenizer, e f-string e coisa de tokenizer. Um
teste assim daria falsa confianca.

**O que ele e:** deteccao do padrao exato que quebrou, via `tokenize`. Uma
f-string de aspas SIMPLES (`f"..."` / `f'...'`) que termina numa linha
diferente da que comeca so pode estar atravessando linhas por causa de uma
expressao multi-linha nas chaves — que e a construcao 3.12+. f-strings de
aspas TRIPLAS podem atravessar linhas desde sempre e sao ignoradas.

A cobertura de verdade para 3.11 e a matriz do CI; isto so traz o feedback
para a maquina de quem escreve, antes do push.
"""

import io
import pathlib
import subprocess
import tokenize

import pytest

RAIZ = pathlib.Path(__file__).resolve().parents[2]


def fstrings_multilinha(fonte: str):
    """Linhas com f-string de aspas simples que atravessa linhas (PEP 701).

    Devolve [] em interpretadores anteriores ao 3.12, onde o tokenizer nao
    emite FSTRING_START — la a construcao nem parseia, entao nao ha o que
    detectar.
    """
    inicio_fstring = getattr(tokenize, 'FSTRING_START', None)
    fim_fstring = getattr(tokenize, 'FSTRING_END', None)
    if inicio_fstring is None or fim_fstring is None:
        return []

    achados = []
    pilha = []
    try:
        tokens = tokenize.generate_tokens(io.StringIO(fonte).readline)
        for tok in tokens:
            if tok.type == inicio_fstring:
                # tok.string e o prefixo+abertura: f", f', f""", rf', ...
                triplo = tok.string.endswith('"""') or tok.string.endswith("'''")
                pilha.append((tok.start[0], triplo))
            elif tok.type == fim_fstring and pilha:
                linha_inicio, triplo = pilha.pop()
                if not triplo and tok.end[0] > linha_inicio:
                    achados.append(linha_inicio)
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # Arquivo que nem tokeniza aqui: problema de outra natureza.
        return []
    return achados


def _arquivos_python():
    saida = subprocess.run(
        ['git', 'ls-files', '*.py'], cwd=RAIZ,
        capture_output=True, text=True).stdout.split()
    return [RAIZ / f for f in saida]


class TestODetectorFunciona:
    """Antes de confiar no detector, provar que ele detecta."""

    def test_pega_o_padrao_que_quebrou(self):
        ruim = 'x = f"a {json.dumps(\n    1\n)} b"\n'
        assert fstrings_multilinha(ruim) == [1], "o detector nao pegou o caso real"

    def test_nao_acusa_fstring_normal(self):
        ok = 'x = f"a {y} b"\nz = f"{a}{b}"\n'
        assert fstrings_multilinha(ok) == []

    def test_nao_acusa_fstring_de_aspas_triplas(self):
        """Aspas triplas atravessam linhas desde sempre — sao legitimas."""
        ok = 'x = f"""\nlinha 1 {y}\nlinha 2\n"""\n'
        assert fstrings_multilinha(ok) == []

    def test_pega_o_renderer_PRE_correcao(self):
        """A prova que importa: rodar o detector contra o codigo que
        realmente quebrou o CI, recuperado do git."""
        pre = subprocess.run(
            ['git', 'show', 'f9aa006:quantum/runtime/renderer.py'],
            cwd=RAIZ, capture_output=True, text=True)
        if pre.returncode != 0 or not pre.stdout:
            pytest.skip("commit pre-correcao nao esta neste checkout")
        assert fstrings_multilinha(pre.stdout), (
            "o detector NAO pegou o bug historico — nao serve")


class TestOCodigoAtual:
    def test_nenhuma_fstring_multilinha_no_repo(self):
        arquivos = _arquivos_python()
        assert len(arquivos) > 100, "git ls-files nao achou o codigo?"

        problemas = []
        for caminho in arquivos:
            try:
                fonte = caminho.read_text(encoding='utf-8')
            except (UnicodeDecodeError, OSError):
                continue
            for linha in fstrings_multilinha(fonte):
                problemas.append(f"{caminho.relative_to(RAIZ)}:{linha}")

        assert not problemas, (
            "f-string de aspas simples atravessando linhas (PEP 701) nao "
            "compila no Python 3.11, que o pyproject promete suportar. "
            "Ponha a expressao numa variavel antes:\n  " +
            "\n  ".join(problemas))
