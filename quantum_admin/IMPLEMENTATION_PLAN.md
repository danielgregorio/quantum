# Quantum Admin - Plano de Implementacao

## Visao Geral

10 tasks organizadas em 4 fases, priorizando:
1. Quick wins e fundacao
2. Features que outras dependem
3. Features de alto valor
4. Polish e extras

---

## Fase 1: Fundacao (Base para outras features)

### 1.1 Link para Docs no Menu [#3]
**Complexidade:** Baixa (15 min)
**Dependencias:** Nenhuma

```
Arquivos:
- main.py: Adicionar item no menu lateral do get_admin_shell()

Implementacao:
1. Adicionar link no nav com icone de livro + external link
2. URL configuravel via settings (dev vs prod)
```

---

### 1.2 Audit Log - Modelo Base [#8]
**Complexidade:** Media (2-3h)
**Dependencias:** Nenhuma
**Prioridade:** Alta (precisa estar pronto para integrar nas outras features)

```
Arquivos:
- models.py: AuditLog model
- audit_service.py: Helper audit_log()
- main.py: Endpoint GET /projects/{id}/audit-log

Implementacao:
1. Criar modelo AuditLog no banco
2. Criar helper audit_log(db, user, action, resource_type, ...)
3. Criar endpoint para listar audit logs
4. Criar UI basica (aba na Application)
5. Integrar nos endpoints existentes (CRUD de projects, envs, etc)

Modelo:
- id, timestamp, user_id, user_ip
- action (create, update, delete, deploy, rollback, login, etc)
- resource_type, resource_id, resource_name
- details (JSON com old/new values)
- project_id
```

---

### 1.3 Resource Manager - Auto-discovery [#4]
**Complexidade:** Alta (4-5h)
**Dependencias:** Nenhuma
**Prioridade:** Alta (base para Health Monitoring e Dashboard)

```
Arquivos:
- resource_manager.py: Servico central
- main.py: Endpoints /resources/*
- Atualizar UI da pagina Resources

Implementacao:
1. Scanner de portas em uso (psutil)
2. Detector de processos Quantum
3. Integracao com Docker (containers)
4. Alocador automatico de portas
5. UI read-only com opcao de override manual
6. Background task para refresh periodico

Funcoes principais:
- scan_ports() -> Set[int]
- scan_processes() -> List[ProcessInfo]
- allocate_port(app_name) -> int
- release_port(port)
- get_resource_overview() -> ResourceStats
```

---

## Fase 2: Core Features

### 2.1 Dashboard com Metricas [#6]
**Complexidade:** Media (3-4h)
**Dependencias:** Resource Manager (#4), Audit Log (#8)

```
Arquivos:
- main.py: Atualizar get_dashboard_content()
- Endpoints: /dashboard/stats, /dashboard/activity

Implementacao:
1. Cards de metricas (Applications, Connectors, Environments, Users)
2. Cards secundarios (Jobs, Tests, Containers, Requests)
3. Recent Activity (ultimos eventos do audit log)
4. System Health (status dos servicos)
5. Quick Actions (atalhos)

Dados:
- Queries ao banco para contagens
- Resource Manager para containers/portas
- Audit Log para atividade recente
```

---

### 2.2 Aba de Logs [#7]
**Complexidade:** Alta (5-6h)
**Dependencias:** Nenhuma (mas integra com apps existentes)

```
Arquivos:
- log_service.py: Coleta e busca de logs
- main.py: Endpoints /api/projects/{id}/logs
- WebSocket para real-time (opcional)
- UI: Nova aba na Application

Implementacao:
1. Definir fontes de log (stdout, arquivos, Docker)
2. Parser de logs com niveis (info, warn, error)
3. Sistema de busca basico (texto, filtros)
4. Sub-abas: All, Application, Database, Access, Errors
5. UI com auto-refresh e highlight
6. Export de logs

Armazenamento:
- Logs em memoria (ultimos N)
- Arquivos rotativos para historico
- Configuracao de retencao
```

---

### 2.3 Migrations SQLite -> PostgreSQL [#1]
**Complexidade:** Media (3-4h)
**Dependencias:** Nenhuma

```
Arquivos:
- src/cli/commands/migrate.py: CLI de migrations
- src/runtime/database_service.py: Failover logic
- projects/blog/scripts/migrate_data.py

Implementacao:
1. CLI: quantum migrate up/down/status
2. Tabela _migrations para tracking
3. Failover: tentar Postgres, fallback SQLite
4. Script de migracao de dados
5. Config unificada no quantum.config.yaml

Fluxo de failover:
1. Tentar conectar primary (Postgres)
2. Se falhar, usar fallback (SQLite)
3. Log warning
4. Retry periodico ao primary
```

---

## Fase 3: Deploy & Observability

### 3.1 Rollback com 1 Clique [#9]
**Complexidade:** Media (3-4h)
**Dependencias:** Deploy system existente, Audit Log (#8)

```
Arquivos:
- models.py: DeployHistory model
- deploy_service.py: Logica de rollback
- main.py: Endpoint POST /projects/{id}/environments/{env}/rollback
- UI: Historico de deploys com botao rollback

Implementacao:
1. Modelo DeployHistory (version, git_commit, image_tag, etc)
2. Salvar historico a cada deploy
3. Endpoint de rollback
4. UI com lista de versoes e botao rollback
5. Confirmacao antes de rollback
6. Audit log do rollback

Fluxo:
1. Usuario clica rollback em versao anterior
2. Confirmacao: "Voltar para v1.2.3?"
3. Stop container atual
4. Start container com tag antiga
5. Health check
6. Atualizar is_current
```

---

### 3.2 Health, Monitoring e Availability [#2]
**Complexidade:** Alta (5-6h)
**Dependencias:** Resource Manager (#4)

```
Arquivos:
- models.py: HealthCheck, Incident
- health_service.py: Logica de health checks
- metrics_service.py: Coleta de metricas
- main.py: Endpoints /projects/{id}/health, /metrics
- UI: Secao Health na Application e Environment

Implementacao:
1. Modelo HealthCheck (endpoint, interval, status)
2. Background job para health checks periodicos
3. Modelo Incident para registrar downtimes
4. Metricas: latency, error rate, requests/min
5. UI: Cards de status na Application
6. UI: Status por Environment
7. Integracao com Uptime Kuma (opcional)

Health checks:
- HTTP GET ao endpoint configurado
- Timeout e retries
- Atualizar status (healthy, degraded, unhealthy)
- Criar Incident se falhar X vezes
```

---

### 3.3 Integracoes Cloud [#5]
**Complexidade:** Alta (6-8h)
**Dependencias:** Deploy system, Audit Log (#8)

```
Arquivos:
- integrations/
  - base.py: Interface base
  - aws_connector.py
  - azure_connector.py
  - gcp_connector.py
  - k8s_connector.py
- models.py: CloudIntegration
- main.py: Endpoints /integrations/*
- UI: Secao em Settings ou menu proprio

Implementacao por provedor:

AWS:
1. Credenciais (Access Key ou IAM Role)
2. Deploy para ECS/EKS/App Runner
3. Usar boto3

Kubernetes:
1. Kubeconfig ou API token
2. Deploy via kubectl/API
3. Usar kubernetes-client

Azure:
1. Service Principal ou Managed Identity
2. Deploy para App Service/Container Apps
3. Usar azure-mgmt-*

GCP:
1. Service Account
2. Deploy para Cloud Run/GKE
3. Usar google-cloud-*

UI:
1. Lista de integracoes configuradas
2. Modal para adicionar nova
3. Test connection
4. Selecao no deploy
```

---

## Fase 4: Polish & DX

### 4.1 Templates de Aplicacao [#10]
**Complexidade:** Media (4-5h)
**Dependencias:** Nenhuma (mas melhor ter outras features prontas)

```
Arquivos:
- templates/
  - blog/
  - api/
  - dashboard/
  - landing/
  - blank/
- template_service.py: Logica de scaffolding
- main.py: Endpoint POST /projects/from-template
- UI: Atualizar modal New Application

Implementacao:
1. Estrutura de templates no filesystem
2. template.yaml com metadata e opcoes
3. Processador de variaveis ({{APP_NAME}})
4. Servico para copiar e processar
5. UI com grid de templates
6. Opcoes por template (auth, database, etc)

Templates iniciais:
- Blog: Posts, tags, admin, SQLite
- REST API: CRUD, JWT, Swagger
- Dashboard: Cards, graficos, tabelas
- Landing: Hero, features, contact
- Blank: Estrutura minima
```

---

## Cronograma Sugerido

```
Semana 1: Fundacao
├── Dia 1: #3 Link Docs (15min) + #8 Audit Log modelo (2h)
├── Dia 2: #8 Audit Log integracao (2h) + #4 Resource Manager inicio (2h)
├── Dia 3: #4 Resource Manager (4h)
├── Dia 4: #4 Resource Manager UI + testes (2h)
└── Dia 5: Buffer / Refinamentos

Semana 2: Core Features
├── Dia 1: #6 Dashboard backend (2h)
├── Dia 2: #6 Dashboard UI (2h) + #7 Logs inicio (2h)
├── Dia 3: #7 Logs service + busca (4h)
├── Dia 4: #7 Logs UI + sub-abas (3h)
└── Dia 5: #1 Migrations (3h)

Semana 3: Deploy & Observability
├── Dia 1: #9 Rollback modelo + backend (3h)
├── Dia 2: #9 Rollback UI (2h) + #2 Health inicio (2h)
├── Dia 3: #2 Health checks + metricas (4h)
├── Dia 4: #2 Health UI (2h)
└── Dia 5: Buffer / Testes

Semana 4: Cloud & Templates
├── Dia 1-2: #5 Cloud - AWS + K8s (4h cada)
├── Dia 3: #5 Cloud - Azure + GCP (4h)
├── Dia 4: #10 Templates estrutura + servico (3h)
└── Dia 5: #10 Templates UI + templates iniciais (3h)
```

---

## Ordem de Execucao (Recomendada)

```
1. [#3]  Link Docs .................. 15 min  ████
2. [#8]  Audit Log .................. 3h      ████████████
3. [#4]  Resource Manager ........... 5h      ████████████████████
4. [#6]  Dashboard .................. 4h      ████████████████
5. [#7]  Logs ....................... 6h      ████████████████████████
6. [#1]  Migrations ................. 4h      ████████████████
7. [#9]  Rollback ................... 4h      ████████████████
8. [#2]  Health/Monitoring .......... 6h      ████████████████████████
9. [#5]  Cloud Integrations ......... 8h      ████████████████████████████████
10.[#10] Templates .................. 5h      ████████████████████

Total estimado: ~45h de desenvolvimento
```

---

## Notas de Implementacao

### Padrao para novos endpoints
```python
@app.post("/resource/{id}/action")
def action_resource(
    id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    # 1. Validar
    # 2. Executar
    # 3. Audit log
    audit_log(db, user.username, "action", "resource", id, resource.name)
    # 4. Retornar
```

### Padrao para UI HTMX
```python
@app.get("/api/projects/{id}/feature-html")
def get_feature_html(id: int, db: Session = Depends(get_db)):
    # Retorna HTMLResponse com fragment
    return HTMLResponse(content=f'''
        <div id="feature-content">
            ...
        </div>
    ''')
```

### Background tasks
```python
from fastapi import BackgroundTasks

@app.on_event("startup")
def start_background_tasks():
    # Resource Manager scan
    # Health checks
    # Log rotation
```

---

## Verificacao Final

Apos implementar tudo, verificar:

- [ ] Dashboard mostra metricas corretas
- [ ] Resource Manager detecta portas/processos
- [ ] Logs aparecem em tempo real
- [ ] Audit log registra todas as acoes
- [ ] Rollback funciona em 1 clique
- [ ] Health checks rodam periodicamente
- [ ] Cloud integrations conectam
- [ ] Templates criam apps funcionais
- [ ] Link docs abre documentacao
- [ ] Migrations rodam sem erros
