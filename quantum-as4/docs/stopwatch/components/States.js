/**
 * States System
 *
 * Provides view state management for MXML applications.
 * Compatible with Adobe Flex States API.
 *
 * Features:
 * - Define multiple view states
 * - Show/hide components based on current state
 * - includeIn and excludeFrom properties
 * - Programmatic state transitions
 * - State change events
 *
 * @example
 * <s:states>
 *     <s:State name="default" />
 *     <s:State name="login" />
 *     <s:State name="register" />
 * </s:states>
 *
 * <s:Button label="Login" click="currentState='login'" includeIn="default" />
 * <s:Panel title="Login Form" includeIn="login" />
 * <s:Panel title="Register Form" includeIn="register" />
 */

export class State {
    constructor(name) {
        this.name = name;
        this.overrides = [];
    }

    toString() {
        return this.name;
    }
}

/**
 * Parse states from MXML
 */
export function parseStates(runtime, statesNode) {
    const states = [];

    if (!statesNode || !statesNode.children) {
        return states;
    }

    for (const child of statesNode.children) {
        if (child.tagName === 'State') {
            const stateName = child.props.name;
            if (stateName) {
                states.push(new State(stateName));
            }
        }
    }

    return states;
}

/**
 * Initialize states system in runtime
 */
export function initializeStates(runtime, states) {
    // Store states
    runtime.states = states;
    runtime.stateComponents = new Map(); // Track components and their state rules

    // Set default current state (first state or empty)
    runtime.currentState = states.length > 0 ? states[0].name : '';

    // Add currentState property to app with getter/setter
    let _currentState = runtime.currentState;

    Object.defineProperty(runtime.app, 'currentState', {
        get: () => _currentState,
        set: (newState) => {
            if (_currentState !== newState) {
                const oldState = _currentState;
                _currentState = newState;
                runtime.currentState = newState;

                // Update component visibility
                updateComponentVisibility(runtime, newState);

                // Fire state change event
                if (runtime.app.currentStateChange) {
                    runtime.app.currentStateChange({
                        type: 'currentStateChange',
                        oldState: oldState,
                        newState: newState
                    });
                }
            }
        },
        enumerable: true,
        configurable: true
    });
}

/**
 * Register a component with state-based visibility rules
 */
export function registerComponentState(runtime, element, includeIn, excludeFrom) {
    if (!includeIn && !excludeFrom) {
        return; // No state rules
    }

    const stateRule = {
        element: element,
        includeIn: includeIn ? includeIn.split(',').map(s => s.trim()) : null,
        excludeFrom: excludeFrom ? excludeFrom.split(',').map(s => s.trim()) : null,
        originalDisplay: element.style.display || ''
    };

    // Generate unique key for this element
    const key = `component_${Date.now()}_${Math.random()}`;
    runtime.stateComponents.set(key, stateRule);

    // Apply initial visibility
    const shouldShow = isComponentVisibleInState(stateRule, runtime.currentState);
    element.style.display = shouldShow ? stateRule.originalDisplay : 'none';
}

/**
 * Check if component should be visible in given state
 */
function isComponentVisibleInState(stateRule, currentState) {
    // If includeIn is specified, component is only visible in those states
    if (stateRule.includeIn) {
        return stateRule.includeIn.includes(currentState);
    }

    // If excludeFrom is specified, component is visible in all states except those
    if (stateRule.excludeFrom) {
        return !stateRule.excludeFrom.includes(currentState);
    }

    // Default: visible in all states
    return true;
}

/**
 * Update visibility of all state-managed components
 */
function updateComponentVisibility(runtime, newState) {
    if (!runtime.stateComponents) {
        return;
    }

    for (const [key, stateRule] of runtime.stateComponents.entries()) {
        const shouldShow = isComponentVisibleInState(stateRule, newState);

        if (shouldShow) {
            // Show component (restore original display)
            stateRule.element.style.display = stateRule.originalDisplay || '';
        } else {
            // Hide component
            stateRule.element.style.display = 'none';
        }
    }
}

/**
 * Render state component (just returns metadata, not a visual element)
 */
export function renderState(runtime, node) {
    // States are handled during initialization, not rendered directly
    return document.createComment(`State: ${node.props.name}`);
}

/**
 * Enhanced component rendering with state support
 * This wraps existing render functions to add state management
 */
export function renderWithStateSupport(runtime, node, renderFunction) {
    // Call original render function
    const element = renderFunction(runtime, node);

    // If element is valid and has state properties, register it
    if (element && element.nodeType === Node.ELEMENT_NODE) {
        const includeIn = node.props.includeIn;
        const excludeFrom = node.props.excludeFrom;

        if (includeIn || excludeFrom) {
            registerComponentState(runtime, element, includeIn, excludeFrom);
        }
    }

    return element;
}

/**
 * Get all available state names
 */
export function getStateNames(runtime) {
    return runtime.states ? runtime.states.map(s => s.name) : [];
}

/**
 * Check if a state exists
 */
export function hasState(runtime, stateName) {
    return runtime.states ? runtime.states.some(s => s.name === stateName) : false;
}

/**
 * Transition to a state by name
 */
export function transitionToState(runtime, stateName) {
    if (hasState(runtime, stateName)) {
        runtime.app.currentState = stateName;
        return true;
    }
    return false;
}
