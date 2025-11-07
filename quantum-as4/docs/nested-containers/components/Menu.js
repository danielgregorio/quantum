/**
 * Menu Component - Context menu or dropdown menu
 *
 * Props:
 * - dataProvider: Array of menu items [{label, icon, children, enabled, separator}]
 * - showRoot: Show as dropdown (default: false)
 *
 * Events:
 * - itemClick: Fired when menu item is clicked (passes item)
 */

export function renderMenu(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-menu';
    container.style.position = 'absolute';
    container.style.background = '#ffffff';
    container.style.border = '1px solid #999';
    container.style.borderRadius = '4px';
    container.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
    container.style.padding = '4px 0';
    container.style.minWidth = '180px';
    container.style.zIndex = '1000';
    container.style.display = 'none'; // Hidden by default

    // Get menu data
    const dataProviderExpr = node.props.dataProvider;
    let menuData = [];

    if (dataProviderExpr) {
        menuData = runtime.evaluateBinding(dataProviderExpr);
        if (!Array.isArray(menuData)) menuData = [];
    }

    // Render menu items
    const renderItems = (items, parentElement, level = 0) => {
        items.forEach(item => {
            if (item.separator) {
                const separator = document.createElement('div');
                separator.className = 'quantum-menu-separator';
                separator.style.height = '1px';
                separator.style.background = '#e0e0e0';
                separator.style.margin = '4px 0';
                parentElement.appendChild(separator);
                return;
            }

            const menuItem = document.createElement('div');
            menuItem.className = 'quantum-menu-item';
            menuItem.style.padding = '8px 32px 8px 12px';
            menuItem.style.cursor = item.enabled === false ? 'not-allowed' : 'pointer';
            menuItem.style.fontSize = '13px';
            menuItem.style.position = 'relative';
            menuItem.style.display = 'flex';
            menuItem.style.alignItems = 'center';
            menuItem.style.gap = '8px';
            menuItem.style.userSelect = 'none';
            menuItem.style.opacity = item.enabled === false ? '0.5' : '1';

            // Icon
            if (item.icon) {
                const icon = document.createElement('span');
                icon.className = 'menu-icon';
                icon.textContent = item.icon;
                icon.style.fontSize = '14px';
                menuItem.appendChild(icon);
            }

            // Label
            const label = document.createElement('span');
            label.textContent = item.label || 'Menu Item';
            menuItem.appendChild(label);

            // Submenu indicator
            if (item.children && item.children.length > 0) {
                const arrow = document.createElement('span');
                arrow.textContent = '▶';
                arrow.style.position = 'absolute';
                arrow.style.right = '12px';
                arrow.style.fontSize = '10px';
                arrow.style.color = '#666';
                menuItem.appendChild(arrow);
            }

            // Hover effects
            if (item.enabled !== false) {
                menuItem.addEventListener('mouseenter', () => {
                    menuItem.style.background = '#3399ff';
                    menuItem.style.color = '#ffffff';

                    // Show submenu if exists
                    if (item.children && item.children.length > 0) {
                        const submenu = menuItem.querySelector('.quantum-submenu');
                        if (submenu) {
                            const rect = menuItem.getBoundingClientRect();
                            submenu.style.display = 'block';
                            submenu.style.left = rect.width + 'px';
                            submenu.style.top = '0';
                        }
                    }
                });

                menuItem.addEventListener('mouseleave', () => {
                    menuItem.style.background = '';
                    menuItem.style.color = '';

                    // Hide submenu
                    if (item.children && item.children.length > 0) {
                        const submenu = menuItem.querySelector('.quantum-submenu');
                        if (submenu) {
                            setTimeout(() => {
                                if (!submenu.matches(':hover')) {
                                    submenu.style.display = 'none';
                                }
                            }, 100);
                        }
                    }
                });

                // Click handler
                menuItem.addEventListener('click', (e) => {
                    e.stopPropagation();

                    if (!item.children || item.children.length === 0) {
                        // Fire itemClick event
                        if (node.events.itemClick) {
                            const handlerName = node.events.itemClick.replace('()', '');
                            if (runtime.app[handlerName]) {
                                runtime.app[handlerName](item);
                            }
                        }

                        // Close menu
                        container.style.display = 'none';
                    }
                });
            }

            // Submenu
            if (item.children && item.children.length > 0) {
                menuItem.style.position = 'relative';

                const submenu = document.createElement('div');
                submenu.className = 'quantum-submenu';
                submenu.style.position = 'absolute';
                submenu.style.background = '#ffffff';
                submenu.style.border = '1px solid #999';
                submenu.style.borderRadius = '4px';
                submenu.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
                submenu.style.padding = '4px 0';
                submenu.style.minWidth = '180px';
                submenu.style.display = 'none';
                submenu.style.zIndex = '1001';

                renderItems(item.children, submenu, level + 1);
                menuItem.appendChild(submenu);
            }

            parentElement.appendChild(menuItem);
        });
    };

    renderItems(menuData, container);

    // Show menu method
    container.show = (x, y) => {
        container.style.display = 'block';
        container.style.left = x + 'px';
        container.style.top = y + 'px';
    };

    // Hide menu method
    container.hide = () => {
        container.style.display = 'none';
    };

    // Hide on outside click
    document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) {
            container.hide();
        }
    });

    runtime.applyCommonProps(container, node.props);
    return container;
}

/**
 * MenuBar Component - Application menu bar
 *
 * Props:
 * - dataProvider: Array of top-level menus [{label, children}]
 *
 * Events:
 * - itemClick: Fired when menu item is clicked
 */

export function renderMenuBar(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-menubar';
    container.style.display = 'flex';
    container.style.background = 'linear-gradient(to bottom, #ffffff 0%, #e8e8e8 100%)';
    container.style.borderBottom = '1px solid #999';
    container.style.padding = '0';
    container.style.gap = '0';

    // Get menu data
    const dataProviderExpr = node.props.dataProvider;
    let menuData = [];

    if (dataProviderExpr) {
        menuData = runtime.evaluateBinding(dataProviderExpr);
        if (!Array.isArray(menuData)) menuData = [];
    }

    // Render top-level menus
    menuData.forEach(topMenu => {
        const menuButton = document.createElement('div');
        menuButton.className = 'quantum-menubar-item';
        menuButton.style.padding = '8px 16px';
        menuButton.style.cursor = 'pointer';
        menuButton.style.fontSize = '13px';
        menuButton.style.userSelect = 'none';
        menuButton.style.position = 'relative';
        menuButton.textContent = topMenu.label || 'Menu';

        // Create dropdown menu
        const dropdown = document.createElement('div');
        dropdown.className = 'quantum-menubar-dropdown';
        dropdown.style.position = 'absolute';
        dropdown.style.top = '100%';
        dropdown.style.left = '0';
        dropdown.style.background = '#ffffff';
        dropdown.style.border = '1px solid #999';
        dropdown.style.borderRadius = '0 0 4px 4px';
        dropdown.style.boxShadow = '0 4px 8px rgba(0,0,0,0.2)';
        dropdown.style.padding = '4px 0';
        dropdown.style.minWidth = '200px';
        dropdown.style.display = 'none';
        dropdown.style.zIndex = '1000';

        // Render menu items
        if (topMenu.children) {
            topMenu.children.forEach(item => {
                if (item.separator) {
                    const separator = document.createElement('div');
                    separator.style.height = '1px';
                    separator.style.background = '#e0e0e0';
                    separator.style.margin = '4px 0';
                    dropdown.appendChild(separator);
                    return;
                }

                const menuItem = document.createElement('div');
                menuItem.className = 'quantum-menubar-dropdown-item';
                menuItem.style.padding = '8px 32px 8px 12px';
                menuItem.style.cursor = item.enabled === false ? 'not-allowed' : 'pointer';
                menuItem.style.fontSize = '13px';
                menuItem.style.opacity = item.enabled === false ? '0.5' : '1';
                menuItem.style.userSelect = 'none';
                menuItem.textContent = item.label || 'Item';

                if (item.enabled !== false) {
                    menuItem.addEventListener('mouseenter', () => {
                        menuItem.style.background = '#3399ff';
                        menuItem.style.color = '#ffffff';
                    });

                    menuItem.addEventListener('mouseleave', () => {
                        menuItem.style.background = '';
                        menuItem.style.color = '';
                    });

                    menuItem.addEventListener('click', (e) => {
                        e.stopPropagation();

                        // Fire itemClick event
                        if (node.events.itemClick) {
                            const handlerName = node.events.itemClick.replace('()', '');
                            if (runtime.app[handlerName]) {
                                runtime.app[handlerName](item);
                            }
                        }

                        // Close dropdown
                        dropdown.style.display = 'none';
                        menuButton.style.background = '';
                    });
                }

                dropdown.appendChild(menuItem);
            });
        }

        menuButton.appendChild(dropdown);

        // Toggle dropdown
        menuButton.addEventListener('click', (e) => {
            e.stopPropagation();

            // Close other dropdowns
            container.querySelectorAll('.quantum-menubar-dropdown').forEach(d => {
                if (d !== dropdown) {
                    d.style.display = 'none';
                }
            });
            container.querySelectorAll('.quantum-menubar-item').forEach(b => {
                if (b !== menuButton) {
                    b.style.background = '';
                }
            });

            // Toggle this dropdown
            if (dropdown.style.display === 'block') {
                dropdown.style.display = 'none';
                menuButton.style.background = '';
            } else {
                dropdown.style.display = 'block';
                menuButton.style.background = 'rgba(51, 153, 255, 0.1)';
            }
        });

        // Hover effect
        menuButton.addEventListener('mouseenter', () => {
            if (dropdown.style.display !== 'block') {
                menuButton.style.background = 'rgba(51, 153, 255, 0.05)';
            }
        });

        menuButton.addEventListener('mouseleave', () => {
            if (dropdown.style.display !== 'block') {
                menuButton.style.background = '';
            }
        });

        container.appendChild(menuButton);
    });

    // Close dropdowns on outside click
    document.addEventListener('click', () => {
        container.querySelectorAll('.quantum-menubar-dropdown').forEach(d => {
            d.style.display = 'none';
        });
        container.querySelectorAll('.quantum-menubar-item').forEach(b => {
            b.style.background = '';
        });
    });

    runtime.applyCommonProps(container, node.props);
    return container;
}
