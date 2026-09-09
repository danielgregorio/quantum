# Devlog: Pretty-print HTML Output

**Data:** 2026-01-30
**Projeto:** Quantum Framework (core runtime)
**Status:** Deployado no forge (10.10.1.40), container `quantum-blog` atualizado

---

## Objetivo

O HTML renderizado pelo Quantum saia em uma unica linha — sem indentacao, sem quebras entre tags. Isso dificultava a leitura no View Source do browser e debug em geral.

## O que foi feito

### Metodo `_prettify_html` no web_server.py

Adicionado um pos-processador de HTML em `src/runtime/web_server.py` que indenta o output final antes de retornar a response. Abordagem puramente string-based, sem dependencias externas.

**Arquivo modificado:**
- `src/runtime/web_server.py` — novo metodo `_prettify_html(self, html: str) -> str`

### Como funciona

1. Tokeniza o HTML em tags e segmentos de texto via regex (`(<[^>]+>)`)
2. Rastreia profundidade de nesting para elementos block-level
3. Adiciona newlines + indentacao (2 espacos) ao redor de tags block-level
4. Preserva conteudo dentro de `<pre>` e `<textarea>` verbatim (whitespace-sensitive)
5. Mantem elementos inline (`<span>`, `<a>`, `<strong>`, etc.) na mesma linha do conteudo
6. Trata void/self-closing elements (`<br>`, `<img>`, `<meta>`, `<link>`, `<input>`) sem incrementar depth

**Elementos block-level tratados:**
`html, head, body, header, footer, main, section, nav, article, aside, div, ul, ol, li, table, thead, tbody, tr, th, td, form, fieldset, h1-h6, p, blockquote, figure, figcaption, details, summary, title, script, style, noscript, template`

**Elementos void:**
`br, hr, img, input, meta, link, col, area, base, embed, source, track, wbr`

**Elementos inline (sem whitespace extra):**
`a, span, strong, em, b, i, u, small, sub, sup, abbr, cite, code, label, button, select, option, time, mark`

### Integracao

Chamado em `_serve_component` logo apos `_extract_inline_assets`, antes de retornar a response:

```python
full_html = self._extract_inline_assets(full_html)
full_html = self._prettify_html(full_html)
return Response(full_html, mimetype='text/html')
```

### Algoritmo (resumo)

```
tokens = split HTML em tags e texto
depth = 0

para cada token:
    se closing block tag (</div>): depth--, indenta, newline
    se opening block tag (<div>): indenta, newline, depth++
    se void element (<br>, <img>): indenta, newline (sem mudar depth)
    se <!DOCTYPE> ou comentario: indenta, newline
    se inline ou texto: sem whitespace extra, indenta so se inicio de linha
```

Preservacao de whitespace: quando dentro de `<pre>` ou `<textarea>`, todo conteudo e emitido verbatim ate a closing tag.

## Deploy

Deploy feito via paramiko (SSH) pois `sshpass` nao estava disponivel no ambiente Windows:

```
1. Upload web_server.py via SFTP para /tmp/ no servidor
2. docker cp /tmp/web_server.py quantum-blog:/app/src/runtime/web_server.py
3. docker restart quantum-blog
```

Ambos containers (`quantum-blog` e `quantum-quantum-blog`) foram atualizados.

## Resultado

**Antes:**
```html
<!DOCTYPE html><html><head><title>Quantum Blog</title><meta name="viewport"...><script src="..."></script></head><body><header><div class="header-inner">...
```

**Depois:**
```html
<!DOCTYPE html>
<html>
  <head>
    <title>Quantum Blog</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    <link rel="stylesheet" href="static/styles-1432583c0d.css">
  </head>
  <body>
    <header>
      <div class="header-inner">
        <a href="/quantum-blog/" class="logo">...</a>
        <nav>
          ...
        </nav>
      </div>
    </header>
    ...
  </body>
</html>
```

Pagina renderiza identicamente no browser — apenas o View Source ficou legivel.

## Notas

- Zero dependencias novas (sem BeautifulSoup, sem lxml)
- Impacto de performance minimo — regex split + loop linear
- Versao inicial teve problema com `<title>`, `<script>`, `<style>` nao sendo indentados (faltavam na lista de block elements). Corrigido na segunda iteracao.
