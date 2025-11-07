/**
 * DataGrid Component - Feature-rich table with sorting, filtering, pagination
 *
 * Props:
 * - dataProvider: Array of objects to display (supports bindings)
 * - columns: Array of column definitions [{field, header, width, sortable}]
 * - sortable: Enable sorting (default: true)
 * - filterable: Enable filtering (default: false)
 * - pageSize: Items per page for pagination (default: no pagination)
 * - selectable: Enable row selection (default: false)
 *
 * Events:
 * - itemClick: Fired when row is clicked (passes row data)
 * - selectionChange: Fired when selection changes
 */

export function renderDataGrid(runtime, node) {
    const container = document.createElement('div');
    container.className = 'quantum-datagrid-container';

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
            sortable: true
        }));
    }

    // State
    const state = {
        sortField: null,
        sortDirection: 'asc',
        filterText: '',
        currentPage: 0,
        selectedRows: new Set()
    };

    const pageSize = node.props.pageSize ? parseInt(node.props.pageSize) : null;
    const sortable = node.props.sortable !== 'false';
    const filterable = node.props.filterable === 'true';
    const selectable = node.props.selectable === 'true';

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
            state.currentPage = 0; // Reset to first page
            updateTable();
        });
        container.appendChild(filterBox);
    }

    // Create table
    const table = document.createElement('table');
    table.className = 'quantum-datagrid';
    table.style.width = '100%';
    table.style.borderCollapse = 'collapse';

    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');

    // Create headers
    columns.forEach(col => {
        const th = document.createElement('th');
        th.textContent = col.header || col.field;
        th.style.padding = '12px';
        th.style.textAlign = 'left';
        th.style.backgroundColor = '#f0f0f0';
        th.style.borderBottom = '2px solid #ddd';
        if (col.width) th.style.width = col.width;

        // Add sorting
        if (sortable && col.sortable !== false) {
            th.style.cursor = 'pointer';
            th.style.userSelect = 'none';
            th.addEventListener('click', () => {
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
            th.appendChild(sortIndicator);
        }

        headerRow.appendChild(th);
    });

    thead.appendChild(headerRow);
    table.appendChild(thead);

    const tbody = document.createElement('tbody');
    table.appendChild(tbody);

    container.appendChild(table);

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
            const row = document.createElement('tr');
            row.style.borderBottom = '1px solid #eee';

            if (selectable) {
                row.style.cursor = 'pointer';
                row.addEventListener('mouseenter', () => {
                    row.style.backgroundColor = '#f5f5f5';
                });
                row.addEventListener('mouseleave', () => {
                    row.style.backgroundColor = state.selectedRows.has(item) ? '#e3f2fd' : '';
                });
                row.addEventListener('click', () => {
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
                });
            }

            columns.forEach(col => {
                const td = document.createElement('td');
                td.style.padding = '12px';
                td.textContent = item[col.field] !== undefined ? item[col.field] : '';
                row.appendChild(td);
            });

            tbody.appendChild(row);

            // Fire itemClick event
            if (node.events.itemClick) {
                row.addEventListener('click', () => {
                    const handlerName = node.events.itemClick.replace('()', '');
                    if (runtime.app[handlerName]) {
                        runtime.app[handlerName](item);
                    }
                });
            }
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
        if (paginationDiv) {
            paginationDiv.innerHTML = '';

            const prevBtn = document.createElement('button');
            prevBtn.textContent = '◀ Previous';
            prevBtn.disabled = state.currentPage === 0;
            prevBtn.style.padding = '6px 12px';
            prevBtn.style.cursor = prevBtn.disabled ? 'not-allowed' : 'pointer';
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
            nextBtn.style.padding = '6px 12px';
            nextBtn.style.cursor = nextBtn.disabled ? 'not-allowed' : 'pointer';
            nextBtn.addEventListener('click', () => {
                state.currentPage++;
                updateTable();
            });
            paginationDiv.appendChild(nextBtn);
        }
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
                        sortable: true
                    }));
                }

                updateTable();
            });
        }
    }

    runtime.applyCommonProps(container, node.props);
    return container;
}
