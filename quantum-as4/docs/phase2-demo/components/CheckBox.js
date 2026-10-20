/**
 * CheckBox Component - Toggle input with two-way binding
 *
 * Props:
 * - label: Label text next to checkbox
 * - selected: Boolean value (supports bindings)
 * - enabled: Enable/disable checkbox (default: true)
 * - labelPlacement: Position of label ("left" | "right", default: "right")
 *
 * Events:
 * - change: Fired when checkbox value changes
 */

export function renderCheckBox(runtime, node) {
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
        runtime.createReactiveBinding(labelText, node.props.label, 'textContent');
    }

    // Set initial selected state
    if (node.props.selected) {
        const initialValue = runtime.evaluateBinding(node.props.selected);
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
                runtime.app[varName] = e.target.checked;
            });

            // Update checkbox when app property changes
            runtime.trackDependency(varName, (newValue) => {
                input.checked = newValue === true || newValue === 'true';
            });
        }
    }

    // Fire change event
    if (node.events.change) {
        input.addEventListener('change', (e) => {
            const handlerName = node.events.change.replace('()', '');
            if (runtime.app[handlerName]) {
                runtime.app[handlerName](e.target.checked);
            }
        });
    }

    runtime.applyCommonProps(container, node.props);
    return container;
}
