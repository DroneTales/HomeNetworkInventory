(function () {
    "use strict";

    function serializeRow(row) {
        var entries = [];
        row.querySelectorAll(".wifi-mac-filter-entry").forEach(function (el) {
            var cb = el.querySelector(".wifi-mac-active");
            entries.push({
                id: el.dataset.id ? parseInt(el.dataset.id, 10) : null,
                device: parseInt(el.dataset.device, 10),
                active: cb ? cb.checked : true
            });
        });
        var hidden = row.querySelector(".wifi-mac-filter-data");
        if (hidden) hidden.value = JSON.stringify(entries);
    }

    function toggleBlock(row) {
        var sel = row.querySelector(".wifi-mac-filter");
        var block = row.querySelector(".wifi-mac-filter-block");
        if (sel && block) block.classList.toggle("d-none", sel.value === "0");
    }

    function addOption(select, id, name, mac) {
        var opt = document.createElement("option");
        opt.value = id;
        opt.dataset.name = name;
        opt.dataset.mac = mac;
        opt.textContent = name + " (" + mac + ")";
        select.appendChild(opt);
    }

    function cfg(key, fallback) {
        var c = window.DEVICES_FORM_CONFIG || {};
        return c[key] || fallback;
    }

    function makeEntry(name, mac, deviceId, active) {
        var row = document.createElement("div");
        row.className = "row g-1 align-items-center wifi-mac-filter-entry py-1";
        row.dataset.device = deviceId;
        row.dataset.name = name;
        row.dataset.mac = mac;

        var colName = document.createElement("div");
        colName.className = "col-12 col-md";
        var span = document.createElement("span");
        span.className = "small";
        span.textContent = name + " ";
        var code = document.createElement("code");
        code.className = "ms-1";
        code.textContent = mac;
        span.appendChild(code);
        colName.appendChild(span);

        var colActive = document.createElement("div");
        colActive.className = "col-6 col-md-1";
        var label = document.createElement("label");
        label.className = "form-check-label small text-nowrap";
        var cb = document.createElement("input");
        cb.type = "checkbox";
        cb.className = "form-check-input wifi-mac-active";
        cb.checked = active !== false;
        label.appendChild(cb);
        label.appendChild(document.createTextNode(" " + cfg("macFilterActive", "active")));
        colActive.appendChild(label);

        var colRemove = document.createElement("div");
        colRemove.className = "col-6 col-md-auto text-end";
        var btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn btn-sm btn-outline-danger remove-wifi-mac px-1";
        btn.textContent = cfg("wifiRemoveLabel", "Remove");
        colRemove.appendChild(btn);

        row.appendChild(colName);
        row.appendChild(colActive);
        row.appendChild(colRemove);
        return row;
    }

    function onAdd(row) {
        var sel = row.querySelector(".wifi-mac-add-select");
        var box = row.querySelector(".wifi-mac-filter-entries");
        if (!sel || !box) return;
        var opt = sel.options[sel.selectedIndex];
        if (!opt || !opt.value) return;
        box.appendChild(makeEntry(opt.dataset.name, opt.dataset.mac, opt.value, true));
        sel.removeChild(opt);
        sel.value = "";
        serializeRow(row);
    }

    function onRemove(row, el) {
        var sel = row.querySelector(".wifi-mac-add-select");
        if (sel && el.dataset.device) addOption(sel, el.dataset.device, el.dataset.name || "", el.dataset.mac || "");
        el.remove();
        serializeRow(row);
    }

    document.addEventListener("click", function (e) {
        var add = e.target.closest(".add-wifi-mac");
        if (add) { var r1 = add.closest(".wifi-row"); if (r1) onAdd(r1); return; }
        var rm = e.target.closest(".remove-wifi-mac");
        if (rm) { var r2 = rm.closest(".wifi-row"); if (r2) onRemove(r2, rm.closest(".wifi-mac-filter-entry")); }
    });

    document.addEventListener("change", function (e) {
        var row = e.target.closest(".wifi-row");
        if (!row) return;
        if (e.target.classList.contains("wifi-mac-filter")) { toggleBlock(row); serializeRow(row); }
        else if (e.target.classList.contains("wifi-mac-active")) serializeRow(row);
    });

    document.addEventListener("submit", function (e) {
        var form = e.target;
        if (form && form.querySelectorAll) form.querySelectorAll(".wifi-row").forEach(serializeRow);
    }, true);

    document.querySelectorAll(".wifi-row").forEach(function (row) {
        toggleBlock(row);
        serializeRow(row);
    });
})();
