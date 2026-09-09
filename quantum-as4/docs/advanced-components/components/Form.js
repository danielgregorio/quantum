/**
 * Form Component - Structured form container
 *
 * Props:
 * - width: Form width (default: 100%)
 * - paddingLeft: Left padding (default: 0)
 * - paddingRight: Right padding (default: 0)
 * - paddingTop: Top padding (default: 10)
 * - paddingBottom: Bottom padding (default: 10)
 *
 * Children: FormItem, FormHeading
 */

export function renderForm(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-form';
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.gap = '12px';
    container.style.width = node.props.width || '100%';

    // Padding
    const paddingTop = node.props.paddingTop || '10';
    const paddingBottom = node.props.paddingBottom || '10';
    const paddingLeft = node.props.paddingLeft || '0';
    const paddingRight = node.props.paddingRight || '0';
    container.style.padding = `${paddingTop}px ${paddingRight}px ${paddingBottom}px ${paddingLeft}px`;

    // Render children
    node.children.forEach(child => {
        const childElement = runtime.renderNode(child);
        container.appendChild(childElement);
    });

    runtime.applyCommonProps(container, node.props);
    return container;
}

/**
 * FormItem Component - Individual form field with label
 *
 * Props:
 * - label: Field label text
 * - required: Show required indicator (default: false)
 * - direction: Layout direction - horizontal/vertical (default: horizontal)
 * - labelWidth: Width of label column (default: 120)
 *
 * Children: Input components (TextInput, ComboBox, etc.)
 */

export function renderFormItem(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-form-item';

    const direction = node.props.direction || 'horizontal';
    const labelWidth = node.props.labelWidth ? parseInt(node.props.labelWidth) : 120;
    const required = node.props.required === 'true';

    if (direction === 'horizontal') {
        container.style.display = 'flex';
        container.style.flexDirection = 'row';
        container.style.alignItems = 'center';
        container.style.gap = '12px';
    } else {
        container.style.display = 'flex';
        container.style.flexDirection = 'column';
        container.style.gap = '6px';
    }

    // Label
    if (node.props.label) {
        const labelElement = document.createElement('label');
        labelElement.className = 'quantum-form-label';
        labelElement.style.fontWeight = '500';
        labelElement.style.fontSize = '13px';
        labelElement.style.color = '#333';
        labelElement.style.userSelect = 'none';

        if (direction === 'horizontal') {
            labelElement.style.width = labelWidth + 'px';
            labelElement.style.flexShrink = '0';
            labelElement.style.textAlign = 'right';
            labelElement.style.paddingRight = '0';
        } else {
            labelElement.style.width = '100%';
        }

        labelElement.textContent = node.props.label;

        // Required indicator
        if (required) {
            const requiredStar = document.createElement('span');
            requiredStar.textContent = ' *';
            requiredStar.style.color = '#e74c3c';
            requiredStar.style.fontWeight = 'bold';
            labelElement.appendChild(requiredStar);
        }

        container.appendChild(labelElement);
    }

    // Input container
    const inputContainer = document.createElement('div');
    inputContainer.className = 'quantum-form-input';
    inputContainer.style.flex = '1';
    inputContainer.style.display = 'flex';
    inputContainer.style.flexDirection = 'column';
    inputContainer.style.gap = '4px';

    // Render children (input components)
    node.children.forEach(child => {
        const childElement = runtime.renderNode(child);
        inputContainer.appendChild(childElement);
    });

    container.appendChild(inputContainer);

    runtime.applyCommonProps(container, node.props);
    return container;
}

/**
 * FormHeading Component - Section heading in form
 *
 * Props:
 * - label: Heading text
 */

export function renderFormHeading(runtime, node) {
    const heading = document.createElement('div');
    heading.className = 'quantum-form-heading';
    heading.style.fontSize = '15px';
    heading.style.fontWeight = 'bold';
    heading.style.color = '#2c3e50';
    heading.style.paddingTop = '15px';
    heading.style.paddingBottom = '8px';
    heading.style.borderBottom = '2px solid #3498db';
    heading.style.marginBottom = '8px';

    heading.textContent = node.props.label || 'Section';

    runtime.applyCommonProps(heading, node.props);
    return heading;
}
