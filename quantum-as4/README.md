# Quantum ActionScript 4 / MXML Compiler

**Compile MXML + ActionScript 4 to JavaScript** - The modern evolution of Adobe Flex

## 🚀 What Is This?

This is a compiler that takes **MXML** (declarative UI markup) and **ActionScript 4** (modern AS3 evolution) and compiles them to vanilla JavaScript that runs in any modern browser.

Think of it as:
- **Flex/Flash for the modern web** - without Flash Player
- **Type-safe frontend development** - like TypeScript but with MXML
- **Write once, deploy everywhere** - Web, Mobile, Desktop, CLI (coming soon)

## ✨ Features

### Current (MVP - v0.1.0)

- ✅ **MXML Parser** - Parse Flex Spark MXML syntax
- ✅ **ActionScript 4 Parser** - Parse AS4 code (variables, functions, decorators)
- ✅ **JavaScript Code Generator** - Compile to vanilla JS
- ✅ **Runtime** - Render MXML components to DOM
- ✅ **Data Binding** - `{curly braces}` bindings work
- ✅ **Event Handlers** - `click="handleClick()"` works
- ✅ **CSS Styling** - External CSS or inline `<fx:Style>`
- ✅ **Basic Components**:
  - `<s:Application>` - Root container
  - `<s:VBox>` - Vertical layout
  - `<s:HBox>` - Horizontal layout
  - `<s:Label>` - Text display
  - `<s:Button>` - Buttons with click handlers
  - `<s:TextInput>` - Text inputs
  - `<s:Panel>` - Containers with title
  - `<s:Spacer>` - Layout spacer

### Coming Soon

- 🔜 **More Components** - DataGrid, List, TabNavigator, etc.
- 🔜 **Full AS4 Features** - async/await, pattern matching, generics
- 🔜 **WebAssembly Compilation** - For performance
- 🔜 **Multi-platform** - Mobile, Desktop, CLI renderers
- 🔜 **Hot Reload** - Instant feedback during development
- 🔜 **Type Checking** - Compile-time type validation

## 📦 Installation

```bash
# Clone the repo
git clone <repo-url>
cd quantum-as4

# Install dependencies
pip install -r requirements.txt

# Make CLI executable
chmod +x quantum-mxml
```

## 🎯 Quick Start

### 1. Create an MXML file

```xml
<?xml version="1.0"?>
<Application
    xmlns:fx="http://ns.adobe.com/mxml/2009"
    xmlns:s="library://ns.adobe.com/flex/spark"
    title="Hello World">

    <fx:Script>
        <![CDATA[
            [Bindable]
            private var message:String = "Hello, ActionScript 4!";

            private function handleClick():void {
                message = "Button clicked!";
            }
        ]]>
    </fx:Script>

    <fx:Style>
        .title {
            font-size: 24px;
            color: #333;
        }
    </fx:Style>

    <s:VBox padding="20" gap="15">
        <s:Label text="{message}" styleName="title"/>
        <s:Button label="Click Me" click="handleClick()"/>
    </s:VBox>

</Application>
```

### 2. Build it

```bash
./quantum-mxml build hello.mxml -o dist
```

### 3. Serve it

```bash
./quantum-mxml serve dist
```

### 4. Open browser

```
http://localhost:8080
```

**That's it!** Your MXML app is running in the browser! 🎉

## 📖 Examples

Check out `examples/hello.mxml` for a complete working example with:
- Data binding
- Event handlers
- Multiple components
- CSS styling
- Reactive state

## 🏗️ Architecture

```
MXML Source → Parser → AST → Code Generator → JavaScript
                                              ↓
                                         Runtime.js
                                              ↓
                                          Browser DOM
```

### Components

- **`compiler/mxml_parser.py`** - Parses MXML files using lxml
- **`compiler/as4_parser.py`** - Parses ActionScript 4 code
- **`compiler/codegen.py`** - Generates JavaScript from AST
- **`compiler/runtime/runtime.js`** - JavaScript runtime that renders components
- **`quantum-mxml`** - CLI tool

## 🤝 Contributing

This is a prototype! Contributions welcome:

1. **Add more components** - Implement DataGrid, List, etc.
2. **Improve transpiler** - Better AS4 → JS conversion
3. **Add tests** - Unit tests for parser and codegen
4. **Performance** - Optimize runtime rendering
5. **Documentation** - More examples and tutorials

## 📝 ActionScript 4 Syntax

AS4 is a modern evolution of ActionScript 3 with:

### Data Binding

```actionscript
[Bindable]
private var message:String = "Hello";
```

### Event Handlers

```actionscript
private function handleClick():void {
    message = "Clicked!";
}
```

### Async/Await (Coming Soon)

```actionscript
private async function loadData():Promise<void> {
    const response = await fetch("/api/data");
    const data = await response.json();
}
```

### Pattern Matching (Coming Soon)

```actionscript
match (status) {
    case "loading": showSpinner();
    case "error": showError();
    case "success": showData();
}
```

## 🎨 MXML Components

### Layout

```xml
<s:VBox padding="20" gap="15">
    <!-- Vertical stack -->
</s:VBox>

<s:HBox gap="10" verticalAlign="middle">
    <!-- Horizontal row -->
</s:HBox>
```

### Display

```xml
<s:Label text="Hello" fontSize="24" fontWeight="bold"/>

<s:Button label="Click Me" click="handleClick()"/>

<s:TextInput text="{username}" change="handleChange()"/>
```

### Containers

```xml
<s:Panel title="Settings">
    <s:VBox padding="15">
        <!-- Content -->
    </s:VBox>
</s:Panel>
```

## 🔧 CLI Commands

```bash
# Build MXML file
./quantum-mxml build input.mxml -o dist

# Build with verbose output
./quantum-mxml build input.mxml -o dist -v

# Serve built app
./quantum-mxml serve dist

# Serve on custom port
./quantum-mxml serve dist --port 3000
```

## 🐛 Known Limitations (MVP)

- ⚠️ Data binding is one-way only (no two-way binding yet)
- ⚠️ Limited component set (10 basic components)
- ⚠️ Simple transpiler (some AS4 features not supported)
- ⚠️ No type checking at compile time
- ⚠️ No source maps
- ⚠️ No minification

These will be addressed in future versions!

## 📜 License

MIT License - See LICENSE file

## 🙏 Acknowledgments

- Inspired by **Adobe Flex** and **Apache Flex**
- MXML syntax compatible with Flex Spark
- ActionScript evolution continues the AS3 legacy

## 🌟 Vision

The goal is to bring back the simplicity and power of Flex development to the modern web:

1. **Declarative UI** - No JSX, no virtual DOM, just MXML
2. **Type Safety** - Strong typing without TypeScript's complexity
3. **Multi-platform** - One codebase, deploy everywhere
4. **Migration Path** - Easy migration for legacy Flex apps
5. **Modern Features** - async/await, pattern matching, null safety

**ActionScript 4 is the future of type-safe frontend development!**

---

Made with ❤️ for the Flex community
