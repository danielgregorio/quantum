# Proposta: Python Nativo no Quantum

## 🎯 Visão

Permitir código Python nativo dentro de componentes Quantum, criando um **híbrido perfeito** entre programação declarativa (XML) e imperativa (Python). Inspirado no `<cfscript>` do ColdFusion, mas levado ao próximo nível.

---

## 🔥 A Magia

```xml
<?xml version="1.0" encoding="UTF-8"?>
<q:component name="AIAnalytics" xmlns:q="https://quantum.lang/ns">

    <!-- O melhor dos dois mundos -->
    <q:python>
        import pandas as pd
        from sklearn.ensemble import RandomForestClassifier
        from openai import OpenAI

        # Carregar e processar dados
        df = pd.read_csv('customers.csv')

        # Machine Learning
        model = RandomForestClassifier()
        model.fit(df[features], df['churn'])
        predictions = model.predict_proba(df[features])

        # AI/LLM
        client = OpenAI()
        insights = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": f"Analyze: {df.describe()}"}]
        )

        # Expor para o template
        q.churn_risk = predictions
        q.ai_insights = insights.choices[0].message.content
        q.top_customers = df.nlargest(10, 'revenue')
    </q:python>

    <!-- UI declarativa com dados do Python -->
    <div class="dashboard">
        <h1>AI-Powered Analytics</h1>

        <section class="insights">
            <h2>🤖 AI Insights</h2>
            <p>{ai_insights}</p>
        </section>

        <section class="customers">
            <h2>Top Customers</h2>
            <q:loop var="customer" items="{top_customers}">
                <div class="customer-card">
                    <span>{customer.name}</span>
                    <span class="revenue">R$ {customer.revenue}</span>
                    <span class="risk" style="color: {customer.churn_risk > 0.7 ? 'red' : 'green'}">
                        Risk: {customer.churn_risk:.1%}
                    </span>
                </div>
            </q:loop>
        </section>
    </div>
</q:component>
```

---

## 🌟 Features Principais

### 1. `<q:python>` - Bloco de Script

```xml
<!-- Bloco simples -->
<q:python>
    result = sum([1, 2, 3, 4, 5])
    q.total = result
</q:python>

<!-- Com escopo isolado -->
<q:python scope="isolated">
    # Variáveis não vazam para fora
    temp = calculate_something()
    q.export('result', temp)  # Exporta explicitamente
</q:python>

<!-- Assíncrono -->
<q:python async="true" timeout="30s">
    import asyncio
    import aiohttp

    async with aiohttp.ClientSession() as session:
        tasks = [fetch(session, url) for url in urls]
        results = await asyncio.gather(*tasks)

    q.api_results = results
</q:python>
```

### 2. `<q:python>` - Expressão Inline

```xml
<!-- Expressão que retorna valor -->
<q:set name="fibonacci" value="{q:python: [0,1,1,2,3,5,8,13,21,34][:n]}" />

<!-- Filtro com lambda -->
<q:set name="adults" value="{q:python: [u for u in users if u['age'] >= 18]}" />

<!-- Formatação complexa -->
<p>Relatório: {q:python: datetime.now().strftime('%d/%m/%Y %H:%M')}</p>

<!-- Cálculo inline -->
<span>Desconto: {q:python: f'R$ {price * 0.1:.2f}'}</span>
```

### 3. `<q:import>` - Módulos Python

```xml
<!-- Importar módulos no escopo do componente -->
<q:import module="pandas" as="pd" />
<q:import module="numpy" as="np" />
<q:import module="myapp.services" names="PaymentGateway, EmailService" />
<q:import module="sklearn.ensemble" names="RandomForestClassifier" />

<!-- Usar diretamente -->
<q:python>
    df = pd.DataFrame(data)
    model = RandomForestClassifier(n_estimators=100)
</q:python>
```

### 4. `<q:class>` - Definir Classes

```xml
<!-- Definir classe Python inline -->
<q:class name="OrderProcessor">
    def __init__(self, db):
        self.db = db

    def process(self, order_id):
        order = self.db.get(order_id)
        # ... lógica de processamento
        return ProcessingResult(success=True)

    def validate(self, order):
        return order.total > 0 and order.items
</q:class>

<!-- Usar a classe -->
<q:python>
    processor = OrderProcessor(db)
    result = processor.process(order_id)
    q.processing_result = result
</q:python>
```

### 5. `<q:decorator>` - Decorators Personalizados

```xml
<!-- Definir decorator -->
<q:decorator name="cached" ttl="5m">
    from functools import lru_cache
    return lru_cache(maxsize=128)
</q:decorator>

<q:decorator name="logged">
    import logging
    def decorator(func):
        def wrapper(*args, **kwargs):
            logging.info(f"Calling {func.__name__}")
            return func(*args, **kwargs)
        return wrapper
    return decorator
</q:decorator>

<!-- Usar em funções -->
<q:function name="fetchUserData" decorators="cached, logged">
    <q:python>
        return api.get_user(user_id)
    </q:python>
</q:function>
```

---

## 🔌 O Bridge `q` - A Ponte Mágica

O objeto `q` é a ponte entre Python e Quantum:

```python
class QuantumBridge:
    """Ponte mágica entre Python e Quantum"""

    # === Variáveis ===
    def __getattr__(self, name):
        """q.variavel - Ler variável do contexto"""
        return self._context.get(name)

    def __setattr__(self, name, value):
        """q.variavel = valor - Definir variável"""
        self._context.set(name, value)

    # === Queries ===
    def query(self, sql, **params):
        """q.query('SELECT * FROM users WHERE id = :id', id=1)"""
        return self._db.execute(sql, params)

    def fetch(self, sql, **params):
        """Alias para query().fetchall()"""
        return self.query(sql, **params).fetchall()

    def fetchone(self, sql, **params):
        """Buscar um registro"""
        return self.query(sql, **params).fetchone()

    # === HTTP ===
    def http(self, url, method='GET', **kwargs):
        """q.http('https://api.example.com', json={...})"""
        return requests.request(method, url, **kwargs)

    def get(self, url, **kwargs):
        return self.http(url, 'GET', **kwargs)

    def post(self, url, **kwargs):
        return self.http(url, 'POST', **kwargs)

    # === Mensagens ===
    def publish(self, topic, message):
        """q.publish('orders.created', order_data)"""
        self._broker.publish(topic, message)

    def send(self, queue, message):
        """q.send('email-queue', email_data)"""
        self._broker.send(queue, message)

    # === Jobs ===
    def dispatch(self, job_name, **params):
        """q.dispatch('process-order', order_id=123)"""
        return self._jobs.dispatch(job_name, params)

    def schedule(self, job_name, cron=None, interval=None):
        """q.schedule('daily-report', cron='0 8 * * *')"""
        return self._scheduler.add(job_name, cron=cron, interval=interval)

    # === Storage ===
    def cache(self, key, value=None, ttl=None):
        """q.cache('user:123', user_data, ttl='5m')"""
        if value is None:
            return self._cache.get(key)
        return self._cache.set(key, value, ttl)

    def session(self, key, value=None):
        """q.session('cart', cart_items)"""
        if value is None:
            return self._session.get(key)
        self._session[key] = value

    # === Logging ===
    def log(self, message, level='info'):
        """q.log('Processando pedido', level='debug')"""
        getattr(self._logger, level)(message)

    def info(self, message): self.log(message, 'info')
    def warn(self, message): self.log(message, 'warning')
    def error(self, message): self.log(message, 'error')
    def debug(self, message): self.log(message, 'debug')

    # === Eventos ===
    def emit(self, event, data=None):
        """q.emit('user:registered', user)"""
        self._events.emit(event, data)

    def on(self, event, handler):
        """q.on('payment:completed', handle_payment)"""
        self._events.on(event, handler)

    # === Utilitários ===
    def render(self, template, **context):
        """q.render('email/welcome.html', user=user)"""
        return self._renderer.render(template, context)

    def redirect(self, url, status=302):
        """q.redirect('/dashboard')"""
        raise RedirectException(url, status)

    def abort(self, status, message=None):
        """q.abort(404, 'Não encontrado')"""
        raise AbortException(status, message)

    # === Formulário/Request ===
    @property
    def form(self):
        """q.form.email, q.form.password"""
        return self._request.form

    @property
    def request(self):
        """q.request.method, q.request.headers"""
        return self._request

    @property
    def files(self):
        """q.files.avatar"""
        return self._request.files
```

---

## 🎨 Exemplos Práticos

### E-commerce com ML

```xml
<q:component name="ProductRecommendations">
    <q:import module="sklearn.neighbors" names="NearestNeighbors" />
    <q:import module="numpy" as="np" />

    <q:python>
        # Buscar histórico do usuário
        user_history = q.fetch('''
            SELECT product_id, rating
            FROM reviews
            WHERE user_id = :user_id
        ''', user_id=q.session('user_id'))

        # Buscar todos os produtos
        products = q.fetch('SELECT * FROM products')

        # Criar matriz de features
        features = np.array([[p['price'], p['category_id'], p['rating']]
                            for p in products])

        # Treinar modelo
        model = NearestNeighbors(n_neighbors=5)
        model.fit(features)

        # Encontrar produtos similares aos que o usuário gostou
        liked_products = [h['product_id'] for h in user_history if h['rating'] >= 4]

        recommendations = []
        for pid in liked_products:
            idx = next(i for i, p in enumerate(products) if p['id'] == pid)
            distances, indices = model.kneighbors([features[idx]])
            recommendations.extend([products[i] for i in indices[0]])

        # Remover duplicados e já comprados
        q.recommendations = list({p['id']: p for p in recommendations
                                  if p['id'] not in liked_products}.values())[:10]
    </q:python>

    <section class="recommendations">
        <h2>Recomendado para você</h2>
        <div class="product-grid">
            <q:loop var="product" items="{recommendations}">
                <div class="product-card">
                    <img src="{product.image}" alt="{product.name}" />
                    <h3>{product.name}</h3>
                    <span class="price">R$ {product.price:.2f}</span>
                    <button q:click="addToCart({product.id})">
                        Adicionar ao Carrinho
                    </button>
                </div>
            </q:loop>
        </div>
    </section>
</q:component>
```

### Dashboard em Tempo Real

```xml
<q:component name="RealtimeDashboard">
    <q:import module="pandas" as="pd" />
    <q:import module="plotly.express" as="px" />

    <q:python>
        # Buscar métricas
        sales = q.fetch('''
            SELECT DATE(created_at) as date, SUM(total) as revenue
            FROM orders
            WHERE created_at >= NOW() - INTERVAL '30 days'
            GROUP BY DATE(created_at)
            ORDER BY date
        ''')

        df = pd.DataFrame(sales)

        # Estatísticas
        q.total_revenue = df['revenue'].sum()
        q.avg_daily = df['revenue'].mean()
        q.growth = ((df['revenue'].iloc[-1] / df['revenue'].iloc[0]) - 1) * 100

        # Gráfico interativo
        fig = px.line(df, x='date', y='revenue', title='Vendas - Últimos 30 dias')
        fig.update_layout(template='plotly_dark')
        q.chart_html = fig.to_html(include_plotlyjs='cdn', full_html=False)

        # Previsão simples
        from sklearn.linear_model import LinearRegression
        import numpy as np

        X = np.arange(len(df)).reshape(-1, 1)
        y = df['revenue'].values

        model = LinearRegression()
        model.fit(X, y)

        next_7_days = np.arange(len(df), len(df) + 7).reshape(-1, 1)
        q.forecast = model.predict(next_7_days).tolist()
    </q:python>

    <div class="dashboard">
        <div class="metrics">
            <div class="metric">
                <span class="label">Receita Total</span>
                <span class="value">R$ {total_revenue:,.2f}</span>
            </div>
            <div class="metric">
                <span class="label">Média Diária</span>
                <span class="value">R$ {avg_daily:,.2f}</span>
            </div>
            <div class="metric">
                <span class="label">Crescimento</span>
                <span class="value {growth > 0 ? 'positive' : 'negative'}">
                    {growth:+.1f}%
                </span>
            </div>
        </div>

        <div class="chart">
            <q:raw>{chart_html}</q:raw>
        </div>

        <div class="forecast">
            <h3>Previsão - Próximos 7 dias</h3>
            <q:loop var="day" items="{forecast}" index="i">
                <div class="forecast-day">
                    <span>Dia {i + 1}</span>
                    <span>R$ {day:,.2f}</span>
                </div>
            </q:loop>
        </div>
    </div>
</q:component>
```

### Processamento de Imagem com AI

```xml
<q:component name="ImageProcessor">
    <q:import module="PIL.Image" as="Image" />
    <q:import module="torch" />
    <q:import module="torchvision.transforms" as="transforms" />
    <q:import module="transformers" names="pipeline" />

    <q:action name="analyzeImage">
        <q:python>
            # Carregar imagem enviada
            image_file = q.files.image
            image = Image.open(image_file)

            # Classificação com modelo pré-treinado
            classifier = pipeline("image-classification", model="google/vit-base-patch16-224")
            classifications = classifier(image)

            # Detecção de objetos
            detector = pipeline("object-detection", model="facebook/detr-resnet-50")
            objects = detector(image)

            # Geração de caption
            captioner = pipeline("image-to-text", model="Salesforce/blip-image-captioning-base")
            caption = captioner(image)[0]['generated_text']

            # Análise de sentimento visual
            q.classifications = classifications[:5]
            q.objects = objects
            q.caption = caption

            # Gerar thumbnail
            image.thumbnail((300, 300))
            thumbnail_path = f"/tmp/thumb_{q.form.image.filename}"
            image.save(thumbnail_path)
            q.thumbnail = thumbnail_path
        </q:python>

        <div class="analysis-result">
            <img src="{thumbnail}" alt="Uploaded image" />

            <h3>Caption Gerado</h3>
            <p class="caption">{caption}</p>

            <h3>Classificações</h3>
            <ul>
                <q:loop var="c" items="{classifications}">
                    <li>{c.label}: {c.score:.1%}</li>
                </q:loop>
            </ul>

            <h3>Objetos Detectados</h3>
            <ul>
                <q:loop var="obj" items="{objects}">
                    <li>{obj.label} ({obj.score:.1%})</li>
                </q:loop>
            </ul>
        </div>
    </q:action>

    <form action="analyzeImage" method="POST" enctype="multipart/form-data">
        <input type="file" name="image" accept="image/*" />
        <button type="submit">Analisar Imagem</button>
    </form>
</q:component>
```

### WebSocket com Async

```xml
<q:component name="ChatRoom">
    <q:import module="asyncio" />
    <q:import module="websockets" />

    <q:python scope="module">
        # Estado do chat (compartilhado)
        connected_users = set()
        message_history = []

        async def broadcast(message):
            for user in connected_users:
                await user.send(message)
    </q:python>

    <q:websocket path="/chat" name="chat-handler">
        <q:python async="true">
            connected_users.add(websocket)
            q.log(f"User connected: {websocket.remote_address}")

            try:
                # Enviar histórico
                for msg in message_history[-50:]:
                    await websocket.send(json.dumps(msg))

                # Loop de mensagens
                async for message in websocket:
                    data = json.loads(message)
                    data['timestamp'] = datetime.now().isoformat()
                    data['user_id'] = q.session('user_id')

                    message_history.append(data)
                    await broadcast(json.dumps(data))

            finally:
                connected_users.remove(websocket)
                q.log(f"User disconnected: {websocket.remote_address}")
        </q:python>
    </q:websocket>

    <div class="chat-container" q:websocket="ws://localhost/chat">
        <div class="messages" q:bind="messages">
            <q:loop var="msg" items="{messages}">
                <div class="message {msg.user_id == session.user_id ? 'own' : ''}">
                    <span class="author">{msg.username}</span>
                    <span class="text">{msg.text}</span>
                    <span class="time">{msg.timestamp}</span>
                </div>
            </q:loop>
        </div>

        <form q:submit="sendMessage">
            <input type="text" q:model="newMessage" placeholder="Digite sua mensagem..." />
            <button type="submit">Enviar</button>
        </form>
    </div>
</q:component>
```

---

## 🛡️ Segurança

### Sandbox Execution

```python
class SecurePythonExecutor:
    """Execução segura de código Python"""

    # Módulos proibidos
    BLOCKED_MODULES = {
        'os', 'sys', 'subprocess', 'shutil',
        'socket', 'ctypes', 'pickle', 'marshal'
    }

    # Builtins permitidos
    SAFE_BUILTINS = {
        'abs', 'all', 'any', 'bool', 'dict', 'enumerate',
        'filter', 'float', 'frozenset', 'int', 'isinstance',
        'len', 'list', 'map', 'max', 'min', 'print', 'range',
        'reversed', 'round', 'set', 'sorted', 'str', 'sum',
        'tuple', 'type', 'zip', 'True', 'False', 'None'
    }

    def execute(self, code, context, timeout=30):
        # Criar namespace restrito
        restricted_globals = {
            '__builtins__': {k: __builtins__[k] for k in self.SAFE_BUILTINS},
            'q': QuantumBridge(context),
            **context.get_safe_imports()
        }

        # Verificar imports proibidos
        self._check_imports(code)

        # Executar com timeout
        with timeout_context(timeout):
            exec(compile(code, '<quantum>', 'exec'), restricted_globals)

        return restricted_globals
```

### Modo de Configuração

```yaml
# quantum.yaml
security:
  python:
    enabled: true
    sandbox: true  # Execução em sandbox
    timeout: 30s   # Timeout máximo

    # Módulos permitidos
    allowed_modules:
      - pandas
      - numpy
      - sklearn
      - requests
      - PIL

    # Módulos bloqueados (override de allowed)
    blocked_modules:
      - os
      - sys
      - subprocess

    # Limite de recursos
    limits:
      memory: 512MB
      cpu_time: 10s

    # Auditoria
    audit:
      enabled: true
      log_level: info
```

---

## 🔧 Implementação

### AST Nodes

```python
@dataclass
class PythonNode(ASTNode):
    """Bloco de código Python"""
    code: str
    scope: str = "component"  # component, isolated, module
    async_mode: bool = False
    timeout: Optional[str] = None
    imports: List[str] = field(default_factory=list)

@dataclass
class ImportNode(ASTNode):
    """Import de módulo Python"""
    module: str
    alias: Optional[str] = None
    names: List[str] = field(default_factory=list)

@dataclass
class ClassNode(ASTNode):
    """Definição de classe Python"""
    name: str
    code: str
    bases: List[str] = field(default_factory=list)

@dataclass
class DecoratorNode(ASTNode):
    """Definição de decorator"""
    name: str
    code: str
```

### Parser

```python
def _parse_python(self, element: ET.Element) -> PythonNode:
    """Parse <q:python> block"""
    code = element.text or ""

    # Limpar indentação
    code = textwrap.dedent(code).strip()

    return PythonNode(
        code=code,
        scope=element.get('scope', 'component'),
        async_mode=element.get('async', 'false').lower() == 'true',
        timeout=element.get('timeout'),
        imports=self._parse_inline_imports(code)
    )

def _parse_import(self, element: ET.Element) -> ImportNode:
    """Parse <q:import> statement"""
    return ImportNode(
        module=element.get('module'),
        alias=element.get('as'),
        names=[n.strip() for n in element.get('names', '').split(',') if n.strip()]
    )
```

### Runtime

```python
def _execute_python(self, node: PythonNode, context: ExecutionContext):
    """Execute Python code block"""

    # Criar bridge
    bridge = QuantumBridge(context, self._services)

    # Preparar namespace
    namespace = {
        'q': bridge,
        **context.get_variables(),
        **self._get_imports(context)
    }

    # Executar
    if node.async_mode:
        return self._execute_async_python(node.code, namespace, node.timeout)
    else:
        return self._execute_sync_python(node.code, namespace, node.timeout)

def _execute_sync_python(self, code: str, namespace: dict, timeout: str = None):
    """Execute synchronous Python code"""
    timeout_seconds = parse_duration(timeout) if timeout else 30

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(exec, compile(code, '<quantum>', 'exec'), namespace)
        try:
            future.result(timeout=timeout_seconds)
        except TimeoutError:
            raise PythonExecutionError(f"Execution timed out after {timeout}")

    return namespace

async def _execute_async_python(self, code: str, namespace: dict, timeout: str = None):
    """Execute async Python code"""
    timeout_seconds = parse_duration(timeout) if timeout else 30

    # Wrap code in async function
    wrapped = f"async def __quantum_async__():\n{textwrap.indent(code, '    ')}"
    exec(compile(wrapped, '<quantum>', 'exec'), namespace)

    try:
        await asyncio.wait_for(
            namespace['__quantum_async__'](),
            timeout=timeout_seconds
        )
    except asyncio.TimeoutError:
        raise PythonExecutionError(f"Async execution timed out after {timeout}")

    return namespace
```

---

## 📊 Comparação

| Feature | ColdFusion | PHP | Quantum |
|---------|------------|-----|---------|
| Script inline | `<cfscript>` | `<?php ?>` | `<q:python>` |
| Expressões | `#expr#` | `<?= ?>` | `{q:python: expr}` |
| Imports | Java classes | `use` | `<q:import>` |
| Async | ❌ | ❌ | ✅ `async="true"` |
| Timeout | ❌ | `max_execution_time` | ✅ `timeout="30s"` |
| Sandbox | ❌ | ❌ | ✅ Configurável |
| ML/AI nativo | ❌ | ❌ | ✅ sklearn, torch |
| Data Science | ❌ | ❌ | ✅ pandas, numpy |

---

## 🚀 Roadmap

### Fase 1: Core (MVP)
- [ ] `<q:python>` básico
- [ ] Bridge `q` com variáveis e queries
- [ ] `<q:import>` para módulos
- [ ] Timeout e tratamento de erros

### Fase 2: Avançado
- [ ] Async/await support
- [ ] `<q:class>` e `<q:decorator>`
- [ ] Expressões inline `{q:python: ...}`
- [ ] Sandbox configurável

### Fase 3: Enterprise
- [ ] Auditoria e logging
- [ ] Limites de recursos (CPU, memória)
- [ ] Pool de workers Python
- [ ] Hot reload de código

---

## 💡 Conclusão

Esta feature transforma o Quantum em uma **plataforma híbrida única**:

1. **Declarativo quando faz sentido** - UI, fluxos, queries
2. **Imperativo quando necessário** - Lógica complexa, ML, AI
3. **Melhor dos dois mundos** - Produtividade + Poder

O desenvolvedor escolhe a ferramenta certa para cada tarefa, sem sair do mesmo arquivo.

**Quantum + Python = 🚀**
