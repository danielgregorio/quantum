/**
 * DatePicker Component - Calendar date selection
 *
 * Props:
 * - selectedDate: Selected date as Date object or string (supports bindings)
 * - minDate: Minimum selectable date
 * - maxDate: Maximum selectable date
 * - formatString: Date format for display (default: "MM/DD/YYYY")
 * - enabled: Enable/disable picker (default: true)
 *
 * Events:
 * - change: Fired when date changes (passes Date object)
 */

export function renderDatePicker(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-datepicker';
    container.style.position = 'relative';
    container.style.display = 'inline-block';

    // Input field
    const input = document.createElement('input');
    input.type = 'text';
    input.placeholder = node.props.formatString || 'MM/DD/YYYY';
    input.readOnly = true;
    input.style.padding = '8px 12px';
    input.style.fontSize = '14px';
    input.style.border = '1px solid #ccc';
    input.style.borderRadius = '4px';
    input.style.cursor = 'pointer';
    input.style.minWidth = '150px';
    input.style.backgroundColor = 'white';

    // Calendar icon
    const icon = document.createElement('span');
    icon.textContent = '📅';
    icon.style.position = 'absolute';
    icon.style.right = '10px';
    icon.style.top = '50%';
    icon.style.transform = 'translateY(-50%)';
    icon.style.pointerEvents = 'none';

    container.appendChild(input);
    container.appendChild(icon);

    // Calendar popup
    const calendar = document.createElement('div');
    calendar.className = 'quantum-datepicker-calendar';
    calendar.style.position = 'absolute';
    calendar.style.top = 'calc(100% + 5px)';
    calendar.style.left = '0';
    calendar.style.backgroundColor = 'white';
    calendar.style.border = '1px solid #ccc';
    calendar.style.borderRadius = '4px';
    calendar.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';
    calendar.style.padding = '10px';
    calendar.style.display = 'none';
    calendar.style.zIndex = '1000';
    calendar.style.minWidth = '280px';

    // State
    let selectedDate = null;
    let currentMonth = new Date();
    currentMonth.setDate(1);

    // Parse initial date
    if (node.props.selectedDate) {
        const dateValue = runtime.evaluateBinding(node.props.selectedDate);
        if (dateValue) {
            selectedDate = dateValue instanceof Date ? dateValue : new Date(dateValue);
            currentMonth = new Date(selectedDate);
            currentMonth.setDate(1);
        }
    }

    // Format date for display
    const formatDate = (date) => {
        if (!date) return '';
        const format = node.props.formatString || 'MM/DD/YYYY';
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const year = date.getFullYear();

        return format
            .replace('MM', month)
            .replace('DD', day)
            .replace('YYYY', year);
    };

    // Update input display
    const updateInput = () => {
        input.value = formatDate(selectedDate);
    };

    // Render calendar
    const renderCalendar = () => {
        calendar.innerHTML = '';

        // Header with month/year and navigation
        const header = document.createElement('div');
        header.style.display = 'flex';
        header.style.justifyContent = 'space-between';
        header.style.alignItems = 'center';
        header.style.marginBottom = '10px';

        const prevBtn = document.createElement('button');
        prevBtn.textContent = '◀';
        prevBtn.style.border = 'none';
        prevBtn.style.background = 'none';
        prevBtn.style.cursor = 'pointer';
        prevBtn.style.fontSize = '18px';
        prevBtn.onclick = () => {
            currentMonth.setMonth(currentMonth.getMonth() - 1);
            renderCalendar();
        };

        const monthYear = document.createElement('span');
        monthYear.style.fontWeight = 'bold';
        monthYear.style.fontSize = '16px';
        monthYear.textContent = currentMonth.toLocaleDateString('en-US', {
            month: 'long',
            year: 'numeric'
        });

        const nextBtn = document.createElement('button');
        nextBtn.textContent = '▶';
        nextBtn.style.border = 'none';
        nextBtn.style.background = 'none';
        nextBtn.style.cursor = 'pointer';
        nextBtn.style.fontSize = '18px';
        nextBtn.onclick = () => {
            currentMonth.setMonth(currentMonth.getMonth() + 1);
            renderCalendar();
        };

        header.appendChild(prevBtn);
        header.appendChild(monthYear);
        header.appendChild(nextBtn);
        calendar.appendChild(header);

        // Day names
        const dayNames = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa'];
        const dayNamesRow = document.createElement('div');
        dayNamesRow.style.display = 'grid';
        dayNamesRow.style.gridTemplateColumns = 'repeat(7, 1fr)';
        dayNamesRow.style.gap = '5px';
        dayNamesRow.style.marginBottom = '5px';

        dayNames.forEach(name => {
            const cell = document.createElement('div');
            cell.textContent = name;
            cell.style.textAlign = 'center';
            cell.style.fontWeight = 'bold';
            cell.style.fontSize = '12px';
            cell.style.color = '#666';
            dayNamesRow.appendChild(cell);
        });
        calendar.appendChild(dayNamesRow);

        // Days grid
        const daysGrid = document.createElement('div');
        daysGrid.style.display = 'grid';
        daysGrid.style.gridTemplateColumns = 'repeat(7, 1fr)';
        daysGrid.style.gap = '5px';

        // Get first day of month and number of days
        const firstDay = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
        const lastDay = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0);
        const daysInMonth = lastDay.getDate();
        const startingDayOfWeek = firstDay.getDay();

        // Add empty cells for days before month starts
        for (let i = 0; i < startingDayOfWeek; i++) {
            const cell = document.createElement('div');
            cell.style.padding = '8px';
            daysGrid.appendChild(cell);
        }

        // Add day cells
        for (let day = 1; day <= daysInMonth; day++) {
            const cell = document.createElement('div');
            const date = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);

            cell.textContent = day;
            cell.style.padding = '8px';
            cell.style.textAlign = 'center';
            cell.style.cursor = 'pointer';
            cell.style.borderRadius = '4px';
            cell.style.fontSize = '14px';

            // Highlight selected date
            if (selectedDate &&
                date.toDateString() === selectedDate.toDateString()) {
                cell.style.backgroundColor = '#1976d2';
                cell.style.color = 'white';
                cell.style.fontWeight = 'bold';
            } else {
                cell.style.backgroundColor = '#f5f5f5';
            }

            cell.addEventListener('mouseenter', () => {
                if (!selectedDate || date.toDateString() !== selectedDate.toDateString()) {
                    cell.style.backgroundColor = '#e0e0e0';
                }
            });

            cell.addEventListener('mouseleave', () => {
                if (!selectedDate || date.toDateString() !== selectedDate.toDateString()) {
                    cell.style.backgroundColor = '#f5f5f5';
                }
            });

            cell.addEventListener('click', () => {
                selectedDate = date;
                updateInput();
                calendar.style.display = 'none';

                // Update bound variable
                if (node.props.selectedDate && node.props.selectedDate.includes('{')) {
                    const varMatch = node.props.selectedDate.match(/\{([^}]+)\}/);
                    if (varMatch) {
                        const varName = varMatch[1].trim();
                        runtime.app[varName] = selectedDate;
                    }
                }

                // Fire change event
                if (node.events.change) {
                    const handlerName = node.events.change.replace('()', '');
                    if (runtime.app[handlerName]) {
                        runtime.app[handlerName](selectedDate);
                    }
                }
            });

            daysGrid.appendChild(cell);
        }

        calendar.appendChild(daysGrid);
    };

    // Toggle calendar
    input.addEventListener('click', () => {
        const isVisible = calendar.style.display === 'block';
        calendar.style.display = isVisible ? 'none' : 'block';
        if (!isVisible) {
            renderCalendar();
        }
    });

    // Close calendar when clicking outside
    document.addEventListener('click', (e) => {
        if (!container.contains(e.target)) {
            calendar.style.display = 'none';
        }
    });

    container.appendChild(calendar);

    // Initial update
    updateInput();

    // Two-way binding
    if (node.props.selectedDate && node.props.selectedDate.includes('{')) {
        const varMatch = node.props.selectedDate.match(/\{([^}]+)\}/);
        if (varMatch) {
            const varName = varMatch[1].trim();
            runtime.trackDependency(varName, (newValue) => {
                selectedDate = newValue instanceof Date ? newValue : new Date(newValue);
                updateInput();
            });
        }
    }

    // Handle enabled/disabled
    const enabled = node.props.enabled !== 'false';
    input.disabled = !enabled;
    if (!enabled) {
        input.style.cursor = 'not-allowed';
        input.style.opacity = '0.5';
        icon.style.opacity = '0.5';
    }

    runtime.applyCommonProps(container, node.props);
    return container;
}
