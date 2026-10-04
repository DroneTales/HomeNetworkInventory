// Home Network Inventory
// Device form: dynamic row add/remove and sync.
//
// Copyright (C) Mike Petrichenko
// e-mail: btframework@gmail.com
// Project repository: https://github.com/DroneTales/HomeNetworkInventory
//
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
    "use strict";

    function setupList(options) {
        const container = document.getElementById(options.containerId);
        const emptyHint = document.getElementById(options.emptyHintId);
        const addBtn = document.getElementById(options.addBtnId);
        const template = document.getElementById(options.templateId);

        if (!container || !addBtn || !template) return;

        function updateEmptyHint() {
            if (!emptyHint) return;
            const rows = container.querySelectorAll("." + options.rowClass);
            emptyHint.classList.toggle("d-none", rows.length > 0);
        }

        function bindRemove(row) {
            const removeBtn = row.querySelector("." + options.removeBtnClass);
            if (removeBtn) {
                removeBtn.addEventListener("click", function () {
                    if (options.beforeRemove && options.beforeRemove(row) === false) return;
                    row.remove();
                    updateEmptyHint();
                    if (options.afterBind) options.afterBind(row);
                    if (options.afterMutation) options.afterMutation();
                });
            }
            if (options.afterBind) options.afterBind(row);
        }

        addBtn.addEventListener("click", function () {
            const clone = template.content.firstElementChild.cloneNode(true);
            container.appendChild(clone);
            bindRemove(clone);
            updateEmptyHint();
            if (options.afterMutation) options.afterMutation();
            const firstInput = clone.querySelector("input, select");
            if (firstInput) firstInput.focus();
        });

        container.querySelectorAll("." + options.rowClass).forEach(bindRemove);
        updateEmptyHint();
        if (options.afterMutation) options.afterMutation();
    }

    function allInterfaceRows() {
        return document.querySelectorAll(".iface-group-container .interface-row");
    }

    function setupInterfaceGroup(group) {
        const container = group.querySelector(".iface-group-container");
        const addBtn = group.querySelector(".add-iface-btn");
        const emptyHint = group.querySelector(".iface-group-empty");
        const template = document.getElementById("interface-row-template");
        const networkId = group.dataset.networkId || "";

        if (!container || !addBtn || !template) return;

        function updateEmpty() {
            if (!emptyHint) return;
            const rows = container.querySelectorAll(".interface-row");
            emptyHint.classList.toggle("d-none", rows.length > 0);
        }

        function bindRemove(row) {
            const removeBtn = row.querySelector(".remove-iface-btn");
            if (removeBtn) {
                removeBtn.addEventListener("click", function () {
                    if (checkInterfaceBeforeRemove(row) === false) return;
                    row.remove();
                    updateEmpty();
                    rebuildBroadcastSelects();
                });
            }
            bindInterfaceRow(row);
        }

        addBtn.addEventListener("click", function () {
            const clone = template.content.firstElementChild.cloneNode(true);
            const netInput = clone.querySelector(".iface-network-id");
            if (netInput) netInput.value = networkId;
            container.appendChild(clone);
            bindRemove(clone);
            updateEmpty();
            rebuildBroadcastSelects();
            const firstInput = clone.querySelector("input, select");
            if (firstInput) firstInput.focus();
        });

        container.querySelectorAll(".interface-row").forEach(bindRemove);
        updateEmpty();
    }

    document.querySelectorAll(".iface-group").forEach(setupInterfaceGroup);
    rebuildBroadcastSelects();

    function bindInterfaceRow(row) {
        const typeSelect = row.querySelector(".iface-type");
        const addressTypeSelect = row.querySelector(".iface-address-type");
        const ipBlock = row.querySelector(".iface-ip-block");
        const wifiBlock = row.querySelector(".iface-wifi-block");

        function refresh() {
            const tval = typeSelect ? typeSelect.value : "ethernet";
            const atval = addressTypeSelect ? addressTypeSelect.value : "static";

            const isPort = tval === "port";
            const isDhcp = atval === "dhcp";

            if (ipBlock) {
                ipBlock.classList.toggle("d-none", isPort);
            }
            if (wifiBlock) {
                wifiBlock.classList.toggle("d-none", tval !== "wifi");
            }

            const fieldsToHide = isPort || isDhcp;
            [".iface-field-address", ".iface-field-mask", ".iface-field-gateway", ".iface-field-dns"]
                .forEach(function (sel) {
                    const el = row.querySelector(sel);
                    if (el) el.classList.toggle("d-none", fieldsToHide);
                });

            const addrTypeField = row.querySelector(".iface-field-address-type");
            if (addrTypeField) addrTypeField.classList.toggle("d-none", isPort);

            const note = row.querySelector(".iface-field-dhcp-note");
            if (note) {
                note.classList.toggle("d-none", !(!isPort && isDhcp));
            }

            const isWifiAp = tval === "wifi_ap";
            const bandField = row.querySelector(".iface-field-band");
            if (bandField) bandField.classList.toggle("d-none", !isWifiAp);

            const macDefault = row.querySelector(".iface-mac-label-default");
            const macAp = row.querySelector(".iface-mac-label-ap");
            if (macDefault) macDefault.classList.toggle("d-none", isWifiAp);
            if (macAp) macAp.classList.toggle("d-none", !isWifiAp);

            if (isDhcp && !isPort) {
                const addr = row.querySelector(".iface-address");
                const mask = row.querySelector(".iface-mask");
                const gw = row.querySelector(".iface-gateway");
                const dns = row.querySelector(".iface-dns");
                if (addr) addr.value = "";
                if (mask) mask.value = "";
                if (gw) gw.value = "";
                if (dns) dns.value = "";
            }
        }

        if (typeSelect) typeSelect.addEventListener("change", function () { refresh(); rebuildBroadcastSelects(); });
        if (addressTypeSelect) addressTypeSelect.addEventListener("change", refresh);

        const nameInput = row.querySelector(".iface-name");
        if (nameInput) nameInput.addEventListener("input", rebuildBroadcastSelects);

        const bandSelect = row.querySelector(".iface-band");
        if (bandSelect) bandSelect.addEventListener("change", rebuildBroadcastSelects);

        refresh();
    }

    document.addEventListener("change", function (e) {
        if (e.target && e.target.classList.contains("wifi-broadcast-by")) {
            e.target.dataset.current = e.target.value;
        }
    });

    function checkInterfaceBeforeRemove(row) {
        const typeSelect = row.querySelector(".iface-type");
        if (!typeSelect || typeSelect.value !== "wifi_ap") return true;

        const rows = allInterfaceRows();
        let idx = -1;
        rows.forEach(function (r, i) { if (r === row) idx = i; });
        if (idx < 0) return true;

        const idInput = row.querySelector(".iface-id");
        const realId = idInput ? idInput.value.trim() : "";
        const targetValue = realId ? realId : ("new:" + idx);

        const ssids = [];
        document.querySelectorAll(".wifi-row").forEach(function (wrow) {
            const sel = wrow.querySelector(".wifi-broadcast-by");
            if (!sel) return;
            const current = sel.dataset.current || sel.value || "";
            if (current === targetValue) {
                const ssidInput = wrow.querySelector(".wifi-ssid");
                if (ssidInput && ssidInput.value.trim()) ssids.push(ssidInput.value.trim());
            }
        });

        if (ssids.length === 0) return true;

        const tpl = (window.DEVICES_FORM_CONFIG && window.DEVICES_FORM_CONFIG.cannotDeleteWifiAp) || "Cannot delete Wi-Fi AP interface: it broadcasts {ssids}.";
        alert(tpl.replace("{ssids}", ssids.join(", ")));
        return false;
    }

    function rebuildBroadcastSelects() {
        const rows = allInterfaceRows();
        const options = [{value: "", label: "—"}];
        rows.forEach(function (r, idx) {
            const type = r.querySelector(".iface-type");
            if (!type || type.value !== "wifi_ap") return;
            const idInput = r.querySelector(".iface-id");
            const nameInput = r.querySelector(".iface-name");
            const bandSelect = r.querySelector(".iface-band");
            const realId = idInput ? idInput.value.trim() : "";
            const name = nameInput ? nameInput.value.trim() : "";
            const band = bandSelect ? bandSelect.value : "";
            let label = name || "wifi_ap";
            if (band) label += " (" + band + ")";
            options.push({
                value: realId ? realId : ("new:" + idx),
                label: label,
            });
        });

        document.querySelectorAll(".wifi-broadcast-by").forEach(function (sel) {
            const current = sel.dataset.current || sel.value || "";
            while (sel.options.length > 0) sel.remove(0);
            options.forEach(function (o) {
                const opt = document.createElement("option");
                opt.value = o.value;
                opt.textContent = o.label;
                sel.appendChild(opt);
            });
            let matched = false;
            for (let i = 0; i < sel.options.length; i++) {
                if (sel.options[i].value === current) {
                    sel.selectedIndex = i;
                    matched = true;
                    break;
                }
            }
            if (!matched) sel.value = "";
            sel.dataset.current = sel.value;
        });
    }

    setupList({
        containerId: "ports-container",
        emptyHintId: "ports-empty",
        addBtnId: "add-port-btn",
        templateId: "port-row-template",
        rowClass: "port-row",
        removeBtnClass: "remove-port-btn",
    });

    setupList({
        containerId: "wifi-container",
        emptyHintId: "wifi-empty",
        addBtnId: "add-wifi-btn",
        templateId: "wifi-row-template",
        rowClass: "wifi-row",
        removeBtnClass: "remove-wifi-btn",
    });

    setupList({
        containerId: "dhcp-container",
        emptyHintId: "dhcp-empty",
        addBtnId: "add-dhcp-btn",
        templateId: "dhcp-row-template",
        rowClass: "dhcp-row",
        removeBtnClass: "remove-dhcp-btn",
    });

    setupList({
        containerId: "credentials-container",
        emptyHintId: "credentials-empty",
        addBtnId: "add-credential-btn",
        templateId: "credential-row-template",
        rowClass: "credential-row",
        removeBtnClass: "remove-credential-btn",
    });

    function bindPortForwardRow(row) {
        const targetType = row.querySelector(".pf-target-type");
        const deviceBlock = row.querySelector(".pf-target-device-block");
        const ipBlock = row.querySelector(".pf-target-ip-block");

        function refreshTarget() {
            const val = targetType ? targetType.value : "device";
            if (deviceBlock) deviceBlock.classList.toggle("d-none", val !== "device");
            if (ipBlock) ipBlock.classList.toggle("d-none", val !== "ip");
        }

        if (targetType) targetType.addEventListener("change", refreshTarget);
        refreshTarget();
    }

    setupList({
        containerId: "pf-container",
        emptyHintId: "pf-empty",
        addBtnId: "add-pf-btn",
        templateId: "pf-row-template",
        rowClass: "pf-row",
        removeBtnClass: "remove-pf-btn",
        afterBind: bindPortForwardRow,
    });

    setupList({
        containerId: "services-container",
        emptyHintId: "services-empty",
        addBtnId: "add-service-btn",
        templateId: "service-row-template",
        rowClass: "service-row",
        removeBtnClass: "remove-service-btn",
    });

    const vendorSelect = document.getElementById("vendor_id");
    const modelSelect = document.getElementById("model_id");

    function loadModels(vendorId, selectedModelId) {
        if (!modelSelect) return;

        while (modelSelect.options.length > 1) {
            modelSelect.remove(1);
        }

        if (!vendorId) return;

        fetch("/api/reference/vendors/" + encodeURIComponent(vendorId) + "/models", {
            credentials: "same-origin",
        })
            .then(function (r) {
                if (!r.ok) throw new Error("HTTP " + r.status);
                return r.json();
            })
            .then(function (models) {
                models.forEach(function (m) {
                    const opt = document.createElement("option");
                    opt.value = m.id;
                    opt.textContent = m.name;
                    if (selectedModelId && String(selectedModelId) === String(m.id)) {
                        opt.selected = true;
                    }
                    modelSelect.appendChild(opt);
                });
            })
            .catch(function () {});
    }

    if (vendorSelect && modelSelect) {
        const preselectedModel = modelSelect.dataset.selected || "";

        vendorSelect.addEventListener("change", function () {
            loadModels(vendorSelect.value, "");
        });

        if (vendorSelect.value) {
            loadModels(vendorSelect.value, preselectedModel);
        }
    }

    (function () {
        const select = document.getElementById("device_type_id");
        const section = document.getElementById("port-forwarding-section");
        if (!select || !section) return;

        function refresh() {
            const opt = select.options[select.selectedIndex];
            const supports = opt && opt.getAttribute("data-supports-pf") === "1";
            section.style.display = supports ? "" : "none";
        }

        select.addEventListener("change", refresh);
        refresh();
    })();
})();

