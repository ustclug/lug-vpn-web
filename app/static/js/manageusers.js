'use strict';

const USER_PAGE_SIZE = 25;

function selectUserPage(records, params, prefix) {
    const defaultSort = prefix ? 'applytime' : 'id';
    const allowed = prefix
        ? ['applytime', 'studentno', 'name', 'email', 'rejectreason']
        : ['id', 'studentno', 'name', 'email', 'last_month_traffic', 'month_traffic', 'expiration'];
    const requestedSort = params.get(prefix + 'sort');
    const sort = allowed.includes(requestedSort) ? requestedSort : defaultSort;
    const requestedDirection = params.get(prefix + 'direction');
    const direction = ['asc', 'desc'].includes(requestedDirection)
        ? requestedDirection : (prefix ? 'desc' : 'asc');
    const query = (params.get('q') || '').trim().toLowerCase();
    const filtered = records.filter(({data}) => ['studentno', 'name', 'email'].some(
        key => String(data[key] ?? '').toLowerCase().includes(query)
    ));
    const numeric = ['id', 'last_month_traffic', 'month_traffic'].includes(sort);
    filtered.sort((a, b) => {
        const left = a.data[sort] ?? (numeric ? 0 : '');
        const right = b.data[sort] ?? (numeric ? 0 : '');
        const order = numeric ? left - right : String(left).localeCompare(String(right));
        return (direction === 'desc' ? -order : order) || a.data.id - b.data.id;
    });
    const requestedOffset = Number(params.get(prefix + 'offset'));
    const offset = Math.min(
        Number.isSafeInteger(requestedOffset) ? Math.max(0, requestedOffset) : 0,
        Math.max(0, Math.ceil(filtered.length / USER_PAGE_SIZE) - 1) * USER_PAGE_SIZE
    );
    return {sort, direction, offset, total: filtered.length,
        visible: filtered.slice(offset, offset + USER_PAGE_SIZE)};
}

(() => {
    const list = document.getElementById('users-list');
    const status = document.getElementById('users-status');
    const retry = document.getElementById('users-retry');
    const form = document.getElementById('user-search');
    const query = document.getElementById('user-query');
    let tables = [];
    let loading = false;

    function render() {
        const params = new URL(location.href).searchParams;
        query.value = params.get('q') || '';
        for (const table of tables) {
            const page = selectUserPage(table.records, params, table.prefix);
            table.page = page;
            // Keep only the current page in the DOM, but retain every user's rows in memory.
            table.body.replaceChildren(...page.visible.flatMap(record => record.rows));
            if (!page.total) {
                table.empty.hidden = false;
                table.body.append(table.empty);
            }
            table.section.querySelector('[data-count]').textContent = page.total;
            table.section.querySelector('[data-page-summary]').textContent =
                `Showing ${page.total ? page.offset + 1 : 0}–${Math.min(page.offset + USER_PAGE_SIZE, page.total)} of ${page.total}`;
            table.section.querySelector('[data-step="-1"]').disabled = page.offset === 0;
            table.section.querySelector('[data-step="1"]').disabled = page.offset + USER_PAGE_SIZE >= page.total;
            for (const button of table.section.querySelectorAll('[data-sort]')) {
                const selected = button.dataset.sort === page.sort;
                button.querySelector('[data-sort-indicator]').textContent = selected ? (page.direction === 'asc' ? '▲' : '▼') : '';
                button.closest('th').setAttribute('aria-sort', selected ? (page.direction === 'asc' ? 'ascending' : 'descending') : 'none');
            }
        }
    }

    async function load() {
        if (loading || tables.length) return;
        loading = true;
        list.setAttribute('aria-busy', 'true');
        status.textContent = 'Loading users…';
        retry.hidden = true;
        try {
            const response = await fetch(list.dataset.url, {
                headers: {Accept: 'application/json'}, cache: 'no-store'
            });
            if (response.status === 401) throw new Error('Your session has expired. Sign in again, then retry.');
            if (response.status === 403) throw new Error('Administrator access required.');
            if (!response.ok) throw new Error('Unable to load users. Please retry.');
            const data = await response.json();
            if (typeof data.html !== 'string') throw new Error('Invalid response. Please retry.');
            // The application renders and escapes this fragment using Jinja.
            list.innerHTML = data.html;
            tables = Array.from(list.querySelectorAll('[data-users]'), section => {
                const prefix = section.dataset.users === 'rejected' ? 'rejected_' : '';
                const records = Array.from(section.querySelectorAll('[data-user]'), row => ({
                    data: JSON.parse(row.dataset.user),
                    rows: prefix ? [row] : [row, row.nextElementSibling]
                }));
                return {section, prefix, records, body: section.querySelector('tbody'),
                    empty: section.querySelector('[data-empty]')};
            });
            if (tables.length !== 2) throw new Error('Invalid response. Please retry.');
            render();
            status.textContent = '';
        } catch (error) {
            tables = [];
            list.replaceChildren();
            status.textContent = error.message;
            retry.hidden = false;
        } finally {
            loading = false;
            list.setAttribute('aria-busy', 'false');
        }
    }

    function navigate(url, replace = false) {
        if (url.href !== location.href) history[replace ? 'replaceState' : 'pushState'](null, '', url);
        render();
    }

    function search(replace) {
        const url = new URL(location.href);
        url.searchParams.set('q', query.value);
        url.searchParams.delete('offset');
        url.searchParams.delete('rejected_offset');
        navigate(url, replace);
    }
    form.addEventListener('submit', event => {
        event.preventDefault();
        search(false);
    });
    query.addEventListener('input', () => search(true));
    list.addEventListener('click', event => {
        const button = event.target.closest('[data-sort], [data-step]');
        if (!button || button.disabled) return;
        const table = tables.find(item => item.section === button.closest('[data-users]'));
        if (!table) return;
        const url = new URL(location.href);
        if (button.dataset.sort) {
            url.searchParams.set(table.prefix + 'sort', button.dataset.sort);
            url.searchParams.set(table.prefix + 'direction',
                table.page.sort === button.dataset.sort && table.page.direction === 'asc' ? 'desc' : 'asc');
            url.searchParams.delete(table.prefix + 'offset');
        } else {
            url.searchParams.set(table.prefix + 'offset', table.page.offset + Number(button.dataset.step) * USER_PAGE_SIZE);
        }
        navigate(url);
    });
    retry.addEventListener('click', load);
    window.addEventListener('popstate', render);
    render();
    load();
})();
