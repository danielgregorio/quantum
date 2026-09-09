# TreeView Icons

This directory contains icons used in the Quantum Component Tree View.

## Icon Types

The extension uses VS Code's built-in ThemeIcon system for tree view icons.
These provide consistent styling across VS Code themes.

### Used Icons (ThemeIcon names):

- `symbol-class` - Components
- `symbol-method` - Functions
- `symbol-variable` - Variables
- `database` - Queries
- `sync` - Loops
- `git-compare` - Conditionals
- `symbol-interface` - UI Elements
- `zap` - Actions
- `file-symlink-file` - Includes
- `symbol-property` - Slots
- `code` - Templates

## Custom Icons

If you need custom icons, place SVG files here with the following naming convention:

- `{type}-light.svg` - Icon for light themes
- `{type}-dark.svg` - Icon for dark themes

Example:
- `component-light.svg`
- `component-dark.svg`

### Icon Requirements

- Format: SVG
- Size: 16x16 pixels
- Colors: Use `#424242` for light theme, `#C5C5C5` for dark theme
- Style: Match VS Code's icon style (simple, monochrome)

## Usage in Code

```typescript
// Using ThemeIcon (recommended)
this.iconPath = new vscode.ThemeIcon('symbol-class');

// Using custom icons
this.iconPath = {
    light: vscode.Uri.joinPath(extensionUri, 'media', 'icons', 'component-light.svg'),
    dark: vscode.Uri.joinPath(extensionUri, 'media', 'icons', 'component-dark.svg')
};
```
