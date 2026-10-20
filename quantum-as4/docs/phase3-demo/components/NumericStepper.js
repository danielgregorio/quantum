/**
 * NumericStepper Component
 *
 * A numeric input with increment/decrement buttons.
 * Compatible with Adobe Flex NumericStepper API.
 *
 * Features:
 * - Increment/decrement buttons
 * - Keyboard input with validation
 * - Min/max value constraints
 * - Custom step size
 * - Change event on value updates
 * - Reactive binding support
 *
 * @example
 * <s:NumericStepper id="quantity"
 *                   value="{quantity}"
 *                   minimum="1"
 *                   maximum="100"
 *                   stepSize="1"
 *                   change="handleQuantityChange(event)" />
 */

export function renderNumericStepper(runtime, node) {
    const container = document.createElement('div');
    const stepperId = node.props.id || `stepper_${Date.now()}`;

    // Parse properties
    let value = parseFloat(node.props.value || '0');
    const minimum = parseFloat(node.props.minimum || '0');
    const maximum = parseFloat(node.props.maximum || '100');
    const stepSize = parseFloat(node.props.stepSize || '1');
    const width = node.props.width ? parseInt(node.props.width) : 100;

    // Container styling
    container.className = 'numeric-stepper';
    container.style.display = 'inline-flex';
    container.style.alignItems = 'stretch';
    container.style.width = width + 'px';
    container.style.height = '24px';
    container.style.border = '1px solid #999999';
    container.style.backgroundColor = 'white';
    container.style.borderRadius = '2px';
    container.style.overflow = 'hidden';

    // Text input (center)
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'stepper-input';
    input.style.flex = '1';
    input.style.border = 'none';
    input.style.outline = 'none';
    input.style.textAlign = 'center';
    input.style.fontSize = '11px';
    input.style.fontFamily = 'Arial, sans-serif';
    input.style.padding = '0 4px';
    input.style.backgroundColor = 'white';
    input.style.color = '#000000';

    // Button container (right side)
    const buttonContainer = document.createElement('div');
    buttonContainer.style.display = 'flex';
    buttonContainer.style.flexDirection = 'column';
    buttonContainer.style.width = '16px';
    buttonContainer.style.borderLeft = '1px solid #999999';

    // Increment button (up arrow)
    const incrementBtn = document.createElement('button');
    incrementBtn.className = 'stepper-button stepper-up';
    incrementBtn.innerHTML = '▲';
    incrementBtn.style.flex = '1';
    incrementBtn.style.border = 'none';
    incrementBtn.style.background = 'linear-gradient(to bottom, #ffffff 0%, #e0e0e0 100%)';
    incrementBtn.style.cursor = 'pointer';
    incrementBtn.style.fontSize = '8px';
    incrementBtn.style.padding = '0';
    incrementBtn.style.lineHeight = '1';
    incrementBtn.style.color = '#333333';
    incrementBtn.style.borderBottom = '1px solid #999999';

    // Decrement button (down arrow)
    const decrementBtn = document.createElement('button');
    decrementBtn.className = 'stepper-button stepper-down';
    decrementBtn.innerHTML = '▼';
    decrementBtn.style.flex = '1';
    decrementBtn.style.border = 'none';
    decrementBtn.style.background = 'linear-gradient(to bottom, #ffffff 0%, #e0e0e0 100%)';
    decrementBtn.style.cursor = 'pointer';
    decrementBtn.style.fontSize = '8px';
    decrementBtn.style.padding = '0';
    decrementBtn.style.lineHeight = '1';
    decrementBtn.style.color = '#333333';

    // Button hover effects
    const addHoverEffect = (btn) => {
        btn.addEventListener('mouseenter', () => {
            btn.style.background = 'linear-gradient(to bottom, #f0f0f0 0%, #d0d0d0 100%)';
        });
        btn.addEventListener('mouseleave', () => {
            btn.style.background = 'linear-gradient(to bottom, #ffffff 0%, #e0e0e0 100%)';
        });
        btn.addEventListener('mousedown', () => {
            btn.style.background = 'linear-gradient(to bottom, #d0d0d0 0%, #b0b0b0 100%)';
        });
        btn.addEventListener('mouseup', () => {
            btn.style.background = 'linear-gradient(to bottom, #f0f0f0 0%, #d0d0d0 100%)';
        });
    };

    addHoverEffect(incrementBtn);
    addHoverEffect(decrementBtn);

    // Validate and constrain value
    const constrainValue = (val) => {
        val = parseFloat(val);
        if (isNaN(val)) val = minimum;
        if (val < minimum) val = minimum;
        if (val > maximum) val = maximum;
        return val;
    };

    // Update display
    const updateDisplay = () => {
        input.value = value.toString();

        // Update button states
        incrementBtn.disabled = value >= maximum;
        decrementBtn.disabled = value <= minimum;

        if (incrementBtn.disabled) {
            incrementBtn.style.opacity = '0.3';
            incrementBtn.style.cursor = 'not-allowed';
        } else {
            incrementBtn.style.opacity = '1';
            incrementBtn.style.cursor = 'pointer';
        }

        if (decrementBtn.disabled) {
            decrementBtn.style.opacity = '0.3';
            decrementBtn.style.cursor = 'not-allowed';
        } else {
            decrementBtn.style.opacity = '1';
            decrementBtn.style.cursor = 'pointer';
        }
    };

    // Fire change event
    const fireChangeEvent = (newValue, oldValue) => {
        // Update reactive binding
        if (node.props.value && node.props.value.includes('{')) {
            const bindingPath = node.props.value.replace(/[{}]/g, '');
            const pathParts = bindingPath.split('.');

            if (pathParts.length === 1) {
                runtime.app[pathParts[0]] = newValue;
            } else {
                let obj = runtime.app;
                for (let i = 0; i < pathParts.length - 1; i++) {
                    obj = obj[pathParts[i]];
                }
                obj[pathParts[pathParts.length - 1]] = newValue;
            }
        }

        // Fire change event handler
        if (node.events && node.events.change) {
            const handlerName = node.events.change.replace(/[()]/g, '');
            if (runtime.app[handlerName]) {
                runtime.app[handlerName]({
                    type: 'change',
                    target: container,
                    value: newValue,
                    oldValue: oldValue
                });
            }
        }
    };

    // Increment handler
    incrementBtn.addEventListener('click', () => {
        if (value < maximum) {
            const oldValue = value;
            value = Math.min(maximum, value + stepSize);
            updateDisplay();
            fireChangeEvent(value, oldValue);
        }
    });

    // Decrement handler
    decrementBtn.addEventListener('click', () => {
        if (value > minimum) {
            const oldValue = value;
            value = Math.max(minimum, value - stepSize);
            updateDisplay();
            fireChangeEvent(value, oldValue);
        }
    });

    // Manual input handler
    input.addEventListener('blur', () => {
        const oldValue = value;
        const newValue = constrainValue(parseFloat(input.value));

        if (newValue !== oldValue) {
            value = newValue;
            fireChangeEvent(value, oldValue);
        }

        updateDisplay();
    });

    // Enter key handler
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            input.blur();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            incrementBtn.click();
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            decrementBtn.click();
        }
    });

    // Only allow numeric input
    input.addEventListener('keypress', (e) => {
        const char = e.key;
        const currentValue = input.value;

        // Allow numbers, minus sign (at start), and decimal point
        if (!/[\d.-]/.test(char)) {
            e.preventDefault();
            return;
        }

        // Only one minus at the start
        if (char === '-' && (currentValue.includes('-') || input.selectionStart !== 0)) {
            e.preventDefault();
            return;
        }

        // Only one decimal point
        if (char === '.' && currentValue.includes('.')) {
            e.preventDefault();
            return;
        }
    });

    // Setup reactive binding
    if (node.props.value && node.props.value.includes('{')) {
        const bindingPath = node.props.value.replace(/[{}]/g, '');

        runtime.addBinding(bindingPath, () => {
            const newValue = constrainValue(runtime.evaluateBinding(node.props.value));
            if (newValue !== value) {
                value = newValue;
                updateDisplay();
            }
        });
    }

    // Initial display
    value = constrainValue(value);
    updateDisplay();

    // Assemble component
    buttonContainer.appendChild(incrementBtn);
    buttonContainer.appendChild(decrementBtn);
    container.appendChild(input);
    container.appendChild(buttonContainer);

    // Store reference if ID provided
    if (node.props.id) {
        runtime.app[node.props.id] = {
            element: container,
            getValue: () => value,
            setValue: (newValue) => {
                const oldValue = value;
                value = constrainValue(newValue);
                updateDisplay();
                fireChangeEvent(value, oldValue);
            },
            getMinimum: () => minimum,
            getMaximum: () => maximum,
            stepUp: () => incrementBtn.click(),
            stepDown: () => decrementBtn.click()
        };
    }

    return container;
}
