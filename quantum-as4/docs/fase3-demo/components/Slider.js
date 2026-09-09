/**
 * Slider Component
 *
 * A draggable slider control for selecting numeric values.
 * Compatible with Adobe Flex HSlider and VSlider API.
 *
 * Features:
 * - Horizontal and vertical orientations
 * - Draggable thumb with track
 * - Min/max value constraints
 * - Snap interval for discrete values
 * - Live dragging or change on release
 * - Optional tick marks and labels
 * - Change event on value updates
 * - Reactive binding support
 *
 * @example
 * <s:HSlider id="volume"
 *            value="{volume}"
 *            minimum="0"
 *            maximum="100"
 *            snapInterval="1"
 *            liveDragging="true"
 *            change="handleVolumeChange(event)" />
 */

export function renderSlider(runtime, node) {
    const container = document.createElement('div');
    const sliderId = node.props.id || `slider_${Date.now()}`;

    // Determine orientation from tag name
    const isVertical = node.tagName === 'VSlider';
    const direction = node.props.direction || (isVertical ? 'vertical' : 'horizontal');
    const isVerticalSlider = direction === 'vertical';

    // Parse properties
    let value = parseFloat(node.props.value || '0');
    const minimum = parseFloat(node.props.minimum || '0');
    const maximum = parseFloat(node.props.maximum || '100');
    const snapInterval = parseFloat(node.props.snapInterval || '0');
    const liveDragging = node.props.liveDragging === 'true';
    const showDataTip = node.props.showDataTip !== 'false';
    const enabled = node.props.enabled !== 'false';

    // Size properties
    const width = node.props.width ? parseInt(node.props.width) : (isVerticalSlider ? 20 : 200);
    const height = node.props.height ? parseInt(node.props.height) : (isVerticalSlider ? 200 : 20);

    // Container styling
    container.className = `slider ${isVerticalSlider ? 'vertical' : 'horizontal'}`;
    container.style.position = 'relative';
    container.style.width = width + 'px';
    container.style.height = height + 'px';
    container.style.display = 'inline-block';
    container.style.opacity = enabled ? '1' : '0.5';
    container.style.cursor = enabled ? 'pointer' : 'not-allowed';

    // Track (background rail)
    const track = document.createElement('div');
    track.className = 'slider-track';
    track.style.position = 'absolute';
    track.style.backgroundColor = '#c0c0c0';
    track.style.border = '1px solid #999999';
    track.style.borderRadius = '2px';

    if (isVerticalSlider) {
        track.style.width = '8px';
        track.style.height = '100%';
        track.style.left = '50%';
        track.style.transform = 'translateX(-50%)';
    } else {
        track.style.width = '100%';
        track.style.height = '8px';
        track.style.top = '50%';
        track.style.transform = 'translateY(-50%)';
    }

    // Fill track (shows progress)
    const fillTrack = document.createElement('div');
    fillTrack.className = 'slider-fill';
    fillTrack.style.position = 'absolute';
    fillTrack.style.backgroundColor = '#0b6fcc';
    fillTrack.style.borderRadius = '2px';

    if (isVerticalSlider) {
        fillTrack.style.width = '100%';
        fillTrack.style.bottom = '0';
    } else {
        fillTrack.style.height = '100%';
        fillTrack.style.left = '0';
    }

    track.appendChild(fillTrack);

    // Thumb (draggable button)
    const thumb = document.createElement('div');
    thumb.className = 'slider-thumb';
    thumb.style.position = 'absolute';
    thumb.style.width = '14px';
    thumb.style.height = '14px';
    thumb.style.backgroundColor = '#f0f0f0';
    thumb.style.border = '1px solid #666666';
    thumb.style.borderRadius = '3px';
    thumb.style.cursor = enabled ? 'grab' : 'not-allowed';
    thumb.style.boxShadow = '0 1px 3px rgba(0,0,0,0.3)';
    thumb.style.zIndex = '10';

    if (isVerticalSlider) {
        thumb.style.left = '50%';
        thumb.style.transform = 'translate(-50%, 50%)';
    } else {
        thumb.style.top = '50%';
        thumb.style.transform = 'translate(-50%, -50%)';
    }

    // Data tip (shows current value)
    const dataTip = document.createElement('div');
    dataTip.className = 'slider-datatip';
    dataTip.style.position = 'absolute';
    dataTip.style.backgroundColor = '#333333';
    dataTip.style.color = 'white';
    dataTip.style.padding = '2px 6px';
    dataTip.style.borderRadius = '3px';
    dataTip.style.fontSize = '11px';
    dataTip.style.whiteSpace = 'nowrap';
    dataTip.style.pointerEvents = 'none';
    dataTip.style.display = 'none';
    dataTip.style.zIndex = '20';

    if (isVerticalSlider) {
        dataTip.style.left = '100%';
        dataTip.style.marginLeft = '8px';
        dataTip.style.top = '50%';
        dataTip.style.transform = 'translateY(-50%)';
    } else {
        dataTip.style.top = '-25px';
        dataTip.style.left = '50%';
        dataTip.style.transform = 'translateX(-50%)';
    }

    thumb.appendChild(dataTip);

    // Constrain value to min/max
    const constrainValue = (val) => {
        val = Math.max(minimum, Math.min(maximum, val));

        // Apply snap interval
        if (snapInterval > 0) {
            val = Math.round(val / snapInterval) * snapInterval;
        }

        return val;
    };

    // Convert position to value
    const positionToValue = (pos) => {
        const range = maximum - minimum;
        let percent;

        if (isVerticalSlider) {
            const trackHeight = track.offsetHeight;
            percent = 1 - (pos / trackHeight);
        } else {
            const trackWidth = track.offsetWidth;
            percent = pos / trackWidth;
        }

        percent = Math.max(0, Math.min(1, percent));
        return constrainValue(minimum + (range * percent));
    };

    // Update thumb position based on value
    const updateThumbPosition = () => {
        const range = maximum - minimum;
        const percent = (value - minimum) / range;

        if (isVerticalSlider) {
            const trackHeight = track.offsetHeight;
            const position = trackHeight * (1 - percent);
            thumb.style.bottom = (position - 7) + 'px';
            fillTrack.style.height = (percent * 100) + '%';
        } else {
            const trackWidth = track.offsetWidth;
            const position = trackWidth * percent;
            thumb.style.left = position + 'px';
            fillTrack.style.width = (percent * 100) + '%';
        }

        dataTip.textContent = Math.round(value * 100) / 100;
    };

    // Fire change event
    const fireChangeEvent = (newValue, isDragging = false) => {
        // Only fire during drag if liveDragging is enabled
        if (isDragging && !liveDragging) {
            return;
        }

        // Update reactive binding
        if (node.props.value && node.props.value.includes('{')) {
            const bindingPath = node.props.value.replace(/[{}]/g, '');
            const pathParts = bindingPath.split('.');

            if (pathParts.length === 1) {
                runtime.app[pathParts[0]] = newValue;
            } else {
                let obj = runtime.app;
                for (let i = 0; i < pathParts.length - 1; i++) {
                    obj = obj[pathParts[i]];
                }
                obj[pathParts[pathParts.length - 1]] = newValue;
            }
        }

        // Fire change event handler
        if (node.events && node.events.change) {
            const handlerName = node.events.change.replace(/[()]/g, '');
            if (runtime.app[handlerName]) {
                runtime.app[handlerName]({
                    type: 'change',
                    target: container,
                    value: newValue,
                    thumbPress: isDragging
                });
            }
        }
    };

    // Drag handling
    let isDragging = false;
    let lastValue = value;

    const startDrag = (e) => {
        if (!enabled) return;

        isDragging = true;
        lastValue = value;
        thumb.style.cursor = 'grabbing';

        if (showDataTip) {
            dataTip.style.display = 'block';
        }

        e.preventDefault();
    };

    const doDrag = (e) => {
        if (!isDragging || !enabled) return;

        const rect = track.getBoundingClientRect();
        let pos;

        if (isVerticalSlider) {
            pos = e.clientY - rect.top;
        } else {
            pos = e.clientX - rect.left;
        }

        const newValue = positionToValue(pos);

        if (newValue !== value) {
            value = newValue;
            updateThumbPosition();
            fireChangeEvent(value, true);
        }

        e.preventDefault();
    };

    const endDrag = () => {
        if (!isDragging || !enabled) return;

        isDragging = false;
        thumb.style.cursor = 'grab';
        dataTip.style.display = 'none';

        // Fire final change event if not live dragging
        if (!liveDragging && value !== lastValue) {
            fireChangeEvent(value, false);
        }
    };

    // Mouse events
    thumb.addEventListener('mousedown', startDrag);
    document.addEventListener('mousemove', doDrag);
    document.addEventListener('mouseup', endDrag);

    // Click on track to jump to position
    track.addEventListener('click', (e) => {
        if (!enabled || e.target === thumb) return;

        const rect = track.getBoundingClientRect();
        let pos;

        if (isVerticalSlider) {
            pos = e.clientY - rect.top;
        } else {
            pos = e.clientX - rect.left;
        }

        const newValue = positionToValue(pos);

        if (newValue !== value) {
            value = newValue;
            updateThumbPosition();
            fireChangeEvent(value, false);
        }
    });

    // Setup reactive binding
    if (node.props.value && node.props.value.includes('{')) {
        const bindingPath = node.props.value.replace(/[{}]/g, '');

        runtime.addBinding(bindingPath, () => {
            const newValue = constrainValue(runtime.evaluateBinding(node.props.value));
            if (newValue !== value && !isDragging) {
                value = newValue;
                updateThumbPosition();
            }
        });
    }

    // Initial position
    value = constrainValue(value);
    updateThumbPosition();

    // Assemble component
    container.appendChild(track);
    container.appendChild(thumb);

    // Store reference if ID provided
    if (node.props.id) {
        runtime.app[node.props.id] = {
            element: container,
            getValue: () => value,
            setValue: (newValue) => {
                value = constrainValue(newValue);
                updateThumbPosition();
                fireChangeEvent(value, false);
            },
            getMinimum: () => minimum,
            getMaximum: () => maximum
        };
    }

    return container;
}

// Export both HSlider and VSlider (they use the same implementation)
export const renderHSlider = renderSlider;
export const renderVSlider = renderSlider;
