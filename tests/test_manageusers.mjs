import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {test} from 'node:test';

function setup() {
    const elements = Object.fromEntries(['users-list', 'users-status', 'users-retry', 'user-search', 'user-query'].map(id => [id, {
        listeners: {}, attributes: {}, dataset: {url: '/manageusers/data/'},
        innerHTML: '', value: '', hidden: false,
        addEventListener(type, handler) { this.listeners[type] = handler; },
        setAttribute(key, value) { this.attributes[key] = value; },
        replaceChildren() { this.innerHTML = ''; },
        querySelector() { return this.innerHTML.includes('<tr>') ? {} : null; }
    }]));
    const requests = [];
    const windowEvents = {};
    const location = new URL('https://vpn.example/manageusers/?offset=25&rejected_offset=50');
    const context = {
        URL, AbortController, location,
        document: {getElementById: id => elements[id]},
        window: {addEventListener: (event, handler) => { windowEvents[event] = handler; }},
        history: {pushState: (_state, _unused, url) => { location.href = url.href; }},
        fetch: (url, options) => new Promise(resolve => requests.push({url, options, resolve}))
    };
    runInNewContext(readFileSync(new URL('../app/static/js/manageusers.js', import.meta.url), 'utf8'), context);
    async function respond(index, html, status = 200) {
        requests[index].resolve({ok: status === 200, status, json: async () => ({html})});
        await new Promise(resolve => setImmediate(resolve));
    }
    function search(value) {
        elements['user-query'].value = value;
        elements['user-search'].listeners.submit({preventDefault() {}});
    }
    return {elements, requests, location, windowEvents, respond, search};
}

test('search resets offsets; stale responses cannot replace newer results', async () => {
    const app = setup();
    assert.equal(app.elements['users-list'].attributes['aria-busy'], 'true');
    app.search(' Alice ');
    assert.equal(app.requests[0].options.signal.aborted, true);
    assert.equal(app.requests[1].url.searchParams.get('q'), 'Alice');
    assert.equal(app.location.searchParams.has('offset'), false);
    assert.equal(app.location.searchParams.has('rejected_offset'), false);
    await app.respond(1, '<tr>Alice</tr>');
    await app.respond(0, '<tr>Old</tr>');
    assert.equal(app.elements['users-list'].innerHTML, '<tr>Alice</tr>');
    assert.equal(app.elements['users-list'].attributes['aria-busy'], 'false');
});

test('errors can be retried and empty results are announced', async () => {
    const app = setup();
    await app.respond(0, '', 500);
    assert.equal(app.elements['users-retry'].hidden, false);
    app.elements['users-retry'].listeners.click();
    await app.respond(1, '<table></table>');
    assert.equal(app.elements['users-retry'].hidden, true);
    assert.equal(app.elements['users-status'].textContent, 'No matching users.');
});

test('sorting uses fetch, detail links keep normal navigation, and history reloads search', async () => {
    const app = setup();
    await app.respond(0, '<tr>Users</tr>');
    let prevented = false;
    const click = href => app.elements['users-list'].listeners.click({
        button: 0, target: {closest: () => ({href})}, preventDefault() { prevented = true; }
    });
    click('https://vpn.example/profile/1/');
    assert.equal(prevented, false);
    click('https://vpn.example/manageusers/?q=Bob&sort=email');
    assert.equal(prevented, true);
    assert.equal(app.requests.length, 2);
    assert.equal(app.elements['user-query'].value, 'Bob');
    app.location.search = '?q=Alice';
    app.windowEvents.popstate();
    assert.equal(app.elements['user-query'].value, 'Alice');
    assert.equal(app.requests[1].options.signal.aborted, true);
});

test('expired sessions show an actionable error', async () => {
    const app = setup();
    await app.respond(0, '', 401);
    assert.match(app.elements['users-status'].textContent, /Sign in again/);
    assert.equal(app.elements['users-retry'].hidden, false);
});
