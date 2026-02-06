# Phase 3-4 Package.json Contributions

This file documents the contributions to add to `package.json` for Phase 3 and 4 features.

## Commands

Add these to `contributes.commands`:

```json
{
    "command": "quantum.openPreview",
    "title": "Open Preview",
    "category": "Quantum",
    "icon": "$(open-preview)"
},
{
    "command": "quantum.openPreviewToSide",
    "title": "Open Preview to the Side",
    "category": "Quantum",
    "icon": "$(open-preview)"
},
{
    "command": "quantum.refreshPreview",
    "title": "Refresh Preview",
    "category": "Quantum",
    "icon": "$(refresh)"
},
{
    "command": "quantum.togglePreviewView",
    "title": "Toggle HTML/Rendered View",
    "category": "Quantum"
},
{
    "command": "quantum.refreshComponentTree",
    "title": "Refresh Component Tree",
    "category": "Quantum",
    "icon": "$(refresh)"
},
{
    "command": "quantum.goToDefinition",
    "title": "Go to Definition",
    "category": "Quantum"
},
{
    "command": "quantum.run",
    "title": "Run Quantum File",
    "category": "Quantum",
    "icon": "$(play)"
},
{
    "command": "quantum.startServer",
    "title": "Start Development Server",
    "category": "Quantum",
    "icon": "$(server)"
},
{
    "command": "quantum.quickRun",
    "title": "Quick Run",
    "category": "Quantum",
    "icon": "$(run)"
},
{
    "command": "quantum.runTask",
    "title": "Run Task...",
    "category": "Quantum"
},
{
    "command": "quantum.explainError",
    "title": "Explain Error",
    "category": "Quantum",
    "icon": "$(lightbulb)"
},
{
    "command": "quantum.suggestFix",
    "title": "Suggest Fix",
    "category": "Quantum",
    "icon": "$(lightbulb-autofix)"
},
{
    "command": "quantum.suggestFixWithAI",
    "title": "Suggest Fix with AI",
    "category": "Quantum"
},
{
    "command": "quantum.lookupDocumentation",
    "title": "Lookup Documentation",
    "category": "Quantum",
    "icon": "$(book)"
}
```

## Menus

Add these to `contributes.menus`:

```json
"editor/title": [
    {
        "command": "quantum.run",
        "when": "resourceLangId == quantum",
        "group": "navigation"
    },
    {
        "command": "quantum.openPreviewToSide",
        "when": "resourceLangId == quantum",
        "group": "navigation"
    }
],
"editor/context": [
    {
        "command": "quantum.explainError",
        "when": "resourceLangId == quantum && editorHasSelection",
        "group": "quantum@1"
    },
    {
        "command": "quantum.suggestFix",
        "when": "resourceLangId == quantum",
        "group": "quantum@2"
    },
    {
        "command": "quantum.lookupDocumentation",
        "when": "resourceLangId == quantum",
        "group": "quantum@3"
    }
],
"view/title": [
    {
        "command": "quantum.refreshComponentTree",
        "when": "view == quantumComponentTree",
        "group": "navigation"
    }
],
"commandPalette": [
    {
        "command": "quantum.openPreview",
        "when": "resourceLangId == quantum"
    },
    {
        "command": "quantum.run",
        "when": "resourceLangId == quantum"
    },
    {
        "command": "quantum.explainError",
        "when": "resourceLangId == quantum"
    }
]
```

## Views

Add these to `contributes.views`:

```json
"quantum": [
    {
        "id": "quantumComponentTree",
        "name": "Component Structure",
        "contextualTitle": "Quantum Components",
        "icon": "$(symbol-class)",
        "when": "resourceLangId == quantum"
    }
]
```

## View Containers

Add to `contributes.viewsContainers`:

```json
"activitybar": [
    {
        "id": "quantum",
        "title": "Quantum",
        "icon": "$(circuit-board)"
    }
]
```

## Configuration

Add these to `contributes.configuration.properties`:

```json
"quantum.pythonPath": {
    "type": "string",
    "default": "python",
    "description": "Path to Python executable"
},
"quantum.frameworkPath": {
    "type": "string",
    "default": "",
    "description": "Path to Quantum framework installation"
},
"quantum.serverPort": {
    "type": "number",
    "default": 8080,
    "description": "Port for development server"
},
"quantum.buildOutputDir": {
    "type": "string",
    "default": "./dist",
    "description": "Output directory for builds"
},
"quantum.preview.autoRefresh": {
    "type": "boolean",
    "default": true,
    "description": "Auto-refresh preview on save"
},
"quantum.preview.refreshDelay": {
    "type": "number",
    "default": 300,
    "description": "Delay in ms before refreshing preview"
},
"quantum.ai.provider": {
    "type": "string",
    "enum": ["anthropic", "openai", "ollama"],
    "default": "anthropic",
    "description": "AI provider for code assistance"
},
"quantum.ai.apiKey": {
    "type": "string",
    "default": "",
    "description": "API key for Anthropic (Claude)"
},
"quantum.ai.model": {
    "type": "string",
    "default": "claude-sonnet-4-20250514",
    "description": "Model to use for Anthropic"
},
"quantum.ai.openaiApiKey": {
    "type": "string",
    "default": "",
    "description": "API key for OpenAI"
},
"quantum.ai.openaiModel": {
    "type": "string",
    "default": "gpt-4",
    "description": "Model to use for OpenAI"
},
"quantum.ai.ollamaUrl": {
    "type": "string",
    "default": "http://localhost:11434",
    "description": "URL for local Ollama server"
},
"quantum.ai.ollamaModel": {
    "type": "string",
    "default": "llama2",
    "description": "Model to use for Ollama"
}
```

## Task Definitions

Add to `contributes.taskDefinitions`:

```json
[
    {
        "type": "quantum",
        "required": ["command"],
        "properties": {
            "command": {
                "type": "string",
                "enum": ["run", "start", "build", "test", "lint"],
                "description": "Quantum command to run"
            },
            "file": {
                "type": "string",
                "description": "File to process"
            },
            "args": {
                "type": "array",
                "items": { "type": "string" },
                "description": "Additional arguments"
            }
        }
    }
]
```

## Problem Matchers

Add to `contributes.problemMatchers`:

```json
[
    {
        "name": "quantum",
        "owner": "quantum",
        "fileLocation": ["relative", "${workspaceFolder}"],
        "pattern": {
            "regexp": "^(.+):(\\d+):(\\d+):\\s+(error|warning|info):\\s+(.+)$",
            "file": 1,
            "line": 2,
            "column": 3,
            "severity": 4,
            "message": 5
        }
    },
    {
        "name": "quantumParser",
        "owner": "quantum",
        "fileLocation": ["relative", "${workspaceFolder}"],
        "pattern": {
            "regexp": "^Parse error in (.+) at line (\\d+): (.+)$",
            "file": 1,
            "line": 2,
            "message": 3
        }
    }
]
```

## Debuggers

Add to `contributes.debuggers`:

```json
[
    {
        "type": "quantum",
        "label": "Quantum Debug",
        "program": "./out/debugAdapter.js",
        "runtime": "node",
        "languages": ["quantum"],
        "configurationAttributes": {
            "launch": {
                "required": ["program"],
                "properties": {
                    "program": {
                        "type": "string",
                        "description": "Quantum file to run",
                        "default": "${file}"
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory",
                        "default": "${workspaceFolder}"
                    },
                    "args": {
                        "type": "array",
                        "items": { "type": "string" },
                        "description": "Command line arguments"
                    }
                }
            }
        },
        "initialConfigurations": [
            {
                "type": "quantum",
                "request": "launch",
                "name": "Run Quantum File",
                "program": "${file}"
            }
        ],
        "configurationSnippets": [
            {
                "label": "Quantum: Run File",
                "description": "Run the current Quantum file",
                "body": {
                    "type": "quantum",
                    "request": "launch",
                    "name": "Run Quantum File",
                    "program": "^\"\\${file}\""
                }
            }
        ]
    }
]
```

## Keybindings

Add to `contributes.keybindings`:

```json
[
    {
        "command": "quantum.run",
        "key": "ctrl+shift+r",
        "mac": "cmd+shift+r",
        "when": "resourceLangId == quantum"
    },
    {
        "command": "quantum.openPreviewToSide",
        "key": "ctrl+k v",
        "mac": "cmd+k v",
        "when": "resourceLangId == quantum"
    },
    {
        "command": "quantum.lookupDocumentation",
        "key": "ctrl+shift+d",
        "mac": "cmd+shift+d",
        "when": "resourceLangId == quantum"
    }
]
```
