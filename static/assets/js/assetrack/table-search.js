(function () {
    function normalize(value) {
        return (value || '').toString().toLowerCase().trim();
    }

    function getTable(input) {
        const selector = input.dataset.tableSearch || input.dataset.tableFilter;

        if (selector) {
            return document.querySelector(selector);
        }

        const card = input.closest('.card');
        if (card) {
            return card.querySelector('table');
        }

        return document.querySelector('table');
    }

    function getSelectorForTable(table) {
        return table.id ? `#${CSS.escape(table.id)}` : null;
    }

    function getControlsForTable(table) {
        const selector = getSelectorForTable(table);
        const controls = Array.from(document.querySelectorAll('[data-table-search], [data-table-filter]'));

        if (!selector) {
            return controls.filter((control) => getTable(control) === table);
        }

        return controls.filter((control) => {
            return control.dataset.tableSearch === selector || control.dataset.tableFilter === selector || getTable(control) === table;
        });
    }

    function getFilterValue(control) {
        if (!control.value) return '';

        if (control.tagName === 'SELECT' && control.dataset.filterMatch !== 'value') {
            return normalize(control.selectedOptions[0] ? control.selectedOptions[0].textContent : '');
        }

        return normalize(control.value);
    }

    function rowMatchesFilter(row, control) {
        const filterValue = getFilterValue(control);
        if (!filterValue) return true;

        const column = parseInt(control.dataset.filterColumn || '', 10);
        const source = Number.isInteger(column) && column > 0 ? row.cells[column - 1] : row;
        const sourceText = normalize(source ? source.textContent : '');

        return sourceText.includes(filterValue);
    }

    function getRowText(row, detailRowsById) {
        const rowText = row.textContent || '';
        const rowId = row.dataset.searchRowId;
        const detailText = rowId && detailRowsById[rowId]
            ? detailRowsById[rowId].map((detailRow) => detailRow.textContent || '').join(' ')
            : '';

        return normalize(`${rowText} ${detailText}`);
    }

    function setNoResultsRow(table, visibleRows) {
        const tbody = table.tBodies[0];
        if (!tbody) return;

        let emptyRow = tbody.querySelector(':scope > tr[data-search-empty-row="true"]');

        if (!emptyRow) {
            const colspan = table.tHead && table.tHead.rows[0] ? table.tHead.rows[0].cells.length : 1;
            emptyRow = document.createElement('tr');
            emptyRow.dataset.searchEmptyRow = 'true';
            emptyRow.hidden = true;
            emptyRow.innerHTML = `<td colspan="${colspan}" class="text-center text-muted py-4">No matching records found</td>`;
            tbody.appendChild(emptyRow);
        }

        emptyRow.hidden = visibleRows !== 0;
    }

    function getDataRows(table) {
        if (!table || !table.tBodies.length) return [];
        return Array.from(table.tBodies[0].rows).filter((row) => {
            const isManualEmptyRow = row.cells.length === 1 && row.cells[0].hasAttribute('colspan');
            return row.dataset.searchEmptyRow !== 'true' && !row.dataset.searchDetailFor && !isManualEmptyRow;
        });
    }

    function getPaginationState(table) {
        if (!table.dataset.pageSize) table.dataset.pageSize = '5';
        if (!table.dataset.currentPage) table.dataset.currentPage = '1';
        return {
            pageSize: parseInt(table.dataset.pageSize, 10) || 5,
            currentPage: parseInt(table.dataset.currentPage, 10) || 1
        };
    }

    function getPaginationContainer(table) {
        if (!table.id) {
            table.id = `asset-table-${Math.random().toString(36).slice(2)}`;
        }

        let container = document.querySelector(`[data-pagination-for="${CSS.escape(table.id)}"]`);
        if (container) return container;

        container = document.createElement('div');
        container.className = 'd-flex flex-column flex-md-row gap-2 justify-content-between align-items-md-center px-3 py-3 border-top';
        container.dataset.paginationFor = table.id;
        container.innerHTML = `
            <div class="d-flex align-items-center gap-2">
                <span class="text-muted small">Rows per page</span>
                <select class="form-select form-select-sm asset-page-size" style="width:auto;">
                    <option value="5">5</option>
                    <option value="10">10</option>
                    <option value="15">15</option>
                    <option value="20">20</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                </select>
            </div>
            <div class="d-flex align-items-center gap-2">
                <span class="text-muted small asset-page-summary"></span>
                <div class="btn-group btn-group-sm">
                    <button type="button" class="btn btn-outline-secondary asset-page-prev">Previous</button>
                    <button type="button" class="btn btn-outline-secondary asset-page-next">Next</button>
                </div>
            </div>
        `;

        const responsive = table.closest('.table-responsive');
        (responsive || table).insertAdjacentElement('afterend', container);

        container.querySelector('.asset-page-size').addEventListener('change', (event) => {
            table.dataset.pageSize = event.target.value;
            table.dataset.currentPage = '1';
            applyPagination(table);
        });
        container.querySelector('.asset-page-prev').addEventListener('click', () => {
            table.dataset.currentPage = String(Math.max(1, getPaginationState(table).currentPage - 1));
            applyPagination(table);
        });
        container.querySelector('.asset-page-next').addEventListener('click', () => {
            table.dataset.currentPage = String(getPaginationState(table).currentPage + 1);
            applyPagination(table);
        });

        return container;
    }

    function applyPagination(table) {
        if (!table || !table.tBodies.length || table.dataset.noPagination === 'true') return;

        const rows = getDataRows(table);
        if (!rows.length) return;

        const {pageSize} = getPaginationState(table);
        const matchedRows = rows.filter((row) => row.dataset.tableMatched !== 'false');
        const pageCount = Math.max(1, Math.ceil(matchedRows.length / pageSize));
        const currentPage = Math.min(getPaginationState(table).currentPage, pageCount);
        table.dataset.currentPage = String(currentPage);

        const visibleStart = (currentPage - 1) * pageSize;
        const visibleEnd = visibleStart + pageSize;
        const visibleSet = new Set(matchedRows.slice(visibleStart, visibleEnd));

        rows.forEach((row) => {
            const shouldShow = visibleSet.has(row);
            row.hidden = !shouldShow;

            const rowId = row.dataset.searchRowId;
            if (!rowId) return;
            Array.from(table.tBodies[0].querySelectorAll(`tr[data-search-detail-for="${CSS.escape(rowId)}"]`)).forEach((detailRow) => {
                detailRow.hidden = !shouldShow || detailRow.dataset.expanded !== 'true';
            });
        });

        const container = getPaginationContainer(table);
        const first = matchedRows.length ? visibleStart + 1 : 0;
        const last = Math.min(visibleEnd, matchedRows.length);
        container.querySelector('.asset-page-size').value = String(pageSize);
        container.querySelector('.asset-page-summary').textContent = `${first}-${last} of ${matchedRows.length}`;
        container.querySelector('.asset-page-prev').disabled = currentPage <= 1;
        container.querySelector('.asset-page-next').disabled = currentPage >= pageCount;
    }

    function filterTable(input) {
        const table = getTable(input);
        if (!table || !table.tBodies.length) return;

        const controls = getControlsForTable(table);
        const searchControls = controls.filter((control) => control.dataset.tableSearch !== undefined);
        const filterControls = controls.filter((control) => control.dataset.tableFilter !== undefined);
        const terms = searchControls.map((control) => normalize(control.value)).filter(Boolean);
        const rows = Array.from(table.tBodies[0].rows);
        const detailRowsById = {};
        if (!getDataRows(table).length) return;

        rows.forEach((row) => {
            const detailFor = row.dataset.searchDetailFor;
            if (!detailFor) return;

            if (!detailRowsById[detailFor]) {
                detailRowsById[detailFor] = [];
            }
            detailRowsById[detailFor].push(row);
        });

        let visibleRows = 0;

        rows.forEach((row) => {
            if (row.dataset.searchEmptyRow === 'true') return;
            if (row.cells.length === 1 && row.cells[0].hasAttribute('colspan')) {
                row.hidden = false;
                return;
            }

            const detailFor = row.dataset.searchDetailFor;
            if (detailFor) {
                const parent = table.tBodies[0].querySelector(`tr[data-search-row-id="${CSS.escape(detailFor)}"]`);
                row.hidden = !parent || parent.hidden || row.dataset.expanded !== 'true';
                return;
            }

            const rowText = getRowText(row, detailRowsById);
            const matchesSearch = terms.every((term) => rowText.includes(term));
            const matchesFilters = filterControls.every((control) => rowMatchesFilter(row, control));
            const isMatch = matchesSearch && matchesFilters;
            row.dataset.tableMatched = isMatch ? 'true' : 'false';
            row.hidden = !isMatch;

            if (isMatch) {
                visibleRows += 1;
            }

            const rowId = row.dataset.searchRowId;
            if (rowId && detailRowsById[rowId]) {
                detailRowsById[rowId].forEach((detailRow) => {
                    detailRow.hidden = !isMatch || detailRow.dataset.expanded !== 'true';
                });
            }
        });

        setNoResultsRow(table, visibleRows);
        table.dataset.currentPage = '1';
        applyPagination(table);
    }

    function initTableSearch() {
        document.querySelectorAll('table').forEach((table) => {
            getDataRows(table).forEach((row) => {
                if (!row.dataset.tableMatched) row.dataset.tableMatched = 'true';
            });
            applyPagination(table);
        });

        document.querySelectorAll('[data-table-search], [data-table-filter]').forEach((input) => {
            filterTable(input);
            input.addEventListener('input', () => filterTable(input));
            input.addEventListener('change', () => filterTable(input));
        });
    }

    function moveModalsToBody() {
        document.querySelectorAll('.nxl-container .modal').forEach((modal) => {
            document.body.appendChild(modal);
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        moveModalsToBody();
        initTableSearch();
    });

    window.AsseTrackTableSearch = {
        filterTable,
        applyPagination,
        refresh: initTableSearch
    };
})();
