/**
 * Modal Component - Dialog/Popup overlay
 *
 * Props:
 * - title: Modal title
 * - visible: Show/hide modal (supports bindings)
 * - width: Modal width (default: 500px)
 * - height: Modal height (default: auto)
 * - closeButton: Show close button (default: true)
 * - overlay: Show overlay background (default: true)
 * - centered: Center modal on screen (default: true)
 *
 * Events:
 * - close: Fired when modal is closed
 * - open: Fired when modal is opened
 */

export function renderModal(runtime, node) {
    // Modal overlay (backdrop)
    const overlay = document.createElement('div');
    overlay.className = 'quantum-modal-overlay';
    overlay.style.position = 'fixed';
    overlay.style.top = '0';
    overlay.style.left = '0';
    overlay.style.width = '100%';
    overlay.style.height = '100%';
    overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
    overlay.style.display = 'none';
    overlay.style.zIndex = '1000';
    overlay.style.justifyContent = 'center';
    overlay.style.alignItems = 'center';

    // Modal container
    const modal = document.createElement('div');
    modal.className = 'quantum-modal';
    modal.style.backgroundColor = 'white';
    modal.style.borderRadius = '8px';
    modal.style.boxShadow = '0 4px 20px rgba(0,0,0,0.3)';
    modal.style.maxWidth = '90%';
    modal.style.maxHeight = '90%';
    modal.style.display = 'flex';
    modal.style.flexDirection = 'column';
    modal.style.overflow = 'hidden';

    // Set width
    const width = node.props.width || '500px';
    modal.style.width = width;

    // Set height
    if (node.props.height) {
        modal.style.height = node.props.height;
    }

    // Modal header
    const header = document.createElement('div');
    header.className = 'quantum-modal-header';
    header.style.padding = '20px';
    header.style.borderBottom = '1px solid #eee';
    header.style.display = 'flex';
    header.style.justifyContent = 'space-between';
    header.style.alignItems = 'center';

    const title = document.createElement('h3');
    title.style.margin = '0';
    title.style.fontSize = '20px';
    title.style.fontWeight = 'bold';

    // Setup reactive binding for title
    if (node.props.title) {
        runtime.createReactiveBinding(title, node.props.title, 'textContent');
    }

    header.appendChild(title);

    // Close button
    const closeButton = node.props.closeButton !== 'false';
    if (closeButton) {
        const closeBtn = document.createElement('button');
        closeBtn.textContent = '✕';
        closeBtn.style.border = 'none';
        closeBtn.style.background = 'none';
        closeBtn.style.fontSize = '24px';
        closeBtn.style.cursor = 'pointer';
        closeBtn.style.color = '#999';
        closeBtn.style.padding = '0';
        closeBtn.style.width = '30px';
        closeBtn.style.height = '30px';

        closeBtn.addEventListener('mouseenter', () => {
            closeBtn.style.color = '#333';
        });

        closeBtn.addEventListener('mouseleave', () => {
            closeBtn.style.color = '#999';
        });

        closeBtn.addEventListener('click', () => {
            closeModal();
        });

        header.appendChild(closeBtn);
    }

    modal.appendChild(header);

    // Modal body
    const body = document.createElement('div');
    body.className = 'quantum-modal-body';
    body.style.padding = '20px';
    body.style.flex = '1';
    body.style.overflow = 'auto';

    // Render children into body
    node.children.forEach(child => {
        body.appendChild(runtime.renderComponent(child));
    });

    modal.appendChild(body);

    // Add modal to overlay
    overlay.appendChild(modal);

    // Functions to open/close modal
    const openModal = () => {
        overlay.style.display = 'flex';
        document.body.style.overflow = 'hidden'; // Prevent body scroll

        // Fire open event
        if (node.events.open) {
            const handlerName = node.events.open.replace('()', '');
            if (runtime.app[handlerName]) {
                runtime.app[handlerName]();
            }
        }
    };

    const closeModal = () => {
        overlay.style.display = 'none';
        document.body.style.overflow = ''; // Restore body scroll

        // Update binding if exists
        if (visibleBinding) {
            runtime.app[visibleBinding] = false;
        }

        // Fire close event
        if (node.events.close) {
            const handlerName = node.events.close.replace('()', '');
            if (runtime.app[handlerName]) {
                runtime.app[handlerName]();
            }
        }
    };

    // Close on overlay click (not on modal click)
    const overlayClickable = node.props.overlayClose !== 'false';
    if (overlayClickable) {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                closeModal();
            }
        });
    }

    // Close on Escape key
    const escapeToClose = node.props.escapeToClose !== 'false';
    if (escapeToClose) {
        const handleEscape = (e) => {
            if (e.key === 'Escape' && overlay.style.display === 'flex') {
                closeModal();
            }
        };
        document.addEventListener('keydown', handleEscape);
    }

    // Handle visible prop (binding support)
    let visibleBinding = null;
    if (node.props.visible) {
        const isVisible = runtime.evaluateBinding(node.props.visible);

        if (isVisible === true || isVisible === 'true') {
            openModal();
        }

        // Setup reactive binding for visible
        if (node.props.visible.includes('{')) {
            const varMatch = node.props.visible.match(/\{([^}]+)\}/);
            if (varMatch) {
                visibleBinding = varMatch[1].trim();
                runtime.trackDependency(visibleBinding, (newValue) => {
                    if (newValue === true || newValue === 'true') {
                        openModal();
                    } else {
                        closeModal();
                    }
                });
            }
        }
    }

    // Expose modal control functions on runtime (for programmatic control)
    if (!runtime.modals) {
        runtime.modals = {};
    }

    const modalId = node.props.id || `modal_${Date.now()}`;
    runtime.modals[modalId] = {
        open: openModal,
        close: closeModal
    };

    // Add to document body (modals should be top-level)
    document.body.appendChild(overlay);

    // Return a placeholder (since modal is in body)
    const placeholder = document.createElement('div');
    placeholder.style.display = 'none';
    placeholder.setAttribute('data-modal-id', modalId);

    return placeholder;
}
