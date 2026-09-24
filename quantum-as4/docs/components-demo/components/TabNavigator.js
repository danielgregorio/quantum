/**
 * TabNavigator Component - Tabbed interface container
 *
 * Props:
 * - selectedIndex: Currently selected tab index (supports bindings)
 * - width: Width of tab navigator
 * - height: Height of tab navigator
 *
 * Children:
 * - Each child should be a container with a 'label' property for the tab
 *
 * Events:
 * - change: Fired when tab changes (passes new index)
 *
 * Example:
 * <TabNavigator selectedIndex="{currentTab}">
 *   <VBox label="Tab 1">...</VBox>
 *   <VBox label="Tab 2">...</VBox>
 * </TabNavigator>
 */

export function renderTabNavigator(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-tabnavigator';
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.border = '1px solid #ccc';
    container.style.borderRadius = '4px';
    container.style.overflow = 'hidden';
    container.style.backgroundColor = 'white';

    // Set dimensions
    if (node.props.width) {
        container.style.width = node.props.width;
    }
    if (node.props.height) {
        container.style.height = node.props.height;
    }

    // State
    let selectedIndex = 0;

    // Get initial selected index
    if (node.props.selectedIndex !== undefined) {
        const initialIndex = runtime.evaluateBinding(node.props.selectedIndex);
        if (initialIndex !== undefined && initialIndex !== null) {
            selectedIndex = parseInt(initialIndex);
        }
    }

    // Tab bar
    const tabBar = document.createElement('div');
    tabBar.className = 'quantum-tabbar';
    tabBar.style.display = 'flex';
    tabBar.style.borderBottom = '1px solid #ccc';
    tabBar.style.backgroundColor = '#f5f5f5';

    // Content area
    const contentArea = document.createElement('div');
    contentArea.className = 'quantum-tabcontent';
    contentArea.style.flex = '1';
    contentArea.style.overflow = 'auto';
    contentArea.style.padding = '15px';

    // Get tab children
    const tabs = node.children || [];

    // Render tabs
    const renderTabs = () => {
        tabBar.innerHTML = '';
        contentArea.innerHTML = '';

        if (tabs.length === 0) {
            const emptyMessage = document.createElement('div');
            emptyMessage.textContent = 'No tabs available';
            emptyMessage.style.padding = '20px';
            emptyMessage.style.textAlign = 'center';
            emptyMessage.style.color = '#999';
            contentArea.appendChild(emptyMessage);
            return;
        }

        // Create tab buttons
        tabs.forEach((tab, index) => {
            const tabButton = document.createElement('button');
            tabButton.className = 'quantum-tab';

            // Get label from tab props
            const tabLabel = tab.props.label || `Tab ${index + 1}`;
            tabButton.textContent = tabLabel;

            // Styling
            tabButton.style.padding = '12px 24px';
            tabButton.style.border = 'none';
            tabButton.style.backgroundColor = 'transparent';
            tabButton.style.cursor = 'pointer';
            tabButton.style.fontSize = '14px';
            tabButton.style.fontWeight = '500';
            tabButton.style.transition = 'all 0.2s';
            tabButton.style.borderBottom = '3px solid transparent';
            tabButton.style.color = '#666';

            // Active tab styling
            if (index === selectedIndex) {
                tabButton.style.backgroundColor = 'white';
                tabButton.style.borderBottom = '3px solid #1976d2';
                tabButton.style.color = '#1976d2';
                tabButton.style.fontWeight = 'bold';
            }

            // Hover effect
            tabButton.addEventListener('mouseenter', () => {
                if (index !== selectedIndex) {
                    tabButton.style.backgroundColor = '#e8e8e8';
                }
            });

            tabButton.addEventListener('mouseleave', () => {
                if (index !== selectedIndex) {
                    tabButton.style.backgroundColor = 'transparent';
                }
            });

            // Click handler
            tabButton.addEventListener('click', () => {
                selectedIndex = index;

                // Update bound variable
                if (node.props.selectedIndex && node.props.selectedIndex.includes('{')) {
                    const varMatch = node.props.selectedIndex.match(/\{([^}]+)\}/);
                    if (varMatch) {
                        const varName = varMatch[1].trim();
                        runtime.app[varName] = selectedIndex;
                    }
                }

                // Fire change event
                if (node.events.change) {
                    const handlerName = node.events.change.replace('()', '');
                    if (runtime.app[handlerName]) {
                        runtime.app[handlerName](selectedIndex);
                    }
                }

                // Re-render tabs
                renderTabs();
            });

            tabBar.appendChild(tabButton);
        });

        // Render selected tab content
        if (selectedIndex >= 0 && selectedIndex < tabs.length) {
            const selectedTab = tabs[selectedIndex];
            const tabContent = runtime.renderComponent(selectedTab);
            contentArea.appendChild(tabContent);
        }
    };

    // Initial render
    renderTabs();

    // Two-way binding for selectedIndex
    if (node.props.selectedIndex && node.props.selectedIndex.includes('{')) {
        const varMatch = node.props.selectedIndex.match(/\{([^}]+)\}/);
        if (varMatch) {
            const varName = varMatch[1].trim();
            runtime.trackDependency(varName, (newValue) => {
                selectedIndex = parseInt(newValue);
                renderTabs();
            });
        }
    }

    container.appendChild(tabBar);
    container.appendChild(contentArea);

    runtime.applyCommonProps(container, node.props);
    return container;
}
