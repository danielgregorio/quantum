/**
 * ComboBox Component - Dropdown select with data provider
 *
 * Props:
 * - dataProvider: Array of items or objects (supports bindings)
 * - labelField: Field name to display (for object arrays, default: "label")
 * - selectedIndex: Selected item index (supports bindings)
 * - selectedItem: Selected item object (supports bindings)
 * - prompt: Placeholder text when nothing selected
 * - enabled: Enable/disable combobox (default: true)
 * - width: Width of combobox
 *
 * Events:
 * - change: Fired when selection changes (passes selectedItem)
 */

export function renderComboBox(runtime, node) {
    const select = document.createElement('select');
    select.className = 'quantum-combobox';
    select.style.padding = '8px 12px';
    select.style.fontSize = '14px';
    select.style.border = '1px solid #ccc';
    select.style.borderRadius = '4px';
    select.style.backgroundColor = 'white';
    select.style.cursor = 'pointer';
    select.style.minWidth = '150px';

    // Set width
    if (node.props.width) {
        select.style.width = node.props.width;
    }

    // Get data provider
    const dataProviderExpr = node.props.dataProvider;
    let data = [];

    if (dataProviderExpr) {
        data = runtime.evaluateBinding(dataProviderExpr);
        if (!Array.isArray(data)) data = [];
    }

    const labelField = node.props.labelField || 'label';

    // Render function
    const renderOptions = () => {
        select.innerHTML = '';

        // Add prompt option if specified
        if (node.props.prompt) {
            const promptOption = document.createElement('option');
            promptOption.value = '';
            promptOption.textContent = node.props.prompt;
            promptOption.disabled = true;
            promptOption.selected = true;
            select.appendChild(promptOption);
        }

        // Add data options
        data.forEach((item, index) => {
            const option = document.createElement('option');
            option.value = index;

            // Handle both string arrays and object arrays
            if (typeof item === 'object') {
                option.textContent = item[labelField] || item.toString();
            } else {
                option.textContent = item;
            }

            select.appendChild(option);
        });
    };

    // Initial render
    renderOptions();

    // Set initial selection
    if (node.props.selectedIndex !== undefined) {
        const initialIndex = runtime.evaluateBinding(node.props.selectedIndex);
        if (initialIndex !== undefined && initialIndex !== null) {
            // +1 if prompt exists
            select.selectedIndex = node.props.prompt ? parseInt(initialIndex) + 1 : parseInt(initialIndex);
        }
    }

    // Handle enabled/disabled
    const enabled = node.props.enabled !== 'false';
    select.disabled = !enabled;
    if (!enabled) {
        select.style.cursor = 'not-allowed';
        select.style.opacity = '0.5';
    }

    // Two-way binding for selectedIndex
    if (node.props.selectedIndex && node.props.selectedIndex.includes('{')) {
        const varMatch = node.props.selectedIndex.match(/\{([^}]+)\}/);
        if (varMatch) {
            const varName = varMatch[1].trim();

            // Update app property when selection changes
            select.addEventListener('change', (e) => {
                const index = e.target.selectedIndex;
                const adjustedIndex = node.props.prompt ? index - 1 : index;
                runtime.app[varName] = adjustedIndex;
            });

            // Update select when app property changes
            runtime.trackDependency(varName, (newValue) => {
                const adjustedIndex = node.props.prompt ? newValue + 1 : newValue;
                select.selectedIndex = adjustedIndex;
            });
        }
    }

    // Two-way binding for selectedItem
    if (node.props.selectedItem && node.props.selectedItem.includes('{')) {
        const varMatch = node.props.selectedItem.match(/\{([^}]+)\}/);
        if (varMatch) {
            const varName = varMatch[1].trim();

            // Update app property when selection changes
            select.addEventListener('change', (e) => {
                const index = e.target.selectedIndex;
                const adjustedIndex = node.props.prompt ? index - 1 : index;
                runtime.app[varName] = data[adjustedIndex];
            });

            // Update select when app property changes
            runtime.trackDependency(varName, (newValue) => {
                const index = data.indexOf(newValue);
                const adjustedIndex = node.props.prompt ? index + 1 : index;
                select.selectedIndex = adjustedIndex;
            });
        }
    }

    // Fire change event
    if (node.events.change) {
        select.addEventListener('change', (e) => {
            const index = e.target.selectedIndex;
            const adjustedIndex = node.props.prompt ? index - 1 : index;
            const selectedItem = data[adjustedIndex];

            const handlerName = node.events.change.replace('()', '');
            if (runtime.app[handlerName]) {
                runtime.app[handlerName](selectedItem, adjustedIndex);
            }
        });
    }

    // Reactive data provider
    if (dataProviderExpr && dataProviderExpr.includes('{')) {
        const varMatch = dataProviderExpr.match(/\{([^}]+)\}/);
        if (varMatch) {
            const varName = varMatch[1].trim().split('.')[0];
            runtime.trackDependency(varName, () => {
                data = runtime.evaluateBinding(dataProviderExpr);
                if (!Array.isArray(data)) data = [];
                renderOptions();
            });
        }
    }

    runtime.applyCommonProps(select, node.props);
    return select;
}
