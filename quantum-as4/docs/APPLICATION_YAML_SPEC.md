# Application Configuration Specification

## Overview

`application.yaml` defines the application metadata, target platforms, and build configuration for Quantum AS4/MXML applications.

## Full Example

```yaml
# application.yaml

# Application Metadata
application:
  name: "My Awesome App"
  version: "1.0.0"
  description: "A cross-platform application built with ActionScript 4"
  author: "Your Name"
  license: "MIT"
  homepage: "https://example.com"

# Entry Point
entry:
  mxml: "src/Main.mxml"        # Main MXML file
  assets: "assets/"              # Assets directory

# Target Platforms
targets:
  web:
    enabled: true
    output: "dist/web"
    config:
      title: "My Awesome App"
      favicon: "assets/favicon.ico"
      meta:
        description: "A great web app"
        keywords: ["app", "quantum", "as4"]
      pwa:
        enabled: true
        manifest: "manifest.json"
      optimize: true             # Minify, tree-shake
      source_maps: true

  mobile:
    enabled: true
    output: "dist/mobile"
    config:
      type: "react-native"       # or "flutter"
      bundle_id: "com.example.myapp"
      app_name: "My App"
      icon: "assets/icon.png"
      splash_screen: "assets/splash.png"
      platforms:
        - android
        - ios
      android:
        min_sdk: 21
        target_sdk: 33
      ios:
        min_version: "13.0"

  desktop:
    enabled: true
    output: "dist/desktop"
    config:
      type: "tauri"              # or "electron"
      name: "My Awesome App"
      icon: "assets/icon.png"
      window:
        width: 1200
        height: 800
        resizable: true
        fullscreen: false
      platforms:
        - windows
        - macos
        - linux

  cli:
    enabled: false
    output: "dist/cli"
    config:
      type: "rich"               # Python Rich TUI
      name: "myapp"
      executable: true

# Build Configuration
build:
  mode: "development"            # or "production"
  source_maps: true
  hot_reload: true
  watch: true

  # Optimization
  optimize:
    minify: false
    tree_shake: false
    bundle_splitting: false

  # TypeScript-style checking
  type_checking:
    enabled: true
    strict: false

# Assets
assets:
  images:
    - "assets/images/**/*"
  fonts:
    - "assets/fonts/**/*"
  data:
    - "assets/data/**/*.json"

# Dependencies
dependencies:
  # AS4 packages
  - "quantum-ui-components@1.0.0"
  - "quantum-charts@2.1.0"

# Platform-Specific Overrides
overrides:
  mobile:
    assets:
      # Use smaller images for mobile
      images:
        - "assets/images-mobile/**/*"

  cli:
    # CLI might not need images
    assets:
      images: []

# Deployment
deploy:
  web:
    provider: "netlify"          # or "vercel", "aws", etc.
    domain: "myapp.example.com"

  mobile:
    provider: "app-store"

  desktop:
    provider: "github-releases"
```

---

## Field Definitions

### application

**Required metadata about the application**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Application display name |
| `version` | string | Yes | SemVer version (e.g., "1.0.0") |
| `description` | string | No | Short description |
| `author` | string | No | Author name |
| `license` | string | No | License type (MIT, Apache, etc.) |
| `homepage` | string | No | Project homepage URL |

### entry

**Application entry point**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `mxml` | string | Yes | Path to main MXML file |
| `assets` | string | No | Path to assets directory |

### targets

**Platform-specific build configurations**

Each target (web, mobile, desktop, cli) has:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `enabled` | boolean | Yes | Enable this target |
| `output` | string | Yes | Output directory |
| `config` | object | Yes | Platform-specific config |

---

## Platform-Specific Configs

### Web

```yaml
web:
  enabled: true
  output: "dist/web"
  config:
    title: "App Title"
    favicon: "path/to/favicon.ico"
    meta:
      description: "SEO description"
      keywords: ["keyword1", "keyword2"]
      og_image: "path/to/og-image.png"
    pwa:
      enabled: true
      manifest: "manifest.json"
      service_worker: true
    optimize: true
    source_maps: true
    bundle:
      type: "module"              # or "iife"
      format: "esm"
```

### Mobile

```yaml
mobile:
  enabled: true
  output: "dist/mobile"
  config:
    type: "react-native"          # or "flutter"
    bundle_id: "com.company.app"
    app_name: "App Name"
    icon: "assets/icon.png"
    splash_screen: "assets/splash.png"
    orientation: "portrait"       # or "landscape", "both"
    platforms:
      - android
      - ios
    android:
      min_sdk: 21
      target_sdk: 33
      permissions:
        - "INTERNET"
        - "CAMERA"
    ios:
      min_version: "13.0"
      capabilities:
        - "push-notifications"
```

### Desktop

```yaml
desktop:
  enabled: true
  output: "dist/desktop"
  config:
    type: "tauri"                 # or "electron"
    name: "App Name"
    identifier: "com.company.app"
    icon: "assets/icon.png"
    window:
      width: 1200
      height: 800
      min_width: 800
      min_height: 600
      resizable: true
      maximized: false
      fullscreen: false
      decorations: true
      transparent: false
    system_tray:
      enabled: true
      icon: "assets/tray-icon.png"
    platforms:
      - windows
      - macos
      - linux
```

### CLI

```yaml
cli:
  enabled: true
  output: "dist/cli"
  config:
    type: "rich"                  # Python Rich TUI
    name: "myapp"
    executable: true
    entry_command: "myapp"
    colors: true
    mouse: true
    keyboard_shortcuts:
      quit: "q"
      help: "?"
```

---

## Build Modes

### Development

```yaml
build:
  mode: "development"
  source_maps: true
  hot_reload: true
  watch: true
  optimize:
    minify: false
    tree_shake: false
```

### Production

```yaml
build:
  mode: "production"
  source_maps: false
  hot_reload: false
  optimize:
    minify: true
    tree_shake: true
    bundle_splitting: true
```

---

## Validation Rules

1. **At least one target must be enabled**
2. **entry.mxml must exist**
3. **version must be valid SemVer**
4. **Icon files must exist if specified**
5. **bundle_id must be valid reverse domain notation**
6. **Platform-specific fields validated per target**

---

## Usage in CLI

```bash
# Build all enabled targets
quantum-mxml build

# Build specific target
quantum-mxml build --target web
quantum-mxml build --target mobile
quantum-mxml build --target desktop

# Build multiple targets
quantum-mxml build --targets web,mobile

# Override mode
quantum-mxml build --mode production

# Specify config file
quantum-mxml build --config my-app.yaml
```

---

## Example: Simple Web App

```yaml
application:
  name: "Todo App"
  version: "1.0.0"

entry:
  mxml: "src/App.mxml"

targets:
  web:
    enabled: true
    output: "dist"
    config:
      title: "Todo App"
      favicon: "assets/favicon.ico"
```

## Example: Mobile-Only App

```yaml
application:
  name: "Mobile App"
  version: "1.0.0"

entry:
  mxml: "src/Mobile.mxml"

targets:
  mobile:
    enabled: true
    output: "dist/mobile"
    config:
      type: "react-native"
      bundle_id: "com.example.app"
      app_name: "Mobile App"
      icon: "assets/icon.png"
      platforms:
        - android
        - ios
```

## Example: All Platforms

```yaml
application:
  name: "Universal App"
  version: "2.0.0"

entry:
  mxml: "src/Main.mxml"

targets:
  web:
    enabled: true
    output: "dist/web"
    config:
      title: "Universal App"

  mobile:
    enabled: true
    output: "dist/mobile"
    config:
      type: "react-native"
      bundle_id: "com.example.universal"

  desktop:
    enabled: true
    output: "dist/desktop"
    config:
      type: "tauri"
      name: "Universal App"

  cli:
    enabled: true
    output: "dist/cli"
    config:
      type: "rich"
      name: "universal"
```
