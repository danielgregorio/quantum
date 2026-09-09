/**
 * Image Component - Display images with loading states
 *
 * Props:
 * - source: Image URL (supports binding)
 * - width: Image width (can be auto, number, or percentage)
 * - height: Image height (can be auto, number, or percentage)
 * - maintainAspectRatio: Maintain aspect ratio (default: true)
 * - scaleMode: How to scale - none/stretch/letterbox/zoom (default: letterbox)
 * - smooth: Enable image smoothing (default: true)
 * - alt: Alt text for accessibility
 * - showBusyCursor: Show loading cursor (default: true)
 *
 * Events:
 * - complete: Fired when image loads successfully
 * - ioError: Fired when image fails to load
 * - progress: Fired during loading (if supported)
 */

export function renderImage(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-image-container';
    container.style.position = 'relative';
    container.style.display = 'inline-block';
    container.style.overflow = 'hidden';

    const maintainAspectRatio = node.props.maintainAspectRatio !== 'false';
    const scaleMode = node.props.scaleMode || 'letterbox';
    const smooth = node.props.smooth !== 'false';
    const showBusyCursor = node.props.showBusyCursor !== 'false';

    // Set container size
    if (node.props.width) {
        const width = node.props.width;
        container.style.width = width.includes('%') || width === 'auto' ? width : width + 'px';
    }

    if (node.props.height) {
        const height = node.props.height;
        container.style.height = height.includes('%') || height === 'auto' ? height : height + 'px';
    }

    // Create image element
    const img = document.createElement('img');
    img.className = 'quantum-image';
    img.style.display = 'block';

    // Apply scale mode
    switch (scaleMode) {
        case 'none':
            img.style.width = 'auto';
            img.style.height = 'auto';
            break;
        case 'stretch':
            img.style.width = '100%';
            img.style.height = '100%';
            img.style.objectFit = 'fill';
            break;
        case 'letterbox':
            img.style.width = '100%';
            img.style.height = '100%';
            img.style.objectFit = 'contain';
            break;
        case 'zoom':
            img.style.width = '100%';
            img.style.height = '100%';
            img.style.objectFit = 'cover';
            break;
        default:
            img.style.width = '100%';
            img.style.height = maintainAspectRatio ? 'auto' : '100%';
    }

    // Image smoothing
    if (!smooth) {
        img.style.imageRendering = 'pixelated';
    }

    // Alt text
    if (node.props.alt) {
        img.alt = node.props.alt;
    }

    // Loading placeholder
    const loadingIndicator = document.createElement('div');
    loadingIndicator.className = 'quantum-image-loading';
    loadingIndicator.style.position = 'absolute';
    loadingIndicator.style.top = '50%';
    loadingIndicator.style.left = '50%';
    loadingIndicator.style.transform = 'translate(-50%, -50%)';
    loadingIndicator.style.fontSize = '32px';
    loadingIndicator.style.color = '#bdc3c7';
    loadingIndicator.textContent = '⏳';
    loadingIndicator.style.display = 'none';

    // Error placeholder
    const errorIndicator = document.createElement('div');
    errorIndicator.className = 'quantum-image-error';
    errorIndicator.style.position = 'absolute';
    errorIndicator.style.top = '50%';
    errorIndicator.style.left = '50%';
    errorIndicator.style.transform = 'translate(-50%, -50%)';
    errorIndicator.style.fontSize = '14px';
    errorIndicator.style.color = '#e74c3c';
    errorIndicator.style.textAlign = 'center';
    errorIndicator.style.padding = '10px';
    errorIndicator.innerHTML = '❌<br>Image load failed';
    errorIndicator.style.display = 'none';

    container.appendChild(img);
    container.appendChild(loadingIndicator);
    container.appendChild(errorIndicator);

    // Load image function
    const loadImage = () => {
        const source = runtime.evaluateBinding(node.props.source || '');

        if (!source) {
            img.style.display = 'none';
            return;
        }

        // Show loading
        loadingIndicator.style.display = 'block';
        errorIndicator.style.display = 'none';
        img.style.display = 'none';

        if (showBusyCursor) {
            container.style.cursor = 'wait';
        }

        // Set source
        img.src = source;
    };

    // Image load success
    img.addEventListener('load', () => {
        loadingIndicator.style.display = 'none';
        img.style.display = 'block';

        if (showBusyCursor) {
            container.style.cursor = 'default';
        }

        // Fire complete event
        if (node.events.complete) {
            const handlerName = node.events.complete.replace(/\(.*?\)/, '');
            if (runtime.app[handlerName]) {
                runtime.app[handlerName]({
                    target: img,
                    width: img.naturalWidth,
                    height: img.naturalHeight
                });
            }
        }
    });

    // Image load error
    img.addEventListener('error', () => {
        loadingIndicator.style.display = 'none';
        errorIndicator.style.display = 'block';
        img.style.display = 'none';

        if (showBusyCursor) {
            container.style.cursor = 'default';
        }

        // Fire ioError event
        if (node.events.ioError) {
            const handlerName = node.events.ioError.replace(/\(.*?\)/, '');
            if (runtime.app[handlerName]) {
                runtime.app[handlerName]({
                    type: 'ioError',
                    text: 'Image load failed'
                });
            }
        }
    });

    // Initial load
    loadImage();

    // Setup reactive binding for source
    if (node.props.source && node.props.source.includes('{')) {
        const varMatch = node.props.source.match(/\{([^}]+)\}/);
        if (varMatch) {
            const varName = varMatch[1].trim().split('.')[0];
            runtime.trackDependency(varName, loadImage);
        }
    }

    runtime.applyCommonProps(container, node.props);
    return container;
}
