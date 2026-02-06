# Package Manager

Quantum's package manager allows you to share and reuse components across projects. Packages are self-contained bundles of `.q` components that can be installed, published, and versioned.

## Package Structure

A Quantum package follows this structure:

```
my-component/
├── quantum.yaml         # Package manifest (required)
├── src/
│   ├── index.q          # Main component (entry point)
│   └── SubComponent.q   # Additional components
├── examples/
│   └── demo.q           # Usage examples
└── README.md            # Documentation
```

## Package Manifest

The `quantum.yaml` file defines your package:

```yaml
name: my-component
version: 1.0.0
description: A reusable UI component for Quantum
author: Your Name <your@email.com>
license: MIT
main: src/index.q

# Keywords for search
keywords:
  - ui
  - component
  - button

# Package dependencies
dependencies:
  ui-base: ^1.0.0
  icons: ">=2.0.0"

# Repository and homepage
repository: https://github.com/you/my-component
homepage: https://my-component.example.com

# Exported component names
exports:
  - MyComponent
  - MySubComponent
```

### Manifest Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Package name (lowercase, alphanumeric with hyphens) |
| `version` | Yes | Semantic version (e.g., "1.0.0") |
| `description` | No | Package description |
| `author` | No | Author name and email |
| `license` | No | License identifier (default: "MIT") |
| `main` | No | Entry point file (default: "src/index.q") |
| `dependencies` | No | Map of package name to version constraint |
| `keywords` | No | List of search keywords |
| `repository` | No | Repository URL |
| `homepage` | No | Homepage URL |
| `exports` | No | List of exported component names |

### Version Constraints

Quantum supports several version constraint formats:

| Format | Description | Example |
|--------|-------------|---------|
| Exact | Specific version | `1.0.0` |
| Caret | Compatible with version | `^1.0.0` (>=1.0.0 <2.0.0) |
| Tilde | Approximately equivalent | `~1.0.0` (>=1.0.0 <1.1.0) |
| Range | Greater/less than | `>=1.0.0`, `<2.0.0` |
| Any | Any version | `*` |

## Creating a Package

### Using `quantum pkg init`

The fastest way to create a new package:

```bash
# Create in current directory
quantum pkg init

# Create in specific directory with options
quantum pkg init ./my-package -n my-package -a "Your Name" -d "Package description"
```

Options:

| Option | Short | Description |
|--------|-------|-------------|
| `--name` | `-n` | Package name |
| `--description` | `-d` | Package description |
| `--author` | `-a` | Author name |
| `--license` | `-l` | License identifier (default: MIT) |

### Generated Files

After running `quantum pkg init`, you'll have:

**quantum.yaml:**
```yaml
name: my-package
version: 1.0.0
description: ""
author: ""
license: MIT
main: src/index.q
```

**src/index.q:**
```xml
<q:component name="MyPackage">
  <!-- Component parameters -->
  <q:param name="title" type="string" default="MyPackage" />

  <!-- Component template -->
  <div class="my-package">
    <h1>{title}</h1>
    <q:slot />
  </div>
</q:component>
```

**examples/demo.q:**
```xml
<q:component name="Demo">
  <q:import component="MyPackage" from="../src" />

  <MyPackage title="Hello World">
    <p>This is a demo of the my-package component.</p>
  </MyPackage>
</q:component>
```

## Installing Packages

### From Local Path

```bash
quantum pkg install ./path/to/package
```

### From Git Repository

```bash
# From GitHub
quantum pkg install github:user/package-name

# From any Git URL
quantum pkg install https://github.com/user/package.git

# Specific version/tag
quantum pkg install github:user/package@v1.0.0
```

### Options

| Option | Description |
|--------|-------------|
| `--version`, `-v` | Install specific version |
| `--no-deps` | Skip dependency resolution |

### Example

```bash
# Install with dependencies
quantum pkg install ./my-button

# Install specific version without dependencies
quantum pkg install github:quantum/ui-kit@2.0.0 --no-deps
```

## Using Installed Packages

Once installed, import components in your `.q` files:

```xml
<q:component name="MyApp">
  <!-- Import from installed package -->
  <q:import component="Button" from="ui-kit" />
  <q:import component="Card" from="ui-kit" />
  <q:import component="Modal" from="modals" />

  <Card title="Welcome">
    <p>Hello from my app!</p>
    <Button variant="primary" on-click="handleClick">
      Click Me
    </Button>
  </Card>
</q:component>
```

## Package Commands

### List Installed Packages

```bash
quantum pkg list
```

Output:
```
[INFO] Installed packages (3):

   ui-kit@2.1.0
      A comprehensive UI component kit
      Versions: 2.1.0, 2.0.0, 1.5.0

   modals@1.0.0
      Modal and dialog components

   icons@3.0.0
      Icon library for Quantum
```

### Search Packages

```bash
quantum pkg search button
```

Output:
```
[INFO] Found 2 package(s):

   ui-kit@2.1.0
      A comprehensive UI component kit
      Keywords: ui, button, component, form

   button-lib@1.0.0
      Standalone button components
      Keywords: button, ui
```

### Get Package Info

```bash
quantum pkg info ui-kit
```

Output:
```
[INFO] Package: ui-kit

   Version:     2.1.0
   Description: A comprehensive UI component kit
   Author:      Quantum Team
   License:     MIT
   Main:        src/index.q
   Path:        ~/.quantum/packages/ui-kit/2.1.0
   Keywords:    ui, button, component, form

   Dependencies:
      icons: ^3.0.0

   Exports:
      Button
      Card
      Modal
      Input
      Select

   All versions: 2.1.0, 2.0.0, 1.5.0, 1.0.0
```

### Remove a Package

```bash
# Remove all versions
quantum pkg remove ui-kit

# Remove specific version
quantum pkg remove ui-kit -v 1.5.0
```

## Publishing Packages

### Create Archive

Create a distributable archive of your package:

```bash
quantum pkg publish ./my-package
```

Output:
```
[INFO] Publishing package from /path/to/my-package
[SUCCESS] Package archive created!
   Archive: /path/to/my-package/my-package-1.0.0.tar.gz

Share this archive or upload to a registry.
```

### Archive Contents

The archive includes:
- `quantum.yaml` manifest
- All files in `src/`
- `README.md` if present
- `LICENSE` if present

Excluded by default:
- `.git/`
- `node_modules/`
- `__pycache__/`
- `*.pyc`
- `.env`

## Dependency Resolution

When installing a package, Quantum automatically resolves dependencies:

```bash
quantum pkg install my-app
```

Output:
```
[INFO] Installing package from ./my-app
[INFO] Resolving dependencies...
   - ui-kit@2.1.0
   - icons@3.0.0 (dependency of ui-kit)
[SUCCESS] Installed 3 package(s):
   my-app@1.0.0
   ui-kit@2.1.0
   icons@3.0.0
```

### Dependency Conflicts

If there are conflicting version requirements, Quantum will report:

```
[ERROR] Dependency conflict:
   my-app requires icons@^2.0.0
   ui-kit requires icons@^3.0.0

Resolution options:
   1. Update my-app to support icons@3.0.0
   2. Use --no-deps to skip dependency resolution
```

## Package Storage

Installed packages are stored in:

- **Global:** `~/.quantum/packages/<name>/<version>/`
- **Project-local:** `./quantum_packages/<name>/<version>/`

### Import Resolution Order

1. Project-local `./components/`
2. Project-local `./quantum_packages/`
3. Global `~/.quantum/packages/`

## Example: Creating a Button Package

### Step 1: Initialize

```bash
mkdir quantum-button
cd quantum-button
quantum pkg init -n quantum-button -d "A customizable button component"
```

### Step 2: Create the Component

Edit `src/index.q`:

```xml
<q:component name="Button">
  <!-- Props -->
  <q:param name="variant" type="string" default="primary" />
  <q:param name="size" type="string" default="md" />
  <q:param name="disabled" type="boolean" default="false" />
  <q:param name="loading" type="boolean" default="false" />
  <q:param name="onClick" type="string" />

  <!-- Computed class -->
  <q:set name="buttonClass" value="btn btn-{variant} btn-{size}" />

  <button class="{buttonClass}" disabled="{disabled}" on-click="{onClick}">
    <q:if condition="{loading}">
      <span class="spinner"></span>
    </q:if>
    <q:slot />
  </button>

  <style>
    .btn {
      padding: 8px 16px;
      border-radius: 4px;
      border: none;
      cursor: pointer;
      font-size: 14px;
    }
    .btn-primary { background: #007bff; color: white; }
    .btn-secondary { background: #6c757d; color: white; }
    .btn-danger { background: #dc3545; color: white; }
    .btn-sm { padding: 4px 8px; font-size: 12px; }
    .btn-lg { padding: 12px 24px; font-size: 16px; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .spinner {
      display: inline-block;
      width: 12px;
      height: 12px;
      border: 2px solid currentColor;
      border-top-color: transparent;
      border-radius: 50%;
      animation: spin 0.6s linear infinite;
      margin-right: 8px;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</q:component>
```

### Step 3: Add Example

Edit `examples/demo.q`:

```xml
<q:component name="ButtonDemo">
  <q:import component="Button" from="../src" />

  <h1>Button Demo</h1>

  <h2>Variants</h2>
  <Button variant="primary">Primary</Button>
  <Button variant="secondary">Secondary</Button>
  <Button variant="danger">Danger</Button>

  <h2>Sizes</h2>
  <Button size="sm">Small</Button>
  <Button size="md">Medium</Button>
  <Button size="lg">Large</Button>

  <h2>States</h2>
  <Button disabled="true">Disabled</Button>
  <Button loading="true">Loading</Button>
</q:component>
```

### Step 4: Update Manifest

```yaml
name: quantum-button
version: 1.0.0
description: A customizable button component for Quantum
author: Your Name
license: MIT
main: src/index.q
keywords:
  - button
  - ui
  - component
exports:
  - Button
```

### Step 5: Publish

```bash
quantum pkg publish .
```

## Best Practices

### Naming Conventions

- Use lowercase with hyphens: `my-component`
- Use descriptive names: `form-validation`, `data-table`
- Prefix with scope for organization: `@myorg/button`

### Versioning

Follow semantic versioning:
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

### Documentation

Include a comprehensive README.md:

```markdown
# My Component

Short description of what it does.

## Installation

\`\`\`bash
quantum pkg install my-component
\`\`\`

## Usage

\`\`\`xml
<q:import component="MyComponent" from="my-component" />

<MyComponent prop="value">
  Content here
</MyComponent>
\`\`\`

## Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| prop | string | "" | Description |

## Examples

See the `examples/` directory for more examples.

## License

MIT
```

### Component Design

1. **Use sensible defaults** - Components should work with minimal configuration
2. **Document all props** - Use `<q:param>` with descriptions
3. **Support slots** - Allow content projection with `<q:slot>`
4. **Include styles** - Bundle necessary CSS
5. **Be accessible** - Include ARIA attributes where needed

## Related Documentation

- [Plugin System](/extensibility/plugins) - Extend Quantum with plugins
- [Components](/guide/components) - Component basics
- [Import System](/guide/components#importing-components) - Importing components
