/**
 * ProgressBar Component - Visual progress indicator
 *
 * Props:
 * - value: Current progress value (0-100) - supports binding
 * - maximum: Maximum value (default: 100)
 * - minimum: Minimum value (default: 0)
 * - mode: Display mode - determinate/indeterminate (default: determinate)
 * - label: Custom label text (supports binding, use %1% for value, %2% for max, %3% for percent)
 * - labelPlacement: Label position - center/left/right/top/bottom (default: center)
 * - width: Width in pixels (default: 200)
 * - height: Height in pixels (default: 20)
 * - barColor: Progress bar color (default: #3498db)
 * - trackColor: Track/background color (default: #ecf0f1)
 * - showLabel: Show percentage label (default: true)
 *
 * Events:
 * - complete: Fired when progress reaches maximum
 */

export function renderProgressBar(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-progressbar-container';
    container.style.display = 'flex';
    container.style.flexDirection = 'column';
    container.style.gap = '6px';

    const mode = node.props.mode || 'determinate';
    const minimum = node.props.minimum ? parseFloat(node.props.minimum) : 0;
    const maximum = node.props.maximum ? parseFloat(node.props.maximum) : 100;
    const width = node.props.width ? parseInt(node.props.width) : 200;
    const height = node.props.height ? parseInt(node.props.height) : 20;
    const barColor = node.props.barColor || '#3498db';
    const trackColor = node.props.trackColor || '#ecf0f1';
    const showLabel = node.props.showLabel !== 'false';
    const labelPlacement = node.props.labelPlacement || 'center';

    // Track (background)
    const track = document.createElement('div');
    track.className = 'quantum-progressbar-track';
    track.style.width = width + 'px';
    track.style.height = height + 'px';
    track.style.backgroundColor = trackColor;
    track.style.borderRadius = '10px';
    track.style.overflow = 'hidden';
    track.style.position = 'relative';
    track.style.boxShadow = 'inset 0 1px 2px rgba(0,0,0,0.1)';

    // Bar (progress fill)
    const bar = document.createElement('div');
    bar.className = 'quantum-progressbar-bar';
    bar.style.height = '100%';
    bar.style.backgroundColor = barColor;
    bar.style.borderRadius = '10px';
    bar.style.transition = 'width 0.3s ease';
    bar.style.boxShadow = '0 1px 0 rgba(255,255,255,0.3) inset';

    // Indeterminate animation
    if (mode === 'indeterminate') {
        bar.style.width = '30%';
        bar.style.animation = 'progressbar-indeterminate 1.5s ease-in-out infinite';

        // Add animation keyframes
        if (!document.getElementById('progressbar-animation')) {
            const style = document.createElement('style');
            style.id = 'progressbar-animation';
            style.textContent = `
                @keyframes progressbar-indeterminate {
                    0% { transform: translateX(-100%); }
                    50% { transform: translateX(400%); }
                    100% { transform: translateX(-100%); }
                }
            `;
            document.head.appendChild(style);
        }
    }

    // Label
    const label = document.createElement('div');
    label.className = 'quantum-progressbar-label';
    label.style.fontSize = '12px';
    label.style.fontWeight = '500';
    label.style.color = '#333';
    label.style.textAlign = 'center';
    label.style.userSelect = 'none';

    // Label on bar
    const barLabel = document.createElement('div');
    barLabel.style.position = 'absolute';
    barLabel.style.top = '0';
    barLabel.style.left = '0';
    barLabel.style.right = '0';
    barLabel.style.bottom = '0';
    barLabel.style.display = 'flex';
    barLabel.style.alignItems = 'center';
    barLabel.style.justifyContent = 'center';
    barLabel.style.fontSize = '11px';
    barLabel.style.fontWeight = 'bold';
    barLabel.style.color = '#ffffff';
    barLabel.style.textShadow = '0 1px 2px rgba(0,0,0,0.3)';
    barLabel.style.pointerEvents = 'none';

    track.appendChild(bar);

    if (showLabel && labelPlacement === 'center') {
        track.appendChild(barLabel);
    }

    // Update function
    const updateProgress = () => {
        if (mode === 'indeterminate') {
            return; // No value update needed for indeterminate
        }

        // Get value with binding support
        let value = 0;
        if (node.props.value) {
            value = parseFloat(runtime.evaluateBinding(node.props.value));
        }

        // Clamp value
        value = Math.max(minimum, Math.min(maximum, value));

        // Calculate percentage
        const range = maximum - minimum;
        const percent = range > 0 ? ((value - minimum) / range) * 100 : 0;

        // Update bar width
        bar.style.width = percent + '%';

        // Update label
        if (showLabel) {
            let labelText = node.props.label || '%3%%';

            // Replace tokens
            labelText = labelText.replace('%1%', value.toString());
            labelText = labelText.replace('%2%', maximum.toString());
            labelText = labelText.replace('%3%', Math.round(percent).toString());

            if (labelPlacement === 'center') {
                barLabel.textContent = labelText;
            } else {
                label.textContent = labelText;
            }
        }

        // Fire complete event if reached maximum
        if (value >= maximum && node.events.complete) {
            const handlerName = node.events.complete.replace(/\(.*?\)/, '');
            if (runtime.app[handlerName]) {
                runtime.app[handlerName]({ value, maximum });
            }
        }
    };

    // Initial update
    updateProgress();

    // Setup reactive binding for value
    if (node.props.value && node.props.value.includes('{')) {
        const varMatch = node.props.value.match(/\{([^}]+)\}/);
        if (varMatch) {
            const varName = varMatch[1].trim().split('.')[0];
            runtime.trackDependency(varName, updateProgress);
        }
    }

    // Layout based on labelPlacement
    if (labelPlacement === 'top' && showLabel) {
        container.appendChild(label);
        container.appendChild(track);
    } else if (labelPlacement === 'bottom' && showLabel) {
        container.appendChild(track);
        container.appendChild(label);
    } else if (labelPlacement === 'left' && showLabel) {
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.alignItems = 'center';
        row.style.gap = '10px';
        label.style.textAlign = 'right';
        label.style.minWidth = '60px';
        row.appendChild(label);
        row.appendChild(track);
        container.appendChild(row);
    } else if (labelPlacement === 'right' && showLabel) {
        const row = document.createElement('div');
        row.style.display = 'flex';
        row.style.alignItems = 'center';
        row.style.gap = '10px';
        label.style.textAlign = 'left';
        label.style.minWidth = '60px';
        row.appendChild(track);
        row.appendChild(label);
        container.appendChild(row);
    } else {
        container.appendChild(track);
    }

    runtime.applyCommonProps(container, node.props);
    return container;
}
