# ActionScript 4 / MXML Examples

This directory contains example applications demonstrating the features and capabilities of the ActionScript 4 / MXML compiler.

## Quick Start

To build and run any example:

```bash
# Build an example
./quantum-mxml build examples/hello.mxml -o dist

# Run the built application
cd dist && python3 -m http.server 8080

# Open in browser
# http://localhost:8080
```

## Examples Overview

### 1. Component Library Demo (`components-demo.mxml`)

**Comprehensive showcase of all UI components with interactive features**

**Features:**
- ✅ CheckBox with two-way binding
- ✅ ComboBox with data providers
- ✅ DatePicker with date selection
- ✅ Tree component (hierarchical data)
- ✅ TabNavigator (tabbed interface)
- ✅ Reactive data binding
- ✅ Event handlers

**What it demonstrates:**
- Two-way data binding with `{variable}` syntax
- Form components with validation
- Dropdown selection with arrays
- Date handling with Date objects
- Event handlers for user interactions

**Build command:**
```bash
./quantum-mxml build examples/components-demo.mxml -o demo-dist
```

**Key code snippets:**
```xml
<!-- CheckBox with binding -->
<s:CheckBox label="I agree" selected="{agreedToTerms}" change="handleCheckboxChange"/>

<!-- ComboBox with data -->
<s:ComboBox dataProvider="{countries}"
            selectedIndex="{selectedCountry}"
            prompt="Choose a country..."/>

<!-- DatePicker -->
<s:DatePicker selectedDate="{selectedDate}" change="handleDateChange"/>
```

---

### 2. Hello World (`hello.mxml`)

**Basic "Hello World" application demonstrating core MXML features**

**Features:**
- ✅ VBox and HBox layouts
- ✅ Label and Button components
- ✅ Data binding with `{message}`
- ✅ Event handlers (click)
- ✅ CSS styling
- ✅ Panel containers

**What it demonstrates:**
- Basic MXML structure
- Declarative UI layout
- ActionScript event handlers
- Reactive data binding
- Click counters

**Build command:**
```bash
./quantum-mxml build examples/hello.mxml -o dist
```

**Key code snippet:**
```xml
<s:VBox padding="40" gap="20" width="600">
  <s:Label text="ActionScript 4 + MXML" styleName="title"/>
  <s:Label text="{message}" styleName="subtitle"/>
  <s:Button label="Click Me!" click="handleClick()"/>
</s:VBox>
```

---

### 3. Multi-File Application (`multi-file/`)

**Complex application demonstrating modular architecture with multiple MXML files**

**Structure:**
```
multi-file/
├── application.yaml          # Build configuration
└── src/
    ├── Main.mxml            # Entry point
    ├── components/          # Reusable components
    │   ├── Header.mxml
    │   ├── Footer.mxml
    │   └── StatCard.mxml
    ├── screens/             # Screen/view components
    │   ├── Dashboard.mxml
    │   └── Settings.mxml
    └── services/            # Business logic
        └── UserService.as4
```

**Features:**
- ✅ Namespace imports (`xmlns:components="components.*"`)
- ✅ Component composition
- ✅ Automatic dependency resolution
- ✅ Clean separation of concerns

**What it demonstrates:**
- Multi-file project organization
- Custom component creation
- Namespace-based imports
- Component reusability

**Build command:**
```bash
./quantum-mxml build multi-file/src/Main.mxml -o multi-file/dist
```

**Key code snippet:**
```xml
<s:Application
    xmlns:components="components.*"
    xmlns:screens="screens.*">

    <components:Header userName="Admin"/>
    <screens:Dashboard/>
    <components:Footer/>
</s:Application>
```

---

## Adobe Flex Test Examples (`../test-adobe-examples/`)

Real-world Adobe Flex MXML files used for compatibility testing. All examples compile successfully with 100% success rate.

### Test Examples:

#### 1. **SimpleVBox.mxml**
Basic VBox layout with Label, Button, and TextInput components.

```bash
./quantum-mxml build test-adobe-examples/SimpleVBox.mxml -o test-results/simple
```

#### 2. **DataBindingExample.mxml**
Demonstrates `[Bindable]` variables, data binding expressions, and reactive updates.

**Features:**
- Bindable variables
- Curly brace binding `{username}`, `{count}`
- Click event handlers
- Counter increment

```bash
./quantum-mxml build test-adobe-examples/DataBindingExample.mxml -o test-results/databinding
```

#### 3. **NestedContainers.mxml**
Login form with nested VBox and HBox layouts, demonstrating complex UI composition.

**Features:**
- Panel component
- Form layout with labels and inputs
- Button groups with HBox
- Password input field

```bash
./quantum-mxml build test-adobe-examples/NestedContainers.mxml -o test-results/nested
```

#### 4. **FlexClient.mxml**
Real production code from [fernandoacorreia/flex-and-python-test](https://github.com/fernandoacorreia/flex-and-python-test) GitHub repository.

**Features:**
- Import statements
- Custom namespace
- Image component
- Production-ready structure

```bash
./quantum-mxml build test-adobe-examples/FlexClient.mxml -o test-results/flexclient
```

#### 5. **StopWatch.mxml**
Complex example from [PureMVC/puremvc-as3-demo-flex-stopwatch](https://github.com/PureMVC/puremvc-as3-demo-flex-stopwatch).

**Features:**
- ApplicationControlBar
- Multiple event handlers
- State management with constants
- Bindable properties
- Complex UI with multiple containers
- 121 lines of production code

```bash
./quantum-mxml build test-adobe-examples/StopWatch.mxml -o test-results/stopwatch
```

**Test Report:**
See `ADOBE_EXAMPLES_TEST_REPORT.md` for detailed compatibility testing results.

---

## Component Reference

### Layout Components

#### VBox
Vertical layout container that arranges children in a column.

```xml
<s:VBox padding="20" gap="10" width="100%">
  <!-- children arranged vertically -->
</s:VBox>
```

**Props:**
- `padding` - Inner padding (px)
- `gap` - Space between children (px)
- `width`, `height` - Dimensions

---

#### HBox
Horizontal layout container that arranges children in a row.

```xml
<s:HBox gap="15" horizontalAlign="center">
  <!-- children arranged horizontally -->
</s:HBox>
```

**Props:**
- `gap` - Space between children (px)
- `horizontalAlign` - Alignment (left, center, right)

---

#### Panel
Container with title and border.

```xml
<s:Panel title="User Profile" width="400">
  <s:VBox padding="20">
    <!-- panel content -->
  </s:VBox>
</s:Panel>
```

**Props:**
- `title` - Panel header text
- `width`, `height` - Dimensions

---

### Form Components

#### Label
Text display component.

```xml
<s:Label text="Username:" fontSize="16" fontWeight="bold"/>
<s:Label text="{dynamicValue}"/>
```

**Props:**
- `text` - Text content (supports binding)
- `fontSize` - Font size (px)
- `fontWeight` - bold/normal
- `color` - Text color

---

#### Button
Clickable button with event handler.

```xml
<s:Button label="Submit" click="handleSubmit()"/>
```

**Props:**
- `label` - Button text
- `enabled` - Enable/disable (default: true)

**Events:**
- `click` - Fired when clicked

---

#### TextInput
Single-line text input field.

```xml
<s:TextInput id="username" text="{userInput}"/>
```

**Props:**
- `text` - Input value (supports two-way binding)
- `displayAsPassword` - Hide characters (default: false)
- `enabled` - Enable/disable

---

#### CheckBox
Checkbox with label.

```xml
<s:CheckBox label="Remember me"
            selected="{rememberMe}"
            change="handleCheckboxChange"/>
```

**Props:**
- `label` - Label text
- `selected` - Checked state (supports two-way binding)
- `enabled` - Enable/disable
- `labelPlacement` - "left" or "right" (default: right)

**Events:**
- `change` - Fired when state changes

---

#### ComboBox
Dropdown selection component.

```xml
<s:ComboBox dataProvider="{items}"
            selectedIndex="{selectedIdx}"
            prompt="Choose one..."
            labelField="name"
            change="handleSelection"/>
```

**Props:**
- `dataProvider` - Array of items (supports binding)
- `selectedIndex` - Selected item index (supports two-way binding)
- `labelField` - Field to display (for object arrays)
- `prompt` - Placeholder text
- `enabled` - Enable/disable

**Events:**
- `change` - Fired when selection changes (passes item, index)

---

#### DatePicker
Date selection component.

```xml
<s:DatePicker selectedDate="{birthDate}"
              change="handleDateChange"/>
```

**Props:**
- `selectedDate` - Selected date (supports two-way binding with Date object)
- `formatString` - Display format (default: "MM/DD/YYYY")
- `enabled` - Enable/disable

**Events:**
- `change` - Fired when date changes (passes Date object)

---

### Advanced Components

#### DataGrid
Sortable, filterable data table (stub - full implementation in `compiler/runtime/components/DataGrid.js`).

**Features:**
- Column sorting
- Client-side filtering
- Pagination
- Row selection

---

#### List
Scrollable list with virtualization (stub - full implementation in `compiler/runtime/components/List.js`).

**Features:**
- Large dataset support
- Item renderers
- Selection

---

#### Tree
Hierarchical data display (stub - full implementation in `compiler/runtime/components/Tree.js`).

**Features:**
- Expand/collapse nodes
- Nested data
- Item click events

---

#### TabNavigator
Tabbed interface (stub - full implementation in `compiler/runtime/components/TabNavigator.js`).

**Features:**
- Multiple tabs
- Content switching
- Selected tab binding

---

#### Modal
Dialog/popup overlay (stub - full implementation in `compiler/runtime/components/Modal.js`).

**Features:**
- Overlay backdrop
- Close button
- ESC key support
- Visibility binding

---

## Data Binding

### One-Way Binding
Display dynamic data in UI:

```xml
<s:Label text="{username}"/>
<s:Label text="Count: {clickCount}"/>
<s:Label text="Welcome, {user.firstName}!"/>
```

### Two-Way Binding
Synchronize UI and data automatically:

```xml
<!-- TextInput -->
<s:TextInput text="{userInput}"/>

<!-- CheckBox -->
<s:CheckBox selected="{agreed}"/>

<!-- ComboBox -->
<s:ComboBox selectedIndex="{selectedIdx}"/>

<!-- DatePicker -->
<s:DatePicker selectedDate="{selectedDate}"/>
```

### ActionScript Variables

Use `[Bindable]` metadata to make variables reactive:

```actionscript
[Bindable]
private var username:String = "John";

[Bindable]
private var count:int = 0;

private function increment():void {
  count++;  // UI updates automatically!
}
```

---

## Event Handlers

### Click Events

```xml
<s:Button label="Submit" click="handleSubmit()"/>
<s:Button label="Cancel" click="handleCancel()"/>
```

### Change Events

```xml
<s:CheckBox change="handleCheckboxChange"/>
<s:ComboBox change="handleSelection"/>
<s:DatePicker change="handleDateChange"/>
```

### ActionScript Handlers

```actionscript
private function handleSubmit():void {
  trace("Form submitted");
  // Handle submission
}

private function handleCheckboxChange(checked:Boolean):void {
  trace("Checkbox: " + checked);
}

private function handleSelection(item:Object, index:int):void {
  trace("Selected: " + item + " at " + index);
}
```

---

## Styling

### Inline Styles

```xml
<s:Label text="Title"
         fontSize="24"
         fontWeight="bold"
         color="#333"/>
```

### CSS Styles

```xml
<fx:Style>
  .title {
    font-size: 24px;
    font-weight: bold;
    color: #1976d2;
  }

  .button {
    padding: 10px 20px;
    background-color: #1976d2;
    color: white;
  }
</fx:Style>

<s:Label text="My Title" styleName="title"/>
<s:Button label="Click" styleName="button"/>
```

---

## Build Configuration

### application.yaml

```yaml
name: MyApplication
version: 1.0.0
description: My MXML Application

# Build targets
targets:
  - platform: web
    output: dist/web

# Entry point
entry: src/Main.mxml

# Development settings
dev:
  hotReload: true
  sourceMaps: true
```

---

## Tips & Best Practices

### 1. **Component Organization**
```
src/
├── Main.mxml              # Entry point
├── components/            # Reusable UI components
│   ├── Button.mxml
│   └── Card.mxml
├── screens/               # Screen/page components
│   ├── Home.mxml
│   └── Settings.mxml
└── services/              # Business logic (AS4 files)
    └── ApiService.as4
```

### 2. **Use Namespaces for Imports**
```xml
<s:Application
    xmlns:components="components.*"
    xmlns:screens="screens.*">

    <components:Header/>
    <screens:Home/>
</s:Application>
```

### 3. **Leverage Two-Way Binding**
```xml
<!-- Instead of manual updates -->
<s:TextInput id="input" change="handleChange()"/>

<!-- Use two-way binding -->
<s:TextInput text="{userInput}"/>
```

### 4. **Keep ActionScript Separate**
```xml
<fx:Script>
<![CDATA[
  // Business logic here
  private function processData():void {
    // ...
  }
]]>
</fx:Script>
```

### 5. **Use [Bindable] for Reactive Data**
```actionscript
[Bindable]
private var items:Array = [];

// When items change, UI updates automatically
items.push(newItem);
```

---

## Troubleshooting

### Build Errors

**Error: "Cannot find module"**
- Check your namespace imports
- Verify file paths are correct
- Ensure files exist in the specified location

**Error: "Syntax error in MXML"**
- Validate XML structure (closing tags, quotes)
- Check namespace declarations
- Verify component names are correct

### Runtime Errors

**Component not rendering**
- Check browser console for errors
- Verify reactive-runtime.js is loaded
- Ensure component is registered in ReactiveRuntime

**Data binding not working**
- Use `[Bindable]` metadata on variables
- Use curly braces `{variable}` in MXML
- Check that variable names match exactly

---

## Resources

- **Compiler Documentation**: `../README.md`
- **Adobe Flex Test Report**: `../ADOBE_EXAMPLES_TEST_REPORT.md`
- **Component Implementations**: `../compiler/runtime/components/`
- **Reactive Runtime**: `../compiler/runtime/reactive-runtime.js`

---

## Contributing

To add a new example:

1. Create a new `.mxml` file in `examples/`
2. Add description to this README
3. Test compilation: `./quantum-mxml build examples/your-example.mxml -o test-dist`
4. Commit and push

---

## License

MIT License - See main project LICENSE file.
