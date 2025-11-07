/**
 * Tree Component - Hierarchical data display
 *
 * Props:
 * - dataProvider: Hierarchical array of objects (supports bindings)
 * - labelField: Field name to display (default: "label")
 * - childrenField: Field name for children array (default: "children")
 * - showRoot: Show root node (default: true)
 * - expandDepth: Auto-expand to this depth (default: 1)
 *
 * Events:
 * - itemClick: Fired when node is clicked (passes item)
 * - itemOpen: Fired when node is expanded
 * - itemClose: Fired when node is collapsed
 */

export function renderTree(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-tree';
    container.style.fontFamily = 'sans-serif';
    container.style.fontSize = '14px';
    container.style.userSelect = 'none';

    // Get data provider
    const dataProviderExpr = node.props.dataProvider;
    let data = [];

    if (dataProviderExpr) {
        const rootData = runtime.evaluateBinding(dataProviderExpr);
        if (Array.isArray(rootData)) {
            data = rootData;
        } else if (rootData && typeof rootData === 'object') {
            // Single root node
            data = [rootData];
        }
    }

    const labelField = node.props.labelField || 'label';
    const childrenField = node.props.childrenField || 'children';
    const showRoot = node.props.showRoot !== 'false';
    const expandDepth = node.props.expandDepth ? parseInt(node.props.expandDepth) : 1;

    // Track expanded state
    const expandedNodes = new Set();

    // Render tree node
    const renderNode = (item, depth = 0, parent = null) => {
        const nodeContainer = document.createElement('div');
        nodeContainer.style.marginLeft = depth > 0 ? '20px' : '0';

        const nodeRow = document.createElement('div');
        nodeRow.style.display = 'flex';
        nodeRow.style.alignItems = 'center';
        nodeRow.style.padding = '4px 8px';
        nodeRow.style.cursor = 'pointer';
        nodeRow.style.borderRadius = '4px';

        const hasChildren = item[childrenField] && item[childrenField].length > 0;
        const nodeId = item.id || item[labelField];
        const isExpanded = expandedNodes.has(nodeId);

        // Auto-expand based on depth
        if (depth < expandDepth && hasChildren) {
            expandedNodes.add(nodeId);
        }

        // Expand/collapse icon
        const icon = document.createElement('span');
        icon.style.marginRight = '8px';
        icon.style.fontSize = '12px';
        icon.style.width = '16px';
        icon.style.display = 'inline-block';
        icon.style.textAlign = 'center';

        if (hasChildren) {
            icon.textContent = expandedNodes.has(nodeId) ? '▼' : '▶';
        } else {
            icon.textContent = '•';
            icon.style.color = '#999';
        }

        // Label
        const label = document.createElement('span');
        label.textContent = item[labelField] || item.toString();
        label.style.flex = '1';

        nodeRow.appendChild(icon);
        nodeRow.appendChild(label);

        // Hover effect
        nodeRow.addEventListener('mouseenter', () => {
            nodeRow.style.backgroundColor = '#f0f0f0';
        });

        nodeRow.addEventListener('mouseleave', () => {
            nodeRow.style.backgroundColor = 'transparent';
        });

        // Click handler
        nodeRow.addEventListener('click', (e) => {
            e.stopPropagation();

            if (hasChildren) {
                // Toggle expand/collapse
                if (expandedNodes.has(nodeId)) {
                    expandedNodes.delete(nodeId);

                    // Fire itemClose event
                    if (node.events.itemClose) {
                        const handlerName = node.events.itemClose.replace('()', '');
                        if (runtime.app[handlerName]) {
                            runtime.app[handlerName](item);
                        }
                    }
                } else {
                    expandedNodes.add(nodeId);

                    // Fire itemOpen event
                    if (node.events.itemOpen) {
                        const handlerName = node.events.itemOpen.replace('()', '');
                        if (runtime.app[handlerName]) {
                            runtime.app[handlerName](item);
                        }
                    }
                }

                // Re-render tree
                renderTree();
            }

            // Fire itemClick event
            if (node.events.itemClick) {
                const handlerName = node.events.itemClick.replace('()', '');
                if (runtime.app[handlerName]) {
                    runtime.app[handlerName](item);
                }
            }
        });

        nodeContainer.appendChild(nodeRow);

        // Render children if expanded
        if (hasChildren && expandedNodes.has(nodeId)) {
            const childrenContainer = document.createElement('div');
            item[childrenField].forEach(child => {
                childrenContainer.appendChild(renderNode(child, depth + 1, item));
            });
            nodeContainer.appendChild(childrenContainer);
        }

        return nodeContainer;
    };

    // Render entire tree
    const renderTree = () => {
        container.innerHTML = '';

        if (data.length === 0) {
            const emptyMessage = document.createElement('div');
            emptyMessage.textContent = 'No data available';
            emptyMessage.style.padding = '20px';
            emptyMessage.style.textAlign = 'center';
            emptyMessage.style.color = '#999';
            container.appendChild(emptyMessage);
            return;
        }

        data.forEach(item => {
            container.appendChild(renderNode(item, showRoot ? 0 : -1));
        });
    };

    // Initial render
    renderTree();

    // Reactive data provider
    if (dataProviderExpr && dataProviderExpr.includes('{')) {
        const varMatch = dataProviderExpr.match(/\{([^}]+)\}/);
        if (varMatch) {
            const varName = varMatch[1].trim().split('.')[0];
            runtime.trackDependency(varName, () => {
                const rootData = runtime.evaluateBinding(dataProviderExpr);
                if (Array.isArray(rootData)) {
                    data = rootData;
                } else if (rootData && typeof rootData === 'object') {
                    data = [rootData];
                }
                renderTree();
            });
        }
    }

    runtime.applyCommonProps(container, node.props);
    return container;
}
