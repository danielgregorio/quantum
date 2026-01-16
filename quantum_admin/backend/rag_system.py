"""
RAG (Retrieval-Augmented Generation) System for Quantum AI
Indexes Quantum framework documentation, intents, and best practices
"""

import json
import re
from typing import List, Dict, Any, Tuple
from pathlib import Path


class QuantumRAG:
    """
    RAG system calibrated for Quantum framework
    Retrieves relevant context for AI responses
    """

    def __init__(self):
        self.knowledge_base = self._build_knowledge_base()
        self.intent_patterns = self._load_intent_patterns()

    def _build_knowledge_base(self) -> List[Dict[str, Any]]:
        """Build comprehensive knowledge base"""
        return [
            # Databinding
            {
                "id": "databinding-basics",
                "category": "databinding",
                "keywords": ["databinding", "binding", "variable", "{}", "expression", "context"],
                "title": "Databinding Basics",
                "content": """
Quantum uses curly braces {} for databinding expressions:

**Simple variables**: {username}, {email}
**Object properties**: {user.name}, {user.email}
**Array access**: {items[0]}, {users[index]}
**Nested**: {user.address.city}

Context variables automatically available:
- {session} - Session data
- {user} - Logged in user
- {isLoggedIn} - Authentication status
- {request} - Request information

Example:
<p>Hello, {user.name}!</p>
<p>You have {notifications.length} new messages</p>
""",
                "examples": [
                    "{user.name}",
                    "{items[0].title}",
                    "{session.isLoggedIn}"
                ]
            },

            # Components
            {
                "id": "component-structure",
                "category": "components",
                "keywords": ["component", "structure", "xml", "create", "template"],
                "title": "Component Structure",
                "content": """
Basic Quantum component structure:

<?quantum version="1.0"?>
<component name="mycomp">
    <h1>Hello, {name}!</h1>
    <p>This is a Quantum component</p>
</component>

Best practices:
- Use descriptive component names
- Keep components focused (single responsibility)
- Pass data via context variables
- Reuse components with <include>
""",
                "examples": [
                    '<component name="hello">...</component>',
                    '<include src="header.q" />'
                ]
            },

            # Loops
            {
                "id": "loops",
                "category": "loops",
                "keywords": ["loop", "iterate", "array", "foreach", "repeat"],
                "title": "Loops and Iteration",
                "content": """
Use <loop> to iterate over arrays:

<loop array="users">
    <div class="user-card">
        <h3>{item.name}</h3>
        <p>{item.email}</p>
    </div>
</loop>

Available variables inside loop:
- {item} - Current item
- {index} - Current index (0-based)
- {isFirst} - True for first item
- {isLast} - True for last item

Nested loops:
<loop array="categories">
    <h2>{item.name}</h2>
    <loop array="item.products">
        <p>{item.name}</p>
    </loop>
</loop>
""",
                "examples": [
                    '<loop array="items">{item}</loop>',
                    '<loop array="users"><p>{index}: {item.name}</p></loop>'
                ]
            },

            # Conditionals
            {
                "id": "conditionals",
                "category": "conditionals",
                "keywords": ["if", "conditional", "condition", "else", "ternary"],
                "title": "Conditional Rendering",
                "content": """
Use <if> for conditional rendering:

<if condition="{isLoggedIn}">
    <p>Welcome back, {user.name}!</p>
</if>

<if condition="{user.role == 'admin'}">
    <button>Admin Panel</button>
</if>

Operators supported:
- ==, != - Equality
- >, <, >=, <= - Comparison
- and, or - Logical operators

Examples:
<if condition="{score >= 90}">Grade: A</if>
<if condition="{user.isPremium and user.isActive}">Premium Active</if>
""",
                "examples": [
                    '<if condition="{isAdmin}">Admin content</if>',
                    '<if condition="{count > 0}">You have items</if>'
                ]
            },

            # Database
            {
                "id": "database-queries",
                "category": "database",
                "keywords": ["database", "query", "sql", "datasource", "crud"],
                "title": "Database Operations",
                "content": """
Database operations in Quantum:

1. Create a datasource in Admin UI
2. Use <query> element:

<query name="getUsers" datasource="mydb">
    SELECT * FROM users WHERE active = true
</query>

<loop array="getUsers">
    <p>{item.username}</p>
</loop>

Best practices:
- Always use parameterized queries
- Limit results with LIMIT clause
- Handle errors gracefully
- Use connection pooling

Security:
- NEVER concatenate user input into queries
- Use parameter binding
- Validate all inputs
- Implement proper access control
""",
                "examples": [
                    '<query name="users" datasource="db">SELECT * FROM users</query>',
                    '<loop array="users">{item.name}</loop>'
                ]
            },

            # Services
            {
                "id": "services",
                "category": "services",
                "keywords": ["service", "email", "file", "upload", "action"],
                "title": "Quantum Services",
                "content": """
Available services in Quantum:

**DatabaseService**: Execute queries, transactions
**EmailService**: Send emails, templates
**FileUploadService**: Handle file uploads
**AuthService**: Authentication, sessions
**ActionHandler**: Custom server-side logic

Example usage:
<action name="sendEmail" service="email">
    <param name="to">{user.email}</param>
    <param name="subject">Welcome!</param>
    <param name="body">Hello {user.name}</param>
</action>

File uploads:
<form action="/upload" method="POST" enctype="multipart/form-data">
    <input type="file" name="file" />
    <button type="submit">Upload</button>
</form>
""",
                "examples": [
                    '<action name="send" service="email">...</action>',
                    '<input type="file" name="upload" />'
                ]
            },

            # Security
            {
                "id": "security-practices",
                "category": "security",
                "keywords": ["security", "xss", "sql injection", "csrf", "auth"],
                "title": "Security Best Practices",
                "content": """
Security guidelines for Quantum:

**Input Validation**:
- Always validate user input
- Sanitize before database operations
- Use parameterized queries

**Output Encoding**:
- Quantum auto-escapes HTML by default
- Be careful with raw output
- Validate file uploads

**Authentication**:
- Use AuthService for user management
- Implement session timeout
- Enable HTTPS in production
- Consider 2FA for sensitive data

**CSRF Protection**:
- Use CSRF tokens in forms
- Validate origin headers
- Implement SameSite cookies

**Common Vulnerabilities to Avoid**:
- SQL Injection: Use parameterized queries
- XSS: Don't use raw HTML from users
- Path Traversal: Validate file paths
- Insecure Deserialization: Validate JSON input
""",
                "examples": [
                    "Parameterized: SELECT * FROM users WHERE id = ?",
                    "CSRF Token: <input type=\"hidden\" name=\"csrf_token\" value=\"{csrf}\" />"
                ]
            },

            # Performance
            {
                "id": "performance",
                "category": "performance",
                "keywords": ["performance", "optimization", "cache", "speed", "slow"],
                "title": "Performance Optimization",
                "content": """
Performance tips for Quantum:

**Query Optimization**:
- Use LIMIT to restrict result sets
- Add indexes on frequently queried columns
- Avoid N+1 query problems
- Use connection pooling

**Caching**:
- Enable query result caching
- Cache expensive computations
- Use CDN for static assets

**Component Optimization**:
- Keep components small and focused
- Avoid deep nesting
- Minimize loop iterations
- Lazy load heavy components

**Monitoring**:
- Use Admin UI monitoring
- Track slow queries
- Monitor memory usage
- Set up alerts for issues
""",
                "examples": [
                    "SELECT * FROM users LIMIT 100",
                    "CREATE INDEX idx_email ON users(email)"
                ]
            }
        ]

    def _load_intent_patterns(self) -> List[Dict[str, Any]]:
        """Load intent recognition patterns"""
        return [
            {
                "intent": "databinding",
                "patterns": [
                    r"\{.*\}",
                    r"variable",
                    r"bind(ing)?",
                    r"expression",
                    r"context"
                ]
            },
            {
                "intent": "component",
                "patterns": [
                    r"component",
                    r"create.*component",
                    r"structure",
                    r"template"
                ]
            },
            {
                "intent": "loop",
                "patterns": [
                    r"loop",
                    r"iterate",
                    r"array",
                    r"for.*each"
                ]
            },
            {
                "intent": "conditional",
                "patterns": [
                    r"\bif\b",
                    r"condition",
                    r"else"
                ]
            },
            {
                "intent": "database",
                "patterns": [
                    r"database",
                    r"query",
                    r"sql",
                    r"select",
                    r"insert",
                    r"update",
                    r"delete"
                ]
            },
            {
                "intent": "error",
                "patterns": [
                    r"error",
                    r"bug",
                    r"issue",
                    r"problem",
                    r"not working",
                    r"fail(ed|ing)?"
                ]
            },
            {
                "intent": "security",
                "patterns": [
                    r"security",
                    r"auth(entication)?",
                    r"xss",
                    r"injection",
                    r"csrf"
                ]
            },
            {
                "intent": "performance",
                "patterns": [
                    r"performance",
                    r"slow",
                    r"optimi[zs]e",
                    r"fast(er)?",
                    r"cache"
                ]
            }
        ]

    def detect_intent(self, query: str) -> List[str]:
        """Detect intents from query"""
        query_lower = query.lower()
        detected = []

        for intent_def in self.intent_patterns:
            intent = intent_def["intent"]
            patterns = intent_def["patterns"]

            for pattern in patterns:
                if re.search(pattern, query_lower):
                    detected.append(intent)
                    break

        return detected

    def search(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Search knowledge base for relevant documents
        Returns top N most relevant documents
        """
        query_lower = query.lower()
        results = []

        # Detect intents
        intents = self.detect_intent(query)

        # Score each document
        for doc in self.knowledge_base:
            score = 0

            # Category match
            if doc["category"] in intents:
                score += 10

            # Keyword matches
            for keyword in doc["keywords"]:
                if keyword in query_lower:
                    score += 5

            # Title match
            if any(word in doc["title"].lower() for word in query_lower.split()):
                score += 3

            # Content match (partial)
            query_words = query_lower.split()
            content_lower = doc["content"].lower()
            for word in query_words:
                if len(word) > 3 and word in content_lower:
                    score += 1

            if score > 0:
                results.append((score, doc))

        # Sort by score and return top N
        results.sort(key=lambda x: x[0], reverse=True)
        return [doc for score, doc in results[:limit]]

    def get_context(self, query: str) -> str:
        """
        Get context for AI response
        Returns formatted context from relevant documents
        """
        relevant_docs = self.search(query)

        if not relevant_docs:
            return ""

        context = "**Relevant Documentation:**\n\n"

        for doc in relevant_docs:
            context += f"## {doc['title']}\n\n"
            context += doc['content'].strip() + "\n\n"

            if doc.get('examples'):
                context += "**Examples:**\n"
                for example in doc['examples']:
                    context += f"- `{example}`\n"
                context += "\n"

        return context

    def enhance_response(self, query: str, base_response: str) -> str:
        """
        Enhance AI response with RAG context
        """
        context = self.get_context(query)

        if not context:
            return base_response

        # Combine context with response
        enhanced = context + "\n\n" + base_response

        return enhanced


# Singleton instance
_rag_instance = None


def get_rag_system() -> QuantumRAG:
    """Get or create RAG system instance"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = QuantumRAG()
    return _rag_instance
