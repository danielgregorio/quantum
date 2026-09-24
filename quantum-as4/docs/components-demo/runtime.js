/**
 * Quantum Runtime - Renders MXML components to DOM
 *
 * Supports Flex Spark components:
 * - VBox, HBox (layout containers)
 * - Label (text display)
 * - Button (interaction)
 * - TextInput (forms)
 * - DataGrid (tables)
 * - Panel (containers)
 * - Spacer (layout)
 */

export class QuantumRuntime {
    constructor() {
        this.app = null;
        this.container = null;
        this.bindings = new Map(); // Track data bindings
        this.elements = new Map(); // Track DOM elements by binding
    }

    setApp(app) {
        this.app = app;
    }

    /**
     * Render component tree to DOM
     */
    render(componentTree, container) {
        this.container = container;

        // Clear container
        container.innerHTML = '';

        // Render root component
        const element = this.renderComponent(componentTree);
        container.appendChild(element);
    }

    /**
     * Render a single component
     */
    renderComponent(node) {
        const renderer = this.components[node.type];

        if (!renderer) {
            console.warn(`Unknown component: ${node.type}`);
            return this.renderUnknown(node);
        }

        return renderer.call(this, node);
    }

    /**
     * Evaluate data binding expressions
     * Example: "{message}" → app.message
     */
    evaluateBinding(text) {
        if (!text) return '';

        // Replace {variable} with actual value
        return text.replace(/\{([^}]+)\}/g, (match, expr) => {
            try {
                // Simple property access for now
                const value = this.app[expr.trim()];

                // Track this binding
                if (!this.bindings.has(expr.trim())) {
                    this.bindings.set(expr.trim(), []);
                }

                return value !== undefined ? value : '';
            } catch (e) {
                console.error(`Error evaluating binding: ${expr}`, e);
                return match;
            }
        });
    }

    /**
     * Execute event handler
     */
    executeHandler(handlerCode, event) {
        if (!this.app) return;

        try {
            // Extract function name from "handleClick()"
            const funcName = handlerCode.replace(/\(.*\)/, '');

            if (typeof this.app[funcName] === 'function') {
                this.app[funcName](event);
            } else {
                console.error(`Handler not found: ${funcName}`);
            }
        } catch (e) {
            console.error(`Error executing handler: ${handlerCode}`, e);
        }
    }

    /**
     * Notify that a bindable property changed
     */
    notifyChange(propertyName, newValue) {
        console.log(`Property changed: ${propertyName} = ${newValue}`);

        // Re-render all elements bound to this property
        if (this.bindings.has(propertyName)) {
            const elements = this.bindings.get(propertyName);
            elements.forEach(el => {
                if (el.updateBinding) {
                    el.updateBinding(propertyName, newValue);
                }
            });
        }

        // For now, simple approach: re-render everything
        // TODO: Optimize to only update changed elements
        // this.render(this.currentTree, this.container);
    }

    /**
     * Component Renderers
     */
    components = {
        Application: (node) => this.renderApplication(node),
        VBox: (node) => this.renderVBox(node),
        HBox: (node) => this.renderHBox(node),
        Label: (node) => this.renderLabel(node),
        Button: (node) => this.renderButton(node),
        TextInput: (node) => this.renderTextInput(node),
        Panel: (node) => this.renderPanel(node),
        Spacer: (node) => this.renderSpacer(node),
        DataGrid: (node) => this.renderDataGrid(node),
        List: (node) => this.renderList(node),
    };

    renderApplication(node) {
        const div = document.createElement('div');
        div.className = 'quantum-application';

        // Apply props
        this.applyCommonProps(div, node.props);

        // Render children
        node.children.forEach(child => {
            div.appendChild(this.renderComponent(child));
        });

        return div;
    }

    renderVBox(node) {
        const div = document.createElement('div');
        div.className = 'quantum-vbox';
        div.style.display = 'flex';
        div.style.flexDirection = 'column';

        // Apply Flex-specific props
        if (node.props.padding) {
            div.style.padding = node.props.padding + 'px';
        }
        if (node.props.gap) {
            div.style.gap = node.props.gap + 'px';
        }
        if (node.props.width) {
            div.style.width = node.props.width;
        }
        if (node.props.height) {
            div.style.height = node.props.height;
        }

        // Apply common props
        this.applyCommonProps(div, node.props);

        // Render children
        node.children.forEach(child => {
            div.appendChild(this.renderComponent(child));
        });

        return div;
    }

    renderHBox(node) {
        const div = document.createElement('div');
        div.className = 'quantum-hbox';
        div.style.display = 'flex';
        div.style.flexDirection = 'row';

        // Apply Flex-specific props
        if (node.props.padding) {
            div.style.padding = node.props.padding + 'px';
        }
        if (node.props.gap) {
            div.style.gap = node.props.gap + 'px';
        }
        if (node.props.verticalAlign) {
            div.style.alignItems = node.props.verticalAlign === 'middle' ? 'center' : node.props.verticalAlign;
        }
        if (node.props.horizontalAlign) {
            const align = node.props.horizontalAlign;
            if (align === 'space-between') div.style.justifyContent = 'space-between';
            else if (align === 'center') div.style.justifyContent = 'center';
            else if (align === 'right') div.style.justifyContent = 'flex-end';
        }

        this.applyCommonProps(div, node.props);

        // Render children
        node.children.forEach(child => {
            div.appendChild(this.renderComponent(child));
        });

        return div;
    }

    renderLabel(node) {
        const span = document.createElement('span');
        span.className = 'quantum-label';

        // Evaluate data binding
        const text = this.evaluateBinding(node.props.text || '');
        span.textContent = text;

        // Apply props
        if (node.props.fontSize) {
            span.style.fontSize = node.props.fontSize + 'px';
        }
        if (node.props.fontWeight) {
            span.style.fontWeight = node.props.fontWeight;
        }
        if (node.props.color) {
            span.style.color = node.props.color;
        }

        this.applyCommonProps(span, node.props);

        return span;
    }

    renderButton(node) {
        const button = document.createElement('button');
        button.className = 'quantum-button';
        button.textContent = node.props.label || 'Button';

        // Apply props
        if (node.props.enabled === 'false') {
            button.disabled = true;
        }

        this.applyCommonProps(button, node.props);

        // Attach event handlers
        if (node.events.click) {
            button.addEventListener('click', (e) => {
                this.executeHandler(node.events.click, e);
            });
        }

        return button;
    }

    renderTextInput(node) {
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'quantum-textinput';

        // Apply props
        if (node.props.text) {
            input.value = this.evaluateBinding(node.props.text);
        }
        if (node.props.placeholder) {
            input.placeholder = node.props.placeholder;
        }
        if (node.props.maxChars) {
            input.maxLength = parseInt(node.props.maxChars);
        }

        this.applyCommonProps(input, node.props);

        // Attach event handlers
        if (node.events.change) {
            input.addEventListener('change', (e) => {
                this.executeHandler(node.events.change, e);
            });
        }
        if (node.events.input) {
            input.addEventListener('input', (e) => {
                this.executeHandler(node.events.input, e);
            });
        }

        return input;
    }

    renderPanel(node) {
        const div = document.createElement('div');
        div.className = 'quantum-panel';

        // Panel has title
        if (node.props.title) {
            const header = document.createElement('div');
            header.className = 'quantum-panel-header';
            header.textContent = node.props.title;
            div.appendChild(header);
        }

        // Panel body
        const body = document.createElement('div');
        body.className = 'quantum-panel-body';

        // Render children
        node.children.forEach(child => {
            body.appendChild(this.renderComponent(child));
        });

        div.appendChild(body);

        this.applyCommonProps(div, node.props);

        return div;
    }

    renderSpacer(node) {
        const div = document.createElement('div');
        div.className = 'quantum-spacer';
        div.style.flex = '1';

        if (node.props.width) {
            div.style.width = node.props.width;
            div.style.flex = '0';
        }
        if (node.props.height) {
            div.style.height = node.props.height;
            div.style.flex = '0';
        }

        return div;
    }

    renderDataGrid(node) {
        // Simplified DataGrid - just render as table
        const table = document.createElement('table');
        table.className = 'quantum-datagrid';

        // TODO: Implement full DataGrid functionality
        // For now, just placeholder
        const caption = document.createElement('caption');
        caption.textContent = 'DataGrid (TODO)';
        table.appendChild(caption);

        this.applyCommonProps(table, node.props);

        return table;
    }

    renderList(node) {
        const ul = document.createElement('ul');
        ul.className = 'quantum-list';

        // TODO: Implement List functionality

        this.applyCommonProps(ul, node.props);

        return ul;
    }

    renderUnknown(node) {
        const div = document.createElement('div');
        div.className = 'quantum-unknown';
        div.textContent = `[Unknown: ${node.type}]`;
        div.style.border = '1px dashed red';
        div.style.padding = '10px';
        return div;
    }

    /**
     * Apply common props to elements
     */
    applyCommonProps(element, props) {
        if (props.styleName) {
            element.classList.add(props.styleName);
        }
        if (props.id) {
            element.id = props.id;
        }
        if (props.visible === 'false') {
            element.style.display = 'none';
        }
        if (props.width) {
            element.style.width = props.width;
        }
        if (props.height) {
            element.style.height = props.height;
        }
    }
}
