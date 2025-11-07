/**
 * Reactive Runtime - Enhanced version with true reactivity
 *
 * Features:
 * - Automatic DOM updates when data changes (using Proxy)
 * - Two-way binding for form inputs
 * - Dependency tracking
 * - Efficient re-rendering (only update changed elements)
 */

// Import advanced components
import { DragManager } from './DragManager.js';
import { renderList } from './components/List.js';
import { renderDataGridAdvanced } from './components/DataGridAdvanced.js';
import { renderTileList } from './components/TileList.js';
import { renderAccordion, renderAccordionHeader } from './components/Accordion.js';
import { renderMenu, renderMenuBar } from './components/Menu.js';

// Import FASE 1 MVP components
import { renderHTTPService } from './components/HTTPService.js';
import { renderForm, renderFormItem, renderFormHeading } from './components/Form.js';
import { renderProgressBar } from './components/ProgressBar.js';
import { renderImage } from './components/Image.js';
import { renderAlert, Alert } from './components/Alert.js';

// Import FASE 2 components
import { renderNumericStepper } from './components/NumericStepper.js';
import { renderHSlider, renderVSlider } from './components/Slider.js';
import { renderTextArea } from './components/TextArea.js';
import { renderState, initializeStates, parseStates } from './components/States.js';
import { renderStringValidator, renderNumberValidator, renderEmailValidator } from './components/Validators.js';

// Import FASE 3 components
import { renderFade, renderMove, renderResize, renderGlow } from './components/Effects.js';
import { renderDateFormatter, renderNumberFormatter, renderCurrencyFormatter, renderPhoneFormatter, renderZipCodeFormatter } from './components/Formatters.js';

// Import Quantum Integration components
import { renderQuantumService, renderQuantumComponent, renderQuantumBridge } from './components/QuantumIntegration.js';

export class ReactiveRuntime {
    constructor() {
        this.app = null;
        this.container = null;
        this.components = {}; // Component type → render function

        // Reactive system
        this.dependencies = new Map(); // property → Set of update functions
        this.bindings = new Map(); // element → binding info
        this.currentlyRendering = null;

        // Component registry
        this.registerDefaultComponents();
    }

    setApp(app) {
        this.app = this.makeReactive(app);
    }

    /**
     * Make an object reactive using Proxy
     * When properties change, automatically update DOM
     */
    makeReactive(obj) {
        const self = this;

        return new Proxy(obj, {
            get(target, property) {
                const value = target[property];

                // Track dependency if we're currently rendering
                if (self.currentlyRendering && typeof value !== 'function') {
                    self.trackDependency(property, self.currentlyRendering);
                }

                return value;
            },

            set(target, property, value) {
                const oldValue = target[property];

                // Only update if value actually changed
                if (oldValue === value) {
                    return true;
                }

                target[property] = value;

                console.log(`[Reactive] Property changed: ${property} = ${value}`);

                // Trigger updates for all elements that depend on this property
                self.notifyDependents(property, value);

                return true;
            }
        });
    }

    /**
     * Track that current element depends on a property
     */
    trackDependency(property, updateFn) {
        if (!this.dependencies.has(property)) {
            this.dependencies.set(property, new Set());
        }
        this.dependencies.get(property).add(updateFn);
    }

    /**
     * Alias for trackDependency - used by some components
     */
    addBinding(property, updateFn) {
        return this.trackDependency(property, updateFn);
    }

    /**
     * Notify all elements that depend on a property
     */
    notifyDependents(property, newValue) {
        if (this.dependencies.has(property)) {
            const updateFns = this.dependencies.get(property);

            console.log(`[Reactive] Updating ${updateFns.size} dependent(s) for: ${property}`);

            for (const updateFn of updateFns) {
                try {
                    updateFn(newValue);
                } catch (error) {
                    console.error('Error updating dependent:', error);
                }
            }
        }
    }

    /**
     * Alias for notifyDependents - used by generated code from codegen.py
     */
    notifyChange(property, newValue) {
        return this.notifyDependents(property, newValue);
    }

    /**
     * Evaluate binding expression and track dependency
     */
    evaluateBinding(expression, trackingElement = null) {
        if (!expression) return '';

        // Track current rendering context
        const previousContext = this.currentlyRendering;
        this.currentlyRendering = trackingElement;

        try {
            // Extract variable name from {variable} or {object.property}
            const varMatch = expression.match(/\{([^}]+)\}/);
            if (varMatch) {
                const varName = varMatch[1].trim();

                // Simple property access
                if (!varName.includes('.')) {
                    const value = this.app[varName];
                    return value !== undefined ? value : '';
                }

                // Nested property access (e.g., user.name)
                const parts = varName.split('.');
                let value = this.app;
                for (const part of parts) {
                    value = value?.[part];
                }
                return value !== undefined ? value : '';
            }

            return expression;
        } finally {
            this.currentlyRendering = previousContext;
        }
    }

    /**
     * Create a reactive binding for an element
     */
    createReactiveBinding(element, expression, property = 'textContent') {
        // Extract variable name
        const varMatch = expression.match(/\{([^}]+)\}/);
        if (!varMatch) return;

        const varName = varMatch[1].trim().split('.')[0]; // Get root variable name

        // Create update function
        const updateFn = (newValue) => {
            const value = this.evaluateBinding(expression);

            if (property === 'textContent') {
                element.textContent = value;
            } else {
                element[property] = value;
            }
        };

        // Track dependency
        this.trackDependency(varName, updateFn);

        // Initial update
        updateFn();
    }

    /**
     * Setup two-way binding for input elements
     */
    setupTwoWayBinding(inputElement, varName) {
        // Update app property when input changes
        inputElement.addEventListener('input', (e) => {
            const value = e.target.value;

            // Handle nested properties
            if (varName.includes('.')) {
                const parts = varName.split('.');
                let obj = this.app;
                for (let i = 0; i < parts.length - 1; i++) {
                    obj = obj[parts[i]];
                }
                obj[parts[parts.length - 1]] = value;
            } else {
                this.app[varName] = value;
            }
        });

        // Update input when app property changes
        const updateFn = (newValue) => {
            if (inputElement.value !== newValue) {
                inputElement.value = newValue;
            }
        };

        this.trackDependency(varName, updateFn);
    }

    /**
     * Render component tree to DOM
     */
    render(componentTree, container) {
        this.container = container;
        container.innerHTML = '';

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
     * Register default components
     */
    registerDefaultComponents() {
        this.components = {
            Application: (node) => this.renderApplication(node),
            VBox: (node) => this.renderVBox(node),
            HBox: (node) => this.renderHBox(node),
            Label: (node) => this.renderLabel(node),
            Button: (node) => this.renderButton(node),
            TextInput: (node) => this.renderTextInput(node),
            Panel: (node) => this.renderPanel(node),
            Spacer: (node) => this.renderSpacer(node),
            DataGrid: (node) => this.renderDataGrid(node),
            List: (node) => renderList(this, node), // Enhanced version with drag support
            Modal: (node) => this.renderModal(node),
            CheckBox: (node) => this.renderCheckBox(node),
            ComboBox: (node) => this.renderComboBox(node),
            DatePicker: (node) => this.renderDatePicker(node),
            Tree: (node) => this.renderTree(node),
            TabNavigator: (node) => this.renderTabNavigator(node),
            // Advanced components
            AdvancedDataGrid: (node) => renderDataGridAdvanced(this, node),
            TileList: (node) => renderTileList(this, node),
            Accordion: (node) => renderAccordion(this, node),
            AccordionHeader: (node) => renderAccordionHeader(this, node),
            Menu: (node) => renderMenu(this, node),
            MenuBar: (node) => renderMenuBar(this, node),
            // FASE 1 MVP Components
            HTTPService: (node) => renderHTTPService(this, node),
            Form: (node) => renderForm(this, node),
            FormItem: (node) => renderFormItem(this, node),
            FormHeading: (node) => renderFormHeading(this, node),
            ProgressBar: (node) => renderProgressBar(this, node),
            Image: (node) => renderImage(this, node),
            Alert: (node) => renderAlert(this, node),
            // FASE 2 Components
            NumericStepper: (node) => renderNumericStepper(this, node),
            HSlider: (node) => renderHSlider(this, node),
            VSlider: (node) => renderVSlider(this, node),
            Slider: (node) => renderHSlider(this, node), // Default to horizontal
            TextArea: (node) => renderTextArea(this, node),
            State: (node) => renderState(this, node),
            states: (node) => this.renderStates(node), // Container for multiple State elements
            StringValidator: (node) => renderStringValidator(this, node),
            NumberValidator: (node) => renderNumberValidator(this, node),
            EmailValidator: (node) => renderEmailValidator(this, node),
            // FASE 3 Components
            Fade: (node) => renderFade(this, node),
            Move: (node) => renderMove(this, node),
            Resize: (node) => renderResize(this, node),
            Glow: (node) => renderGlow(this, node),
            DateFormatter: (node) => renderDateFormatter(this, node),
            NumberFormatter: (node) => renderNumberFormatter(this, node),
            CurrencyFormatter: (node) => renderCurrencyFormatter(this, node),
            PhoneFormatter: (node) => renderPhoneFormatter(this, node),
            ZipCodeFormatter: (node) => renderZipCodeFormatter(this, node),
            // Quantum Integration Components
            QuantumService: (node) => renderQuantumService(this, node),
            QuantumComponent: (node) => renderQuantumComponent(this, node),
            QuantumBridge: (node) => renderQuantumBridge(this, node),
        };

        // Make Alert class globally available
        if (typeof window !== 'undefined') {
            window.Alert = Alert;
        }
    }

    // Component Renderers

    renderApplication(node) {
        const div = document.createElement('div');
        div.className = 'quantum-application';
        this.applyCommonProps(div, node.props);

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

        if (node.props.padding) div.style.padding = node.props.padding + 'px';
        if (node.props.gap) div.style.gap = node.props.gap + 'px';
        if (node.props.width) div.style.width = node.props.width;
        if (node.props.height) div.style.height = node.props.height;

        this.applyCommonProps(div, node.props);

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

        if (node.props.padding) div.style.padding = node.props.padding + 'px';
        if (node.props.gap) div.style.gap = node.props.gap + 'px';
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

        node.children.forEach(child => {
            div.appendChild(this.renderComponent(child));
        });

        return div;
    }

    renderLabel(node) {
        const span = document.createElement('span');
        span.className = 'quantum-label';

        // Setup reactive binding for text
        if (node.props.text) {
            this.createReactiveBinding(span, node.props.text, 'textContent');
        }

        if (node.props.fontSize) span.style.fontSize = node.props.fontSize + 'px';
        if (node.props.fontWeight) span.style.fontWeight = node.props.fontWeight;
        if (node.props.color) span.style.color = node.props.color;

        this.applyCommonProps(span, node.props);

        return span;
    }

    renderButton(node) {
        const button = document.createElement('button');
        button.className = 'quantum-button';
        button.textContent = node.props.label || 'Button';

        if (node.props.enabled === 'false') {
            button.disabled = true;
        }

        this.applyCommonProps(button, node.props);

        // Event handlers
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

        // Initial value with reactive binding
        if (node.props.text) {
            const varMatch = node.props.text.match(/\{([^}]+)\}/);
            if (varMatch) {
                const varName = varMatch[1].trim();

                // Set initial value
                input.value = this.evaluateBinding(node.props.text);

                // Setup two-way binding
                this.setupTwoWayBinding(input, varName);
            } else {
                input.value = node.props.text;
            }
        }

        if (node.props.placeholder) {
            input.placeholder = node.props.placeholder;
        }
        if (node.props.maxChars) {
            input.maxLength = parseInt(node.props.maxChars);
        }

        this.applyCommonProps(input, node.props);

        // Event handlers
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

        if (node.props.title) {
            const header = document.createElement('div');
            header.className = 'quantum-panel-header';
            header.textContent = node.props.title;
            div.appendChild(header);
        }

        const body = document.createElement('div');
        body.className = 'quantum-panel-body';

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
        // Import from components/DataGrid.js
        // For now, use inline stub - full implementation in separate file
        const container = document.createElement('div');
        container.className = 'quantum-datagrid-container';

        const message = document.createElement('div');
        message.style.padding = '20px';
        message.style.border = '2px dashed #ccc';
        message.style.borderRadius = '4px';
        message.style.textAlign = 'center';
        message.style.color = '#666';
        message.innerHTML = `
            <strong>DataGrid Component</strong><br>
            Full implementation available in components/DataGrid.js<br>
            Features: sorting, filtering, pagination, row selection
        `;
        container.appendChild(message);

        this.applyCommonProps(container, node.props);
        return container;
    }

    renderList(node) {
        // Import from components/List.js
        // For now, use inline stub - full implementation in separate file
        const container = document.createElement('div');
        container.className = 'quantum-list-container';

        const message = document.createElement('div');
        message.style.padding = '20px';
        message.style.border = '2px dashed #ccc';
        message.style.borderRadius = '4px';
        message.style.textAlign = 'center';
        message.style.color = '#666';
        message.innerHTML = `
            <strong>List Component</strong><br>
            Full implementation available in components/List.js<br>
            Features: virtualization, item renderers, selection
        `;
        container.appendChild(message);

        this.applyCommonProps(container, node.props);
        return container;
    }

    renderModal(node) {
        // Import from components/Modal.js
        // For now, use inline stub - full implementation in separate file
        const overlay = document.createElement('div');
        overlay.className = 'quantum-modal-overlay';
        overlay.style.position = 'fixed';
        overlay.style.top = '50%';
        overlay.style.left = '50%';
        overlay.style.transform = 'translate(-50%, -50%)';
        overlay.style.padding = '20px';
        overlay.style.backgroundColor = 'white';
        overlay.style.border = '2px dashed #ccc';
        overlay.style.borderRadius = '8px';
        overlay.style.zIndex = '1000';
        overlay.style.textAlign = 'center';
        overlay.style.color = '#666';

        overlay.innerHTML = `
            <strong>Modal Component</strong><br>
            Full implementation available in components/Modal.js<br>
            Features: overlay, close button, ESC key, animations
        `;

        // Render children
        node.children.forEach(child => {
            overlay.appendChild(this.renderComponent(child));
        });

        this.applyCommonProps(overlay, node.props);
        return overlay;
    }

    renderCheckBox(node) {
        const container = document.createElement('label');
        container.className = 'quantum-checkbox';
        container.style.display = 'inline-flex';
        container.style.alignItems = 'center';
        container.style.cursor = 'pointer';
        container.style.userSelect = 'none';
        container.style.gap = '8px';

        const input = document.createElement('input');
        input.type = 'checkbox';
        input.style.cursor = 'pointer';
        input.style.width = '18px';
        input.style.height = '18px';

        const labelText = document.createElement('span');
        labelText.style.fontSize = '14px';

        // Set label
        if (node.props.label) {
            this.createReactiveBinding(labelText, node.props.label, 'textContent');
        }

        // Set initial selected state
        if (node.props.selected) {
            const initialValue = this.evaluateBinding(node.props.selected);
            input.checked = initialValue === true || initialValue === 'true';
        }

        // Handle enabled/disabled
        const enabled = node.props.enabled !== 'false';
        input.disabled = !enabled;
        if (!enabled) {
            container.style.cursor = 'not-allowed';
            container.style.opacity = '0.5';
        }

        // Label placement
        const labelPlacement = node.props.labelPlacement || 'right';
        if (labelPlacement === 'left') {
            container.appendChild(labelText);
            container.appendChild(input);
        } else {
            container.appendChild(input);
            container.appendChild(labelText);
        }

        // Two-way binding
        if (node.props.selected && node.props.selected.includes('{')) {
            const varMatch = node.props.selected.match(/\{([^}]+)\}/);
            if (varMatch) {
                const varName = varMatch[1].trim();

                // Update app property when checkbox changes
                input.addEventListener('change', (e) => {
                    this.app[varName] = e.target.checked;
                });

                // Update checkbox when app property changes
                this.trackDependency(varName, (newValue) => {
                    input.checked = newValue === true || newValue === 'true';
                });
            }
        }

        // Fire change event
        if (node.events.change) {
            input.addEventListener('change', (e) => {
                const handlerName = node.events.change.replace('()', '');
                if (this.app[handlerName]) {
                    this.app[handlerName](e.target.checked);
                }
            });
        }

        this.applyCommonProps(container, node.props);
        return container;
    }

    renderComboBox(node) {
        const select = document.createElement('select');
        select.className = 'quantum-combobox';
        select.style.padding = '8px 12px';
        select.style.fontSize = '14px';
        select.style.border = '1px solid #ccc';
        select.style.borderRadius = '4px';
        select.style.backgroundColor = 'white';
        select.style.cursor = 'pointer';

        // Get data provider
        let data = [];
        if (node.props.dataProvider) {
            data = this.evaluateBinding(node.props.dataProvider);
            if (!Array.isArray(data)) data = [];
        }

        const labelField = node.props.labelField || 'label';

        // Add prompt option
        if (node.props.prompt) {
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = node.props.prompt;
            opt.disabled = true;
            opt.selected = true;
            select.appendChild(opt);
        }

        // Add data options
        data.forEach((item, index) => {
            const opt = document.createElement('option');
            opt.value = index;
            opt.textContent = typeof item === 'object' ? item[labelField] : item;
            select.appendChild(opt);
        });

        // Two-way binding for selectedIndex
        if (node.props.selectedIndex && node.props.selectedIndex.includes('{')) {
            const varMatch = node.props.selectedIndex.match(/\{([^}]+)\}/);
            if (varMatch) {
                const varName = varMatch[1].trim();
                select.addEventListener('change', (e) => {
                    this.app[varName] = node.props.prompt ? e.target.selectedIndex - 1 : e.target.selectedIndex;
                });
                this.trackDependency(varName, (newValue) => {
                    select.selectedIndex = node.props.prompt ? newValue + 1 : newValue;
                });
            }
        }

        // Change event
        if (node.events.change) {
            select.addEventListener('change', (e) => {
                const idx = node.props.prompt ? e.target.selectedIndex - 1 : e.target.selectedIndex;
                const handlerName = node.events.change.replace('()', '');
                if (this.app[handlerName]) {
                    this.app[handlerName](data[idx], idx);
                }
            });
        }

        this.applyCommonProps(select, node.props);
        return select;
    }

    renderDatePicker(node) {
        const input = document.createElement('input');
        input.type = 'date';
        input.className = 'quantum-datepicker';
        input.style.padding = '8px 12px';
        input.style.fontSize = '14px';
        input.style.border = '1px solid #ccc';
        input.style.borderRadius = '4px';

        // Set initial value
        if (node.props.selectedDate) {
            const dateValue = this.evaluateBinding(node.props.selectedDate);
            if (dateValue) {
                const date = dateValue instanceof Date ? dateValue : new Date(dateValue);
                input.value = date.toISOString().split('T')[0];
            }
        }

        // Two-way binding
        if (node.props.selectedDate && node.props.selectedDate.includes('{')) {
            const varMatch = node.props.selectedDate.match(/\{([^}]+)\}/);
            if (varMatch) {
                const varName = varMatch[1].trim();
                input.addEventListener('change', (e) => {
                    this.app[varName] = new Date(e.target.value);
                });
                this.trackDependency(varName, (newValue) => {
                    const date = newValue instanceof Date ? newValue : new Date(newValue);
                    input.value = date.toISOString().split('T')[0];
                });
            }
        }

        // Change event
        if (node.events.change) {
            input.addEventListener('change', (e) => {
                const handlerName = node.events.change.replace('()', '');
                if (this.app[handlerName]) {
                    this.app[handlerName](new Date(e.target.value));
                }
            });
        }

        this.applyCommonProps(input, node.props);
        return input;
    }

    renderTree(node) {
        const container = document.createElement('div');
        container.className = 'quantum-tree';
        container.style.fontFamily = 'sans-serif';
        container.style.fontSize = '14px';
        container.textContent = 'Tree Component (Advanced hierarchical view available in components/Tree.js)';
        container.style.padding = '20px';
        container.style.border = '2px dashed #ccc';
        container.style.borderRadius = '4px';
        container.style.color = '#666';
        this.applyCommonProps(container, node.props);
        return container;
    }

    renderTabNavigator(node) {
        const container = document.createElement('div');
        container.className = 'quantum-tabnavigator';
        container.textContent = 'TabNavigator Component (Full tabbed interface available in components/TabNavigator.js)';
        container.style.padding = '20px';
        container.style.border = '2px dashed #ccc';
        container.style.borderRadius = '4px';
        container.style.color = '#666';
        this.applyCommonProps(container, node.props);
        return container;
    }

    renderStates(node) {
        // States container is just a logical grouping - doesn't render anything visual
        // Just process child State elements
        const container = document.createElement('div');
        container.style.display = 'none'; // Hidden container

        if (node.children && node.children.length > 0) {
            for (const child of node.children) {
                const childElement = this.renderComponent(child);
                if (childElement) {
                    container.appendChild(childElement);
                }
            }
        }

        return container;
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
        if (props.styleName) element.classList.add(props.styleName);
        if (props.id) element.id = props.id;
        if (props.visible === 'false') element.style.display = 'none';
        if (props.width) element.style.width = props.width;
        if (props.height) element.style.height = props.height;
    }

    /**
     * Execute event handler
     */
    executeHandler(handlerCode, event) {
        if (!this.app) return;

        try {
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
     * Health check system for automated testing
     */
    registerHealthCheck() {
        // Store health status on window for external access
        window.__quantumHealth = {
            status: 'initializing',
            timestamp: Date.now(),
            errors: [],
            warnings: [],
            app: this.app ? this.app.constructor.name : 'unknown'
        };

        // Capture console errors
        const originalError = console.error;
        console.error = (...args) => {
            window.__quantumHealth.errors.push({
                message: args.join(' '),
                timestamp: Date.now()
            });
            originalError.apply(console, args);
        };

        // Capture console warnings
        const originalWarn = console.warn;
        console.warn = (...args) => {
            window.__quantumHealth.warnings.push({
                message: args.join(' '),
                timestamp: Date.now()
            });
            originalWarn.apply(console, args);
        };

        // Mark as ready after a short delay (allow components to mount)
        setTimeout(() => {
            if (window.__quantumHealth.status === 'initializing') {
                window.__quantumHealth.status = 'ready';
                window.__quantumHealth.readyTimestamp = Date.now();
                console.log('[QUANTUM-HEALTH] Application loaded successfully');
            }
        }, 100);

        // Listen for global errors
        window.addEventListener('error', (event) => {
            window.__quantumHealth.status = 'error';
            window.__quantumHealth.errors.push({
                message: event.message,
                filename: event.filename,
                lineno: event.lineno,
                colno: event.colno,
                timestamp: Date.now()
            });
        });

        // Listen for unhandled promise rejections
        window.addEventListener('unhandledrejection', (event) => {
            window.__quantumHealth.status = 'error';
            window.__quantumHealth.errors.push({
                message: `Unhandled promise rejection: ${event.reason}`,
                timestamp: Date.now()
            });
        });
    }
}
