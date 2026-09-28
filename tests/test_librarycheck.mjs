import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { runInNewContext } from "node:vm";
import { test } from "node:test";

const cacheLifetime = 10 * 60 * 1000;
const script = new URL("../app/static/js/librarycheck.js", import.meta.url);

// A simple in-memory sessionStorage implementation for testing purposes.
function storage() {
    const entries = new Map();
    return {
        getItem: (key) => entries.get(key) ?? null,
        setItem: (key, value) => entries.set(key, value),
        removeItem: (key) => entries.delete(key),
    };
}

// Each setup runs the real script in a new page context. Sharing sessionStorage
// between setups models a reload or redirect within the same browser tab.
function setup({
    sessionStorage = storage(),
    clock = { now: 1000 },
    studentno = "PB123",
} = {}) {
    const fields = Object.fromEntries(
        ["name", "email", "role"].map((name) => [name, { textContent: "" }]),
    );
    const button = {
        listeners: {},
        addEventListener(type, handler) {
            this.listeners[type] = handler;
        },
        click() {
            this.listeners.click();
        },
    };
    const row = {
        dataset: { libraryId: "7", libraryStudentno: studentno },
        querySelector: (selector) =>
            selector === "[data-library-check]" ? button : null,
    };
    const requests = [];
    const alerts = [];
    const events = {};
    const context = {
        window: {
            sessionStorage,
            addEventListener: (event, handler) => {
                events[event] = handler;
            },
            alert: (message) => alerts.push(message),
        },
        document: {
            querySelectorAll: (selector) =>
                selector === "[data-library-id]" ? [row] : [],
            getElementById: (id) => fields[id.split("-")[0]],
        },
        fetch: (url, options) =>
            new Promise((resolve) => requests.push({ url, options, resolve })),
        console: { log() {} },
        Date: class extends Date {
            static now() {
                return clock.now;
            }
        },
    };
    runInNewContext(readFileSync(script, "utf8"), context);
    events.load();

    async function respond(data, status = 200) {
        requests
            .at(-1)
            .resolve({
                ok: status >= 200 && status < 300,
                status,
                json: async () => data,
            });
        // Wait for fetch and JSON parsing to update the displayed fields.
        await new Promise((resolve) => setImmediate(resolve));
    }

    return { fields, button, requests, alerts, respond };
}

test("successful checks are reused after a reload in the same tab", async () => {
    const sessionStorage = storage();
    const first = setup({ sessionStorage });
    assert.equal(first.requests.length, 1);
    await first.respond({
        status: "ok",
        name: "Alice",
        email: "alice@example.com",
        type: "Student",
    });
    assert.equal(first.fields.name.textContent, "Alice");

    // Returning from Pass or Reject reloads the page but keeps this tab's storage.
    const reloaded = setup({ sessionStorage });
    assert.equal(reloaded.requests.length, 0);
    assert.equal(reloaded.fields.name.textContent, "Alice");
    assert.equal(reloaded.fields.email.textContent, "alice@example.com");
    assert.equal(reloaded.fields.role.textContent, "Student");
});

test("Check fetches a fresh result and replaces the cached one", async () => {
    const sessionStorage = storage();
    const first = setup({ sessionStorage });
    await first.respond({ status: "ok", name: "Alice" });

    const cached = setup({ sessionStorage });
    assert.equal(cached.requests.length, 0);
    // An explicit Check must bypass the result that the page just reused.
    cached.button.click();
    assert.equal(cached.requests.length, 1);
    await cached.respond({ status: "ok", name: "Alicia" });

    const reloaded = setup({ sessionStorage });
    assert.equal(reloaded.requests.length, 0);
    assert.equal(reloaded.fields.name.textContent, "Alicia");
});

test("expired results and changed student numbers are fetched again", async () => {
    const sessionStorage = storage();
    const clock = { now: 1000 };
    const first = setup({ sessionStorage, clock });
    await first.respond({ status: "ok", name: "Alice" });

    clock.now += cacheLifetime - 1;
    assert.equal(setup({ sessionStorage, clock }).requests.length, 0);
    clock.now += 1;
    assert.equal(setup({ sessionStorage, clock }).requests.length, 1);
    // The old entry must also be ignored when an applicant's student number changes.
    assert.equal(
        setup({ sessionStorage, clock: { now: 1000 }, studentno: "PB456" })
            .requests.length,
        1,
    );
});

test("a non-ok manual result clears the old display and is not cached", async () => {
    const sessionStorage = storage();
    const first = setup({ sessionStorage });
    await first.respond({ status: "ok", name: "Alice" });

    const cached = setup({ sessionStorage });
    cached.button.click();
    // A later "not found" must clear the earlier match from both the page and cache.
    await cached.respond({ status: "not found" });
    assert.equal(cached.fields.name.textContent, "");
    assert.deepEqual(cached.alerts, ["Bad status: not found"]);
    assert.equal(setup({ sessionStorage }).requests.length, 1);
});

test("unavailable session storage does not prevent a fresh check", async () => {
    // Browser privacy settings can make storage methods throw.
    const blockedStorage = {
        getItem() {
            throw new Error("blocked");
        },
        setItem() {
            throw new Error("blocked");
        },
        removeItem() {
            throw new Error("blocked");
        },
    };
    const page = setup({ sessionStorage: blockedStorage });
    assert.equal(page.requests.length, 1);
    await page.respond({ status: "ok", name: "Alice" });
    assert.equal(page.fields.name.textContent, "Alice");
});
