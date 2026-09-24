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

    function setupSide(prefix) {
        const deviceSelect = document.getElementById(prefix + "_device_id");
        const portSelect = document.getElementById(prefix + "_port_id");
        if (!deviceSelect || !portSelect) return;

        function fillPorts(selectedPortId) {
            while (portSelect.options.length > 1) {
                portSelect.remove(1);
            }

            const deviceId = deviceSelect.value;
            if (!deviceId) return;

            const device = byId[String(deviceId)];
            if (!device) return;

            device.ports.forEach(function (p) {
                const opt = document.createElement("option");
                opt.value = p.id;
                opt.textContent = p.interface_name
                    ? p.name + " (" + p.interface_name + ")"
                    : p.name;
                if (selectedPortId && String(selectedPortId) === String(p.id)) {
                    opt.selected = true;
                }
                portSelect.appendChild(opt);
            });
        }

        deviceSelect.addEventListener("change", function () {
            fillPorts("");
        });

        return { fillPorts: fillPorts };
    }

    const source = setupSide("source");
    const target = setupSide("target");

    // Восстановление после ошибки валидации: предзаполним селекты
    // по сохранённым id портов из form_data.
    const initialSourcePortId = "{{ form_data.source_port_id if form_data else '' }}";
    const initialTargetPortId = "{{ form_data.target_port_id if form_data else '' }}";

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

    if (source) {
        const found = findDeviceByPort(initialSourcePortId);
        if (found) {
            document.getElementById("source_device_id").value = found.device.id;
            source.fillPorts(found.port.id);
        }
    }
    if (target) {
        const found = findDeviceByPort(initialTargetPortId);
        if (found) {
            document.getElementById("target_device_id").value = found.device.id;
            target.fillPorts(found.port.id);
        }
    }
})();

