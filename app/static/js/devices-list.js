(function () {
    "use strict";

    const table = document.querySelector("table[data-sortable]");
    if (!table) return;

    const tbody = table.querySelector("tbody");
    if (!tbody) return;

    const headers = table.querySelectorAll("th[data-sort]");
    if (!headers.length) return;

    // Запоминаем исходный порядок (пришёл с сервера, отсортирован по IP).
    const originalOrder = Array.from(tbody.querySelectorAll("tr"));
    originalOrder.forEach((tr, i) => { tr.dataset.origIndex = i; });

    let currentColumn = null;   // индекс колонки, по которой сортируем сейчас
    let currentState = 0;       // 0 = выкл, 1 = asc, 2 = desc

    function parseIPv4(str) {
        if (!str || str === "—") return null;
        const parts = str.split(".");
        if (parts.length !== 4) return null;
        const nums = parts.map(p => parseInt(p, 10));
        if (nums.some(n => isNaN(n) || n < 0 || n > 255)) return null;
        return nums;
    }

    function getCellValue(tr, colIndex, type) {
        const cell = tr.children[colIndex];
        if (!cell) return null;
        const text = cell.textContent.trim();
        if (!text || text === "—") return null;

        if (type === "ip") {
            return parseIPv4(text);
        }
        return text.toLowerCase();
    }

    function compareValues(va, vb, type) {
        if (type === "ip") {
            for (let i = 0; i < 4; i++) {
                if (va[i] !== vb[i]) return va[i] - vb[i];
            }
            return 0;
        }
        if (va < vb) return -1;
        if (va > vb) return 1;
        return 0;
    }

    function applySort(colIndex, type, direction) {
        const rows = Array.from(tbody.querySelectorAll("tr"));

        // Пустые всегда в конец, независимо от направления.
        const nonEmpty = [];
        const empty = [];

        rows.forEach(tr => {
            const v = getCellValue(tr, colIndex, type);
            if (v === null) empty.push(tr);
            else nonEmpty.push(tr);
        });

        nonEmpty.sort((a, b) => {
            const va = getCellValue(a, colIndex, type);
            const vb = getCellValue(b, colIndex, type);
            const cmp = compareValues(va, vb, type);
            return direction === 1 ? cmp : -cmp;
        });

        // Пустые — в конец, среди пустых сохраняем исходный порядок.
        empty.sort((a, b) =>
            parseInt(a.dataset.origIndex, 10) - parseInt(b.dataset.origIndex, 10)
        );

        [...nonEmpty, ...empty].forEach(tr => tbody.appendChild(tr));
    }

    function restoreOriginal() {
        originalOrder.forEach(tr => tbody.appendChild(tr));
    }

    function updateHeaders(activeColIndex) {
        headers.forEach(th => {
            const arrow = th.querySelector(".sort-arrow");
            if (!arrow) return;
            if (th.cellIndex === activeColIndex && currentState !== 0) {
                arrow.textContent = currentState === 1 ? " ↑" : " ↓";
            } else {
                arrow.textContent = "";
            }
        });
    }

    headers.forEach(th => {
        th.style.cursor = "pointer";
        th.addEventListener("click", () => {
            const colIndex = th.cellIndex;
            const type = th.dataset.type || "text";

            if (currentColumn === colIndex) {
                // Тот же столбец — переключаем состояние по кругу: 1 → 2 → 0
                currentState = (currentState + 1) % 3;
            } else {
                // Другой столбец — начинаем с asc
                currentColumn = colIndex;
                currentState = 1;
            }

            if (currentState === 0) {
                restoreOriginal();
                currentColumn = null;
            } else {
                applySort(colIndex, type, currentState);
            }
            updateHeaders(currentColumn === null ? -1 : currentColumn);
        });
    });
})();

