/**
 * Advanced DataGrid Component - Enhanced table with column resizing, inline editing
 *
 * Props:
 * - dataProvider: Array of objects to display (supports bindings)
 * - columns: Array of column definitions [{field, header, width, sortable, editable, type}]
 * - sortable: Enable sorting (default: true)
 * - filterable: Enable filtering (default: false)
 * - pageSize: Items per page for pagination (default: no pagination)
 * - selectable: Enable row selection (default: false)
 * - editable: Enable inline editing (default: false)
 * - resizableColumns: Enable column resizing (default: false)
 * - dragEnabled: Enable row dragging (default: false)
 *
 * Events:
 * - itemClick: Fired when row is clicked
 * - selectionChange: Fired when selection changes
 * - cellEdit: Fired when cell is edited (passes {item, field, oldValue, newValue})
 * - rowsReordered: Fired when rows are reordered via drag
 */

import { DragManager } from '../DragManager.js';

export function renderDataGridAdvanced(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-datagrid-container quantum-datagrid-advanced';

    // Get data provider (can be binding)
    const dataProviderExpr = node.props.dataProvider;
    let data = [];

    if (dataProviderExpr) {
        data = runtime.evaluateBinding(dataProviderExpr);
        if (!Array.isArray(data)) data = [];
    }

    // Get columns
    const columnsExpr = node.props.columns;
    let columns = columnsExpr ? runtime.evaluateBinding(columnsExpr) : [];

    // Auto-generate columns from first data item if not specified
    if (columns.length === 0 && data.length > 0) {
        columns = Object.keys(data[0]).map(key => ({
            field: key,
            header: key.charAt(0).toUpperCase() + key.slice(1),
            sortable: true,
            editable: false,
            type: 'text',
            width: 150
        }));
    }

    // State
    const state = {
        sortField: null,
        sortDirection: 'asc',
        filterText: '',
        currentPage: 0,
        selectedRows: new Set(),
        editingCell: null,
        columnWidths: {},
        resizingColumn: null
    };

    // Initialize column widths
    columns.forEach(col => {
        state.columnWidths[col.field] = col.width || 150;
    });

    const pageSize = node.props.pageSize ? parseInt(node.props.pageSize) : null;
    const sortable = node.props.sortable !== 'false';
    const filterable = node.props.filterable === 'true';
    const selectable = node.props.selectable === 'true';
    const editable = node.props.editable === 'true';
    const resizableColumns = node.props.resizableColumns === 'true';
    const dragEnabled = node.props.dragEnabled === 'true';

    // Create filter input if enabled
    if (filterable) {
        const filterBox = document.createElement('input');
        filterBox.type = 'text';
        filterBox.placeholder = 'Filter...';
        filterBox.className = 'quantum-datagrid-filter';
        filterBox.style.marginBottom = '10px';
        filterBox.style.padding = '8px';
        filterBox.style.width = '200px';
        filterBox.addEventListener('input', (e) => {
            state.filterText = e.target.value.toLowerCase();
            state.currentPage = 0;
            updateTable();
        });
        container.appendChild(filterBox);
    }

    // Create table wrapper for scrolling
    const tableWrapper = document.createElement('div');
    tableWrapper.className = 'quantum-datagrid-wrapper';
    tableWrapper.style.overflowX = 'auto';
    tableWrapper.style.position = 'relative';

    // Create table
    const table = document.createElement('table');
    table.className = 'quantum-datagrid quantum-datagrid-resizable';
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';
    table.style.position = 'relative';

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');

    // Create headers with resizing
    columns.forEach((col, colIndex) => {
        const th = document.createElement('th');
        th.style.padding = '12px';
        th.style.textAlign = 'left';
        th.style.backgroundColor = '#f0f0f0';
        th.style.borderBottom = '2px solid #ddd';
        th.style.position = 'relative';
        th.style.width = state.columnWidths[col.field] + 'px';
        th.style.minWidth = '50px';

        const headerContent = document.createElement('div');
        headerContent.style.display = 'flex';
        headerContent.style.alignItems = 'center';
        headerContent.style.justifyContent = 'space-between';

        const headerText = document.createElement('span');
        headerText.textContent = col.header || col.field;
        headerContent.appendChild(headerText);

        // Add sorting
        if (sortable && col.sortable !== false) {
            th.style.cursor = 'pointer';
            th.style.userSelect = 'none';
            headerText.addEventListener('click', () => {
                if (state.sortField === col.field) {
                    state.sortDirection = state.sortDirection === 'asc' ? 'desc' : 'asc';
                } else {
                    state.sortField = col.field;
                    state.sortDirection = 'asc';
                }
                updateTable();
            });

            const sortIndicator = document.createElement('span');
            sortIndicator.className = 'sort-indicator';
            sortIndicator.style.marginLeft = '5px';
            sortIndicator.style.color = '#666';
            headerContent.appendChild(sortIndicator);
        }

        th.appendChild(headerContent);

        // Add column resizer
        if (resizableColumns) {
            const resizer = document.createElement('div');
            resizer.className = 'column-resizer';
            resizer.style.position = 'absolute';
            resizer.style.right = '0';
            resizer.style.top = '0';
            resizer.style.bottom = '0';
            resizer.style.width = '5px';
            resizer.style.cursor = 'col-resize';
            resizer.style.userSelect = 'none';
            resizer.style.zIndex = '1';

            resizer.addEventListener('mouseenter', () => {
                resizer.style.background = 'rgba(51, 153, 255, 0.3)';
            });

            resizer.addEventListener('mouseleave', () => {
                if (!state.resizingColumn) {
                    resizer.style.background = '';
                }
            });

            resizer.addEventListener('mousedown', (e) => {
                e.preventDefault();
                e.stopPropagation();

                const startX = e.clientX;
                const startWidth = state.columnWidths[col.field];

                state.resizingColumn = { col, th, startX, startWidth };

                const onMouseMove = (e) => {
                    const delta = e.clientX - startX;
                    const newWidth = Math.max(50, startWidth + delta);
                    state.columnWidths[col.field] = newWidth;
                    th.style.width = newWidth + 'px';

                    // Update all cells in this column
                    const colCells = tbody.querySelectorAll(`td:nth-child(${colIndex + 1})`);
                    colCells.forEach(cell => {
                        cell.style.width = newWidth + 'px';
                    });
                };

                const onMouseUp = () => {
                    state.resizingColumn = null;
                    resizer.style.background = '';
                    document.removeEventListener('mousemove', onMouseMove);
                    document.removeEventListener('mouseup', onMouseUp);
                };

                document.addEventListener('mousemove', onMouseMove);
                document.addEventListener('mouseup', onMouseUp);
            });

            th.appendChild(resizer);
        }

        headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    table.appendChild(tbody);

    tableWrapper.appendChild(table);
    container.appendChild(tableWrapper);

    // Pagination controls
    let paginationDiv = null;
    if (pageSize) {
        paginationDiv = document.createElement('div');
        paginationDiv.className = 'quantum-datagrid-pagination';
        paginationDiv.style.marginTop = '10px';
        paginationDiv.style.display = 'flex';
        paginationDiv.style.alignItems = 'center';
        paginationDiv.style.gap = '10px';
        container.appendChild(paginationDiv);
    }

    // Update table function
    const updateTable = () => {
        let processedData = [...data];

        // Apply filtering
        if (state.filterText) {
            processedData = processedData.filter(item => {
                return columns.some(col => {
                    const value = item[col.field];
                    return value && value.toString().toLowerCase().includes(state.filterText);
                });
            });
        }

        // Apply sorting
        if (state.sortField) {
            processedData.sort((a, b) => {
                const aVal = a[state.sortField];
                const bVal = b[state.sortField];
                const comparison = aVal < bVal ? -1 : aVal > bVal ? 1 : 0;
                return state.sortDirection === 'asc' ? comparison : -comparison;
            });
        }

        // Calculate pagination
        const totalPages = pageSize ? Math.ceil(processedData.length / pageSize) : 1;
        const totalItems = processedData.length;

        // Apply pagination
        if (pageSize) {
            const start = state.currentPage * pageSize;
            processedData = processedData.slice(start, start + pageSize);
        }

        // Clear tbody
        tbody.innerHTML = '';

        // Render rows
        processedData.forEach((item, idx) => {
            const row = createRow(item, idx);
            tbody.appendChild(row);
        });

        // Show "no data" message if empty
        if (processedData.length === 0) {
            const row = document.createElement('tr');
            const td = document.createElement('td');
            td.colSpan = columns.length;
            td.textContent = state.filterText ? 'No matching records found' : 'No data available';
            td.style.padding = '20px';
            td.style.textAlign = 'center';
            td.style.color = '#999';
            row.appendChild(td);
            tbody.appendChild(row);
        }

        // Update sort indicators
        headerRow.querySelectorAll('th').forEach((th, idx) => {
            const indicator = th.querySelector('.sort-indicator');
            if (indicator) {
                if (columns[idx].field === state.sortField) {
                    indicator.textContent = state.sortDirection === 'asc' ? '▲' : '▼';
                } else {
                    indicator.textContent = '';
                }
            }
        });

        // Update pagination
        updatePagination(totalPages, totalItems);
    };

    // Create row function
    const createRow = (item, idx) => {
        const row = document.createElement('tr');
        row.style.borderBottom = '1px solid #eee';
        row.dataset.index = idx;

        // Selection
        if (selectable) {
            row.style.cursor = 'pointer';
            row.addEventListener('mouseenter', () => {
                if (!state.selectedRows.has(item)) {
                    row.style.backgroundColor = '#f5f5f5';
                }
            });
            row.addEventListener('mouseleave', () => {
                row.style.backgroundColor = state.selectedRows.has(item) ? '#e3f2fd' : '';
            });
            row.addEventListener('click', (e) => {
                if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'SELECT') {
                    if (state.selectedRows.has(item)) {
                        state.selectedRows.delete(item);
                        row.style.backgroundColor = '';
                    } else {
                        state.selectedRows.add(item);
                        row.style.backgroundColor = '#e3f2fd';
                    }

                    // Fire selectionChange event
                    if (node.events.selectionChange) {
                        runtime.app[node.events.selectionChange.replace('()', '')](Array.from(state.selectedRows));
                    }
                }
            });
        }

        // Create cells
        columns.forEach((col, colIndex) => {
            const td = document.createElement('td');
            td.style.padding = '12px';
            td.style.width = state.columnWidths[col.field] + 'px';

            const cellValue = item[col.field] !== undefined ? item[col.field] : '';

            // Editable cells
            if (editable && col.editable !== false) {
                td.style.cursor = 'text';
                td.addEventListener('dblclick', () => {
                    enterEditMode(td, item, col.field, cellValue, col.type || 'text');
                });
            }

            td.textContent = cellValue;
            row.appendChild(td);
        });

        // Drag support for rows
        if (dragEnabled) {
            row.draggable = true;
            row.style.cursor = 'move';

            row.addEventListener('dragstart', (e) => {
                const dragData = {
                    format: 'datagrid-rows',
                    source: container,
                    data: [item],
                    sourceIndex: idx
                };
                DragManager.doDrag(row, dragData, null, ['move']);
            });
        }

        return row;
    };

    // Enter edit mode for a cell
    const enterEditMode = (td, item, field, value, type) => {
        const oldValue = value;

        // Create input based on type
        let input;
        if (type === 'select') {
            input = document.createElement('select');
            // Add options from column definition
        } else if (type === 'checkbox') {
            input = document.createElement('input');
            input.type = 'checkbox';
            input.checked = value === true || value === 'true';
        } else if (type === 'number') {
            input = document.createElement('input');
            input.type = 'number';
            input.value = value;
        } else {
            input = document.createElement('input');
            input.type = 'text';
            input.value = value;
        }

        input.style.width = '100%';
        input.style.padding = '4px';
        input.style.border = '1px solid #3399ff';
        input.style.boxSizing = 'border-box';

        const finishEdit = (save) => {
            const newValue = type === 'checkbox' ? input.checked : input.value;

            if (save && newValue !== oldValue) {
                item[field] = newValue;
                td.textContent = newValue;

                // Fire cellEdit event
                if (node.events.cellEdit) {
                    const handlerName = node.events.cellEdit.replace('()', '');
                    if (runtime.app[handlerName]) {
                        runtime.app[handlerName]({ item, field, oldValue, newValue });
                    }
                }

                // Update reactive data
                if (dataProviderExpr && dataProviderExpr.includes('{')) {
                    const varMatch = dataProviderExpr.match(/\{([^}]+)\}/);
                    if (varMatch) {
                        const varName = varMatch[1].trim().split('.')[0];
                        runtime.app[varName] = [...data]; // Trigger reactivity
                    }
                }
            } else {
                td.textContent = oldValue;
            }
        };

        td.textContent = '';
        td.appendChild(input);
        input.focus();

        input.addEventListener('blur', () => finishEdit(true));
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                finishEdit(true);
            } else if (e.key === 'Escape') {
                e.preventDefault();
                finishEdit(false);
            }
        });
    };

    // Update pagination
    const updatePagination = (totalPages, totalItems) => {
        if (!paginationDiv) return;

        paginationDiv.innerHTML = '';

        const prevBtn = document.createElement('button');
        prevBtn.textContent = '◀ Previous';
        prevBtn.disabled = state.currentPage === 0;
        prevBtn.className = 'quantum-button';
        prevBtn.addEventListener('click', () => {
            state.currentPage--;
            updateTable();
        });
        paginationDiv.appendChild(prevBtn);

        const pageInfo = document.createElement('span');
        const start = state.currentPage * pageSize + 1;
        const end = Math.min((state.currentPage + 1) * pageSize, totalItems);
        pageInfo.textContent = `${start}-${end} of ${totalItems} items (Page ${state.currentPage + 1}/${totalPages})`;
        paginationDiv.appendChild(pageInfo);

        const nextBtn = document.createElement('button');
        nextBtn.textContent = 'Next ▶';
        nextBtn.disabled = state.currentPage >= totalPages - 1;
        nextBtn.className = 'quantum-button';
        nextBtn.addEventListener('click', () => {
            state.currentPage++;
            updateTable();
        });
        paginationDiv.appendChild(nextBtn);
    };

    // Initial render
    updateTable();

    // Setup reactive binding for dataProvider
    if (dataProviderExpr && dataProviderExpr.includes('{')) {
        const varMatch = dataProviderExpr.match(/\{([^}]+)\}/);
        if (varMatch) {
            const varName = varMatch[1].trim().split('.')[0];
            runtime.trackDependency(varName, () => {
                data = runtime.evaluateBinding(dataProviderExpr);
                if (!Array.isArray(data)) data = [];

                // Auto-generate columns if needed
                if (columns.length === 0 && data.length > 0) {
                    columns = Object.keys(data[0]).map(key => ({
                        field: key,
                        header: key.charAt(0).toUpperCase() + key.slice(1),
                        sortable: true,
                        editable: false,
                        type: 'text',
                        width: 150
                    }));
                }

                updateTable();
            });
        }
    }

    runtime.applyCommonProps(container, node.props);
    return container;
}
