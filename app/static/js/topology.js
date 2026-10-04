// Home Network Inventory
// Topology graph rendering and side panel.
//
// Copyright (C) Mike Petrichenko
// e-mail: btframework@gmail.com
// Project repository: https://github.com/DroneTales/HomeNetworkInventory
//
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
    "use strict";

    const container = document.getElementById("topology-container");
    if (!container) return;

    const legend = document.getElementById("topo-legend");
    const legendToggle = document.getElementById("topo-legend-toggle");
    if (legend && legendToggle) {
        legendToggle.addEventListener("click", function () {
            legend.classList.toggle("open");
        });
    }

    const dataUrl = container.dataset.dataUrl || "/topology/data";
    const canEdit = container.dataset.canEdit === "1";
    const positionsUrl = "/topology/positions";

    fetch(dataUrl, { credentials: "same-origin" })
        .then(function (r) { return r.json(); })
        .then(function (data) { render(data); })
        .catch(function (err) {
            container.innerHTML = '<div class="text-danger small p-3">Failed to load topology: ' + err + '</div>';
        });

    function render(data) {
        const elements = [];

        const portsByDevice = {};
        const portsById = {};
        const devicesById = {};
        data.ports.forEach(function (p) {
            portsById[p.id] = p;
            if (!portsByDevice[p.device_id]) portsByDevice[p.device_id] = [];
            portsByDevice[p.device_id].push(p);
        });
        data.devices.forEach(function (d) {
            devicesById[d.device_id] = d;
        });

        const edgesByPort = {};
        data.edges.forEach(function (e) {
            if (!edgesByPort[e.source]) edgesByPort[e.source] = [];
            if (!edgesByPort[e.target]) edgesByPort[e.target] = [];
            edgesByPort[e.source].push(e);
            edgesByPort[e.target].push(e);
        });

        elements.push({
            data: {
                id: "site-root",
                label: data.site.name,
                type: "site",
            }
        });

        data.locations.forEach(function (loc) {
            elements.push({
                data: {
                    id: "loc-" + loc.id,
                    label: loc.name,
                    type: "location",
                    parent: "site-root",
                }
            });
        });

        const hasUnassigned = data.devices.some(function (d) { return !d.location_id; });
        if (hasUnassigned) {
            elements.push({
                data: {
                    id: "loc-unassigned",
                    label: "",
                    type: "unassigned",
                    parent: "site-root",
                }
            });
        }

        data.devices.forEach(function (d) {
            const parent = d.location_id ? ("loc-" + d.location_id) : "loc-unassigned";
            elements.push({
                data: {
                    id: d.id,
                    label: d.label,
                    human_name: d.human_name,
                    category: d.category,
                    icon: d.icon,
                    ip: d.ip,
                    mac: d.mac,
                    has_wifi: d.has_wifi ? 1 : 0,
                    is_wifi_client: d.is_wifi_client ? 1 : 0,
                    wifi_ssids: (d.wifi_ssids || []).join(", "),
                    wifi_client_ssids: (d.wifi_client_ssids || []).join(", "),
                    wifi_clients: (d.wifi_clients || []).join(","),
                    wifi_broadcasters: (d.wifi_broadcasters || []).join(","),
                    parent: parent,
                },
                classes: "leaf",
            });
        });

        const deviceIds = new Set(data.devices.map(function (d) { return d.id; }));
        const portDevice = {};
        data.ports.forEach(function (p) {
            portDevice[p.id] = "device-" + p.device_id;
        });

        data.edges.forEach(function (e) {
            const srcDev = portDevice[e.source];
            const tgtDev = portDevice[e.target];
            if (!srcDev || !tgtDev) return;
            if (!deviceIds.has(srcDev) || !deviceIds.has(tgtDev)) return;
            if (srcDev === tgtDev) return;
            elements.push({
                data: {
                    id: e.id,
                    source: srcDev,
                    target: tgtDev,
                    type: e.type,
                    cable: e.cable,
                }
            });
        });

        container.innerHTML = "";

        const cy = cytoscape({
            container: container,
            elements: elements,
            style: [
                {
                    selector: "node[type = 'site']",
                    style: {
                        "shape": "round-rectangle",
                        "background-color": "#0f172a",
                        "background-opacity": 0.4,
                        "border-color": "#1e40af",
                        "border-width": 2,
                        "border-style": "solid",
                        "label": "data(label)",
                        "text-valign": "top",
                        "text-halign": "center",
                        "text-margin-y": -8,
                        "font-size": 14,
                        "font-weight": "bold",
                        "color": "#60a5fa",
                        "padding": 30,
                    }
                },
                {
                    selector: "node[type = 'location']",
                    style: {
                        "shape": "round-rectangle",
                        "background-color": "#1e293b",
                        "background-opacity": 0.35,
                        "border-color": "#334155",
                        "border-width": 1,
                        "border-style": "dashed",
                        "label": "data(label)",
                        "text-valign": "top",
                        "text-halign": "center",
                        "text-margin-y": -12,
                        "font-size": 11,
                        "font-weight": 700,
                        "color": "#cbd5e1",
                        "text-transform": "uppercase",
                        "text-outline-color": "#0b0f14",
                        "text-outline-width": 3,
                        "padding": 16,
                    }
                },
                {
                    selector: "node[type = 'unassigned']",
                    style: {
                        "shape": "round-rectangle",
                        "background-color": "#7c2d12",
                        "background-opacity": 0.25,
                        "border-color": "#ea580c",
                        "border-width": 2,
                        "border-style": "dashed",
                        "label": "",
                        "padding": 16,
                    }
                },
                {
                    selector: "node.leaf",
                    style: {
                        "shape": "round-rectangle",
                        "background-color": "#1e293b",
                        "background-opacity": 0,
                        "border-color": "#334155",
                        "border-width": 0,
                        "label": "",
                        "width": 60,
                        "height": 60,
                    }
                },
                {
                    selector: "edge",
                    style: {
                        "width": 2,
                        "line-color": "#475569",
                        "target-arrow-color": "#475569",
                        "curve-style": "bezier",
                    }
                },
                {
                    selector: "edge[type = 'logical']",
                    style: {
                        "line-style": "dashed",
                        "line-color": "#64748b",
                    }
                },
                {
                    selector: "node:selected",
                    style: {
                        "border-color": "#3b82f6",
                        "border-width": 3,
                    }
                },
                {
                    selector: "node.topo-highlighted",
                    style: {
                        "border-color": "#fbbf24",
                        "border-width": 3,
                        "border-style": "solid",
                    }
                },
                {
                    selector: "node.topo-related",
                    style: {
                        "border-color": "#22c55e",
                        "border-width": 3,
                        "border-style": "solid",
                    }
                }
            ],
            layout: {
                name: "fcose",
                animate: true,
                animationDuration: 500,
                nodeRepulsion: 8000,
                idealEdgeLength: 120,
            },
            wheelSensitivity: 0.2,
        });

        cy.nodeHtmlLabel([
            {
                query: "node.leaf",
                tpl: function (d) {
                    let wifi = '';
                    if (d.has_wifi) {
                        wifi = '<span class="topo-badge topo-badge-wifi" title="Wi-Fi access point"><i class="fa-solid fa-wifi"></i></span>';
                    } else if (d.is_wifi_client) {
                        wifi = '<span class="topo-badge topo-badge-wifi-client" title="Connected via Wi-Fi"><i class="fa-solid fa-wifi"></i></span>';
                    }
                    return '<div class="topo-node topo-cat-' + d.category + '">' +
                           '<i class="fa-solid ' + d.icon + '"></i>' +
                           wifi +
                           '</div>';
                }
            },
        ]);

        const hasPositions = (data.positions || []).length > 0;
        const savedPositions = {};
        (data.positions || []).forEach(function (p) {
            savedPositions["device-" + p.device_id] = { x: p.x, y: p.y };
        });

        cy.ready(function () {
            cy.on("layoutstop", function () {
                if (!hasPositions) return;
                cy.nodes("node.leaf").forEach(function (n) {
                    const pos = savedPositions[n.id()];
                    if (pos) {
                        n.position({ x: pos.x, y: pos.y });
                    }
                });
                cy.fit(null, 30);
            });
        });

        function runFcose() {
            cy.layout({
                name: "fcose",
                animate: true,
                animationDuration: 500,
                nodeRepulsion: 8000,
                idealEdgeLength: 120,
            }).run();
        }

        function collectAllPositions() {
            const list = [];
            cy.nodes("node.leaf").forEach(function (n) {
                const p = n.position();
                list.push({
                    device_id: parseInt(n.id().replace("device-", ""), 10),
                    x: p.x,
                    y: p.y,
                });
            });
            return list;
        }

        const saveBtn = document.getElementById("topology-save-btn");
        if (saveBtn && canEdit) {
            saveBtn.addEventListener("click", function () {
                const list = collectAllPositions();
                if (list.length === 0) return;
                saveBtn.disabled = true;
                fetch(positionsUrl, {
                    method: "POST",
                    credentials: "same-origin",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ positions: list }),
                }).then(function (r) {
                    return r.json();
                }).then(function (data) {
                    if (data && data.ok) {
                        saveBtn.classList.remove("btn-primary");
                        saveBtn.classList.add("btn-success");
                        setTimeout(function () {
                            saveBtn.classList.remove("btn-success");
                            saveBtn.classList.add("btn-primary");
                        }, 1200);
                    }
                }).catch(function () { /* silent */ })
                  .finally(function () { saveBtn.disabled = false; });
            });
        }

        const resetBtn = document.getElementById("topology-reset-btn");
        if (resetBtn && canEdit) {
            resetBtn.addEventListener("click", function () {
                const msg = t("topology.reset.confirm");
                if (!window.confirm(msg)) return;
                resetBtn.disabled = true;
                fetch(positionsUrl, {
                    method: "DELETE",
                    credentials: "same-origin",
                }).then(function () {
                    runFcose();
                }).finally(function () { resetBtn.disabled = false; });
            });
        }

        const tooltip = document.createElement("div");
        tooltip.className = "topo-tooltip";
        tooltip.style.position = "fixed";
        tooltip.style.zIndex = "99999";
        tooltip.style.pointerEvents = "none";
        document.body.appendChild(tooltip);

        cy.on("mouseover", "node.leaf", function (e) {
            const d = e.target.data();
            const orig = e.originalEvent || {};
            const x = orig.clientX != null ? orig.clientX : 0;
            const y = orig.clientY != null ? orig.clientY : 0;

            let html = "";
            if (d.human_name) {
                html += '<div class="topo-tooltip-title">' + d.human_name + '</div>';
                html += '<div class="topo-tooltip-sub">' + d.label + '</div>';
            } else {
                html += '<div class="topo-tooltip-title">' + d.label + '</div>';
            }
            if (d.ip) {
                html += '<div class="topo-tooltip-value">' + d.ip + '</div>';
            }
            if (d.wifi_ssids) {
                html += '<div class="topo-tooltip-wifi">' + d.wifi_ssids + ' →</div>';
            }
            if (d.wifi_client_ssids) {
                html += '<div class="topo-tooltip-wifi">→ ' + d.wifi_client_ssids + '</div>';
            }
            tooltip.innerHTML = html;
            tooltip.style.display = "block";
            tooltip.style.left = (x + 16) + "px";
            tooltip.style.top = (y + 16) + "px";
            requestAnimationFrame(function () {
                tooltip.classList.add("visible");
                positionTooltip(x, y);
            });
        });

        function positionTooltip(x, y) {
            const rect = tooltip.getBoundingClientRect();
            let left = x + 16;
            let top = y + 16;
            if (left + rect.width > window.innerWidth - 8) {
                left = x - rect.width - 16;
            }
            if (top + rect.height > window.innerHeight - 8) {
                top = y - rect.height - 16;
            }
            if (left < 8) left = 8;
            if (top < 8) top = 8;
            tooltip.style.left = left + "px";
            tooltip.style.top = top + "px";
        }

        cy.on("mousemove", "node.leaf", function (e) {
            if (tooltip.style.display !== "block") return;
            const orig = e.originalEvent || {};
            if (orig.clientX == null) return;
            positionTooltip(orig.clientX, orig.clientY);
        });

        cy.on("mouseout", "node.leaf", function () {
            tooltip.classList.remove("visible");
            tooltip.style.display = "none";
        });

        const fitBtn = document.getElementById("topology-fit-btn");
        if (fitBtn) {
            fitBtn.addEventListener("click", function () {
                cy.fit(null, 30);
            });
        }

        const panel = document.getElementById("topo-panel");
        const panelTitle = document.getElementById("topo-panel-title");
        const panelBody = document.getElementById("topo-panel-body");
        const panelClose = document.getElementById("topo-panel-close");

        function clearHighlight() {
            cy.elements("node.topo-highlighted").removeClass("topo-highlighted");
            cy.elements("node.topo-related").removeClass("topo-related");
        }

        function setHighlight(nodeId) {
            clearHighlight();
            const n = cy.getElementById(nodeId);
            if (n && !n.empty()) {
                n.addClass("topo-highlighted");
                setRelated(n.data());
            }
        }

        function setRelated(d) {
            function mark(ids) {
                String(ids || "").split(",").forEach(function (raw) {
                    const id = raw.trim();
                    if (!id) return;
                    const el = cy.getElementById("device-" + id);
                    if (el && !el.empty()) el.addClass("topo-related");
                });
            }
            mark(d.wifi_clients);
            mark(d.wifi_broadcasters);
        }

        function closePanel() {
            panel.classList.remove("open");
            clearHighlight();
        }

        if (panelClose) {
            panelClose.addEventListener("click", closePanel);
        }

        function openDevicePanel(deviceNodeId, focus) {
            const node = cy.getElementById(deviceNodeId);
            if (!node || node.empty()) return;
            const d = node.data();

            const deviceId = parseInt(deviceNodeId.replace("device-", ""), 10);
            const devicesPayload = devicesById[deviceId];
            if (!devicesPayload) return;

            setHighlight(deviceNodeId);

            if (focus) {
                cy.animate({
                    center: { eles: node },
                    zoom: Math.max(cy.zoom(), 1.2),
                }, { duration: 300 });
            }

            let titleHtml = "";
            if (d.human_name) {
                titleHtml += d.label ? "" : "";
                titleHtml += esc(d.human_name);
                titleHtml += '<span class="topo-panel-sub">' + esc(d.label) + '</span>';
            } else {
                titleHtml += esc(d.label);
            }
            panelTitle.innerHTML = titleHtml;

            let body = "";
            body += '<div class="topo-panel-actions">';
            body += '<a href="/devices/' + deviceId + '">' + esc(t("topology.open_device")) + '</a>';
            body += '</div>';

            const myPorts = portsByDevice[deviceId] || [];
            if (myPorts.length > 0) {
                body += '<div class="topo-panel-section">';
                body += '<div class="topo-panel-section-title">' + esc(t("topology.section.ports")) + '</div>';
                body += '<div class="topo-port-list">';
                myPorts.forEach(function (p) {
                    const portIdStr = "port-" + p.port_id;
                    const edges = edgesByPort[portIdStr] || [];
                    let targets = [];
                    edges.forEach(function (e) {
                        const otherPortId = (e.source === portIdStr) ? e.target : e.source;
                        const otherPort = portsById[otherPortId];
                        if (otherPort) {
                            const otherDev = devicesById[otherPort.device_id];
                            if (otherDev) {
                                targets.push({
                                    device_id: otherDev.device_id,
                                    hostname: otherDev.label,
                                    port: otherPort.label
                                });
                            }
                        }
                    });
                    body += '<div class="topo-port-row">';
                    body += '<span class="topo-port-name">' + esc(p.label) + '</span>';
                    if (targets.length === 0) {
                        body += '<span class="topo-port-none">' + esc(t("topology.port.none")) + '</span>';
                    } else {
                        targets.forEach(function (tg) {
                            body += '<span class="topo-port-arrow">→</span>';
                            body += '<a class="topo-port-target" data-device="device-' + tg.device_id + '">' +
                                    esc(tg.hostname) + ' / ' + esc(tg.port) + '</a>';
                        });
                    }
                    body += '</div>';
                });
                body += '</div></div>';
            } else {
                body += '<div class="topo-panel-section">';
                body += '<div class="topo-port-none">' + esc(t("topology.ports.empty")) + '</div>';
                body += '</div>';
            }

            panelBody.innerHTML = body;
            panelBody.querySelectorAll(".topo-port-target").forEach(function (el) {
                el.addEventListener("click", function () {
                    const targetId = el.dataset.device;
                    openDevicePanel(targetId, true);
                });
            });

            panel.classList.add("open");
        }

        cy.on("tap", "node.leaf", function (e) {
            openDevicePanel(e.target.id(), false);
        });

        cy.on("tap", function (e) {
            if (e.target === cy) {
                closePanel();
            }
        });

        function esc(s) {
            return String(s == null ? "" : s)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;");
        }

        function t(key) {
            return (window.TOPO_I18N && window.TOPO_I18N[key]) || key;
        }

        window.topologyCy = cy;
    }
})();
