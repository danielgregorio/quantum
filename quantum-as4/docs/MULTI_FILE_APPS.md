# Multi-File Application Architecture

## Overview

Real applications consist of multiple MXML files organized as:
- **Entry point** - Main application (Main.mxml)
- **Screens/Views** - Different pages (Dashboard.mxml, Settings.mxml)
- **Custom Components** - Reusable UI (UserCard.mxml, DataTable.mxml)
- **Layouts** - Layout templates (MainLayout.mxml)
- **Services** - Business logic (UserService.as4, API.as4)

---

## File Organization

### Recommended Structure

```
my-app/
├── application.yaml
├── src/
│   ├── Main.mxml              # Entry point
│   ├── components/            # Reusable components
│   │   ├── UserCard.mxml
│   │   ├── DataTable.mxml
│   │   └── Modal.mxml
│   ├── screens/               # Application screens
│   │   ├── Dashboard.mxml
│   │   ├── Settings.mxml
│   │   └── Profile.mxml
│   ├── layouts/               # Layout templates
│   │   ├── MainLayout.mxml
│   │   └── AuthLayout.mxml
│   └── services/              # Business logic (AS4)
│       ├── UserService.as4
│       ├── API.as4
│       └── Auth.as4
└── assets/
    ├── images/
    └── fonts/
```

---

## Importing MXML Components

### Method 1: Namespace Imports (Flex-style) - RECOMMENDED

```xml
<!-- Main.mxml -->
<?xml version="1.0"?>
<Application
    xmlns:fx="http://ns.adobe.com/mxml/2009"
    xmlns:s="library://ns.adobe.com/flex/spark"
    xmlns:components="components.*"
    xmlns:screens="screens.*">

    <fx:Script>
        <![CDATA[
            private var currentScreen:String = "dashboard";
        ]]>
    </fx:Script>

    <s:VBox width="100%" height="100%">
        <!-- Use custom components -->
        <components:UserCard user="{currentUser}"/>

        <!-- Use screens -->
        <screens:Dashboard visible="{currentScreen == 'dashboard'}"/>
        <screens:Settings visible="{currentScreen == 'settings'}"/>
    </s:VBox>

</Application>
```

**How it works:**
1. `xmlns:components="components.*"` tells compiler to look in `src/components/` directory
2. `<components:UserCard/>` resolves to `src/components/UserCard.mxml`
3. Compiler automatically parses and includes UserCard.mxml

### Method 2: Explicit Imports (Alternative)

```xml
<!-- Main.mxml -->
<Application>
    <fx:Script>
        <![CDATA[
            import components.UserCard;
            import screens.Dashboard;
            import services.UserService;
        ]]>
    </fx:Script>

    <s:VBox>
        <UserCard user="{currentUser}"/>
        <Dashboard/>
    </s:VBox>
</Application>
```

---

## Defining Custom Components

### Example: UserCard.mxml

```xml
<?xml version="1.0"?>
<!-- src/components/UserCard.mxml -->
<Component
    xmlns:fx="http://ns.adobe.com/mxml/2009"
    xmlns:s="library://ns.adobe.com/flex/spark">

    <!-- Component props (like React props) -->
    <fx:Metadata>
        [Property(name="user", type="User", required="true")]
        [Event(name="onClick", type="Event")]
    </fx:Metadata>

    <fx:Script>
        <![CDATA[
            // Props (automatically bound)
            [Bindable]
            public var user:User;

            // Event handlers
            private function handleCardClick():void {
                dispatchEvent(new Event("onClick"));
            }
        ]]>
    </fx:Script>

    <fx:Style>
        .user-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
        }
    </fx:Style>

    <s:VBox styleName="user-card" click="handleCardClick()">
        <s:HBox gap="10">
            <s:Image source="{user.avatar}" width="50" height="50"/>
            <s:VBox>
                <s:Label text="{user.name}" fontSize="18" fontWeight="bold"/>
                <s:Label text="{user.email}" color="#666"/>
            </s:VBox>
        </s:HBox>
    </s:VBox>

</Component>
```

### Using the Component

```xml
<!-- Main.mxml -->
<Application xmlns:components="components.*">
    <fx:Script>
        <![CDATA[
            [Bindable]
            private var users:Vector.<User>;

            private function handleUserClick(event:Event):void {
                trace("User clicked!");
            }
        ]]>
    </fx:Script>

    <s:VBox>
        <!-- Repeat for each user -->
        <components:UserCard
            user="{users[0]}"
            onClick="handleUserClick(event)"/>

        <components:UserCard
            user="{users[1]}"
            onClick="handleUserClick(event)"/>
    </s:VBox>
</Application>
```

---

## Screens (Full-Page Views)

### Example: Dashboard.mxml

```xml
<?xml version="1.0"?>
<!-- src/screens/Dashboard.mxml -->
<Screen
    xmlns:fx="http://ns.adobe.com/mxml/2009"
    xmlns:s="library://ns.adobe.com/flex/spark"
    xmlns:components="components.*">

    <fx:Script>
        <![CDATA[
            import services.UserService;

            [Bindable]
            private var users:Vector.<User>;

            private async function loadData():Promise<void> {
                users = await UserService.getAll();
            }

            // Called when screen becomes visible
            public function onActivate():void {
                loadData();
            }
        ]]>
    </fx:Script>

    <s:VBox width="100%" height="100%" padding="20" gap="15">
        <s:Label text="Dashboard" fontSize="24" fontWeight="bold"/>

        <s:HBox gap="20">
            <components:StatCard title="Total Users" value="{users.length}"/>
            <components:StatCard title="Active" value="{getActiveCount()}"/>
        </s:HBox>

        <components:DataTable data="{users}"/>
    </s:VBox>

</Screen>
```

---

## Layouts (Wrapper Components)

### Example: MainLayout.mxml

```xml
<?xml version="1.0"?>
<!-- src/layouts/MainLayout.mxml -->
<Layout
    xmlns:fx="http://ns.adobe.com/mxml/2009"
    xmlns:s="library://ns.adobe.com/flex/spark"
    xmlns:components="components.*">

    <fx:Metadata>
        [Property(name="currentScreen", type="String")]
    </fx:Metadata>

    <s:VBox width="100%" height="100%">
        <!-- Header -->
        <components:Header/>

        <!-- Main content area -->
        <s:HBox flex="1">
            <!-- Sidebar -->
            <components:Sidebar currentScreen="{currentScreen}"/>

            <!-- Content (children go here) -->
            <s:VBox flex="1" padding="20">
                <fx:Children/>  <!-- This is where child content goes -->
            </s:VBox>
        </s:HBox>

        <!-- Footer -->
        <components:Footer/>
    </s:VBox>

</Layout>
```

### Using Layouts

```xml
<!-- Main.mxml -->
<Application xmlns:layouts="layouts.*" xmlns:screens="screens.*">

    <layouts:MainLayout currentScreen="dashboard">
        <!-- Everything here goes into <fx:Children/> slot -->
        <screens:Dashboard/>
    </layouts:MainLayout>

</Application>
```

---

## ActionScript 4 Services

### Example: UserService.as4

```actionscript
// src/services/UserService.as4
package services {
    import quantum.http.fetch;

    public class UserService {

        private static const API_URL:String = "http://localhost:8000/api";

        public static async function getAll():Promise<Vector.<User>> {
            const response = await fetch(`${API_URL}/users`);
            const data = await response.json();
            return Vector.<User>(data);
        }

        public static async function getById(id:int):Promise<User> {
            const response = await fetch(`${API_URL}/users/${id}`);
            return await response.json();
        }

        public static async function create(user:UserCreate):Promise<User> {
            const response = await fetch(`${API_URL}/users`, {
                method: "POST",
                body: JSON.stringify(user)
            });
            return await response.json();
        }
    }
}
```

### Using Services in MXML

```xml
<Application>
    <fx:Script>
        <![CDATA[
            import services.UserService;

            [Bindable]
            private var users:Vector.<User>;

            private async function loadUsers():Promise<void> {
                users = await UserService.getAll();
            }
        ]]>
    </fx:Script>
</Application>
```

---

## Configuration in application.yaml

### Option 1: Auto-Discovery (RECOMMENDED)

```yaml
application:
  name: "My App"
  version: "1.0.0"

entry:
  mxml: "src/Main.mxml"

# Compiler auto-discovers all .mxml and .as4 files in src/
source:
  directories:
    - "src/"

  # Optional: Explicit component paths
  components:
    - "src/components/**/*.mxml"
  screens:
    - "src/screens/**/*.mxml"
  services:
    - "src/services/**/*.as4"
```

**How it works:**
1. Compiler starts with `Main.mxml`
2. Parses namespace declarations: `xmlns:components="components.*"`
3. When it sees `<components:UserCard/>`, looks for `src/components/UserCard.mxml`
4. Recursively parses imported files
5. Builds dependency graph
6. Compiles all files into single output

### Option 2: Explicit File List

```yaml
application:
  name: "My App"
  version: "1.0.0"

entry:
  mxml: "src/Main.mxml"

files:
  # Explicitly list all files (not recommended for large apps)
  components:
    - "src/components/UserCard.mxml"
    - "src/components/DataTable.mxml"
  screens:
    - "src/screens/Dashboard.mxml"
    - "src/screens/Settings.mxml"
  services:
    - "src/services/UserService.as4"
```

---

## Compilation Strategy

### Single Bundle (Default)

All MXML/AS4 files compiled into single output:

**Web:**
```
dist/web/
├── index.html
├── app.js              # All components bundled
├── styles.css          # All styles merged
└── runtime.js
```

### Code Splitting (Lazy Loading)

Split into chunks for better performance:

```yaml
build:
  code_splitting:
    enabled: true
    strategy: "screen"  # Split by screen
```

**Web:**
```
dist/web/
├── index.html
├── main.js             # Entry point + common components
├── dashboard.js        # Dashboard screen (lazy loaded)
├── settings.js         # Settings screen (lazy loaded)
└── runtime.js
```

---

## Compilation Process

### Step 1: Parse Entry Point

```python
# Start with Main.mxml
entry_ast = MXMLParser().parse("src/Main.mxml")
```

### Step 2: Discover Dependencies

```python
# Extract namespace declarations
namespaces = {
    "components": "components.*",
    "screens": "screens.*"
}

# Extract component usage
# <components:UserCard/> → need to load src/components/UserCard.mxml
dependencies = extract_dependencies(entry_ast, namespaces)
```

### Step 3: Recursively Parse

```python
def parse_recursive(file_path, visited=set()):
    if file_path in visited:
        return

    visited.add(file_path)
    ast = MXMLParser().parse(file_path)

    # Find dependencies of this file
    deps = extract_dependencies(ast)

    for dep in deps:
        parse_recursive(dep, visited)

    return ast
```

### Step 4: Build Dependency Graph

```python
graph = DependencyGraph()
graph.add_entry("Main.mxml")
graph.add_dependency("Main.mxml", "components/UserCard.mxml")
graph.add_dependency("Main.mxml", "screens/Dashboard.mxml")
graph.add_dependency("screens/Dashboard.mxml", "components/DataTable.mxml")
```

### Step 5: Compile in Order

```python
# Topological sort - compile dependencies first
compile_order = graph.topological_sort()
# Result: [DataTable, UserCard, Dashboard, Main]

for file in compile_order:
    compile_file(file)
```

---

## Benefits of This Approach

1. **Modular** - Split code into logical files
2. **Reusable** - Components can be shared
3. **Maintainable** - Each file has single responsibility
4. **Type-safe** - Imports are validated at compile time
5. **Scalable** - Works for small and large apps
6. **Familiar** - Same as Flex (easy to learn)

---

## Example: Complete Multi-File App

### File Structure

```
src/
├── Main.mxml
├── components/
│   ├── UserCard.mxml
│   └── DataTable.mxml
├── screens/
│   └── Dashboard.mxml
└── services/
    └── UserService.as4
```

### Main.mxml

```xml
<Application xmlns:screens="screens.*">
    <screens:Dashboard/>
</Application>
```

### screens/Dashboard.mxml

```xml
<Screen xmlns:components="components.*">
    <fx:Script>
        <![CDATA[
            import services.UserService;

            [Bindable]
            private var users:Vector.<User>;

            private async function load():Promise<void> {
                users = await UserService.getAll();
            }
        ]]>
    </fx:Script>

    <s:VBox>
        <components:DataTable data="{users}"/>
    </s:VBox>
</Screen>
```

### components/DataTable.mxml

```xml
<Component>
    <fx:Metadata>
        [Property(name="data", type="Vector.<any>")]
    </fx:Metadata>

    <s:DataGrid dataProvider="{data}"/>
</Component>
```

### services/UserService.as4

```actionscript
package services {
    public class UserService {
        public static async function getAll():Promise<Vector.<User>> {
            // Implementation
        }
    }
}
```

---

## Next Steps

1. ✅ Implement namespace resolution
2. ✅ Implement recursive file parsing
3. ✅ Build dependency graph
4. ✅ Compile files in correct order
5. ✅ Handle circular dependencies
6. ✅ Implement code splitting (optional)
