/**
 * List Component - Virtualized list with item renderers
 *
 * Props:
 * - dataProvider: Array of items to display (supports bindings)
 * - itemRenderer: Function to render each item (optional)
 * - labelField: Field name to display (if no itemRenderer)
 * - selectable: Enable item selection (default: false)
 * - virtualized: Enable virtualization for large lists (default: false)
 * - itemHeight: Height of each item for virtualization (default: 40)
 *
 * Events:
 * - itemClick: Fired when item is clicked
 * - selectionChange: Fired when selection changes
 */

export function renderList(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-list-container';

    // Get data provider
    const dataProviderExpr = node.props.dataProvider;
    let data = [];

    if (dataProviderExpr) {
        data = runtime.evaluateBinding(dataProviderExpr);
        if (!Array.isArray(data)) data = [];
    }

    const labelField = node.props.labelField || 'label';
    const selectable = node.props.selectable === 'true';
    const virtualized = node.props.virtualized === 'true';
    const itemHeight = node.props.itemHeight ? parseInt(node.props.itemHeight) : 40;

    // State
    const state = {
        selectedIndex: -1,
        selectedItem: null,
        scrollTop: 0
    };

    if (virtualized) {
        // Virtualized list (for large datasets)
        container.style.overflow = 'auto';
        container.style.position = 'relative';

        const contentHeight = data.length * itemHeight;
        const innerContainer = document.createElement('div');
        innerContainer.style.height = `${contentHeight}px`;
        innerContainer.style.position = 'relative';

        const updateVisibleItems = () => {
            const viewportHeight = container.clientHeight || 400;
            const scrollTop = container.scrollTop;

            const startIndex = Math.floor(scrollTop / itemHeight);
            const endIndex = Math.min(
                data.length,
                Math.ceil((scrollTop + viewportHeight) / itemHeight) + 1
            );

            // Clear and render only visible items
            innerContainer.innerHTML = '';

            for (let i = startIndex; i < endIndex; i++) {
                const item = data[i];
                const itemDiv = createItemElement(item, i);
                itemDiv.style.position = 'absolute';
                itemDiv.style.top = `${i * itemHeight}px`;
                itemDiv.style.height = `${itemHeight}px`;
                itemDiv.style.width = '100%';
                innerContainer.appendChild(itemDiv);
            }
        };

        container.addEventListener('scroll', updateVisibleItems);
        container.appendChild(innerContainer);

        // Set initial height
        if (node.props.height) {
            container.style.height = node.props.height;
        } else {
            container.style.height = '400px';
        }

        updateVisibleItems();

    } else {
        // Standard list
        const ul = document.createElement('ul');
        ul.className = 'quantum-list';
        ul.style.listStyle = 'none';
        ul.style.padding = '0';
        ul.style.margin = '0';

        data.forEach((item, index) => {
            const li = createItemElement(item, index);
            ul.appendChild(li);
        });

        container.appendChild(ul);
    }

    function createItemElement(item, index) {
        const li = document.createElement('li');
        li.className = 'quantum-list-item';
        li.style.padding = '10px 15px';
        li.style.borderBottom = '1px solid #eee';
        li.style.display = 'flex';
        li.style.alignItems = 'center';

        // Render item content
        if (node.props.itemRenderer) {
            // Custom item renderer (future enhancement)
            li.textContent = typeof item === 'object' ? item[labelField] : item;
        } else {
            // Default renderer
            li.textContent = typeof item === 'object' ? item[labelField] : item;
        }

        // Make selectable
        if (selectable) {
            li.style.cursor = 'pointer';

            li.addEventListener('mouseenter', () => {
                if (state.selectedIndex !== index) {
                    li.style.backgroundColor = '#f5f5f5';
                }
            });

            li.addEventListener('mouseleave', () => {
                if (state.selectedIndex !== index) {
                    li.style.backgroundColor = '';
                }
            });

            li.addEventListener('click', () => {
                // Update selection
                const previousIndex = state.selectedIndex;
                state.selectedIndex = index;
                state.selectedItem = item;

                // Update visual state
                if (virtualized) {
                    updateVisibleItems();
                } else {
                    container.querySelectorAll('.quantum-list-item').forEach((el, idx) => {
                        el.style.backgroundColor = idx === index ? '#e3f2fd' : '';
                        el.style.fontWeight = idx === index ? 'bold' : 'normal';
                    });
                }

                li.style.backgroundColor = '#e3f2fd';
                li.style.fontWeight = 'bold';

                // Fire selectionChange event
                if (node.events.selectionChange && previousIndex !== index) {
                    const handlerName = node.events.selectionChange.replace('()', '');
                    if (runtime.app[handlerName]) {
                        runtime.app[handlerName](item, index);
                    }
                }
            });
        }

        // Fire itemClick event
        if (node.events.itemClick) {
            li.style.cursor = 'pointer';
            li.addEventListener('click', () => {
                const handlerName = node.events.itemClick.replace('()', '');
                if (runtime.app[handlerName]) {
                    runtime.app[handlerName](item, index);
                }
            });
        }

        return li;
    }

    // Setup reactive binding for dataProvider
    if (dataProviderExpr && dataProviderExpr.includes('{')) {
        const varMatch = dataProviderExpr.match(/\{([^}]+)\}/);
        if (varMatch) {
            const varName = varMatch[1].trim().split('.')[0];
            runtime.trackDependency(varName, () => {
                data = runtime.evaluateBinding(dataProviderExpr);
                if (!Array.isArray(data)) data = [];

                // Re-render list
                if (virtualized) {
                    const contentHeight = data.length * itemHeight;
                    container.querySelector('div').style.height = `${contentHeight}px`;
                    updateVisibleItems();
                } else {
                    const ul = container.querySelector('ul');
                    ul.innerHTML = '';
                    data.forEach((item, index) => {
                        const li = createItemElement(item, index);
                        ul.appendChild(li);
                    });
                }
            });
        }
    }

    runtime.applyCommonProps(container, node.props);
    return container;
}
