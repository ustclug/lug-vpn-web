import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {test} from 'node:test';

function element() {
    return {listeners: {}, attributes: {}, dataset: {}, value: '', hidden: false,
        addEventListener(type, handler) { this.listeners[type] = handler; },
        setAttribute(key, value) { this.attributes[key] = value; },
        replaceChildren(...children) { this.children = children; },
        append(child) { this.children.push(child); }};
}
function setup() {
    const elements = Object.fromEntries(['users-list', 'users-status', 'users-retry'].map(id => [id, element()]));
    const sections = ['active', 'rejected'].map(kind => {
        const section = element();
        section.dataset.users = kind;
        const nodes = Object.fromEntries(['[data-query]', 'tbody', '[data-empty]', '[data-count]', '[data-page-summary]', '[data-step="-1"]', '[data-step="1"]'].map(key => [key, element()]));
        const rows = Array.from({length: 60}, (_, index) => ({dataset: {user: JSON.stringify({
            id: index + 1, name: `User ${index + 1}`, studentno: `PB${index + 1}`,
            email: `user${index + 1}@example.com`, month_traffic: index * 100,
            applytime: '2026-01-01', expiration: ''
        })}, nextElementSibling: element()}));
        section.querySelector = key => nodes[key];
        section.querySelectorAll = key => key === '[data-user]' ? rows : [];
        return section;
    });
    elements['users-list'].dataset.url = '/manageusers/data/';
    elements['users-list'].querySelectorAll = () => sections;
    const requests = [];
    const windowEvents = {};
    const location = new URL('https://vpn.example/manageusers/');
    const updateLocation = (_state, _unused, url) => { location.href = url.href; };
    const context = {URL, location,
        document: {getElementById: id => elements[id]},
        window: {addEventListener: (event, handler) => { windowEvents[event] = handler; }},
        history: {pushState: updateLocation, replaceState: updateLocation},
        fetch: (url, options) => new Promise(resolve => requests.push({url, options, resolve}))};
    runInNewContext(readFileSync(new URL('../app/static/js/manageusers.js', import.meta.url), 'utf8'), context);
    async function respond(index = 0, status = 200) {
        requests[index].resolve({ok: status === 200, status, json: async () => ({html: 'server fragment'})});
        await new Promise(resolve => setImmediate(resolve));
    }
    function search(value, section = 0) {
        sections[section].querySelector('[data-query]').value = value;
        elements['users-list'].listeners.input({target: {
            matches: () => true, closest: () => sections[section]
        }});
    }
    function click(section, dataset) {
        elements['users-list'].listeners.click({target: {closest: () => ({dataset, closest: () => sections[section]})}});
    }
    const ids = (section = 0) => sections[section].querySelector('tbody').children
        .filter(row => row.dataset?.user).map(row => JSON.parse(row.dataset.user).id);
    return {elements, requests, location, windowEvents, respond, search, click, ids, select: context.selectUserPage};
}

test('loads once; searches all users including later pages without another request', async () => {
    const app = setup();
    await app.respond();
    assert.equal(app.ids().length, 25);
    app.search('USER60@EXAMPLE.COM');
    assert.deepEqual(app.ids(), [60]);
    assert.equal(app.ids(1).length, 25);
    app.search('PB59', 1);
    assert.deepEqual(app.ids(1), [59]);
    assert.deepEqual(app.ids(), [60]);
    app.search('missing');
    assert.deepEqual(app.ids(), []);
    app.search('');
    assert.equal(app.ids().length, 25);
    assert.equal(app.requests.length, 1);
});

test('URL searches apply after the single response arrives', async () => {
    const app = setup();
    app.location.search = '?q=PB59';
    await app.respond();
    assert.deepEqual(app.ids(), [59]);
    assert.equal(app.requests.length, 1);
});

test('paging, numeric sorting, and history operate on cached rows', async () => {
    const app = setup();
    await app.respond();
    app.click(0, {step: '1'});
    assert.equal(app.ids()[0], 26);
    app.click(0, {sort: 'month_traffic'});
    assert.equal(app.ids()[0], 1);
    app.click(0, {sort: 'month_traffic'});
    assert.equal(app.ids()[0], 60);
    app.location.search = '?q=PB58';
    app.windowEvents.popstate();
    assert.deepEqual(app.ids(), [58]);
    assert.equal(app.requests.length, 1);
});

test('failure can be retried, but a loaded list is not fetched again', async () => {
    const app = setup();
    await app.respond(0, 500);
    assert.equal(app.elements['users-retry'].hidden, false);
    app.elements['users-retry'].listeners.click();
    await app.respond(1);
    app.elements['users-retry'].listeners.click();
    assert.equal(app.requests.length, 2);
    assert.equal(app.elements['users-retry'].hidden, true);
});

test('expired sessions show an actionable error', async () => {
    const app = setup();
    await app.respond(0, 401);
    assert.match(app.elements['users-status'].textContent, /Sign in again/);
});

test('literal wildcard search, null values, invalid sort and offset are handled', () => {
    const app = setup();
    const records = [{data: {id: 1, name: null, email: 'x%_/@example.com'}},
        {data: {id: 2, name: '张三', studentno: 'PB2', email: 'other@example.com'}}];
    const page = app.select(records, new URLSearchParams('q=%25_&sort=invalid&offset=999'), '');
    assert.equal(page.total, 1);
    assert.equal(page.offset, 0);
    assert.equal(page.visible[0].data.id, 1);
    assert.equal(app.select(records, new URLSearchParams('q=张'), '').total, 1);
    assert.equal(app.select(records, new URLSearchParams('offset=NaN'), '').offset, 0);
    assert.equal(app.select(records, new URLSearchParams('offset=-20'), '').offset, 0);
});
