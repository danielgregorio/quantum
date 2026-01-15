# Quantum - ColdFusion-Inspired Web Framework

> ⚡ **Status:** Full-Stack Framework (12/12 Phases Complete)
> 🎯 **Philosophy:** Simplicity over configuration - Write once, deploy anywhere!
> 🧪 **Tests:** 16/16 passing (100%)

## 📖 What is Quantum?

Quantum is an experimental web framework inspired by Adobe ColdFusion, designed to bring the simplicity and pragmatism of ColdFusion development to the modern web. Write declarative XML-based components that render to HTML, handle forms, query databases, send emails, and more - all with minimal boilerplate.

### ✨ Key Features

- **🎨 XML-Based Syntax** - Declarative, ColdFusion-style `.q` components
- **🔄 Server-Side Rendering** - Fast SSR with component caching
- **📊 Database Integration** - SQL queries with parameter binding & Query-of-Queries
- **🔐 Built-in Auth** - RBAC, bcrypt hashing, session management
- **📧 Email Support** - SMTP integration with HTML templates
- **📤 File Uploads** - Secure upload handling with validation
- **🎯 HTMX Integration** - Progressive enhancement out of the box
- **🏝️ Islands Architecture** - Client-side reactivity when needed
- **✅ Full Test Suite** - 100% passing tests with pytest

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/danielgregorio/quantum.git
cd quantum

# Install dependencies
pip install -r requirements.txt

# Start the server
python quantum.py start
```

Server starts at: **http://localhost:8080**
Health check: **http://localhost:8080/_health**

### Your First Component

Create `components/hello.q`:

```xml
<q:component name="HelloWorld">
  <q:param name="name" type="string" default="World" />

  <html>
    <body>
      <h1>Hello {name}!</h1>
      <p>Welcome to Quantum Framework.</p>
    </body>
  </html>

  <style>
    h1 {
      color: #007bff;
      font-family: Arial, sans-serif;
    }
  </style>
</q:component>
```

Access at: **http://localhost:8080/hello**

## 📚 Language Features

### Databinding

```xml
<p>User: {user.name}</p>
<p>Total: ${price * quantity}</p>
<p>Items: {items.length}</p>
```

### Control Structures

```xml
<!-- Conditionals -->
<q:if condition="{user.isAdmin}">
  <button>Admin Panel</button>
</q:if>
<q:else>
  <p>Access Denied</p>
</q:else>

<!-- Loops -->
<q:loop type="array" array="{products}" item="product">
  <div class="product">
    <h3>{product.name}</h3>
    <p>${product.price}</p>
  </div>
</q:loop>
```

### Database Queries

```xml
<q:query datasource="db" name="users">
  SELECT * FROM users
  WHERE status = :status
  ORDER BY created_at DESC
</q:query>

<q:loop type="query" query="{users}" item="user">
  <p>{user.name} - {user.email}</p>
</q:loop>
```

### Forms & Actions

```xml
<form method="POST" action="/contact?action=submit">
  <input type="email" name="email" required />
  <textarea name="message" required></textarea>
  <button type="submit">Send</button>
</form>

<q:action name="submit" method="POST">
  <q:param name="email" type="email" required="true" />
  <q:param name="message" type="string" required="true" />

  <q:mail to="admin@example.com" from="{email}" subject="New Contact">
    Message from {email}: {message}
  </q:mail>

  <q:redirect url="/contact" flash="Message sent successfully!" />
</q:action>
```

### Authentication

```xml
<q:component name="Dashboard" require_auth="true" require_role="admin">
  <h1>Admin Dashboard</h1>
  <p>Welcome, {session.userName}!</p>
  <p>User ID: {session.userId}</p>
</q:component>
```

## 🗂️ Project Structure

```
quantum/
├── src/
│   ├── core/
│   │   ├── parser.py              # XML → AST parser
│   │   ├── ast_nodes.py           # AST node definitions
│   │   └── features/              # 16 feature modules
│   │       ├── state_management/
│   │       ├── loops/
│   │       ├── conditionals/
│   │       ├── functions/
│   │       ├── database/
│   │       └── ...
│   ├── runtime/
│   │   ├── component.py           # Main execution engine
│   │   ├── web_server.py          # Flask web server
│   │   ├── renderer.py            # HTML renderer
│   │   ├── auth_service.py        # Authentication
│   │   ├── email_service.py       # Email sending
│   │   └── ...
│   └── cli/
│       └── runner.py              # CLI interface
├── components/                    # Your .q components
├── tests/                         # Test suite (100% passing)
├── docs/                          # VitePress documentation
├── quantum.py                     # Main entry point
└── requirements.txt               # Python dependencies
```

## ✅ Implementation Status

### Completed Features (12/12 Phases)

| Feature | Status | Description |
|---------|--------|-------------|
| Template Mixing | ✅ 100% | HTML + Quantum tags, SSR, Databinding |
| Component Composition | ✅ 95% | Import, props, slots |
| Forms & Actions | ✅ 100% | Server-side validation, flash messages |
| Database Queries | ✅ 100% | SQL, Query-of-Queries, transactions |
| Session Management | ✅ 100% | Session/application/request scopes |
| Authentication | ✅ 100% | RBAC, bcrypt, session-based auth |
| File Uploads | ✅ 100% | Secure handling, validation |
| Email Sending | ✅ 100% | SMTP integration |
| Developer Experience | ✅ 100% | CLI tools, error messages, health check |
| HTMX Partials | ✅ 100% | Progressive enhancement |
| Islands Architecture | ✅ 100% | Client-side reactivity |
| Testing Infrastructure | ✅ 100% | pytest, 100% passing tests |

### Planned Features (Roadmap Q1-Q3 2025)

| Feature | Status | Priority | Est. Time |
|---------|--------|----------|-----------|
| q:invoke | 📝 Planned | HIGH | 2-3 weeks |
| q:data | 📝 Planned | HIGH | 2-3 weeks |
| q:llm | 📝 Planned | HIGH | 3-4 weeks |
| q:agent | 📝 Planned | LOW | 4-6 weeks |
| REST API Runtime | 🚧 Partial | MEDIUM | 2 weeks |
| Event System | 🚧 Partial | MEDIUM | 1 week |

## 🧪 Testing

Run the full test suite:

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_parser.py -v
```

Current test status: **16/16 passing (100%)** ✅

## 📊 Statistics

- **~8,500 lines** of code
- **16 feature modules** fully structured
- **156+ training examples** for ML
- **31 demo components** available
- **28% code coverage** (growing)

## 🎯 Use Cases

Quantum is perfect for:

- **Rapid prototyping** - Build working apps fast
- **Internal tools** - Admin panels, dashboards
- **CRUD applications** - Database-driven apps
- **Content management** - CMS, blogs, wikis
- **Learning** - Understand full-stack development

## 🔗 Documentation

- [Architecture](./ARCHITECTURE.md) - System design & patterns
- [Roadmap](./ROADMAP.md) - Future features & timeline
- [Implementation Status](./IMPLEMENTATION_STATUS.md) - Detailed status
- [Feature Workflow](./FEATURE_WORKFLOW.md) - Development process
- [VitePress Docs](./docs/) - Full documentation site

## 🤝 Contributing

Quantum is an experimental project exploring intent-driven development. Contributions welcome!

1. Check [ROADMAP.md](./ROADMAP.md) for planned features
2. Read [ARCHITECTURE.md](./ARCHITECTURE.md) for system design
3. Look for issues tagged `good-first-issue`
4. Submit PR with tests

## 📝 License

[MIT License](./LICENSE)

## 🙏 Acknowledgments

Inspired by:
- **Adobe ColdFusion** - Simplicity & pragmatism
- **HTMX** - Progressive enhancement philosophy
- **Flask** - Micro-framework design
- **Vue.js** - Reactive components

---

**Made with ❤️ by [danielgregorio](https://github.com/danielgregorio)**

⭐ Star this repo if you find it interesting!
