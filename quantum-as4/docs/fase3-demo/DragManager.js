/**
 * DragManager - Handles drag and drop operations for Flex components
 *
 * Features:
 * - Drag source tracking
 * - Drop target registration
 * - Drag data transfer
 * - Visual feedback (drag image, drop indicators)
 * - Drag operations: copy, move, link
 *
 * Usage:
 *   DragManager.doDrag(sourceElement, dragData, dragImage, allowedActions)
 *   DragManager.acceptDragDrop(targetElement, dropHandler)
 */

export class DragManager {
    static _instance = null;

    static get instance() {
        if (!DragManager._instance) {
            DragManager._instance = new DragManager();
        }
        return DragManager._instance;
    }

    constructor() {
        this.isDragging = false;
        this.dragSource = null;
        this.dragData = null;
        this.dragImage = null;
        this.currentDropTarget = null;
        this.allowedActions = ['move', 'copy', 'link'];
        this.currentAction = 'move';

        // Drag feedback element
        this.feedbackElement = null;
        this.dropIndicator = null;

        // Event handlers
        this._onMouseMove = this.handleMouseMove.bind(this);
        this._onMouseUp = this.handleMouseUp.bind(this);
    }

    /**
     * Initiate a drag operation
     *
     * @param {HTMLElement} sourceElement - The element being dragged
     * @param {Object} dragData - Data associated with the drag (e.g., {format: 'items', data: [...]})
     * @param {HTMLElement|null} dragImage - Optional custom drag image
     * @param {Array<string>} allowedActions - Allowed drag actions: ['move', 'copy', 'link']
     */
    static doDrag(sourceElement, dragData, dragImage = null, allowedActions = ['move']) {
        const instance = DragManager.instance;

        instance.isDragging = true;
        instance.dragSource = sourceElement;
        instance.dragData = dragData;
        instance.allowedActions = allowedActions;
        instance.currentAction = allowedActions[0];

        // Create drag feedback
        instance.createDragFeedback(dragImage || sourceElement);

        // Add global listeners
        document.addEventListener('mousemove', instance._onMouseMove);
        document.addEventListener('mouseup', instance._onMouseUp);

        // Prevent text selection during drag
        document.body.style.userSelect = 'none';

        // Fire dragStart event
        const event = new CustomEvent('dragStart', {
            detail: { dragData, source: sourceElement }
        });
        sourceElement.dispatchEvent(event);
    }

    /**
     * Register an element as a drop target
     *
     * @param {HTMLElement} targetElement - The drop target element
     * @param {Function} dropHandler - Handler called on drop: (dragData, action) => boolean
     * @param {Function} dragEnterHandler - Optional handler for drag enter
     * @param {Function} dragOverHandler - Optional handler for drag over
     */
    static acceptDragDrop(targetElement, dropHandler, dragEnterHandler = null, dragOverHandler = null) {
        const instance = DragManager.instance;

        targetElement._dropHandler = dropHandler;
        targetElement._dragEnterHandler = dragEnterHandler;
        targetElement._dragOverHandler = dragOverHandler;
        targetElement._isDropTarget = true;

        // Store original background for restoration
        targetElement._originalBackground = targetElement.style.background;
    }

    /**
     * Create visual feedback for dragging
     */
    createDragFeedback(sourceElement) {
        // Create feedback element (follows mouse)
        this.feedbackElement = document.createElement('div');
        this.feedbackElement.className = 'drag-feedback';
        this.feedbackElement.style.position = 'fixed';
        this.feedbackElement.style.pointerEvents = 'none';
        this.feedbackElement.style.opacity = '0.7';
        this.feedbackElement.style.zIndex = '10000';
        this.feedbackElement.style.padding = '8px 12px';
        this.feedbackElement.style.background = 'rgba(51, 153, 255, 0.9)';
        this.feedbackElement.style.color = 'white';
        this.feedbackElement.style.borderRadius = '4px';
        this.feedbackElement.style.boxShadow = '0 4px 8px rgba(0,0,0,0.3)';
        this.feedbackElement.style.fontSize = '12px';
        this.feedbackElement.style.fontWeight = 'bold';

        // Clone source content or use custom text
        const itemCount = this.dragData?.data?.length || 1;
        this.feedbackElement.textContent = `${itemCount} item${itemCount > 1 ? 's' : ''}`;

        document.body.appendChild(this.feedbackElement);
    }

    /**
     * Handle mouse move during drag
     */
    handleMouseMove(e) {
        if (!this.isDragging) return;

        // Update feedback position
        if (this.feedbackElement) {
            this.feedbackElement.style.left = (e.clientX + 10) + 'px';
            this.feedbackElement.style.top = (e.clientY + 10) + 'px';
        }

        // Check for drop targets
        const elementsAtPoint = document.elementsFromPoint(e.clientX, e.clientY);
        const dropTarget = elementsAtPoint.find(el => el._isDropTarget);

        if (dropTarget !== this.currentDropTarget) {
            // Leave previous target
            if (this.currentDropTarget) {
                this.currentDropTarget.style.background = this.currentDropTarget._originalBackground;

                const event = new CustomEvent('dragLeave', {
                    detail: { dragData: this.dragData }
                });
                this.currentDropTarget.dispatchEvent(event);
            }

            // Enter new target
            this.currentDropTarget = dropTarget;

            if (dropTarget) {
                // Visual feedback
                dropTarget.style.background = 'rgba(51, 153, 255, 0.1)';

                // Call handler
                if (dropTarget._dragEnterHandler) {
                    dropTarget._dragEnterHandler(this.dragData);
                }

                const event = new CustomEvent('dragEnter', {
                    detail: { dragData: this.dragData }
                });
                dropTarget.dispatchEvent(event);
            }
        }

        // Drag over
        if (dropTarget && dropTarget._dragOverHandler) {
            dropTarget._dragOverHandler(this.dragData, e);
        }
    }

    /**
     * Handle mouse up (end drag)
     */
    handleMouseUp(e) {
        if (!this.isDragging) return;

        let dropAccepted = false;

        // Process drop
        if (this.currentDropTarget && this.currentDropTarget._dropHandler) {
            dropAccepted = this.currentDropTarget._dropHandler(this.dragData, this.currentAction, e);

            // Restore background
            this.currentDropTarget.style.background = this.currentDropTarget._originalBackground;

            // Fire drop event
            const event = new CustomEvent('dragDrop', {
                detail: {
                    dragData: this.dragData,
                    action: this.currentAction,
                    accepted: dropAccepted
                }
            });
            this.currentDropTarget.dispatchEvent(event);
        }

        // Fire dragComplete on source
        if (this.dragSource) {
            const event = new CustomEvent('dragComplete', {
                detail: {
                    dragData: this.dragData,
                    dropTarget: this.currentDropTarget,
                    action: this.currentAction,
                    accepted: dropAccepted
                }
            });
            this.dragSource.dispatchEvent(event);
        }

        // Cleanup
        this.cleanup();
    }

    /**
     * Cleanup drag operation
     */
    cleanup() {
        // Remove feedback
        if (this.feedbackElement) {
            this.feedbackElement.remove();
            this.feedbackElement = null;
        }

        if (this.dropIndicator) {
            this.dropIndicator.remove();
            this.dropIndicator = null;
        }

        // Restore drop target background
        if (this.currentDropTarget) {
            this.currentDropTarget.style.background = this.currentDropTarget._originalBackground;
        }

        // Remove listeners
        document.removeEventListener('mousemove', this._onMouseMove);
        document.removeEventListener('mouseup', this._onMouseUp);

        // Restore text selection
        document.body.style.userSelect = '';

        // Reset state
        this.isDragging = false;
        this.dragSource = null;
        this.dragData = null;
        this.dragImage = null;
        this.currentDropTarget = null;
    }

    /**
     * Show drop indicator at position
     */
    static showDropIndicator(targetElement, position = 'before') {
        const instance = DragManager.instance;

        if (!instance.dropIndicator) {
            instance.dropIndicator = document.createElement('div');
            instance.dropIndicator.className = 'drop-indicator';
            instance.dropIndicator.style.position = 'absolute';
            instance.dropIndicator.style.width = '100%';
            instance.dropIndicator.style.height = '2px';
            instance.dropIndicator.style.background = '#3399ff';
            instance.dropIndicator.style.pointerEvents = 'none';
            instance.dropIndicator.style.zIndex = '9999';
            document.body.appendChild(instance.dropIndicator);
        }

        const rect = targetElement.getBoundingClientRect();
        instance.dropIndicator.style.left = rect.left + 'px';
        instance.dropIndicator.style.width = rect.width + 'px';

        if (position === 'before') {
            instance.dropIndicator.style.top = rect.top + 'px';
        } else {
            instance.dropIndicator.style.top = (rect.bottom - 2) + 'px';
        }

        instance.dropIndicator.style.display = 'block';
    }

    /**
     * Hide drop indicator
     */
    static hideDropIndicator() {
        const instance = DragManager.instance;
        if (instance.dropIndicator) {
            instance.dropIndicator.style.display = 'none';
        }
    }
}

// Make available globally
if (typeof window !== 'undefined') {
    window.DragManager = DragManager;
}
