# Getting Started

Welcome to Quantum! This guide will help you get up and running with the Quantum language in just a few minutes.

## What is Quantum?

Quantum is an experimental declarative language that uses XML syntax to create components, web applications, and jobs. It's designed with the philosophy of "simplicity over configuration" - making complex tasks simple while keeping the language clean and readable.

## Installation

### Prerequisites

- Python 3.8 or higher
- Git (for cloning the repository)

### Clone and Setup

```bash
# Clone the repository
git clone https://github.com/danielgregorio/quantum.git
cd quantum

# Install dependencies (Flask for web server)
pip install flask

# Test the installation
python quantum.py run examples/hello.q
```

You should see:
```
[EXEC] Executing component: HelloWorld
[SUCCESS] Result: Hello World!
```

## Your First Component

Let's create a simple "Hello World" component:

```xml
<!-- hello.q -->
<q:component name="HelloWorld" xmlns:q="https://quantum.lang/ns">
  <q:return value="Hello World!" />
</q:component>
```

Run it with:
```bash
python quantum.py run hello.q
```

## Adding Dynamic Content

Now let's make it dynamic with a loop:

```xml
<!-- greetings.q -->
<q:component name="Greetings" xmlns:q="https://quantum.lang/ns">
  <q:loop type="list" var="name" items="Alice,Bob,Charlie">
    <q:return value="Hello {name}!" />
  </q:loop>
</q:component>
```

**Output:** `["Hello Alice!", "Hello Bob!", "Hello Charlie!"]`

## Understanding the Structure

Every Quantum file contains:

1. **Root Element**: Either `q:component`, `q:application`, or `q:job`
2. **Namespace**: Always include `xmlns:q="https://quantum.lang/ns"`
3. **Content**: The logic and output of your component

### Components

Components are reusable pieces of logic that can:
- Accept parameters (`q:param`)
- Return values (`q:return`)
- Contain loops (`q:loop`)
- Use conditional logic (`q:if`, `q:else`)

### Applications

Applications are deployable web services:
- HTML applications serve web pages
- API applications serve JSON endpoints

```xml
<!-- webapp.q -->
<q:application id="webapp" type="html" xmlns:q="https://quantum.lang/ns">
  <q:route path="/hello" method="GET">
    <q:return value="Hello from Web App!" />
  </q:route>
</q:application>
```

## Next Steps

- Learn about [Loop Structures](/guide/loops) for data iteration
- Explore [Variable Databinding](/guide/databinding) for dynamic content
- Check out [Examples](/examples/) for real-world use cases

## Debug Mode

For detailed execution information, use the `--debug` flag:

```bash
python quantum.py run examples/hello.q --debug
```

This shows:
- File parsing details
- AST generation info
- Validation steps
- Execution flow