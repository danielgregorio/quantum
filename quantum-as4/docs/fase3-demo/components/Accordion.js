/**
 * Accordion Component - Collapsible panels
 *
 * Props:
 * - allowMultipleExpanded: Allow multiple panels open (default: false)
 * - selectedIndex: Initially selected panel index (default: 0)
 *
 * Children:
 * - AccordionHeader: Panel headers
 * - AccordionPanel: Panel content
 *
 * Events:
 * - change: Fired when selection changes (passes selectedIndex)
 */

export function renderAccordion(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-accordion';
    container.style.border = '1px solid #999';
    container.style.borderRadius = '4px';
    container.style.overflow = 'hidden';

    const allowMultipleExpanded = node.props.allowMultipleExpanded === 'true';
    const initialIndex = node.props.selectedIndex ? parseInt(node.props.selectedIndex) : 0;

    // State
    const state = {
        expandedPanels: new Set(allowMultipleExpanded ? [] : [initialIndex])
    };

    // Extract panels from children
    const panels = [];
    let currentPanel = null;

    node.children.forEach(child => {
        if (child.type === 'AccordionHeader') {
            if (currentPanel) {
                panels.push(currentPanel);
            }
            currentPanel = {
                header: child.props.title || 'Panel',
                content: []
            };
        } else if (currentPanel) {
            currentPanel.content.push(child);
        }
    });

    if (currentPanel) {
        panels.push(currentPanel);
    }

    // If no structured panels, create from direct children pairs
    if (panels.length === 0 && node.children.length > 0) {
        for (let i = 0; i < node.children.length; i += 2) {
            panels.push({
                header: node.children[i]?.props?.title || `Panel ${i / 2 + 1}`,
                content: node.children[i + 1] ? [node.children[i + 1]] : []
            });
        }
    }

    // Render panels
    panels.forEach((panel, index) => {
        const panelElement = createPanel(panel, index);
        container.appendChild(panelElement);
    });

    function createPanel(panel, index) {
        const panelContainer = document.createElement('div');
        panelContainer.className = 'quantum-accordion-panel';
        panelContainer.style.borderBottom = index < panels.length - 1 ? '1px solid #ddd' : 'none';

        // Header
        const header = document.createElement('div');
        header.className = 'quantum-accordion-header';
        header.style.padding = '12px 15px';
        header.style.background = 'linear-gradient(to bottom, #ffffff 0%, #e8e8e8 100%)';
        header.style.cursor = 'pointer';
        header.style.userSelect = 'none';
        header.style.display = 'flex';
        header.style.alignItems = 'center';
        header.style.justifyContent = 'space-between';
        header.style.fontWeight = 'bold';
        header.style.fontSize = '13px';
        header.style.transition = 'background 0.2s ease';

        const headerText = document.createElement('span');
        headerText.textContent = panel.header;
        header.appendChild(headerText);

        // Expand indicator
        const indicator = document.createElement('span');
        indicator.className = 'accordion-indicator';
        indicator.textContent = state.expandedPanels.has(index) ? '▼' : '▶';
        indicator.style.fontSize = '10px';
        indicator.style.color = '#666';
        indicator.style.transition = 'transform 0.2s ease';
        header.appendChild(indicator);

        // Content container
        const content = document.createElement('div');
        content.className = 'quantum-accordion-content';
        content.style.overflow = 'hidden';
        content.style.transition = 'max-height 0.3s ease, padding 0.3s ease';
        content.style.backgroundColor = '#ffffff';

        const contentInner = document.createElement('div');
        contentInner.style.padding = '0';

        // Render panel content
        panel.content.forEach(child => {
            const childElement = runtime.renderNode(child);
            contentInner.appendChild(childElement);
        });

        content.appendChild(contentInner);

        // Set initial state
        if (state.expandedPanels.has(index)) {
            content.style.maxHeight = 'none';
            contentInner.style.padding = '15px';
        } else {
            content.style.maxHeight = '0';
            contentInner.style.padding = '0 15px';
        }

        // Toggle handler
        header.addEventListener('click', () => {
            const isExpanded = state.expandedPanels.has(index);

            if (!allowMultipleExpanded) {
                // Collapse all others
                state.expandedPanels.clear();
                container.querySelectorAll('.quantum-accordion-content').forEach((c, i) => {
                    if (i !== index) {
                        c.style.maxHeight = '0';
                        c.querySelector('div').style.padding = '0 15px';
                    }
                });
                container.querySelectorAll('.accordion-indicator').forEach((ind, i) => {
                    if (i !== index) {
                        ind.textContent = '▶';
                    }
                });
            }

            if (isExpanded) {
                // Collapse
                state.expandedPanels.delete(index);
                content.style.maxHeight = '0';
                contentInner.style.padding = '0 15px';
                indicator.textContent = '▶';
            } else {
                // Expand
                state.expandedPanels.add(index);
                content.style.maxHeight = contentInner.scrollHeight + 30 + 'px';
                contentInner.style.padding = '15px';
                indicator.textContent = '▼';

                // Adjust after transition
                setTimeout(() => {
                    if (state.expandedPanels.has(index)) {
                        content.style.maxHeight = 'none';
                    }
                }, 300);
            }

            // Fire change event
            if (node.events.change) {
                const handlerName = node.events.change.replace('()', '');
                if (runtime.app[handlerName]) {
                    runtime.app[handlerName](index, !isExpanded);
                }
            }
        });

        // Hover effect
        header.addEventListener('mouseenter', () => {
            header.style.background = 'linear-gradient(to bottom, #ffffff 0%, #f0f0f0 100%)';
        });

        header.addEventListener('mouseleave', () => {
            header.style.background = 'linear-gradient(to bottom, #ffffff 0%, #e8e8e8 100%)';
        });

        panelContainer.appendChild(header);
        panelContainer.appendChild(content);

        return panelContainer;
    }

    runtime.applyCommonProps(container, node.props);
    return container;
}

/**
 * AccordionHeader - Header for accordion panel
 */
export function renderAccordionHeader(runtime, node) {
    // This is just a placeholder - actual rendering happens in parent Accordion
    const div = document.createElement('div');
    div.style.display = 'none';
    return div;
}
