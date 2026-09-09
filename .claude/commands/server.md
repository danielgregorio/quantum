# Agente de Server Quantum

Voce e um agente especializado em gerenciar o ciclo de vida do Quantum Web Server.

## Uso

```
/server              # Mostra status do server
/server start        # Sobe o server em background
/server stop         # Para o server via PID
/server restart      # Stop + Start
/server logs         # Mostra ultimas 30 linhas do quantum.log
/server logs -f      # Tail continuo do log
```

O argumento passado pelo usuario esta em: $ARGUMENTS

## Workflow por Subcomando

### Determinar Subcomando

Analisar `$ARGUMENTS`:
- Vazio ou `status` -> executar **Status**
- `start` -> executar **Start**
- `stop` -> executar **Stop**
- `restart` -> executar **Restart**
- `logs` -> executar **Logs**
- `logs -f` -> executar **Logs (follow)**

---

### Status (`/server` ou `/server status`)

1. Checar se `.quantum.pid` existe na raiz do projeto
2. Se nao existe, reportar: **Server parado** (nenhum PID file encontrado)
3. Se existe, ler o PID do arquivo
4. Verificar se o processo esta vivo:
   - **Windows**: `tasklist /FI "PID eq {pid}" /NH`
   - **Unix/Mac**: `kill -0 {pid}`
5. Ler `quantum.config.yaml` para obter a porta (`server.port`)
6. Fazer health check: `curl -s http://localhost:{port}/health`
7. Reportar ao usuario:
   - Estado: rodando ou parado (PID stale)
   - PID do processo
   - Porta configurada
   - Resultado do health check

---

### Start (`/server start`)

1. **Checar se ja esta rodando**:
   - Se `.quantum.pid` existe e o processo esta vivo, avisar o usuario e nao iniciar outro
2. **Ler configuracao**:
   - Ler `quantum.config.yaml` para obter a porta (`server.port`)
3. **Iniciar o server**:
   - Rodar via Bash com `run_in_background=true`:
     ```
     quantum start
     ```
4. **Smoke test**:
   - Aguardar alguns segundos: `sleep 3`
   - Fazer health check: `curl -s http://localhost:{port}/health`
5. **Reportar resultado**:
   - Se health check respondeu: Server rodando na porta {port}
   - Se nao respondeu: Avisar que o server pode ter falhado ao iniciar, sugerir `/server logs`

---

### Stop (`/server stop`)

1. **Parar o server**:
   - Rodar via Bash: `quantum stop`
2. **Confirmar**:
   - Verificar que `.quantum.pid` foi removido
3. **Reportar resultado**:
   - Sucesso ou falha, incluindo mensagem de saida do comando

---

### Restart (`/server restart`)

1. Executar o workflow de **Stop** (ignorar erro se server ja estava parado)
2. Aguardar 1 segundo: `sleep 1`
3. Executar o workflow de **Start**

---

### Logs (`/server logs`)

1. **Ler configuracao**:
   - Ler `quantum.config.yaml` para obter:
     - Path de logs: `paths.logs` (default: `./logs`)
     - Nome do arquivo: `logging.filename` (default: `quantum.log`)
   - Caminho final: `{paths.logs}/{logging.filename}`
2. **Modo normal** (`/server logs`):
   - Usar a tool Read para mostrar as ultimas 50 linhas do arquivo de log
   - Se o arquivo nao existir, informar ao usuario
3. **Modo follow** (`/server logs -f`):
   - Usar Bash com `run_in_background=true`: `tail -f {log_path}`
   - Informar o usuario que o tail esta rodando em background

---

## Arquivos Relevantes

| Arquivo | Descricao |
|---------|-----------|
| `.quantum.pid` | PID file do server (criado automaticamente) |
| `quantum.config.yaml` | Configuracao do server (porta, host, logs) |
| `logs/quantum.log` | Arquivo de log do server |
| `quantum/cli/runner.py` | CLI com comandos `start` e `stop` |
| `src/runtime/web_server.py` | Web server Flask (grava PID, endpoint /health) |

## Regras

- Sempre verificar status antes de start para evitar duplicatas
- Sempre fazer smoke test (health check) apos start
- Server roda em background via `run_in_background=true` do Bash
- Ler a porta de `quantum.config.yaml`, nunca usar valor hardcoded
- No Windows, usar `tasklist` para checar processo; no Unix, usar `kill -0`
- Se o PID file existir mas o processo nao estiver vivo, considerar como server parado (PID stale)
- Reportar resultados de forma clara e concisa ao usuario
