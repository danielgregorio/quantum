# Quantum AS4 Multi-Platform Compiler Architecture

## Overview

The Quantum AS4 compiler compiles MXML + ActionScript 4 **directly** to native code for each target platform. No intermediate "JavaScript pseudocode" layer!

## High-Level Architecture

```
┌─────────────────────────────────────────────────────┐
│          MXML + AS4 Source Files                     │
│                  application.yaml                    │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│              MXML Parser (mxml_parser.py)            │
│  • Parse XML structure                               │
│  • Extract <fx:Script>, <fx:Style>                  │
│  • Build component tree                              │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│              AS4 Parser (as4_parser.py)              │
│  • Parse ActionScript 4 code                         │
│  • Build AST (variables, functions, classes)         │
│  • Type information extraction                       │
└──────────────────┬──────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────────────────┐
│         Platform-Agnostic AST (Intermediate)         │
│  • Component tree with platform-neutral semantics    │
│  • Business logic AST                                │
│  • Style information                                 │
│  • Assets metadata                                   │
└──────────────────┬──────────────────────────────────┘
                   ↓
         ┌─────────┴─────────┬──────────┬──────────┐
         ↓                   ↓          ↓          ↓
┌────────────────┐  ┌────────────┐  ┌──────────┐  ┌──────────┐
│  Web Compiler  │  │   Mobile   │  │ Desktop  │  │   CLI    │
│                │  │  Compiler  │  │ Compiler │  │ Compiler │
└────────┬───────┘  └─────┬──────┘  └────┬─────┘  └────┬─────┘
         ↓                ↓               ↓              ↓
┌────────────────┐  ┌────────────┐  ┌──────────┐  ┌──────────┐
│ HTML/JS/CSS    │  │React Native│  │  Tauri   │  │ Rich TUI │
│ + runtime.js   │  │    Code    │  │   Rust   │  │  Python  │
└────────────────┘  └────────────┘  └──────────┘  └──────────┘
```

---

## Component Details

### 1. Platform-Agnostic AST

**Purpose:** Single representation that can be compiled to any platform

```python
@dataclass
class UniversalAST:
    """Platform-agnostic intermediate representation"""

    # Application metadata
    app_info: AppInfo

    # UI component tree (platform-neutral)
    component_tree: ComponentTree

    # Business logic
    code_ast: CodeAST

    # Styles (will be adapted per platform)
    styles: StyleSheet

    # Assets (images, fonts, etc.)
    assets: AssetManifest

    # Data bindings
    bindings: List[Binding]

    # Events and handlers
    events: Dict[str, EventHandler]
```

**Key Insight:** The AST describes **WHAT** the app does, not **HOW** it's rendered on each platform.

Example:
```python
Button(
    label="Click Me",
    onClick="handleClick",
    style={"color": "blue", "padding": 10}
)
```

This is platform-neutral. Each compiler interprets it:
- Web: `<button onclick="...">`
- Mobile: `<TouchableOpacity onPress="...">`
- Desktop: `gtk::Button`
- CLI: `[Enter] to click`

---

### 2. Platform-Specific Compilers

Each compiler translates the Universal AST to native code for its platform.

#### Web Compiler (`compilers/web.py`)

**Input:** UniversalAST
**Output:** HTML + JavaScript (ES6 modules) + CSS

```python
class WebCompiler:
    def compile(self, ast: UniversalAST, config: WebConfig) -> WebOutput:
        """Compile to web application"""

        # Generate HTML structure
        html = self._generate_html(ast)

        # Generate JavaScript (no runtime needed!)
        # Use native Web Components or direct DOM manipulation
        js = self._generate_javascript(ast)

        # Generate CSS
        css = self._generate_css(ast.styles)

        # Generate manifest.json for PWA (if enabled)
        if config.pwa.enabled:
            manifest = self._generate_pwa_manifest(config)

        return WebOutput(
            html=html,
            javascript=js,
            css=css,
            manifest=manifest,
            assets=self._process_assets(ast.assets)
        )
```

**Web Output Structure:**
```
dist/web/
├── index.html
├── app.js              # Compiled AS4 → JavaScript
├── styles.css          # Compiled styles
├── manifest.json       # PWA manifest (optional)
├── service-worker.js   # Service worker (optional)
└── assets/
    ├── images/
    ├── fonts/
    └── data/
```

#### Mobile Compiler (`compilers/mobile.py`)

**Input:** UniversalAST
**Output:** React Native or Flutter code

```python
class MobileCompiler:
    def compile(self, ast: UniversalAST, config: MobileConfig) -> MobileOutput:
        """Compile to mobile application"""

        if config.type == "react-native":
            return self._compile_react_native(ast, config)
        elif config.type == "flutter":
            return self._compile_flutter(ast, config)
```

**React Native Output:**
```jsx
// Generated from MXML <s:Button label="Click" click="handleClick()"/>

import { TouchableOpacity, Text } from 'react-native';

function ButtonComponent({ label, onClick }) {
    return (
        <TouchableOpacity onPress={onClick}>
            <Text>{label}</Text>
        </TouchableOpacity>
    );
}
```

**Mobile Output Structure:**
```
dist/mobile/
├── package.json
├── App.js              # Main component
├── components/         # Generated components
├── screens/            # Screens from MXML
├── assets/             # Processed assets
├── android/            # Android project
└── ios/                # iOS project
```

#### Desktop Compiler (`compilers/desktop.py`)

**Input:** UniversalAST
**Output:** Tauri Rust + Frontend

```python
class DesktopCompiler:
    def compile(self, ast: UniversalAST, config: DesktopConfig) -> DesktopOutput:
        """Compile to desktop application"""

        if config.type == "tauri":
            return self._compile_tauri(ast, config)
        elif config.type == "electron":
            return self._compile_electron(ast, config)
```

**Tauri Output:**
```rust
// src-tauri/src/main.rs
// Generated window configuration

use tauri::Manager;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let window = app.get_window("main").unwrap();
            window.set_title("My App")?;
            window.set_size(tauri::Size::Logical(1200.0, 800.0))?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running application");
}
```

**Desktop Output Structure:**
```
dist/desktop/
├── src-tauri/
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── src/
│       └── main.rs      # Rust backend
├── src/
│   ├── index.html
│   ├── app.js           # Frontend (same as web)
│   └── styles.css
└── icons/
```

#### CLI Compiler (`compilers/cli.py`)

**Input:** UniversalAST
**Output:** Python Rich TUI or Rust TUI

```python
class CLICompiler:
    def compile(self, ast: UniversalAST, config: CLIConfig) -> CLIOutput:
        """Compile to CLI application"""

        if config.type == "rich":
            return self._compile_rich_tui(ast, config)
        elif config.type == "rust-tui":
            return self._compile_rust_tui(ast, config)
```

**Rich TUI Output:**
```python
# Generated from MXML

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def render_user_list(users):
    table = Table(title="Users")
    table.add_column("ID")
    table.add_column("Name")

    for user in users:
        table.add_row(str(user.id), user.name)

    console.print(table)
```

**CLI Output Structure:**
```
dist/cli/
├── myapp                # Executable
├── src/
│   ├── __init__.py
│   ├── main.py          # Entry point
│   ├── components/      # Generated TUI components
│   └── models/          # Data models
└── assets/
```

---

## 3. Component Mapping

How MXML components map to each platform:

| MXML Component | Web | Mobile (RN) | Desktop (Tauri) | CLI (Rich) |
|----------------|-----|-------------|-----------------|------------|
| `<s:VBox>` | `<div style="flex-direction:column">` | `<View style={{flexDirection:'column'}}>` | `<div style="flex-direction:column">` | `Panel()` |
| `<s:HBox>` | `<div style="flex-direction:row">` | `<View style={{flexDirection:'row'}}>` | `<div style="flex-direction:row">` | `Columns()` |
| `<s:Label>` | `<span>` | `<Text>` | `<span>` | `Text()` |
| `<s:Button>` | `<button>` | `<TouchableOpacity>` | `<button>` | `Button()` or `[Enter]` prompt |
| `<s:TextInput>` | `<input type="text">` | `<TextInput>` | `<input type="text">` | `Prompt.ask()` |
| `<s:DataGrid>` | `<table>` + JS | `<FlatList>` | `<table>` + JS | `Table()` |
| `<s:List>` | `<ul>` + JS | `<FlatList>` | `<ul>` + JS | `Table()` or list |
| `<s:Panel>` | `<div class="panel">` | `<View style={panelStyle}>` | `<div class="panel">` | `Panel(border=True)` |
| `<s:Image>` | `<img>` | `<Image>` | `<img>` | `[IMAGE]` placeholder |

---

## 4. Compilation Process

```python
# quantum-mxml build

def build(config_file: str):
    # 1. Load configuration
    config = load_application_config(config_file)

    # 2. Parse MXML + AS4
    mxml_ast = MXMLParser().parse(config.entry.mxml)
    as4_ast = AS4Parser().parse(mxml_ast.script)

    # 3. Create Universal AST
    universal_ast = create_universal_ast(mxml_ast, as4_ast, config)

    # 4. Validate AST
    validator = ASTValidator()
    validator.validate(universal_ast)

    # 5. Compile for each enabled target
    for target in config.targets:
        if not target.enabled:
            continue

        if target.name == "web":
            compiler = WebCompiler()
            output = compiler.compile(universal_ast, target.config)
            write_output(target.output, output)

        elif target.name == "mobile":
            compiler = MobileCompiler()
            output = compiler.compile(universal_ast, target.config)
            write_output(target.output, output)

        elif target.name == "desktop":
            compiler = DesktopCompiler()
            output = compiler.compile(universal_ast, target.config)
            write_output(target.output, output)

        elif target.name == "cli":
            compiler = CLICompiler()
            output = compiler.compile(universal_ast, target.config)
            write_output(target.output, output)

    print(f"✅ Built {len(enabled_targets)} targets")
```

---

## 5. Platform-Specific Optimizations

Each compiler applies platform-specific optimizations:

### Web
- Tree shaking (remove unused code)
- Code splitting (lazy loading)
- Minification
- Gzip compression
- Image optimization (WebP conversion)
- PWA caching strategies

### Mobile
- Image asset optimization (multiple resolutions)
- Bundle size reduction
- Native module integration
- Platform-specific APIs (camera, GPS)
- App store optimization

### Desktop
- Binary size optimization
- Native system integration
- Window management
- System tray
- Auto-updates

### CLI
- Startup time optimization
- Memory footprint reduction
- Terminal compatibility
- Colors/no-colors modes

---

## 6. Development vs Production

### Development Mode
```yaml
build:
  mode: "development"
  source_maps: true
  hot_reload: true
  watch: true
```

**Behavior:**
- No minification (readable code)
- Source maps enabled (debugging)
- Hot reload (instant feedback)
- Verbose error messages
- Development server with CORS

### Production Mode
```yaml
build:
  mode: "production"
  optimize: true
```

**Behavior:**
- Minification enabled
- Tree shaking
- Bundle splitting
- Image optimization
- Error tracking (Sentry, etc.)
- CDN-ready assets

---

## 7. Asset Processing

Assets are processed per-platform:

```python
class AssetProcessor:
    def process(self, asset: Asset, target: Platform) -> ProcessedAsset:
        """Process asset for specific platform"""

        if asset.type == "image":
            if target == Platform.WEB:
                # Convert to WebP, generate srcset
                return self._process_image_web(asset)

            elif target == Platform.MOBILE:
                # Generate @1x, @2x, @3x versions
                return self._process_image_mobile(asset)

            elif target == Platform.DESKTOP:
                # Normal processing
                return self._process_image_desktop(asset)

            elif target == Platform.CLI:
                # Skip or convert to ASCII art
                return None  # Skip images in CLI
```

---

## Benefits of This Architecture

1. **Native Performance** - Each platform gets optimized native code
2. **No Runtime Overhead** - No "universal runtime" slowing things down
3. **Platform Features** - Can use platform-specific APIs
4. **Small Bundle Sizes** - Only include what's needed per platform
5. **Better UX** - Native look and feel on each platform
6. **Easy to Extend** - Add new platforms without touching others

---

## Next Steps

1. ✅ Create Universal AST structure
2. ⏳ Implement Web Compiler (refactor current codegen)
3. ⏳ Implement Mobile Compiler (React Native)
4. ⏳ Implement Desktop Compiler (Tauri)
5. ⏳ Implement CLI Compiler (Rich TUI)
6. ⏳ Add asset processing
7. ⏳ Add hot reload
8. ⏳ Add production optimizations
