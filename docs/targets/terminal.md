# Terminal Target (Textual)

The Terminal target generates [Textual](https://textual.textualize.io/) TUI (Terminal User Interface) applications. It creates Python applications that run in the terminal with rich, interactive interfaces.

## Overview

When you build with `--target terminal` or `--target textual`, Quantum:

1. Maps UI components to Textual widgets
2. Generates Textual CSS for styling
3. Creates a Python application with compose() method
4. Handles graceful degradation for unsupported features

## Requirements

Install Textual:

```bash
pip install textual
```

## Building for Terminal

```bash
# Build UI application to Textual TUI
python src/cli/runner.py run myapp.q --target textual

# Output is saved as {app_id}_textual.py
# Run the terminal app
python myapp_textual.py
```

## Component Mapping

Quantum UI components map to Textual widgets:

| Quantum Component | Textual Widget |
|-------------------|----------------|
| `ui:window` | `Vertical` (container) |
| `ui:hbox` | `Horizontal` |
| `ui:vbox` | `Vertical` |
| `ui:text` | `Static` |
| `ui:button` | `Button` |
| `ui:input` | `Input` |
| `ui:checkbox` | `Checkbox` |
| `ui:switch` | `Switch` |
| `ui:select` | `Select` |
| `ui:table` | `DataTable` |
| `ui:tabs` | `TabbedContent` + `TabPane` |
| `ui:section` | `Collapsible` |
| `ui:scrollbox` | `ScrollableContainer` |
| `ui:progress` | `ProgressBar` |
| `ui:loading` | `LoadingIndicator` |
| `ui:tree` | `Tree` |
| `ui:log` | `RichLog` |
| `ui:markdown` | `Markdown` |
| `ui:header` | `Header` |
| `ui:footer` | `Footer` |
| `ui:rule` | `Rule` |
| `ui:panel` | `Vertical` with border |
| `ui:grid` | `Grid` |
| `ui:list` | `OptionList` or `Vertical` |
| `ui:menu` | `OptionList` |

## Generated Code Structure

### Imports

```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Grid, ScrollableContainer
from textual.widgets import (
    Static, Button, Input, Checkbox, Switch, Select,
    DataTable, TabbedContent, TabPane, Collapsible,
    ProgressBar, LoadingIndicator, Tree, RichLog,
    Markdown, Header, Footer, Rule, Label, OptionList,
)
```

### App Class

```python
class QuantumApp(App):
    """Quantum UI Textual Application"""

    TITLE = "My App"

    CSS = '''
    /* Base styles */
    .q-panel { border: solid $primary; padding: 1 2; }

    /* Dynamic styles */
    #vbox_1 { padding: 2 4; }
    '''

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id='window_1'):
            with Vertical(id='vbox_1'):
                yield Static("Welcome!", id='text_1')
                yield Button("Click Me", variant='primary', id='btn_1')
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == 'btn_1':
            self.notify("Button clicked!")


if __name__ == "__main__":
    app = QuantumApp()
    app.run()
```

## Textual CSS

### CSS Generation

Textual uses its own CSS dialect. The adapter generates compatible styles:

```xml
<ui:vbox padding="lg" gap="md">
```

Generated CSS:

```css
#vbox_1 { padding: 2 4; }
```

### Token Translation

Design tokens are converted to Textual-compatible values:

| Token | Textual Value | Description |
|-------|---------------|-------------|
| `xs` | 1 | 1 character |
| `sm` | 1 | 1 character |
| `md` | 2 | 2 characters |
| `lg` | 3 | 3 characters |
| `xl` | 4 | 4 characters |

### Color Tokens

Colors use Textual CSS variables:

```css
.q-badge-primary { background: $primary; color: $text; }
.q-badge-success { background: $success; color: $text; }
.q-badge-danger { background: $error; color: $text; }
```

### Text Styling

```xml
<ui:text weight="bold">Bold text</ui:text>
```

```css
#text_1 { text-style: bold; }
```

## Layouts

### Horizontal and Vertical Containers

```xml
<ui:hbox gap="md">
  <ui:button>Left</ui:button>
  <ui:button>Right</ui:button>
</ui:hbox>
```

```python
with Horizontal(id='hbox_1'):
    yield Button("Left", id='btn_1')
    yield Button("Right", id='btn_2')
```

### Grid Layout

```xml
<ui:grid columns="3">
  <ui:text>1</ui:text>
  <ui:text>2</ui:text>
  <ui:text>3</ui:text>
</ui:grid>
```

```python
with Grid(id='grid_1'):
    yield Static("1", id='text_1')
    yield Static("2", id='text_2')
    yield Static("3", id='text_3')
```

### Panels with Titles

```xml
<ui:panel title="Settings">
  <ui:text>Panel content</ui:text>
</ui:panel>
```

```python
with Vertical(id='panel_1', classes='q-panel'):
    yield Static("Settings", classes='q-panel-title')
    yield Static("Panel content", id='text_1')
```

## Interactive Components

### Tabs

```xml
<ui:tabs>
  <ui:tab title="Tab 1">Content 1</ui:tab>
  <ui:tab title="Tab 2">Content 2</ui:tab>
</ui:tabs>
```

```python
with TabbedContent(id='tabs_1'):
    with TabPane("Tab 1"):
        yield Static("Content 1", id='text_1')
    with TabPane("Tab 2"):
        yield Static("Content 2", id='text_2')
```

### Collapsible Sections

```xml
<ui:accordion>
  <ui:section title="Details" expanded="true">
    Section content
  </ui:section>
</ui:accordion>
```

```python
with Collapsible(title="Details", collapsed=False, id='section_1'):
    yield Static("Section content", id='text_1')
```

### Forms

```xml
<ui:form>
  <ui:formitem label="Name">
    <ui:input bind="name" placeholder="Enter name" />
  </ui:formitem>
  <ui:formitem label="Active">
    <ui:switch bind="active" />
  </ui:formitem>
  <ui:button variant="primary">Submit</ui:button>
</ui:form>
```

```python
with Vertical(id='form_1'):
    with Horizontal(id='formitem_1'):
        yield Label("Name")
        yield Input(placeholder="Enter name", id='input_1')
    with Horizontal(id='formitem_2'):
        yield Label("Active")
        yield Switch(id='sw_1')
    yield Button("Submit", variant='primary', id='btn_1')
```

## Data Components

### DataTable

```xml
<ui:table>
  <ui:column key="name" label="Name" />
  <ui:column key="email" label="Email" />
</ui:table>
```

```python
yield DataTable(id='table_1')

# In on_mount or data loading:
# table = self.query_one('#table_1', DataTable)
# table.add_columns('Name', 'Email')
# table.add_rows([('Alice', 'alice@example.com'), ...])
```

### Tree

```xml
<ui:tree source="{fileTree}">
</ui:tree>
```

```python
yield Tree("Tree", id='tree_1')
```

### Log Console

```xml
<ui:log />
```

```python
yield RichLog(id='log_1')

# To write logs:
# log = self.query_one('#log_1', RichLog)
# log.write("Log message")
```

## Graceful Degradation

Some features don't translate well to terminal interfaces. The adapter handles these gracefully:

### Images

Images display as text placeholders:

```xml
<ui:image src="/path/to/image.png" alt="Profile" />
```

```python
yield Static("[Profile]", id='img_1', classes='q-image-placeholder')
```

### Links

Links show URL information:

```xml
<ui:link to="https://example.com">Visit Site</ui:link>
```

```python
yield Static("Visit Site -> https://example.com", id='link_1', classes='q-link')
```

### Charts

Charts are not supported in terminal mode. Consider using:
- ASCII art charts
- Table data display
- Progress bars for simple metrics

## Feature Compatibility

The adapter tracks features that may have limited support:

| Feature | Support | Notes |
|---------|---------|-------|
| Gap | Warning | Textual doesn't support gap directly |
| Font Size | Warning | Terminal has fixed font size |
| Pixel Units | Warning | Use character units instead |
| Images | Degraded | Shows placeholder text |
| External Links | Degraded | Shows URL as text |
| Justify (between/around) | Warning | Limited support |
| Complex Animations | No | Terminal has limited animation |

Get compatibility warnings:

```python
from runtime.ui_textual_adapter import UITextualAdapter

adapter = UITextualAdapter()
# After generating...
warnings = adapter.get_compatibility_warnings()
for warning in warnings:
    print(f"Warning: {warning}")
```

## Event Handling

### Button Events

```python
def on_button_pressed(self, event: Button.Pressed) -> None:
    button_id = event.button.id

    if button_id == 'btn_submit':
        self.handle_submit()
    elif button_id == 'btn_cancel':
        self.handle_cancel()

def handle_submit(self):
    # Get input values
    name_input = self.query_one('#input_name', Input)
    name = name_input.value
    self.notify(f"Submitted: {name}")
```

### Input Changes

```python
def on_input_changed(self, event: Input.Changed) -> None:
    if event.input.id == 'search':
        self.filter_results(event.value)
```

### Switch/Checkbox

```python
def on_switch_changed(self, event: Switch.Changed) -> None:
    if event.switch.id == 'dark_mode':
        self.dark = event.value
```

## Keyboard Bindings

Add keyboard shortcuts:

```python
class QuantumApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("d", "toggle_dark", "Toggle dark mode"),
        ("ctrl+s", "save", "Save"),
    ]

    def action_toggle_dark(self) -> None:
        self.dark = not self.dark

    def action_save(self) -> None:
        self.notify("Saved!")
```

## Example: System Monitor

### Quantum Source

```xml
<q:application id="monitor" type="ui" xmlns:q="https://quantum.lang/ns"
               xmlns:ui="https://quantum.lang/ui">

  <ui:window title="System Monitor">
    <ui:header>System Monitor</ui:header>

    <ui:vbox padding="md" gap="sm">
      <ui:hbox gap="lg">
        <ui:panel title="CPU" width="1/2">
          <ui:progress value="45" max="100" />
          <ui:text>45% Usage</ui:text>
        </ui:panel>

        <ui:panel title="Memory" width="1/2">
          <ui:progress value="72" max="100" />
          <ui:text>72% Usage</ui:text>
        </ui:panel>
      </ui:hbox>

      <ui:panel title="Processes">
        <ui:table>
          <ui:column key="name" label="Process" />
          <ui:column key="cpu" label="CPU %" />
          <ui:column key="mem" label="Memory" />
        </ui:table>
      </ui:panel>

      <ui:panel title="Logs">
        <ui:log />
      </ui:panel>
    </ui:vbox>

    <ui:footer>Press Q to quit</ui:footer>
  </ui:window>

</q:application>
```

### Generated Textual App

```python
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Static, Header, Footer, ProgressBar,
    DataTable, RichLog,
)


class QuantumApp(App):
    """Quantum UI Textual Application"""

    TITLE = "System Monitor"

    CSS = '''
    .q-panel { border: solid $primary; padding: 1 2; }
    .q-panel-title { text-style: bold; color: $text; }
    '''

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical(id='window_1'):
            with Vertical(id='vbox_1'):
                with Horizontal(id='hbox_1'):
                    with Vertical(id='panel_1', classes='q-panel'):
                        yield Static("CPU", classes='q-panel-title')
                        yield ProgressBar(id='prog_1')
                        yield Static("45% Usage", id='text_1')

                    with Vertical(id='panel_2', classes='q-panel'):
                        yield Static("Memory", classes='q-panel-title')
                        yield ProgressBar(id='prog_2')
                        yield Static("72% Usage", id='text_2')

                with Vertical(id='panel_3', classes='q-panel'):
                    yield Static("Processes", classes='q-panel-title')
                    yield DataTable(id='table_1')

                with Vertical(id='panel_4', classes='q-panel'):
                    yield Static("Logs", classes='q-panel-title')
                    yield RichLog(id='log_1')

        yield Footer()

    def on_mount(self) -> None:
        # Set up progress bars
        prog1 = self.query_one('#prog_1', ProgressBar)
        prog1.update(progress=45, total=100)

        prog2 = self.query_one('#prog_2', ProgressBar)
        prog2.update(progress=72, total=100)

        # Set up table
        table = self.query_one('#table_1', DataTable)
        table.add_columns('Process', 'CPU %', 'Memory')
        table.add_rows([
            ('python', '12.3', '256MB'),
            ('chrome', '8.5', '1.2GB'),
            ('vscode', '5.2', '512MB'),
        ])

        # Write initial log
        log = self.query_one('#log_1', RichLog)
        log.write("[green]System monitor started[/green]")


if __name__ == "__main__":
    app = QuantumApp()
    app.run()
```

## Use Cases

Terminal UIs are ideal for:

- **DevOps Tools** - Server monitoring, deployment scripts
- **CLI Applications** - Interactive command-line tools
- **System Utilities** - File managers, process monitors
- **Data Processing** - Log viewers, data validators
- **Developer Tools** - Database browsers, API testers
- **SSH Access** - Remote administration without GUI

## Best Practices

1. **Keep layouts simple** - Terminal space is limited
2. **Use keyboard shortcuts** - Terminal users expect them
3. **Provide feedback** - Use notifications and status indicators
4. **Test in different terminals** - Rendering may vary
5. **Handle resize** - Make layouts responsive to terminal size

## Related

- [HTML Target](/targets/html) - Web output
- [Desktop Target](/targets/desktop) - Native desktop apps
- [Mobile Target](/targets/mobile) - React Native apps
- [Textual Documentation](https://textual.textualize.io/)
