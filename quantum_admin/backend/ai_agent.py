"""
Quantum Admin - Advanced AI Agent
Integrates SLM with RAG, function calling, and code generation
"""

import json
import re
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import requests


# ============================================================================
# SLM Integration (Ollama/LM Studio)
# ============================================================================

class SLMProvider:
    """Interface for Small Language Models"""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.model = "phi3"  # Default: Microsoft Phi-3 (3.8B params)

    def generate(self, prompt: str, system: Optional[str] = None, max_tokens: int = 500) -> str:
        """Generate completion using Ollama"""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.7
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                return self._fallback_response(prompt)

        except Exception as e:
            print(f"SLM error: {e}")
            return self._fallback_response(prompt)

    def _fallback_response(self, prompt: str) -> str:
        """Fallback when SLM unavailable"""
        return "AI assistant temporarily unavailable. Using rule-based fallback."


# ============================================================================
# Function Registry (Tools for AI)
# ============================================================================

class FunctionRegistry:
    """Registry of functions AI can call"""

    def __init__(self):
        self.functions: Dict[str, Callable] = {}
        self.descriptions: Dict[str, Dict[str, Any]] = {}
        self._register_builtin_functions()

    def register(self, name: str, func: Callable, description: str, parameters: Dict[str, Any]):
        """Register a new function"""
        self.functions[name] = func
        self.descriptions[name] = {
            "description": description,
            "parameters": parameters
        }

    def _register_builtin_functions(self):
        """Register built-in functions"""

        # Database query generation
        self.register(
            name="generate_sql_query",
            func=self._generate_sql,
            description="Generate SQL query based on natural language",
            parameters={
                "type": "object",
                "properties": {
                    "intent": {"type": "string", "description": "What user wants to query"},
                    "table": {"type": "string", "description": "Target table name"}
                },
                "required": ["intent"]
            }
        )

        # Model generation
        self.register(
            name="generate_model",
            func=self._generate_model,
            description="Generate SQLAlchemy model code",
            parameters={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string"},
                    "columns": {"type": "array", "items": {"type": "object"}}
                }
            }
        )

        # Migration suggestion
        self.register(
            name="suggest_migration",
            func=self._suggest_migration,
            description="Suggest database migration",
            parameters={
                "type": "object",
                "properties": {
                    "changes": {"type": "string", "description": "Desired changes"}
                }
            }
        )

    def _generate_sql(self, intent: str, table: str = None) -> str:
        """Generate SQL query"""
        # Simple SQL generation logic
        if "all" in intent.lower() and table:
            return f"SELECT * FROM {table}"
        elif "count" in intent.lower() and table:
            return f"SELECT COUNT(*) FROM {table}"
        else:
            return f"SELECT * FROM {table or 'table_name'} WHERE condition"

    def _generate_model(self, table_name: str, columns: List[Dict]) -> str:
        """Generate SQLAlchemy model"""
        model = f"""class {table_name.capitalize()}(Base):
    __tablename__ = '{table_name}'

"""
        for col in columns:
            model += f"    {col['name']} = Column({col['type']})\n"
        return model

    def _suggest_migration(self, changes: str) -> str:
        """Suggest migration"""
        return f"alembic revision --autogenerate -m \"{changes}\""

    def call(self, function_name: str, **kwargs) -> Any:
        """Execute a function"""
        if function_name in self.functions:
            return self.functions[function_name](**kwargs)
        raise ValueError(f"Unknown function: {function_name}")

    def get_schemas(self) -> List[Dict[str, Any]]:
        """Get all function schemas for AI"""
        return [
            {
                "name": name,
                **desc
            }
            for name, desc in self.descriptions.items()
        ]


# ============================================================================
# Enhanced RAG System
# ============================================================================

class EnhancedRAG:
    """Enhanced RAG with schema understanding"""

    def __init__(self, schema_inspector=None):
        self.schema_inspector = schema_inspector
        self.knowledge_base = self._build_knowledge()
        self.conversation_memory: List[Dict[str, str]] = []

    def _build_knowledge(self) -> Dict[str, Any]:
        """Build comprehensive knowledge base"""
        return {
            "database": {
                "sql_patterns": [
                    {"pattern": "select.*from", "category": "query"},
                    {"pattern": "insert.*into", "category": "insert"},
                    {"pattern": "update.*set", "category": "update"},
                    {"pattern": "delete.*from", "category": "delete"}
                ],
                "optimization": [
                    "Add indexes on frequently queried columns",
                    "Use LIMIT for large result sets",
                    "Avoid SELECT * in production",
                    "Use JOIN instead of subqueries when possible"
                ]
            },
            "migrations": {
                "best_practices": [
                    "Always test migrations on dev first",
                    "Use --autogenerate for model changes",
                    "Keep migrations reversible",
                    "Never edit applied migrations"
                ],
                "common_operations": {
                    "add_column": "op.add_column('table', sa.Column('name', sa.String()))",
                    "drop_column": "op.drop_column('table', 'column_name')",
                    "create_table": "op.create_table('name', sa.Column(...))",
                    "add_index": "op.create_index('idx_name', 'table', ['column'])"
                }
            },
            "quantum_admin": {
                "features": [
                    "JWT Authentication with RBAC",
                    "WebSocket real-time updates",
                    "Jenkins Pipeline abstraction",
                    "Container management wizard",
                    "Visual schema inspector",
                    "Alembic migrations",
                    "Redis caching",
                    "Celery background jobs"
                ],
                "urls": {
                    "login": "/static/login.html",
                    "schema": "/static/schema-viewer.html",
                    "pipeline": "/static/pipeline-editor.html",
                    "container": "/static/container-wizard.html",
                    "api_docs": "/docs"
                }
            }
        }

    def add_to_memory(self, role: str, content: str):
        """Add message to conversation memory"""
        self.conversation_memory.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

        # Keep last 10 messages
        if len(self.conversation_memory) > 10:
            self.conversation_memory = self.conversation_memory[-10:]

    def get_context(self, query: str) -> str:
        """Get relevant context for query"""
        context_parts = []

        # Add schema context if available
        if self.schema_inspector:
            try:
                tables = self.schema_inspector.get_all_tables()
                context_parts.append(f"Available tables: {', '.join(tables)}")
            except:
                pass

        # Add relevant knowledge
        query_lower = query.lower()

        if any(word in query_lower for word in ["sql", "query", "select"]):
            context_parts.append("SQL Best Practices: " + ", ".join(self.knowledge_base["database"]["optimization"]))

        if any(word in query_lower for word in ["migration", "migrate", "schema"]):
            context_parts.append("Migration Best Practices: " + ", ".join(self.knowledge_base["migrations"]["best_practices"]))

        if any(word in query_lower for word in ["quantum", "feature", "what can"]):
            context_parts.append("Quantum Admin Features: " + ", ".join(self.knowledge_base["quantum_admin"]["features"]))

        return "\n".join(context_parts)


# ============================================================================
# Main AI Agent
# ============================================================================

class QuantumAIAgent:
    """Advanced AI Agent with SLM, RAG, and function calling"""

    def __init__(self, schema_inspector=None):
        self.slm = SLMProvider()
        self.rag = EnhancedRAG(schema_inspector)
        self.functions = FunctionRegistry()
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build system prompt for AI"""
        return """You are Quantum AI, an expert assistant for Quantum Admin - an enterprise administration interface.

Your capabilities:
- Database schema analysis and SQL generation
- Migration suggestions and best practices
- SQLAlchemy model generation
- Query optimization advice
- Quantum Admin feature guidance

When users ask about database operations, provide specific SQL or model code.
When suggesting migrations, use Alembic syntax.
Always prioritize security and best practices.

Available functions you can call:
""" + json.dumps(self.functions.get_schemas(), indent=2)

    def chat(self, message: str, use_slm: bool = True) -> Dict[str, Any]:
        """Process user message and generate response"""

        # Add to memory
        self.rag.add_to_memory("user", message)

        # Get context from RAG
        context = self.rag.get_context(message)

        # Build full prompt
        full_prompt = f"""Context:
{context}

Conversation history:
{self._format_memory()}

User: {message}
Assistant: {message}


        # Detect if function calling needed
        function_call = self._detect_function_call(message)

        # Generate response
        if use_slm:
            response_text = self.slm.generate(
                prompt=full_prompt,
                system=self.system_prompt,
                max_tokens=500
            )
        else:
            response_text = self._rule_based_response(message, context)

        # Execute function if detected
        function_result = None
        if function_call:
            try:
                function_result = self.functions.call(**function_call)
            except Exception as e:
                function_result = f"Error executing function: {e}"

        # Add to memory
        self.rag.add_to_memory("assistant", response_text)

        return {
            "response": response_text,
            "context": context,
            "function_call": function_call,
            "function_result": function_result,
            "model": "phi3-rag" if use_slm else "rule-based",
            "memory_size": len(self.rag.conversation_memory)
        }

    def _format_memory(self) -> str:
        """Format conversation memory"""
        return "\n".join([
            f"{msg[\"role\"].capitalize()}: {msg[\"content\"]}"
            for msg in self.rag.conversation_memory[-5:]
        ])

    def _detect_function_call(self, message: str) -> Optional[Dict[str, Any]]:
        """Detect if message requires function call"""
        message_lower = message.lower()

        # SQL generation
        if "generate sql" in message_lower or "write query" in message_lower:
            return {
                "function_name": "generate_sql_query",
                "intent": message,
                "table": self._extract_table_name(message)
            }

        # Model generation
        elif "generate model" in message_lower or "create model" in message_lower:
            return {
                "function_name": "generate_model",
                "table_name": self._extract_table_name(message) or "example",
                "columns": []
            }

        # Migration
        elif "migration" in message_lower and ("create" in message_lower or "suggest" in message_lower):
            return {
                "function_name": "suggest_migration",
                "changes": message
            }

        return None

    def _extract_table_name(self, message: str) -> Optional[str]:
        """Extract table name from message"""
        # Simple pattern matching
        match = re.search(r"table[s]?\s+[\"\\`]?(\w+)[\"\\`]?", message, re.IGNORECASE)
        if match:
            return match.group(1)

        match = re.search(r"from\s+[\"\\`]?(\w+)[\"\\`]?", message, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def _rule_based_response(self, message: str, context: str) -> str:
        """Fallback rule-based response"""
        message_lower = message.lower()

        if "help" in message_lower or "what can" in message_lower:
            return """I can help you with:

🔍 Database: Generate SQL queries, optimize queries, suggest indexes
🔄 Migrations: Create and manage Alembic migrations
📝 Models: Generate SQLAlchemy model code
🎯 Quantum Admin: Navigate features, authentication, containers, pipelines

What would you like to do?"""

        elif "quantum" in message_lower and "feature" in message_lower:
            return """Quantum Admin features:

- JWT Authentication & RBAC
- Real-time WebSocket updates
- Jenkins Pipeline designer (<q:pipeline>)
- Visual Container wizard
- Database Schema inspector
- Alembic migrations
- Redis caching & Celery jobs

Access the UI at http://localhost:8000/static/login.html"""

        else:
            return f"I understand you asked about: {message}\n\nContext: {context}\n\nHow can I help you specifically?"

    def clear_memory(self):
        """Clear conversation memory"""
        self.rag.conversation_memory = []


# ============================================================================
# Singleton
# ============================================================================

_agent_instance = None

def get_ai_agent(schema_inspector=None) -> QuantumAIAgent:
    """Get singleton AI agent instance"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = QuantumAIAgent(schema_inspector)
    return _agent_instance

