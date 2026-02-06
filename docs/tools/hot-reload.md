# Hot Reload

Hot reload enables instant updates during development without restarting the server or losing application state.

## Overview

The hot reload system works by:

1. **File Watcher** - Monitors `.q` files for changes
2. **Parser** - Re-parses modified files
3. **Diff Engine** - Detects what changed
4. **WebSocket** - Pushes updates to clients
5. **Client Runtime** - Applies changes without full reload

## Getting Started

### Development Server

Start the development server with hot reload:

```bash
# Start with hot reload enabled
python src/cli/runner.py dev myapp.q

# Or with explicit flag
python src/cli/runner.py start --hot-reload

# Development mode (auto-enables hot reload)
python src/cli/runner.py start --debug
```

### Browser Connection

The development server injects a WebSocket client:

```html
<!-- Auto-injected in development mode -->
<script>
  const ws = new WebSocket('ws://localhost:8080/__quantum_hot');
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === 'reload') {
      window.location.reload();
    } else if (data.type === 'update') {
      __quantumApplyUpdate(data.changes);
    }
  };
</script>
```

## How It Works

### File Change Detection

The file watcher monitors:
- `.q` files in the project
- Component files in `components/`
- Configuration files

```
[Watcher] File changed: app.q
[Parser] Re-parsing app.q
[Diff] Detected changes: 2 nodes modified
[WebSocket] Broadcasting update to 3 clients
```

### Change Types

| Change Type | Hot Reload Action |
|-------------|-------------------|
| UI text content | DOM update |
| Style attributes | CSS update |
| State variables | State sync |
| New components | Full reload |
| Route changes | Full reload |
| Function logic | Full reload |

### Incremental Updates

For supported changes, only affected parts update:

```xml
<!-- Before -->
<ui:text>Hello World</ui:text>

<!-- After -->
<ui:text>Hello Quantum!</ui:text>
```

Only the text node updates, not the entire page.

## State Preservation

### Preserving State During Reload

Application state persists across hot reloads:

```xml
<q:set name="counter" value="0" />
<q:set name="formData" value="{}" />
```

When you change UI code:
1. Current state is captured
2. New UI is rendered
3. State is restored

### State Boundaries

Some changes require state reset:

| Change | State Preserved |
|--------|-----------------|
| UI layout | Yes |
| Text content | Yes |
| Styles | Yes |
| State variable names | No |
| Function signatures | No |
| Route structure | No |

### Manual State Preservation

Mark state that should always persist:

```xml
<q:set name="userSession" value="{}" persist="session" hot-reload="preserve" />
```

## Configuration

### quantum.config.yaml

```yaml
development:
  hot_reload:
    enabled: true
    port: 8081           # WebSocket port
    delay: 100           # Debounce delay (ms)
    full_reload: false   # Always full reload?

  watch:
    paths:
      - "."
      - "components/"
    ignore:
      - "node_modules/"
      - ".git/"
      - "*.pyc"
    extensions:
      - ".q"
      - ".yaml"
```

### Environment Variables

```bash
# Enable hot reload
export QUANTUM_HOT_RELOAD=true

# Set WebSocket port
export QUANTUM_HOT_PORT=8081

# Disable for production
export QUANTUM_HOT_RELOAD=false
```

## WebSocket Protocol

### Server Messages

```javascript
// Component updated
{
  "type": "update",
  "file": "app.q",
  "changes": [
    {"path": "ui:text#title", "prop": "content", "value": "New Title"}
  ]
}

// Full reload required
{
  "type": "reload",
  "reason": "route-change"
}

// Error during reload
{
  "type": "error",
  "message": "Parse error on line 15",
  "file": "app.q",
  "line": 15
}

// Connection established
{
  "type": "connected",
  "version": "1.0.0"
}
```

### Client Handling

```javascript
// Apply incremental updates
function __quantumApplyUpdate(changes) {
  for (const change of changes) {
    const el = document.querySelector(change.path);
    if (el) {
      if (change.prop === 'content') {
        el.textContent = change.value;
      } else if (change.prop === 'style') {
        Object.assign(el.style, change.value);
      } else if (change.prop === 'attribute') {
        el.setAttribute(change.name, change.value);
      }
    }
  }
}
```

## Error Handling

### Parse Errors

When a file has errors, the browser shows an overlay:

```
--------------------------------------------
  Quantum Hot Reload Error
--------------------------------------------

  Parse error in app.q:15

  Expected closing tag for <ui:vbox>
  Found: </ui:hbox>

--------------------------------------------
  Fix the error and save to continue
--------------------------------------------
```

### Runtime Errors

Runtime errors during hot reload:

```javascript
// Error overlay
{
  "type": "runtime-error",
  "message": "Cannot read property 'value' of undefined",
  "stack": "...",
  "component": "UserForm"
}
```

### Recovery

After fixing errors:
1. Save the file
2. Hot reload retries automatically
3. Error overlay dismisses
4. Application continues

## Performance

### Debouncing

Multiple rapid saves are debounced:

```
Save 1 -> Wait 100ms
Save 2 -> Reset timer, Wait 100ms
Save 3 -> Reset timer, Wait 100ms
         -> Reload once
```

### Partial Updates

Only changed components re-render:

```
File changed: header.q
Affected components: Header
Unchanged: Main, Sidebar, Footer

-> Only Header re-renders
```

### Caching

Parsed ASTs are cached:

```
Parse app.q -> Cache AST
Parse header.q -> Cache AST
Change header.q -> Re-parse only header.q
                -> Use cached app.q AST
```

## Troubleshooting

### Hot reload not working

1. Check WebSocket connection in browser console
2. Verify file watcher is running
3. Check for config errors
4. Try restarting dev server

```javascript
// Check connection in browser console
console.log('WebSocket state:', ws.readyState);
// 0 = CONNECTING, 1 = OPEN, 2 = CLOSING, 3 = CLOSED
```

### State lost on reload

1. Check if change requires full reload
2. Use `persist` attribute for important state
3. Mark state with `hot-reload="preserve"`

### Changes not detected

1. Check watch paths in config
2. Verify file extension is monitored
3. Check ignore patterns
4. Try saving file again

### Performance issues

1. Reduce watch scope
2. Increase debounce delay
3. Check for large file changes
4. Disable source maps in development

## Best Practices

### Development Workflow

1. **Start in debug mode** - `--debug` auto-enables hot reload
2. **Use specific watch paths** - Don't watch entire filesystem
3. **Keep components small** - Faster re-parsing
4. **Test state preservation** - Verify critical state survives reload

### File Organization

```
project/
  app.q              # Main application
  components/
    Header.q         # Reusable components
    Sidebar.q
    Footer.q
  pages/
    Home.q           # Page components
    About.q
```

Small, focused files enable faster hot reloads.

### Avoiding Full Reloads

Prefer changes that support incremental updates:

```xml
<!-- Good: Text change (incremental) -->
<ui:text>Updated text</ui:text>

<!-- Good: Style change (incremental) -->
<ui:panel padding="lg">

<!-- Triggers full reload: New component -->
<ui:panel>
  <MyNewComponent />  <!-- Full reload -->
</ui:panel>
```

## Related

- [CLI Commands](/tools/cli) - Development commands
- [VS Code Extension](/tools/vscode-extension) - Editor integration
- [Project Structure](/guide/project-structure) - File organization
