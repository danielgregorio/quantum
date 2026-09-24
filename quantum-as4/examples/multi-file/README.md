# Multi-File MXML Application Example

This example demonstrates how to structure a multi-file Quantum AS4 application with:
- **Multiple screens** (Dashboard, Settings)
- **Reusable components** (Header, Footer, StatCard)
- **Services** (UserService for API calls)
- **Namespace imports** (components.*, screens.*)
- **Automatic dependency resolution**

## File Structure

```
multi-file/
├── application.yaml         # Application configuration
└── src/
    ├── Main.mxml            # Entry point
    ├── components/          # Reusable UI components
    │   ├── Header.mxml      # Navigation header
    │   ├── Footer.mxml      # Footer component
    │   └── StatCard.mxml    # Statistics card
    ├── screens/             # Full-page screens
    │   ├── Dashboard.mxml   # Dashboard screen
    │   └── Settings.mxml    # Settings screen
    └── services/            # Business logic
        └── UserService.as4  # User API service
```

## How It Works

### 1. Entry Point (Main.mxml)

The entry point declares namespaces and uses custom components:

```xml
<Application
    xmlns:components="components.*"
    xmlns:screens="screens.*">

    <!-- Use components from components/ directory -->
    <components:Header userName="Admin"/>

    <!-- Use screens from screens/ directory -->
    <screens:Dashboard/>
</Application>
```

### 2. Custom Components

Components are defined in their own MXML files:

```xml
<!-- components/Header.mxml -->
<Component>
    <fx:Metadata>
        [Property(name="userName", type="String")]
    </fx:Metadata>

    <!-- Component UI -->
</Component>
```

### 3. Services

Services are written in ActionScript 4:

```actionscript
// services/UserService.as4
package services {
    public class UserService {
        public static async function getAll():Promise<Vector.<User>> {
            // API calls
        }
    }
}
```

### 4. Using Services in MXML

Import and use services in your MXML components:

```xml
<Screen>
    <fx:Script>
        <![CDATA[
            import services.UserService;

            private async function loadUsers():Promise<void> {
                users = await UserService.getAll();
            }
        ]]>
    </fx:Script>
</Screen>
```

## Compilation Process

When you run `quantum-mxml build`:

1. **Starts with entry point**: `src/Main.mxml`
2. **Discovers namespaces**: `xmlns:components="components.*"`
3. **Finds component usage**: `<components:Header/>`
4. **Resolves path**: `components.Header` → `src/components/Header.mxml`
5. **Parses component**: Loads and parses `Header.mxml`
6. **Discovers dependencies**: Header might use other components
7. **Recursively parses**: All dependencies are loaded
8. **Builds dependency graph**: Determines compilation order
9. **Compiles in order**: Dependencies first, then dependents
10. **Generates output**: Single bundle or code-split based on config

## Dependency Graph

```
Main.mxml
├── components/Header.mxml
├── components/Footer.mxml
├── screens/Dashboard.mxml
│   ├── components/StatCard.mxml
│   └── services/UserService.as4
└── screens/Settings.mxml
```

**Compilation Order:**
1. `StatCard.mxml` (no dependencies)
2. `Header.mxml` (no dependencies)
3. `Footer.mxml` (no dependencies)
4. `UserService.as4` (no dependencies)
5. `Dashboard.mxml` (depends on StatCard, UserService)
6. `Settings.mxml` (no dependencies)
7. `Main.mxml` (depends on all screens and components)

## Building

```bash
# Build the application
cd examples/multi-file
../../quantum-mxml build --config application.yaml

# Output will be in dist/web/
```

## Key Features Demonstrated

### ✅ Namespace Imports
```xml
xmlns:components="components.*"
<components:Header/>
```

### ✅ Custom Component Props
```xml
<fx:Metadata>
    [Property(name="userName", type="String")]
</fx:Metadata>
```

### ✅ Event Handlers
```xml
<components:Header onNavigate="handleNavigation"/>
```

### ✅ Service Imports
```actionscript
import services.UserService;
```

### ✅ Async/Await
```actionscript
private async function loadUsers():Promise<void> {
    users = await UserService.getAll();
}
```

### ✅ Data Binding
```xml
<s:Label text="{userName}"/>
```

### ✅ Conditional Visibility
```xml
<screens:Dashboard visible="{currentScreen == 'dashboard'}"/>
```

## Notes

This example shows the **structure** of a multi-file app. When the compiler is fully implemented, it will:

1. Automatically discover all dependencies
2. Parse them in the correct order
3. Generate optimized output for each platform
4. Support code splitting for lazy loading

The module system enables building large, maintainable applications without manually managing file dependencies!
