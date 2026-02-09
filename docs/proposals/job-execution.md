# Proposta: Job Execution System

## Visao Geral

Sistema de execucao de tarefas em background inspirado no ColdFusion (cfschedule, cfthread), permitindo agendamento de tarefas, execucao assincrona e processamento em lote.

## Motivacao

O Quantum atualmente nao possui mecanismo nativo para:
- Executar tarefas agendadas (cron-like)
- Processar operacoes em background
- Executar tarefas de longa duracao sem bloquear a UI

**Referencia:** `src/cli/runner.py:219` - `# TODO: Implement real job execution`

## Componentes Propostos

### 1. `q:schedule` - Tarefas Agendadas

Inspirado no `<cfschedule>` do ColdFusion.

```xml
<!-- Tarefa executada a cada hora -->
<q:schedule name="hourly-cleanup"
            interval="1h"
            action="run">
    <q:function name="cleanup">
        <q:query datasource="db">
            DELETE FROM sessions WHERE expires_at < NOW()
        </q:query>
        <q:log level="info">Cleanup completed</q:log>
    </q:function>
</q:schedule>

<!-- Tarefa com cron expression -->
<q:schedule name="daily-report"
            cron="0 8 * * *"
            action="run"
            timezone="America/Sao_Paulo">
    <q:invoke function="generateDailyReport" />
    <q:mail to="{admin.email}" subject="Daily Report">
        <q:body>{report.html}</q:body>
    </q:mail>
</q:schedule>

<!-- Tarefa unica (one-shot) -->
<q:schedule name="send-reminder"
            at="2025-03-01T10:00:00"
            action="run">
    <q:invoke function="sendReminder" />
</q:schedule>

<!-- Pausar/Retomar tarefa -->
<q:schedule name="hourly-cleanup" action="pause" />
<q:schedule name="hourly-cleanup" action="resume" />

<!-- Deletar tarefa -->
<q:schedule name="hourly-cleanup" action="delete" />
```

#### Atributos de `q:schedule`

| Atributo | Tipo | Descricao |
|----------|------|-----------|
| `name` | string | Nome unico da tarefa |
| `action` | enum | run, pause, resume, delete |
| `interval` | duration | Intervalo (30s, 5m, 1h, 1d) |
| `cron` | string | Expressao cron padrao |
| `at` | datetime | Data/hora especifica |
| `timezone` | string | Timezone para execucao |
| `retry` | integer | Numero de tentativas em falha |
| `timeout` | duration | Timeout maximo |
| `overlap` | boolean | Permitir execucoes sobrepostas |
| `enabled` | boolean | Se a tarefa esta ativa |

### 2. `q:thread` - Execucao Assincrona

Inspirado no `<cfthread>` do ColdFusion.

```xml
<!-- Thread simples -->
<q:thread name="email-sender">
    <q:loop type="array" var="user" items="{users}">
        <q:mail to="{user.email}" subject="Newsletter">
            <q:body>{newsletter.html}</q:body>
        </q:mail>
    </q:loop>
</q:thread>

<!-- Continuar sem esperar -->
<p>Emails sendo enviados em background...</p>

<!-- Thread com join (aguardar conclusao) -->
<q:thread name="data-processor" action="run">
    <q:data name="result" source="{largeDataset}" type="transform">
        <q:transform>
            <q:filter condition="{active == true}" />
            <q:compute name="total" expression="{price * quantity}" />
        </q:transform>
    </q:data>
</q:thread>

<q:thread name="data-processor" action="join" timeout="30s" />

<!-- Acessar resultado apos join -->
<p>Total processado: {thread.data-processor.result.length}</p>

<!-- Thread com callback -->
<q:thread name="long-task"
          on-complete="handleComplete"
          on-error="handleError">
    <q:invoke url="https://api.slow.com/process" method="POST" />
</q:thread>
```

#### Atributos de `q:thread`

| Atributo | Tipo | Descricao |
|----------|------|-----------|
| `name` | string | Nome unico da thread |
| `action` | enum | run, join, terminate |
| `priority` | enum | low, normal, high |
| `timeout` | duration | Timeout maximo |
| `on-complete` | function | Callback de sucesso |
| `on-error` | function | Callback de erro |

### 3. `q:job` - Job Queue

Para processamento em lote e filas de trabalho.

```xml
<!-- Definir um job -->
<q:job name="process-order" queue="orders">
    <q:param name="orderId" type="integer" required="true" />

    <q:query name="order" datasource="db">
        SELECT * FROM orders WHERE id = :orderId
    </q:query>

    <q:invoke function="processPayment">
        <q:arg name="order" value="{order[0]}" />
    </q:invoke>

    <q:mail to="{order.customer_email}" subject="Order Confirmed">
        <q:body>Your order #{orderId} has been processed.</q:body>
    </q:mail>
</q:job>

<!-- Enfileirar execucao -->
<q:job name="process-order" action="dispatch">
    <q:param name="orderId" value="{newOrderId}" />
</q:job>

<!-- Enfileirar com delay -->
<q:job name="process-order" action="dispatch" delay="5m">
    <q:param name="orderId" value="{newOrderId}" />
</q:job>

<!-- Enfileirar em lote -->
<q:job name="process-order" action="batch">
    <q:loop type="array" var="id" items="{orderIds}">
        <q:param name="orderId" value="{id}" />
    </q:loop>
</q:job>
```

#### Atributos de `q:job`

| Atributo | Tipo | Descricao |
|----------|------|-----------|
| `name` | string | Nome do job |
| `queue` | string | Nome da fila |
| `action` | enum | define, dispatch, batch |
| `delay` | duration | Delay antes de executar |
| `priority` | integer | Prioridade na fila |
| `attempts` | integer | Maximo de tentativas |
| `backoff` | duration | Delay entre tentativas |
| `timeout` | duration | Timeout por execucao |

## Arquitetura

### Componentes Internos

```
┌─────────────────────────────────────────────────────────────┐
│                      Quantum Runtime                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌───────────────┐    ┌───────────────┐    ┌──────────────┐│
│  │   Scheduler   │    │ Thread Pool   │    │  Job Queue   ││
│  │   (APScheduler)│   │ (concurrent)  │    │  (Redis/SQL) ││
│  └───────┬───────┘    └───────┬───────┘    └──────┬───────┘│
│          │                    │                    │         │
│          ▼                    ▼                    ▼         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                     Job Executor                        │ │
│  │   - Parse q:schedule/q:thread/q:job nodes              │ │
│  │   - Execute function bodies                             │ │
│  │   - Handle errors and retries                           │ │
│  │   - Log execution results                               │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Dependencias Sugeridas

```python
# requirements.txt
APScheduler>=3.10.0      # Scheduler
redis>=4.0.0             # Job queue backend (opcional)
```

### Implementacao

#### 1. AST Nodes

```python
# src/core/ast_nodes.py

@dataclass
class ScheduleNode(QuantumNode):
    """Representa uma tarefa agendada"""
    name: str
    action: str = 'run'  # run, pause, resume, delete
    interval: Optional[str] = None
    cron: Optional[str] = None
    at: Optional[str] = None
    timezone: str = 'UTC'
    retry: int = 3
    timeout: Optional[str] = None
    overlap: bool = False
    enabled: bool = True
    body: List[QuantumNode] = field(default_factory=list)

@dataclass
class ThreadNode(QuantumNode):
    """Representa uma thread de execucao"""
    name: str
    action: str = 'run'  # run, join, terminate
    priority: str = 'normal'  # low, normal, high
    timeout: Optional[str] = None
    on_complete: Optional[str] = None
    on_error: Optional[str] = None
    body: List[QuantumNode] = field(default_factory=list)

@dataclass
class JobNode(QuantumNode):
    """Representa um job na fila"""
    name: str
    queue: str = 'default'
    action: str = 'define'  # define, dispatch, batch
    delay: Optional[str] = None
    priority: int = 0
    attempts: int = 3
    backoff: str = '30s'
    timeout: Optional[str] = None
    params: List[ParamNode] = field(default_factory=list)
    body: List[QuantumNode] = field(default_factory=list)
```

#### 2. Parser

```python
# src/core/parser.py

def _parse_schedule(self, element: ET.Element) -> ScheduleNode:
    node = ScheduleNode(
        name=element.get('name'),
        action=element.get('action', 'run'),
        interval=element.get('interval'),
        cron=element.get('cron'),
        at=element.get('at'),
        timezone=element.get('timezone', 'UTC'),
        retry=int(element.get('retry', 3)),
        timeout=element.get('timeout'),
        overlap=element.get('overlap', 'false').lower() == 'true',
        enabled=element.get('enabled', 'true').lower() == 'true',
    )
    node.body = self._parse_children(element)
    return node

def _parse_thread(self, element: ET.Element) -> ThreadNode:
    node = ThreadNode(
        name=element.get('name'),
        action=element.get('action', 'run'),
        priority=element.get('priority', 'normal'),
        timeout=element.get('timeout'),
        on_complete=element.get('on-complete'),
        on_error=element.get('on-error'),
    )
    node.body = self._parse_children(element)
    return node
```

#### 3. Runtime Executor

```python
# src/runtime/job_executor.py

from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ThreadPoolExecutor
import threading

class JobExecutor:
    def __init__(self, component_runtime):
        self.runtime = component_runtime
        self.scheduler = BackgroundScheduler()
        self.thread_pool = ThreadPoolExecutor(max_workers=10)
        self.threads = {}
        self.jobs = {}

    def execute_schedule(self, node: ScheduleNode, context):
        if node.action == 'run':
            if node.interval:
                self._schedule_interval(node, context)
            elif node.cron:
                self._schedule_cron(node, context)
            elif node.at:
                self._schedule_once(node, context)
        elif node.action == 'pause':
            self.scheduler.pause_job(node.name)
        elif node.action == 'resume':
            self.scheduler.resume_job(node.name)
        elif node.action == 'delete':
            self.scheduler.remove_job(node.name)

    def execute_thread(self, node: ThreadNode, context):
        if node.action == 'run':
            future = self.thread_pool.submit(
                self._run_thread_body,
                node,
                context.copy()
            )
            self.threads[node.name] = {
                'future': future,
                'node': node,
                'result': None
            }
        elif node.action == 'join':
            thread_info = self.threads.get(node.name)
            if thread_info:
                timeout = self._parse_duration(node.timeout)
                thread_info['result'] = thread_info['future'].result(timeout)
        elif node.action == 'terminate':
            # Note: Python threads can't be forcefully terminated
            # This will just mark it for cleanup
            pass

    def _run_thread_body(self, node: ThreadNode, context):
        try:
            result = None
            for stmt in node.body:
                result = self.runtime._execute_statement(stmt, context)

            if node.on_complete:
                self.runtime._call_function(node.on_complete, {'result': result})

            return result
        except Exception as e:
            if node.on_error:
                self.runtime._call_function(node.on_error, {'error': str(e)})
            raise
```

## CLI Integration

```bash
# Listar tarefas agendadas
quantum jobs list

# Ver status de uma tarefa
quantum jobs status hourly-cleanup

# Pausar tarefa
quantum jobs pause hourly-cleanup

# Executar tarefa manualmente
quantum jobs run hourly-cleanup

# Ver historico de execucao
quantum jobs history hourly-cleanup --limit 10

# Worker para processar jobs
quantum worker start --queue orders --concurrency 4
```

### Implementacao CLI

```python
# src/cli/runner.py

def create_jobs_subparser(subparsers):
    jobs_parser = subparsers.add_parser('jobs', help='Manage scheduled jobs')
    jobs_sub = jobs_parser.add_subparsers(dest='jobs_action')

    # List
    list_parser = jobs_sub.add_parser('list', help='List all jobs')
    list_parser.add_argument('--status', choices=['all', 'active', 'paused'])

    # Status
    status_parser = jobs_sub.add_parser('status', help='Get job status')
    status_parser.add_argument('name', help='Job name')

    # Run
    run_parser = jobs_sub.add_parser('run', help='Run job manually')
    run_parser.add_argument('name', help='Job name')

    # Pause/Resume
    pause_parser = jobs_sub.add_parser('pause', help='Pause job')
    pause_parser.add_argument('name', help='Job name')

    resume_parser = jobs_sub.add_parser('resume', help='Resume job')
    resume_parser.add_argument('name', help='Job name')

    # History
    history_parser = jobs_sub.add_parser('history', help='View job history')
    history_parser.add_argument('name', help='Job name')
    history_parser.add_argument('--limit', type=int, default=10)

    # Worker
    worker_parser = jobs_sub.add_parser('worker', help='Start job worker')
    worker_sub = worker_parser.add_subparsers(dest='worker_action')

    start_parser = worker_sub.add_parser('start', help='Start worker')
    start_parser.add_argument('--queue', default='default')
    start_parser.add_argument('--concurrency', type=int, default=4)
```

## Persistencia

### Opcao 1: SQLite (Simples)

```sql
CREATE TABLE quantum_jobs (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,  -- schedule, job
    config TEXT NOT NULL,  -- JSON
    status TEXT DEFAULT 'active',
    last_run DATETIME,
    next_run DATETIME,
    run_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE quantum_job_history (
    id INTEGER PRIMARY KEY,
    job_id INTEGER,
    started_at DATETIME,
    completed_at DATETIME,
    status TEXT,  -- success, error
    result TEXT,
    error TEXT,
    FOREIGN KEY (job_id) REFERENCES quantum_jobs(id)
);
```

### Opcao 2: Redis (Escalavel)

```python
# Job queue usando Redis
import redis

class RedisJobQueue:
    def __init__(self, redis_url='redis://localhost:6379'):
        self.redis = redis.from_url(redis_url)

    def enqueue(self, job_name: str, params: dict, delay: int = 0):
        job_data = {
            'name': job_name,
            'params': params,
            'created_at': datetime.now().isoformat(),
        }

        if delay > 0:
            # Delayed job using sorted set
            execute_at = time.time() + delay
            self.redis.zadd('quantum:delayed', {json.dumps(job_data): execute_at})
        else:
            # Immediate job
            self.redis.lpush(f'quantum:queue:{job_name}', json.dumps(job_data))

    def dequeue(self, queue_name: str, timeout: int = 0):
        result = self.redis.brpop(f'quantum:queue:{queue_name}', timeout)
        if result:
            return json.loads(result[1])
        return None
```

## Exemplos de Uso

### 1. Limpeza Automatica de Sessoes

```xml
<q:schedule name="session-cleanup" interval="1h">
    <q:query datasource="db">
        DELETE FROM sessions WHERE expires_at < NOW()
    </q:query>
    <q:log level="info">Sessions cleaned up</q:log>
</q:schedule>
```

### 2. Relatorio Diario

```xml
<q:schedule name="daily-report" cron="0 8 * * *">
    <q:query name="stats" datasource="db">
        SELECT
            COUNT(*) as orders,
            SUM(total) as revenue
        FROM orders
        WHERE DATE(created_at) = CURDATE() - INTERVAL 1 DAY
    </q:query>

    <q:mail to="admin@company.com" subject="Daily Report">
        <q:body>
            Orders: {stats.orders}
            Revenue: ${stats.revenue}
        </q:body>
    </q:mail>
</q:schedule>
```

### 3. Envio de Emails em Background

```xml
<q:thread name="bulk-email">
    <q:loop type="array" var="subscriber" items="{subscribers}">
        <q:mail to="{subscriber.email}" subject="Newsletter">
            <q:body>{newsletter.html}</q:body>
        </q:mail>

        <!-- Rate limiting -->
        <q:set name="_delay" value="100" />
    </q:loop>
</q:thread>

<p>Newsletter sendo enviada para {subscribers.length} assinantes...</p>
```

### 4. Processamento de Pedidos

```xml
<!-- Definir o job -->
<q:job name="process-order" queue="orders" attempts="3" backoff="5m">
    <q:param name="orderId" type="integer" required="true" />

    <q:query name="order" datasource="db">
        SELECT * FROM orders WHERE id = :orderId
    </q:query>

    <q:invoke name="payment" url="https://payment.api/charge" method="POST">
        <q:body>{order}</q:body>
    </q:invoke>

    <q:if condition="{payment.success}">
        <q:query datasource="db">
            UPDATE orders SET status = 'paid' WHERE id = :orderId
        </q:query>

        <q:mail to="{order.email}" subject="Payment Confirmed">
            <q:body>Your payment has been processed!</q:body>
        </q:mail>
    </q:if>
</q:job>

<!-- Usar em uma action -->
<q:action name="submitOrder">
    <q:query name="newOrder" datasource="db">
        INSERT INTO orders (customer_id, total) VALUES (:customerId, :total)
    </q:query>

    <!-- Enfileirar para processamento async -->
    <q:job name="process-order" action="dispatch">
        <q:param name="orderId" value="{newOrder.insertId}" />
    </q:job>

    <q:redirect to="/orders/{newOrder.insertId}" />
</q:action>
```

## Cronograma de Implementacao

### Fase 1: q:thread (1 semana)
- [ ] AST Node e Parser
- [ ] ThreadPoolExecutor integration
- [ ] Join e Terminate
- [ ] Callbacks (on-complete, on-error)
- [ ] Testes

### Fase 2: q:schedule (1 semana)
- [ ] AST Node e Parser
- [ ] APScheduler integration
- [ ] Interval e cron support
- [ ] Persistencia SQLite
- [ ] CLI commands
- [ ] Testes

### Fase 3: q:job (1 semana)
- [ ] AST Node e Parser
- [ ] Job queue abstraction
- [ ] Redis backend (opcional)
- [ ] Worker process
- [ ] Retry logic
- [ ] Testes

### Fase 4: Polish (3 dias)
- [ ] Documentacao
- [ ] Exemplos
- [ ] Dashboard de monitoramento (opcional)

## Compatibilidade ColdFusion

| ColdFusion | Quantum | Status |
|------------|---------|--------|
| `<cfschedule>` | `<q:schedule>` | Proposto |
| `<cfthread>` | `<q:thread>` | Proposto |
| `<cfthread action="join">` | `<q:thread action="join">` | Proposto |
| Task scheduling | APScheduler | Proposto |
| N/A | `<q:job>` | Novo (job queue) |

## Riscos e Mitigacoes

| Risco | Mitigacao |
|-------|-----------|
| Memory leaks em threads | Timeout obrigatorio, cleanup automatico |
| Jobs perdidos em crash | Persistencia em SQLite/Redis |
| Overload de threads | Thread pool com limite configuravel |
| Execucoes duplicadas | Lock distribuido (Redis) |

## Metricas de Sucesso

- [ ] Todas as 3 tags implementadas e testadas
- [ ] CLI funcional para gerenciamento
- [ ] Persistencia de estado
- [ ] Retry logic funcionando
- [ ] Documentacao completa
- [ ] 10+ exemplos praticos
