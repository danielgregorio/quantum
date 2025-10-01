# Quantum Language

::: tip 🧠 Codename: FF / FireFusion
⚡ **Status:** Core features implemented - Loops and Databinding working!
:::

## What is Quantum?

Quantum is an experimental declarative language that allows you to write components, web applications, and jobs using clean XML syntax. Think of it as a bridge between configuration and programming - write once, deploy anywhere!

## ✨ Key Features

- 🔄 **Loop Structures** - Range, Array, and List loops with full databinding
- 🔗 **Variable Databinding** - Dynamic `{variable}` substitution with expressions
- 🧩 **Component System** - Reusable, modular components
- 🌐 **Web Applications** - HTML and API applications
- ⚡ **Simple Syntax** - XML-based, easy to learn

## 🚀 Quick Example

```xml
<!-- Simple dynamic loop -->
<q:component name="NumberList" xmlns:q="https://quantum.lang/ns">
  <q:loop type="range" var="i" from="1" to="5">
    <q:return value="Number {i}: {i * 2}" />
  </q:loop>
</q:component>
```

**Output:** `["Number 1: 2", "Number 2: 4", "Number 3: 6", "Number 4: 8", "Number 5: 10"]`

## 🎯 Philosophy

**Simplicity over configuration** - Quantum prioritizes readability and ease of use while maintaining powerful capabilities for complex scenarios.

## 📚 Get Started

<div class="vp-feature-grid">
  <div class="vp-feature">
    <div class="vp-feature-icon">📖</div>
    <h3><a href="/guide/getting-started">Getting Started</a></h3>
    <p>Learn the basics and run your first Quantum component</p>
  </div>
  
  <div class="vp-feature">
    <div class="vp-feature-icon">🔄</div>
    <h3><a href="/guide/loops">Loops</a></h3>
    <p>Master Range, Array, and List loops with databinding</p>
  </div>
  
  <div class="vp-feature">
    <div class="vp-feature-icon">🌐</div>
    <h3><a href="/examples/web-applications">Web Apps</a></h3>
    <p>Build HTML and API applications with ease</p>
  </div>
</div>

## 🏆 Current Status

- ✅ **Component System** - Fully functional
- ✅ **Loop Structures** - Range, Array, List loops implemented
- ✅ **Variable Databinding** - `{variable}` and expressions working
- ✅ **Conditional Logic** - `q:if`, `q:else`, `q:elseif` supported
- ✅ **Web & API Servers** - Basic HTTP applications
- 🚧 **State Management** - Coming next (`q:set`)
- 🚧 **Functions** - Planned (`q:function`)

---

*Built with ❤️ using Python and powered by a clean AST-based architecture.*