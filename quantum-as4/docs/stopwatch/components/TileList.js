/**
 * TileList Component - Grid layout for items with thumbnails
 *
 * Props:
 * - dataProvider: Array of items to display (supports bindings)
 * - columnCount: Number of columns (default: auto)
 * - columnWidth: Width of each column in pixels (default: 200)
 * - rowHeight: Height of each row in pixels (default: 200)
 * - itemRenderer: Custom renderer function (optional)
 * - labelField: Field to display as label (default: 'label')
 * - imageField: Field containing image URL (default: 'image')
 * - selectable: Enable item selection (default: false)
 * - allowMultipleSelection: Allow multiple selection (default: false)
 *
 * Events:
 * - itemClick: Fired when item is clicked
 * - selectionChange: Fired when selection changes
 */

export function renderTileList(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-tilelist';
    container.style.display = 'grid';
    container.style.gap = '15px';
    container.style.padding = '15px';

    // Get data provider
    const dataProviderExpr = node.props.dataProvider;
    let data = [];

    if (dataProviderExpr) {
        data = runtime.evaluateBinding(dataProviderExpr);
        if (!Array.isArray(data)) data = [];
    }

    const columnCount = node.props.columnCount ? parseInt(node.props.columnCount) : null;
    const columnWidth = node.props.columnWidth ? parseInt(node.props.columnWidth) : 200;
    const rowHeight = node.props.rowHeight ? parseInt(node.props.rowHeight) : 200;
    const labelField = node.props.labelField || 'label';
    const imageField = node.props.imageField || 'image';
    const selectable = node.props.selectable === 'true';
    const allowMultipleSelection = node.props.allowMultipleSelection === 'true';

    // State
    const state = {
        selectedItems: new Set(),
        selectedIndex: -1
    };

    // Set grid columns
    if (columnCount) {
        container.style.gridTemplateColumns = `repeat(${columnCount}, 1fr)`;
    } else {
        container.style.gridTemplateColumns = `repeat(auto-fill, minmax(${columnWidth}px, 1fr))`;
    }

    // Render items
    const renderItems = () => {
        container.innerHTML = '';

        data.forEach((item, index) => {
            const tile = createTile(item, index);
            container.appendChild(tile);
        });
    };

    // Create tile element
    const createTile = (item, index) => {
        const tile = document.createElement('div');
        tile.className = 'quantum-tilelist-item';
        tile.style.border = '1px solid #ddd';
        tile.style.borderRadius = '6px';
        tile.style.overflow = 'hidden';
        tile.style.backgroundColor = '#fff';
        tile.style.cursor = selectable ? 'pointer' : 'default';
        tile.style.transition = 'all 0.2s ease';
        tile.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';

        // Image container
        const imageContainer = document.createElement('div');
        imageContainer.style.width = '100%';
        imageContainer.style.height = (rowHeight - 60) + 'px';
        imageContainer.style.overflow = 'hidden';
        imageContainer.style.backgroundColor = '#f5f5f5';
        imageContainer.style.display = 'flex';
        imageContainer.style.alignItems = 'center';
        imageContainer.style.justifyContent = 'center';

        // Image or placeholder
        const imageUrl = typeof item === 'object' ? item[imageField] : null;
        if (imageUrl) {
            const img = document.createElement('img');
            img.src = imageUrl;
            img.style.width = '100%';
            img.style.height = '100%';
            img.style.objectFit = 'cover';
            imageContainer.appendChild(img);
        } else {
            const placeholder = document.createElement('div');
            placeholder.textContent = '🖼️';
            placeholder.style.fontSize = '48px';
            placeholder.style.opacity = '0.3';
            imageContainer.appendChild(placeholder);
        }

        tile.appendChild(imageContainer);

        // Label
        const label = document.createElement('div');
        label.className = 'quantum-tilelist-label';
        label.style.padding = '10px';
        label.style.borderTop = '1px solid #eee';
        label.style.fontSize = '13px';
        label.style.fontWeight = 'bold';
        label.style.textAlign = 'center';
        label.style.overflow = 'hidden';
        label.style.textOverflow = 'ellipsis';
        label.style.whiteSpace = 'nowrap';

        const labelText = typeof item === 'object' ? item[labelField] : item;
        label.textContent = labelText || 'Item ' + (index + 1);
        tile.appendChild(label);

        // Hover effect
        tile.addEventListener('mouseenter', () => {
            if (!state.selectedItems.has(item)) {
                tile.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
                tile.style.transform = 'translateY(-2px)';
            }
        });

        tile.addEventListener('mouseleave', () => {
            if (!state.selectedItems.has(item)) {
                tile.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
                tile.style.transform = 'translateY(0)';
            }
        });

        // Selection
        if (selectable) {
            tile.addEventListener('click', (e) => {
                if (allowMultipleSelection && e.ctrlKey) {
                    // Toggle selection
                    if (state.selectedItems.has(item)) {
                        state.selectedItems.delete(item);
                        tile.style.border = '1px solid #ddd';
                        tile.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
                    } else {
                        state.selectedItems.add(item);
                        tile.style.border = '2px solid #3399ff';
                        tile.style.boxShadow = '0 4px 12px rgba(51, 153, 255, 0.3)';
                    }
                } else {
                    // Single selection - clear others
                    container.querySelectorAll('.quantum-tilelist-item').forEach(t => {
                        t.style.border = '1px solid #ddd';
                        t.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
                    });

                    state.selectedItems.clear();
                    state.selectedItems.add(item);
                    state.selectedIndex = index;

                    tile.style.border = '2px solid #3399ff';
                    tile.style.boxShadow = '0 4px 12px rgba(51, 153, 255, 0.3)';
                }

                // Fire selectionChange event
                if (node.events.selectionChange) {
                    const handlerName = node.events.selectionChange.replace('()', '');
                    if (runtime.app[handlerName]) {
                        runtime.app[handlerName](Array.from(state.selectedItems), index);
                    }
                }
            });
        }

        // Item click event
        if (node.events.itemClick) {
            tile.addEventListener('click', () => {
                const handlerName = node.events.itemClick.replace('()', '');
                if (runtime.app[handlerName]) {
                    runtime.app[handlerName](item, index);
                }
            });
        }

        return tile;
    };

    // Initial render
    renderItems();

    // Setup reactive binding for dataProvider
    if (dataProviderExpr && dataProviderExpr.includes('{')) {
        const varMatch = dataProviderExpr.match(/\{([^}]+)\}/);
        if (varMatch) {
            const varName = varMatch[1].trim().split('.')[0];
            runtime.trackDependency(varName, () => {
                data = runtime.evaluateBinding(dataProviderExpr);
                if (!Array.isArray(data)) data = [];
                renderItems();
            });
        }
    }

    runtime.applyCommonProps(container, node.props);
    return container;
}
