"use strict";

(() => {
    const cacheLifetime = 10 * 60 * 1000;

    function cacheKey(row) {
        return `library-check:${row.dataset.libraryId}:${row.dataset.libraryStudentno}`;
    }

    function cachedResult(key) {
        try {
            const saved = window.sessionStorage.getItem(key);
            if (!saved) return null;
            const entry = JSON.parse(saved);
            const age = Date.now() - entry.checkedAt;
            if (
                age >= 0 &&
                age < cacheLifetime &&
                entry.result?.status === "ok"
            ) {
                return entry.result;
            }
            window.sessionStorage.removeItem(key);
        } catch (error) {
            // Storage may be unavailable; a fresh check still works.
        }
        return null;
    }

    function removeCachedResult(key) {
        try {
            window.sessionStorage.removeItem(key);
        } catch (error) {
            // Storage may be unavailable.
        }
    }

    function saveResult(key, result) {
        try {
            window.sessionStorage.setItem(
                key,
                JSON.stringify({ checkedAt: Date.now(), result }),
            );
        } catch (error) {
            // The result remains visible even when storage is unavailable.
        }
    }

    function showResult(id, result) {
        document.getElementById(`name-${id}`).textContent = result.name ?? "";
        document.getElementById(`email-${id}`).textContent = result.email ?? "";
        document.getElementById(`role-${id}`).textContent = result.type ?? "";
    }

    function report(message, manual) {
        if (manual) {
            window.alert(message);
        } else {
            console.log(message);
        }
    }

    async function checkWithLibrary(row, manual) {
        const id = row.dataset.libraryId;
        const key = cacheKey(row);
        // The Check button forces a lookup; page loads may use a fresh saved result.
        if (manual) {
            removeCachedResult(key);
        } else {
            const result = cachedResult(key);
            if (result) {
                showResult(id, result);
                return;
            }
        }

        try {
            // This bypasses the HTTP cache only; sessionStorage is handled above.
            const response = await fetch(`/check/${encodeURIComponent(id)}`, {
                cache: "no-store",
            });
            const data = await response.json();
            if (!response.ok || data.message || data.status !== "ok") {
                // Do not leave an earlier successful identity visible after refresh.
                showResult(id, {});
                report(
                    data.message ||
                        (response.ok
                            ? `Bad status: ${data.status}`
                            : `HTTP ${response.status}`),
                    manual,
                );
                return;
            }
            const result = {
                status: "ok",
                name: data.name,
                email: data.email,
                type: data.type,
            };
            showResult(id, result);
            saveResult(key, result);
        } catch (error) {
            showResult(id, {});
            report("Library API request failed", manual);
        }
    }

    window.addEventListener("load", () => {
        document.querySelectorAll("[data-library-id]").forEach((row) => {
            row.querySelector("[data-library-check]").addEventListener(
                "click",
                () => checkWithLibrary(row, true),
            );
            checkWithLibrary(row, false);
        });
    });
})();
