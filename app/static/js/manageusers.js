'use strict';

(() => {
    const list = document.getElementById('users-list');
    const status = document.getElementById('users-status');
    const retry = document.getElementById('users-retry');
    const form = document.getElementById('user-search');
    const query = document.getElementById('user-query');
    let pending;

    async function load() {
        if (pending) pending.abort();
        const controller = new AbortController();
        pending = controller;
        query.value = new URL(location.href).searchParams.get('q') || '';
        list.setAttribute('aria-busy', 'true');
        // Hide old rows so actions cannot target results from a previous search.
        list.replaceChildren();
        status.textContent = 'Loading users…';
        retry.hidden = true;
        const url = new URL(list.dataset.url, location.href);
        url.search = location.search;
        try {
            const response = await fetch(url, {
                signal: controller.signal,
                headers: {Accept: 'application/json'},
                cache: 'no-store'
            });
            if (response.status === 401) throw new Error('Your session has expired. Sign in again, then retry.');
            if (response.status === 403) throw new Error('Administrator access required.');
            if (!response.ok) throw new Error('Unable to load users. Please retry.');
            const data = await response.json();
            if (typeof data.html !== 'string') throw new Error('Invalid response. Please retry.');
            if (pending !== controller) return;
            // This fragment is rendered and escaped by the application's Jinja template.
            list.innerHTML = data.html;
            status.textContent = list.querySelector('tbody tr') ? '' : 'No matching users.';
        } catch (error) {
            if (pending !== controller || error.name === 'AbortError') return;
            status.textContent = error.message;
            retry.hidden = false;
        } finally {
            if (pending === controller) list.setAttribute('aria-busy', 'false');
        }
    }

    function navigate(url) {
        if (url.href !== location.href) history.pushState(null, '', url);
        load();
    }

    form.addEventListener('submit', event => {
        event.preventDefault();
        const url = new URL(location.href);
        url.searchParams.set('q', query.value.trim());
        url.searchParams.delete('offset');
        url.searchParams.delete('rejected_offset');
        navigate(url);
    });
    list.addEventListener('click', event => {
        const link = event.target.closest('a');
        if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        const url = new URL(link.href);
        if (url.origin !== location.origin || url.pathname !== location.pathname) return;
        event.preventDefault();
        navigate(url);
    });
    retry.addEventListener('click', load);
    window.addEventListener('popstate', load);
    load();
})();
