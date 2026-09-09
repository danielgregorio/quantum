/**
 * TextArea Component
 *
 * A multi-line text input control with scrolling support.
 * Compatible with Adobe Flex TextArea API.
 *
 * Features:
 * - Multi-line text editing
 * - Automatic scrollbars
 * - Character limit enforcement
 * - Word wrap control
 * - Editable/read-only modes
 * - Change and input events
 * - Reactive binding support
 *
 * @example
 * <s:TextArea id="comments"
 *             text="{userComments}"
 *             width="300"
 *             height="150"
 *             maxChars="500"
 *             wordWrap="true"
 *             change="handleCommentChange(event)" />
 */

export function renderTextArea(runtime, node) {
    const container = document.createElement('div');
    const textAreaId = node.props.id || `textarea_${Date.now()}`;

    // Parse properties
    const text = node.props.text || '';
    const maxChars = node.props.maxChars ? parseInt(node.props.maxChars) : null;
    const editable = node.props.editable !== 'false';
    const wordWrap = node.props.wordWrap !== 'false';
    const width = node.props.width ? parseInt(node.props.width) : 200;
    const height = node.props.height ? parseInt(node.props.height) : 100;

    // Container styling
    container.className = 'textarea-container';
    container.style.display = 'inline-block';
    container.style.width = width + 'px';
    container.style.height = height + 'px';
    container.style.position = 'relative';

    // Create textarea element
    const textarea = document.createElement('textarea');
    textarea.className = 'flex-textarea';
    textarea.value = text;
    textarea.disabled = !editable;

    // Flex-style textarea styling
    textarea.style.width = '100%';
    textarea.style.height = '100%';
    textarea.style.border = '1px solid #999999';
    textarea.style.backgroundColor = editable ? '#ffffff' : '#f0f0f0';
    textarea.style.color = '#000000';
    textarea.style.fontFamily = 'Arial, sans-serif';
    textarea.style.fontSize = '11px';
    textarea.style.padding = '4px';
    textarea.style.resize = 'none';
    textarea.style.outline = 'none';
    textarea.style.boxSizing = 'border-box';
    textarea.style.whiteSpace = wordWrap ? 'pre-wrap' : 'pre';
    textarea.style.overflowWrap = wordWrap ? 'break-word' : 'normal';
    textarea.style.overflow = 'auto';

    // Focus styling
    textarea.addEventListener('focus', () => {
        textarea.style.borderColor = '#0b6fcc';
        textarea.style.boxShadow = '0 0 3px rgba(11, 111, 204, 0.5)';
    });

    textarea.addEventListener('blur', () => {
        textarea.style.borderColor = '#999999';
        textarea.style.boxShadow = 'none';
    });

    // Character counter (if maxChars is set)
    let charCounter = null;
    if (maxChars) {
        charCounter = document.createElement('div');
        charCounter.className = 'char-counter';
        charCounter.style.position = 'absolute';
        charCounter.style.bottom = '4px';
        charCounter.style.right = '8px';
        charCounter.style.fontSize = '10px';
        charCounter.style.color = '#666666';
        charCounter.style.backgroundColor = 'rgba(255, 255, 255, 0.9)';
        charCounter.style.padding = '2px 4px';
        charCounter.style.borderRadius = '2px';
        charCounter.style.pointerEvents = 'none';

        const updateCharCounter = () => {
            const remaining = maxChars - textarea.value.length;
            charCounter.textContent = `${textarea.value.length}/${maxChars}`;
            charCounter.style.color = remaining < 10 ? '#e74c3c' : '#666666';
        };

        updateCharCounter();
        container.appendChild(charCounter);

        // Enforce character limit
        textarea.addEventListener('input', () => {
            if (textarea.value.length > maxChars) {
                textarea.value = textarea.value.substring(0, maxChars);
            }
            updateCharCounter();
        });
    }

    // Change event handler
    let lastValue = textarea.value;

    textarea.addEventListener('input', () => {
        const currentValue = textarea.value;

        // Update reactive binding
        if (node.props.text && node.props.text.includes('{')) {
            const bindingPath = node.props.text.replace(/[{}]/g, '');
            const pathParts = bindingPath.split('.');

            if (pathParts.length === 1) {
                runtime.app[pathParts[0]] = currentValue;
            } else {
                let obj = runtime.app;
                for (let i = 0; i < pathParts.length - 1; i++) {
                    obj = obj[pathParts[i]];
                }
                obj[pathParts[pathParts.length - 1]] = currentValue;
            }
        }

        // Fire change event
        if (node.events && node.events.change && currentValue !== lastValue) {
            const handlerName = node.events.change.replace(/[()]/g, '');
            if (runtime.app[handlerName]) {
                runtime.app[handlerName]({
                    type: 'change',
                    target: textarea,
                    text: currentValue,
                    oldText: lastValue
                });
            }
            lastValue = currentValue;
        }

        // Fire textInput event
        if (node.events && node.events.textInput) {
            const handlerName = node.events.textInput.replace(/[()]/g, '');
            if (runtime.app[handlerName]) {
                runtime.app[handlerName]({
                    type: 'textInput',
                    target: textarea,
                    text: currentValue
                });
            }
        }
    });

    // Setup reactive binding
    if (node.props.text && node.props.text.includes('{')) {
        const bindingPath = node.props.text.replace(/[{}]/g, '');

        runtime.addBinding(bindingPath, () => {
            const newValue = runtime.evaluateBinding(node.props.text) || '';
            if (newValue !== textarea.value) {
                textarea.value = newValue;
                lastValue = newValue;

                if (charCounter) {
                    const remaining = maxChars - textarea.value.length;
                    charCounter.textContent = `${textarea.value.length}/${maxChars}`;
                    charCounter.style.color = remaining < 10 ? '#e74c3c' : '#666666';
                }
            }
        });
    }

    // Assemble component
    container.appendChild(textarea);

    // Store reference if ID provided
    if (node.props.id) {
        runtime.app[node.props.id] = {
            element: container,
            textarea: textarea,
            getText: () => textarea.value,
            setText: (newText) => {
                const oldValue = textarea.value;
                textarea.value = newText;

                // Update reactive binding
                if (node.props.text && node.props.text.includes('{')) {
                    const bindingPath = node.props.text.replace(/[{}]/g, '');
                    const pathParts = bindingPath.split('.');

                    if (pathParts.length === 1) {
                        runtime.app[pathParts[0]] = newText;
                    } else {
                        let obj = runtime.app;
                        for (let i = 0; i < pathParts.length - 1; i++) {
                            obj = obj[pathParts[i]];
                        }
                        obj[pathParts[pathParts.length - 1]] = newText;
                    }
                }

                // Fire change event
                if (node.events && node.events.change && newText !== oldValue) {
                    const handlerName = node.events.change.replace(/[()]/g, '');
                    if (runtime.app[handlerName]) {
                        runtime.app[handlerName]({
                            type: 'change',
                            target: textarea,
                            text: newText,
                            oldText: oldValue
                        });
                    }
                }

                lastValue = newText;

                if (charCounter) {
                    const remaining = maxChars - textarea.value.length;
                    charCounter.textContent = `${textarea.value.length}/${maxChars}`;
                    charCounter.style.color = remaining < 10 ? '#e74c3c' : '#666666';
                }
            },
            appendText: (text) => {
                textarea.value += text;
                textarea.scrollTop = textarea.scrollHeight;
            },
            clear: () => {
                textarea.value = '';
                lastValue = '';

                if (charCounter) {
                    charCounter.textContent = `0/${maxChars}`;
                    charCounter.style.color = '#666666';
                }
            },
            setSelection: (beginIndex, endIndex) => {
                textarea.setSelectionRange(beginIndex, endIndex);
                textarea.focus();
            },
            getSelectionBeginIndex: () => textarea.selectionStart,
            getSelectionEndIndex: () => textarea.selectionEnd
        };
    }

    return container;
}
