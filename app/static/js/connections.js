// Home Network Inventory
// Connections list: device/port cascading selects.
//
// Copyright (C) Mike Petrichenko
// e-mail: btframework@gmail.com
// Project repository: https://github.com/DroneTales/HomeNetworkInventory
//
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
    "use strict";

    const payloadEl = document.getElementById("devices-payload");
    if (!payloadEl) return;

    let devices;
    try {
        devices = JSON.parse(payloadEl.textContent || "[]");
    } catch (e) {
        return;
    }

    const byId = {};
    devices.forEach(function (d) {
        byId[String(d.id)] = d;
    });

    const typeEl = document.getElementById("connection_type");

    function currentType() {
        return typeEl ? typeEl.value : "physical";
    }

    function deviceEl(side) {
        return document.getElementById(side + "_device_id");
    }

    function portEl(side) {
        return document.getElementById(side + "_port_id");
    }

    function portValue(side) {
        const el = portEl(side);
        return el ? el.value : "";
    }

    function fillPorts(side, selectedPortId, otherPortId) {
        const devSelect = deviceEl(side);
        const select = portEl(side);
        if (!devSelect || !select) return;

        while (select.options.length > 1) {
            select.remove(1);
        }

        const deviceId = devSelect.value;
        if (!deviceId) return;

        const device = byId[String(deviceId)];
        if (!device) return;

        const connType = currentType();
        device.ports.forEach(function (p) {
            // Never offer the port already chosen on the other side.
            if (otherPortId && String(otherPortId) === String(p.id)) return;
            const isCurrent = selectedPortId && String(selectedPortId) === String(p.id);
            const busy = (p.occupied_types || []).indexOf(connType) !== -1;
            if (busy && !isCurrent) return;
            const opt = document.createElement("option");
            opt.value = p.id;
            opt.textContent = p.interface_name
                ? p.name + " (" + p.interface_name + ")"
                : p.name;
            if (isCurrent) {
                opt.selected = true;
            }
            select.appendChild(opt);
        });
    }

    function refresh() {
        const srcVal = portValue("source");
        const tgtVal = portValue("target");
        fillPorts("source", srcVal, tgtVal);
        fillPorts("target", tgtVal, portValue("source"));
    }

    ["source", "target"].forEach(function (side) {
        const dev = deviceEl(side);
        const port = portEl(side);
        if (dev) dev.addEventListener("change", refresh);
        if (port) port.addEventListener("change", refresh);
    });

    if (typeEl) typeEl.addEventListener("change", refresh);

    // Initial values (edit mode or validation-error restore) come from a JSON tag.
    const stateEl = document.getElementById("form-state");
    let state = {};
    if (stateEl) {
        try {
            state = JSON.parse(stateEl.textContent || "{}");
        } catch (e) {
            state = {};
        }
    }

    function findDeviceByPort(portId) {
        if (!portId) return null;
        for (let i = 0; i < devices.length; i++) {
            const d = devices[i];
            for (let j = 0; j < d.ports.length; j++) {
                if (String(d.ports[j].id) === String(portId)) {
                    return { device: d, port: d.ports[j] };
                }
            }
        }
        return null;
    }

    const initialSourcePortId = state.source_port_id || "";
    const initialTargetPortId = state.target_port_id || "";

    const foundSource = findDeviceByPort(initialSourcePortId);
    if (foundSource && deviceEl("source")) deviceEl("source").value = foundSource.device.id;
    const foundTarget = findDeviceByPort(initialTargetPortId);
    if (foundTarget && deviceEl("target")) deviceEl("target").value = foundTarget.device.id;

    fillPorts("source", initialSourcePortId, initialTargetPortId);
    fillPorts("target", initialTargetPortId, initialSourcePortId);
})();
