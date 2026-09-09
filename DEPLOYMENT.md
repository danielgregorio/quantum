# Servir Quantum em produção

> `PRODUCTION_READINESS.md` Fase 5. Curto de propósito: são quatro coisas, e
> cada uma existe porque a falta dela causou um problema real medido nesta
> auditoria.

---

## 1. `quantum start` não é servidor de produção

Ele roda o servidor de **desenvolvimento** do Flask: um processo, sem
hardening, e desde a correção desta sessão ligado a `127.0.0.1` por padrão.
Use enquanto escreve o app, não para servi-lo.

O caminho de produção é um WSGI de verdade:

```bash
pip install gunicorn                      # não vem junto; é escolha sua
gunicorn 'quantum.runtime.web_server:create_app()' \
    --bind 0.0.0.0:8080 \
    --workers 4
```

> O docstring do `create_app` mandava `gunicorn 'src.runtime.web_server:...'`
> — o layout que deixou de existir quando `src/` virou o pacote `quantum/`.
> O único entry point de produção documentado **não importava**. Corrigido.

No Windows, `gunicorn` não roda; use `waitress`:

```bash
pip install waitress
waitress-serve --listen=0.0.0.0:8080 --call quantum.runtime.web_server:create_app
```

## 2. Defina a chave de sessão, ou os usuários caem aleatoriamente

Sem `QUANTUM_SECRET_KEY` (ou `security.secret_key` no config), **cada worker
gera a própria chave aleatória no import**. Um cookie assinado por um worker é
rejeitado pelo próximo, e o usuário é deslogado sem padrão aparente — o tipo de
bug que se persegue por dias.

```bash
export QUANTUM_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
```

`create_app()` avisa no log quando nenhuma das duas está definida.

## 3. O que deixar no `quantum.config.yaml`

```yaml
server:
  host: 0.0.0.0     # atrás do gunicorn/container; o bind real é do gunicorn
  debug: false      # SEMPRE. O debug do Werkzeug é um console de eval.
  reload: false     # o reload é de desenvolvimento

security:
  python_scripting: false   # é o DEFAULT; só ligue se o app usa q:python
```

O servidor **recusa** rodar o debugger fora de loopback mesmo que o config
peça, porque isso seria execução remota de código para quem alcançar a porta.
Mas não conte com essa rede de proteção: deixe `debug: false`.

Config inválido agora **falha no boot** em vez de cair em defaults em silêncio
— antes, um YAML quebrado descartava seus datasources, host e segurança e
servia com os padrões, com um único warning como aviso.

## 4. Se você serve o Quantum Admin

Ele é uma aplicação separada, com regras próprias. Em produção:

```bash
export QUANTUM_ADMIN_ENV=production            # recusa subir mal configurado
export JWT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export ADMIN_PASSWORD="<uma senha de verdade>"
export QUANTUM_ADMIN_CORS_ORIGINS="https://admin.seu-dominio"
```

Sem `QUANTUM_ADMIN_ENV=production` o admin **sobe assim mesmo**, com chave e
senha aleatórias por processo (a senha é impressa no boot). Isso é bom para
desenvolvimento e ruim para servir: cada worker assina com uma chave
diferente, então os usuários caem. Em produção, defina as duas.

Antes desta sessão a chave e a senha tinham defaults publicados neste
repositório — dava para forjar um token de admin sem nunca ver a tela de
login. Se você tem uma instalação antiga, gere valores novos.

`GITHUB_WEBHOOK_SECRET` / `GITLAB_WEBHOOK_TOKEN` são obrigatórios se você usa
os webhooks: sem eles as rotas **recusam** toda chamada (antes aceitavam
qualquer uma, e um push não assinado dispara deploy).

## 5. Mensageria

O broker default é **sqlite**: durável, sem servidor, um arquivo
(`quantum_messages.db` por padrão, ao lado de `quantum_jobs.db`).

```bash
export QUANTUM_MQ_PATH=/var/lib/quantum/messages.db   # opcional
```

Era `memory`, que vive dentro de um interpretador: sob gunicorn com quatro
workers, quatro filas privadas, e tudo enfileirado morre no restart. Perda
silenciosa de dados como padrão.

Onde o sqlite é ruim, para você decidir com informação: consumidores fazem
*polling* (há latência), não há cluster, e sqlite aceita um escritor por vez —
sob concorrência pesada de escrita ele engasga. Aí é `MESSAGE_BROKER_TYPE`
com `redis` ou `rabbitmq`. `memory` continua disponível e legítimo para um
app de processo único que não quer arquivo nenhum.

## 6. Verificação de saúde

`GET /health` responde 200. Use como readiness probe do container.

```bash
curl -fsS http://localhost:8080/health || exit 1
```

---

## Lista de conferência antes de expor

- [ ] `gunicorn`/`waitress` na frente, não `quantum start`
- [ ] `QUANTUM_SECRET_KEY` definida e estável entre workers
- [ ] `server.debug: false`
- [ ] `security.python_scripting` **desligado** — é o default agora; se o
      seu app o liga, confirme que todo `.q` que ele executa foi escrito por
      você. Sem sandbox, é Python arbitrário no processo (`SECURITY.md`)
- [ ] `paths.uploads` apontando para um diretório dedicado; `q:file` é
      confinado a ele
- [ ] Segredos por variável de ambiente, nunca no YAML versionado
- [ ] `/health` ligado ao orquestrador
- [ ] Ler `PRODUCTION_READINESS.md` — há críticos conhecidos em aberto, e
      expor isto publicamente hoje seria prematuro

## O que ainda não existe

Sendo direto, porque um documento de deploy que omite isso é pior que nenhum:

- **Não há imagem Docker oficial nem manifesto** — a receita acima é o que há.
- **`q:websocket` precisa de um extra**: o transporte é a biblioteca
  `websockets` (`pip install quantum[websocket]`). Sem ela a tag registra a
  conexão e **não abre nada** — e diz isso no log e no `transport` do
  resultado, em vez de fingir. É um cliente: `url=` aponta para outro
  servidor; Quantum não *serve* websockets.
- **Métricas e tracing** não existem além do log.
