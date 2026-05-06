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

    function filterTable(input) {
        const table = getTable(input);
        if (!table || !table.tBodies.length) return;

        const controls = getControlsForTable(table);
        const searchControls = controls.filter((control) => control.dataset.tableSearch !== undefined);
        const filterControls = controls.filter((control) => control.dataset.tableFilter !== undefined);
        const terms = searchControls.map((control) => normalize(control.value)).filter(Boolean);
        const rows = Array.from(table.tBodies[0].rows);
        const detailRowsById = {};

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
    }

    function initTableSearch() {
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
        refresh: initTableSearch
    };
})();
