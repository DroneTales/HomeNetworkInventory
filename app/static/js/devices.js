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
                    row.remove();
                    updateEmptyHint();
                    if (options.afterBind) options.afterBind(row);
                });
            }
            if (options.afterBind) options.afterBind(row);
        }

        addBtn.addEventListener("click", function () {
            const clone = template.content.firstElementChild.cloneNode(true);
            container.appendChild(clone);
            bindRemove(clone);
            updateEmptyHint();
            const firstInput = clone.querySelector("input, select");
            if (firstInput) firstInput.focus();
        });

        container.querySelectorAll("." + options.rowClass).forEach(bindRemove);
        updateEmptyHint();
    }

    setupList({
        containerId: "interfaces-container",
        emptyHintId: "interfaces-empty",
        addBtnId: "add-interface-btn",
        templateId: "interface-row-template",
        rowClass: "interface-row",
        removeBtnClass: "remove-iface-btn",
        afterBind: bindInterfaceRow,
    });

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

            const note = row.querySelector(".iface-field-dhcp-note");
            if (note) {
                note.classList.toggle("d-none", !(!isPort && isDhcp));
            }

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

        if (typeSelect) typeSelect.addEventListener("change", refresh);
        if (addressTypeSelect) addressTypeSelect.addEventListener("change", refresh);
        refresh();
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
})();

