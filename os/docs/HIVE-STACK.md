# Hive Stack - A Consciência do DruidOS

## O Que É

A Hive Stack é o conjunto de daemons Rust que formam a "consciência" do DruidOS. É uma IA local que **observa** o que você faz no sistema e **oferece sugestões** inteligentes.

**Filosofia:** "The Swarm is watching. The Swarm is learning."

---

## Arquitetura Visual

```
┌─────────────────────────────────────────────────────────────────────┐
│                           USUÁRIO                                   │
│                     (terminal, comandos)                            │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      hive-cortex (root)                             │
│                    ORQUESTRADOR CENTRAL                             │
│                                                                     │
│  - Recebe eventos de todos os nerves                                │
│  - Decide quando consultar a IA                                     │
│  - Envia ações para o actuator                                      │
│  - Socket: /run/hive/cortex.sock                                    │
└────┬──────────┬──────────┬──────────┬──────────┬───────────────────┘
     │          │          │          │          │
     ▼          ▼          ▼          ▼          ▼
┌─────────┐┌─────────┐┌─────────┐┌─────────┐┌─────────┐
│ nerve-  ││ nerve-  ││ nerve-  ││ nerve-  ││hive-    │
│ process ││ journal ││ network ││ fs      ││synapse  │
│         ││         ││         ││         ││         │
│Observa  ││Observa  ││Observa  ││Observa  ││CÉREBRO  │
│comandos ││logs     ││portas   ││arquivos ││(IA/SLM) │
└─────────┘└─────────┘└─────────┘└─────────┘└────┬────┘
                                                  │
                                                  ▼
                                           ┌───────────┐
                                           │ Qwen 0.5B │
                                           │  (GGUF)   │
                                           │  469 MB   │
                                           └───────────┘
```

---

## Os Componentes

### 1. hive-cortex (Orquestrador)
**Função:** Cérebro central que coordena tudo

```
Usuário: root
Socket:  /run/hive/cortex.sock
```

- Recebe mensagens de todos os outros componentes via IPC
- Decide o que fazer com cada evento
- Mantém contexto da sessão do usuário
- Roteia mensagens entre componentes

**Exemplo de fluxo:**
```
nerve-process detecta: "rm -rf /home/*"
       │
       ▼
cortex recebe evento "comando perigoso"
       │
       ▼
cortex envia para synapse: "usuário vai deletar home, o que sugerir?"
       │
       ▼
synapse responde: "Sugerir snapshot ZFS antes"
       │
       ▼
cortex mostra notificação ao usuário
```

---

### 2. hive-synapse (IA/Cérebro)
**Função:** Motor de inferência com modelo de linguagem local

```
Usuário: _hive-ai (sem privilégios)
Modelo:  Qwen 2.5 0.5B Instruct (Q4, 469MB)
```

- Roda modelo de linguagem **100% local** (sem internet)
- Recebe contexto do cortex
- Gera sugestões em linguagem natural
- Isolado em sandbox (sem rede, sem disco)

**Exemplo:**
```
Input:  "Usuário executou 'chmod 777 /etc/passwd'. Histórico mostra
         que ele está tentando resolver problema de permissão SSH."

Output: "O comando chmod 777 em /etc/passwd é perigoso e pode
         quebrar a autenticação. Sugiro: chmod 644 /etc/passwd.
         Para SSH, verifique ~/.ssh/authorized_keys com chmod 600."
```

---

### 3. hive-nerve-process (Observador de Comandos)
**Função:** Monitora comandos executados no terminal

```
Usuário: _hive-sense (somente leitura)
```

- Intercepta comandos antes de executar (via eBPF ou auditd)
- Detecta padrões perigosos: `rm -rf`, `chmod 777`, `dd if=/dev/zero`
- Envia eventos para cortex

**Padrões detectados:**
```yaml
- pattern: "rm -rf /"
  severity: critical
  action: block_and_warn

- pattern: "chmod 777"
  severity: high
  action: warn

- pattern: "curl | bash"
  severity: high
  action: warn
```

---

### 4. hive-nerve-journal (Observador de Logs)
**Função:** Monitora logs do sistema em tempo real

```
Usuário: _hive-sense
Fonte:   journald (systemd)
```

- Detecta erros e anomalias nos logs
- Correlaciona com ações do usuário
- Exemplos:
  - "nginx: bind() to 0.0.0.0:80 failed - Address already in use"
  - "sshd: Failed password for root from 192.168.1.100"

---

### 5. hive-nerve-network (Observador de Rede)
**Função:** Monitora portas e conexões

```
Usuário: _hive-sense
```

- Detecta conflitos de porta
- Monitora conexões suspeitas
- Exemplo: "Porta 3000 já está em uso pelo processo node (PID 1234)"

---

### 6. hive-nerve-fs (Observador de Filesystem)
**Função:** Monitora mudanças em arquivos críticos

```
Usuário: _hive-sense
Paths:   /etc, /var/log, /home
```

- Usa inotify para detectar mudanças
- Alerta sobre modificações em arquivos de configuração
- Exemplo: "/etc/nginx/nginx.conf foi modificado"

---

### 7. hive-actuator (Executor de Ações)
**Função:** Executa ações aprovadas pelo usuário

```
Usuário: _hive-act
```

- Único componente que pode FAZER coisas (não só observar)
- Lista branca de ações permitidas
- Rate-limited para segurança
- Exemplos de ações:
  - Criar snapshot ZFS
  - Reiniciar serviço
  - Corrigir permissão

---

### 8. hive-dashboard (Painel de Notificações)
**Função:** Mostra sugestões/notificações e deixa o usuário aprovar ou dispensar

```
Rodado manualmente pelo usuário (tipo `top`) — sem serviço systemd
```

- Conecta no cortex como qualquer outro componente
- Cada sugestão de uma `Notification` vira uma linha navegável
- Aprovar (Enter) manda `UserAction` — cortex monta o `ActionRequest` e despacha pro actuator
- Dispensar (`d`/Esc) manda `UserDismiss`

---

## Fluxo Completo: Exemplo Real

```
1. Usuário digita: rm -rf /var/log/*

2. nerve-process detecta comando perigoso
   └─> Envia para cortex: CommandObserved {
         cmd: "rm -rf /var/log/*",
         severity: high
       }

3. cortex analisa e consulta synapse
   └─> SuggestionRequest {
         context: "usuário quer deletar logs",
         history: [...últimos comandos...]
       }

4. synapse processa com IA local
   └─> SuggestionResponse {
         message: "Deletar /var/log pode quebrar logging.
                   Considere: journalctl --vacuum-size=500M",
         alternatives: ["logrotate -f", "truncate logs"]
       }

5. cortex guarda as sugestões e notifica o hive-dashboard
   (rodando num terminal separado, tipo `top`)
   ┌────────────────────────────────────────┐
   │ Hive Dashboard                         │
   │ Log Anomaly — journalctl --vacuum-size │
   │ [Enter] aprovar  [d] dispensar         │
   └────────────────────────────────────────┘

6. Usuário aprova (Enter) → dashboard manda UserAction → cortex monta
   o ActionRequest de verdade e despacha pro actuator
   └─> ActionRequest {
         action: CreateSnapshot { dataset: "rpool/var" }
       }
```

---

## Segurança

### Princípio do Menor Privilégio

| Componente | Usuário | Pode ler | Pode escrever | Rede |
|------------|---------|----------|---------------|------|
| cortex | root | tudo | socket IPC | não |
| synapse | _hive-ai | nada | nada | **não** |
| nerve-* | _hive-sense | logs, processos | nada | não |
| actuator | _hive-act | nada | ações whitelist | não |
| dashboard | usuário logado | notificações | socket IPC | não |

### Isolamento do Synapse
```
- Sem acesso à rede (não pode "ligar pra casa")
- Sem acesso ao disco (não pode ler seus arquivos)
- Só recebe texto do cortex
- Só retorna texto para cortex
- Seccomp restrito
```

---

## Protocolo IPC

Comunicação via Unix sockets com serialização bincode:

```rust
pub enum HiveMessage {
    // Nerve -> Cortex
    CommandObserved { pid: u32, cmd: String, cwd: PathBuf },
    LogAnomaly { service: String, message: String },
    PortConflict { port: u16, process: String },
    FileChanged { path: PathBuf, action: FileAction },

    // Cortex -> Synapse
    SuggestionRequest { context: Context, query: Option<String> },

    // Synapse -> Cortex
    SuggestionResponse { suggestions: Vec<Suggestion> },

    // Cortex -> Actuator
    ActionRequest { action: Action, confirm: bool },

    // Actuator -> Cortex
    ActionResult { success: bool, output: String },
}
```

---

## Modo Anônimo

Quando o usuário quer privacidade:

```bash
hive --quiet      # Hive observa mas não mostra notificações
hive --detach     # Este terminal é invisível para o Hive
hive --anonymous  # Namespace isolado, sem logging
```

---

## Componentes Desktop (Arquivados)

O alvo do projeto foi redefinido para TUI-only. hive-shell, hive-dock e
hive-term (junto com bark e spore, a stack de framebuffer que os
sustentava) foram movidos para `archive/`, fora do workspace ativo.
O código continua no histórico do git caso a GUI volte a ser prioridade.

O papel de "avisar o usuário" que hive-shell cumpria foi resolvido por
`hive-dashboard` — um painel TUI separado (ratatui), rodado manualmente
pelo usuário, não um overlay gráfico. Ver seção 8 acima.

---

## Status Atual

| Componente | Código | Compilado | Testado | Integrado |
|------------|--------|-----------|---------|-----------|
| hive-cortex | ✅ | ✅ | ✅ | ❌ |
| hive-synapse | ✅ | ✅ | ⚠️ mock | ❌ |
| hive-nerve-process | ✅ | ✅ | ✅ | ❌ |
| hive-nerve-journal | ✅ | ✅ | ✅ | ❌ |
| hive-nerve-network | ✅ | ✅ | ✅ | ❌ |
| hive-nerve-fs | ✅ | ✅ | ✅ | ❌ |
| hive-actuator | ✅ | ✅ | ✅ | ❌ |
| hive-dashboard | ✅ | ✅ | ✅ | ❌ |
| hive-shell | 📦 arquivado | - | - | - |
| hive-dock | 📦 arquivado | - | - | - |
| hive-term | 📦 arquivado | - | - | - |

**Legenda:**
- ✅ Completo
- ⚠️ Parcial (mock ou limitado)
- ❌ Não feito
- 📦 Arquivado (código em `archive/`, fora do escopo atual)

---

## Para Integrar no DruidOS

1. Copiar binários para `/usr/bin/hive-*`
2. Criar usuários: `_hive-ai`, `_hive-sense`, `_hive-act`
3. Criar services systemd
4. Configurar `/etc/hive/config.toml`
5. Copiar modelo para `/var/lib/hive/models/`
6. Habilitar services no boot
