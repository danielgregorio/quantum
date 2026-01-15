# Quantum Framework Introduction

Quantum is an experimental web framework inspired by Adobe ColdFusion. It brings the simplicity and pragmatism of ColdFusion development to the modern web.

## Key Features

- **XML-Based Syntax**: Declarative, ColdFusion-style `.q` components
- **Server-Side Rendering**: Fast SSR with component caching
- **Database Integration**: SQL queries with parameter binding
- **Built-in Authentication**: RBAC, bcrypt hashing, session management
- **Email Support**: SMTP integration with HTML templates
- **AI Integration**: Native LLM support with Ollama (local and free)

## Philosophy

Quantum follows a "zero ceremony" philosophy - write code, not configuration. The framework handles the complexity so you can focus on building your application.

## Getting Started

To create your first component:

```xml
<q:component name="Hello">
  <h1>Hello, Quantum!</h1>
</q:component>
```

Save this as `components/hello.q` and access it at `http://localhost:8080/hello`.
