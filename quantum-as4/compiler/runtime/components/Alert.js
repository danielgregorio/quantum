/**
 * Alert Component - Modal dialog boxes
 *
 * Static methods:
 * - Alert.show(text, title, flags, parent, closeHandler, iconClass)
 *
 * Flags (can be combined with |):
 * - Alert.OK (4) - OK button
 * - Alert.CANCEL (8) - Cancel button
 * - Alert.YES (1) - Yes button
 * - Alert.NO (2) - No button
 * - Alert.NONMODAL (0x8000) - Non-blocking alert
 *
 * Icon classes:
 * - Alert.INFO - Information icon
 * - Alert.WARNING - Warning icon
 * - Alert.ERROR - Error icon
 * - Alert.QUESTION - Question icon
 *
 * Usage:
 * Alert.show("Are you sure?", "Confirm", Alert.YES | Alert.NO, null, handleClose);
 */

export class Alert {
    // Button flags
    static YES = 1;
    static NO = 2;
    static OK = 4;
    static CANCEL = 8;
    static NONMODAL = 0x8000;

    // Icon types
    static INFO = 'info';
    static WARNING = 'warning';
    static ERROR = 'error';
    static QUESTION = 'question';

    /**
     * Show alert dialog
     * @param {string} text - Alert message
     * @param {string} title - Alert title (default: "Alert")
     * @param {number} flags - Button flags (default: Alert.OK)
     * @param {HTMLElement} parent - Parent element (default: document.body)
     * @param {Function} closeHandler - Close handler function(event)
     * @param {string} iconClass - Icon type (default: Alert.INFO)
     */
    static show(text, title = "Alert", flags = Alert.OK, parent = null, closeHandler = null, iconClass = Alert.INFO) {
        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'quantum-alert-overlay';
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.right = '0';
        overlay.style.bottom = '0';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        overlay.style.display = 'flex';
        overlay.style.alignItems = 'center';
        overlay.style.justifyContent = 'center';
        overlay.style.zIndex = '10000';
        overlay.style.animation = 'fadeIn 0.2s ease';

        // Create dialog
        const dialog = document.createElement('div');
        dialog.className = 'quantum-alert-dialog';
        dialog.style.backgroundColor = '#ffffff';
        dialog.style.borderRadius = '8px';
        dialog.style.boxShadow = '0 10px 40px rgba(0,0,0,0.3)';
        dialog.style.minWidth = '300px';
        dialog.style.maxWidth = '500px';
        dialog.style.overflow = 'hidden';
        dialog.style.animation = 'slideDown 0.3s ease';

        // Header
        const header = document.createElement('div');
        header.className = 'quantum-alert-header';
        header.style.padding = '15px 20px';
        header.style.background = 'linear-gradient(to bottom, #ffffff 0%, #f5f5f5 100%)';
        header.style.borderBottom = '1px solid #ddd';
        header.style.fontSize = '16px';
        header.style.fontWeight = 'bold';
        header.style.color = '#2c3e50';
        header.textContent = title;

        // Body
        const body = document.createElement('div');
        body.className = 'quantum-alert-body';
        body.style.padding = '20px';
        body.style.display = 'flex';
        body.style.gap = '15px';
        body.style.alignItems = 'flex-start';

        // Icon
        const iconMap = {
            [Alert.INFO]: { icon: 'ℹ️', color: '#3498db' },
            [Alert.WARNING]: { icon: '⚠️', color: '#f39c12' },
            [Alert.ERROR]: { icon: '❌', color: '#e74c3c' },
            [Alert.QUESTION]: { icon: '❓', color: '#9b59b6' }
        };

        const iconData = iconMap[iconClass] || iconMap[Alert.INFO];

        const icon = document.createElement('div');
        icon.style.fontSize = '32px';
        icon.style.flexShrink = '0';
        icon.textContent = iconData.icon;

        // Message
        const message = document.createElement('div');
        message.className = 'quantum-alert-message';
        message.style.flex = '1';
        message.style.fontSize = '14px';
        message.style.lineHeight = '1.6';
        message.style.color = '#555';
        message.style.paddingTop = '5px';
        message.textContent = text;

        body.appendChild(icon);
        body.appendChild(message);

        // Footer with buttons
        const footer = document.createElement('div');
        footer.className = 'quantum-alert-footer';
        footer.style.padding = '15px 20px';
        footer.style.background = '#f9f9f9';
        footer.style.borderTop = '1px solid #ddd';
        footer.style.display = 'flex';
        footer.style.justifyContent = 'flex-end';
        footer.style.gap = '10px';

        // Close function
        const closeDialog = (event) => {
            overlay.style.animation = 'fadeOut 0.2s ease';
            setTimeout(() => {
                overlay.remove();
            }, 200);

            if (closeHandler) {
                closeHandler(event);
            }
        };

        // Create buttons based on flags
        const createButton = (label, detail) => {
            const button = document.createElement('button');
            button.className = 'quantum-button quantum-alert-button';
            button.textContent = label;
            button.style.minWidth = '80px';
            button.addEventListener('click', () => {
                closeDialog({ detail });
            });
            return button;
        };

        if (flags & Alert.YES) {
            footer.appendChild(createButton('Yes', Alert.YES));
        }

        if (flags & Alert.NO) {
            footer.appendChild(createButton('No', Alert.NO));
        }

        if (flags & Alert.OK) {
            footer.appendChild(createButton('OK', Alert.OK));
        }

        if (flags & Alert.CANCEL) {
            footer.appendChild(createButton('Cancel', Alert.CANCEL));
        }

        // If no buttons specified, add OK by default
        if (!(flags & (Alert.YES | Alert.NO | Alert.OK | Alert.CANCEL))) {
            footer.appendChild(createButton('OK', Alert.OK));
        }

        // Assemble dialog
        dialog.appendChild(header);
        dialog.appendChild(body);
        dialog.appendChild(footer);
        overlay.appendChild(dialog);

        // Close on overlay click (for non-modal)
        if (flags & Alert.NONMODAL) {
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    closeDialog({ detail: Alert.CANCEL });
                }
            });
        }

        // Close on ESC key
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                closeDialog({ detail: Alert.CANCEL });
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);

        // Add to DOM
        const parentElement = parent || document.body;
        parentElement.appendChild(overlay);

        // Add animations if not already in document
        if (!document.getElementById('alert-animations')) {
            const style = document.createElement('style');
            style.id = 'alert-animations';
            style.textContent = `
                @keyframes fadeIn {
                    from { opacity: 0; }
                    to { opacity: 1; }
                }
                @keyframes fadeOut {
                    from { opacity: 1; }
                    to { opacity: 0; }
                }
                @keyframes slideDown {
                    from {
                        opacity: 0;
                        transform: translateY(-20px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }
            `;
            document.head.appendChild(style);
        }

        return overlay;
    }
}

/**
 * Render Alert component (for MXML usage - though Alert is typically used via Alert.show())
 */
export function renderAlert(runtime, node) {
    // Alert is typically used via Alert.show() static method
    // This is just a placeholder for MXML compatibility
    const placeholder = document.createComment('Alert component (use Alert.show() in code)');

    // Make Alert class available in runtime
    if (runtime.app && !runtime.app.Alert) {
        runtime.app.Alert = Alert;
    }

    // Make Alert available globally
    if (typeof window !== 'undefined' && !window.Alert) {
        window.Alert = Alert;
    }

    return placeholder;
}
