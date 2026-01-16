# 🤖 Quantum AI - Sistema Avançado de IA

## 📊 Estado Atual

### ✅ Implementado

1. **RAG Básico** (`rag_system.py`)
   - 7 categorias de conhecimento
   - Detecção de intents com regex
   - Endpoint `/ai/chat`

2. **AI Agent Avançado** (`ai_agent.py` - NOVO!)
   - Integração com SLMs locais (Ollama/LM Studio)
   - Function calling (AI executa funções)
   - Conversation memory
   - Enhanced RAG com schema understanding

### 🎯 Capacidades do Novo AI Agent

#### 1. **Integração com SLM Real**
```python
# Suporta modelos locais via Ollama:
- Phi-3 (Microsoft, 3.8B params) - RECOMENDADO
- TinyLlama (1.1B params)
- Mistral-7B
- Llama-3
```

#### 2. **Function Calling**
O AI pode chamar funções:

| Função | Descrição |
|--------|-----------|
| `generate_sql_query` | Gera SQL a partir de linguagem natural |
| `generate_model` | Cria código SQLAlchemy |
| `suggest_migration` | Sugere comandos Alembic |

#### 3. **Enhanced RAG**
- **Schema Understanding**: Conhece estrutura do banco
- **Conversation Memory**: Lembra últimas 10 mensagens
- **Context Retrieval**: Busca conhecimento relevante
- **Multi-Domain**: Database, Migrations, Quantum Admin

#### 4. **Code Generation**
Exemplos do que AI pode gerar:

**SQL:**
```
User: "Generate SQL to get all active users"
AI: SELECT * FROM users WHERE status = 'active'
```

**Model:**
```
User: "Create model for users table with email and name"
AI: class User(Base):
       __tablename__ = 'users'
       id = Column(Integer, primary_key=True)
       email = Column(String)
       name = Column(String)
```

**Migration:**
```
User: "Create migration to add created_at column"
AI: alembic revision --autogenerate -m "add created_at column"
```

## 🚀 Como Usar

### Setup do SLM (Ollama)

```bash
# 1. Instalar Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. Baixar modelo
ollama pull phi3

# 3. Verificar
ollama list
```

### Uso via API

```bash
# Chat simples
curl -X POST http://localhost:8000/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Generate SQL to count users"}'

# Com contexto
curl -X POST http://localhost:8000/ai/chat \
  -d '{"message": "Optimize my query", "context": "database"}'
```

### Uso via UI

#### Dedicated AI Assistant Page
```
http://localhost:8000/ai-assistant.html
```

**Features**:
- 🎨 Beautiful chat interface with message history
- ⚡ Real-time typing indicators
- 🔧 Quick prompt templates
- 📊 Function calling visibility
- 🎛️ Toggle SLM and schema context
- 🗑️ Clear conversation
- 📱 Responsive design

**Quick Prompts**:
- SQL Generation
- Model Generation
- Migration Help
- Schema Information
- Query Optimization
- WebSocket Usage

#### Command Palette
```
# From any page
Ctrl+K to open command palette
Type "ai" or "chat" to access AI features
```

## 💡 Exemplos de Uso

### 1. Database Queries
```
User: "Show me all tables"
AI: Based on schema inspection:
    - users (5 columns)
    - posts (7 columns)
    - comments (4 columns)

    To query: SELECT * FROM users

User: "Generate SQL to get recent posts"
AI: SELECT * FROM posts
    WHERE created_at > NOW() - INTERVAL '7 days'
    ORDER BY created_at DESC
    LIMIT 10
```

### 2. Model Generation
```
User: "Create a Product model with name, price, stock"
AI: class Product(Base):
       __tablename__ = 'products'

       id = Column(Integer, primary_key=True)
       name = Column(String, nullable=False)
       price = Column(Numeric(10,2))
       stock = Column(Integer, default=0)
```

### 3. Migration Help
```
User: "I need to add an index on email column"
AI: Here's how to create the migration:

    1. Create migration:
       make migration-create MSG="add email index"

    2. Edit the migration file to add:
       op.create_index('idx_users_email', 'users', ['email'])

    3. Apply:
       make migration-upgrade
```

### 4. Quantum Admin Features
```
User: "How do I create a pipeline?"
AI: To create a Jenkins pipeline in Quantum Admin:

    1. Navigate to /static/pipeline-editor.html
    2. Use <q:pipeline> XML syntax:
       <q:pipeline name="My Pipeline">
         <q:stage name="Build">
           <q:step>npm install</q:step>
         </q:stage>
       </q:pipeline>
    3. Click "Generate Jenkinsfile"
    4. Download or deploy
```

## 🔧 Configuração

### Ambiente

```bash
# .env
AI_ENABLED=true
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=phi3
AI_MAX_TOKENS=500
AI_TEMPERATURE=0.7
```

### Fallback

Se Ollama não estiver disponível, o sistema usa:
- Rule-based responses
- Pattern matching
- Conhecimento do RAG

## 📈 Performance

| Métrica | Valor |
|---------|-------|
| Resposta (SLM) | ~2-5s |
| Resposta (Rule-based) | <100ms |
| Memória por sessão | ~10 mensagens |
| Context window | Até 500 tokens |

## 🎯 Próximos Passos

### Melhorias Planejadas

- [ ] Vector embeddings (ChromaDB/FAISS)
- [ ] Fine-tuning em dados Quantum
- [ ] Multi-modal (imagens de diagramas)
- [ ] Code execution sandbox
- [ ] Auto-fix de erros
- [ ] Testes automatizados gerados por AI

### Expansão de Conhecimento

- [ ] Todos os endpoints da API
- [ ] Melhores práticas de segurança
- [ ] Padrões de performance
- [ ] Troubleshooting comum
- [ ] Tutoriais interativos

## 🔒 Segurança

⚠️ **Importante:**
- AI roda localmente (via Ollama)
- Nenhum dado enviado para nuvem
- Function calling tem validação
- SQL gerado deve ser revisado
- Nunca execute código gerado sem revisar

## 📚 Referências

- **Ollama**: https://ollama.com
- **Phi-3**: https://huggingface.co/microsoft/Phi-3
- **RAG**: https://python.langchain.com/docs/use_cases/question_answering/
- **Alembic**: https://alembic.sqlalchemy.org/

---

**Status**: 🚧 Em desenvolvimento ativo
**Versão**: 1.0.0-alpha
**Última atualização**: 2026-01-16
