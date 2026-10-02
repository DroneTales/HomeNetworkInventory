// Home Network Inventory
// Drag-and-drop device between locations on Connections page.
//
// Copyright (C) Mike Petrichenko
// e-mail: btframework@gmail.com
// Project repository: https://github.com/DroneTales/HomeNetworkInventory
//
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
    "use strict";

    const cfg = window.CONNECTIONS_LIST_CONFIG || {};
    const apiUrl = "/connections/move-device";

    function toast(msg, ok) {
        const el = document.createElement("div");
        el.className = "position-fixed bottom-0 end-0 m-3 alert " + (ok ? "alert-success" : "alert-danger");
        el.style.zIndex = "9999";
        el.textContent = msg;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 2500);
    }

    let dragged = null;

    function onDragStart(e) {
        const handle = e.target.closest(".drag-handle");
        if (!handle) return;
        const li = handle.closest("li.location-device");
        if (!li) return;
        dragged = li;
        e.dataTransfer.effectAllowed = "move";
        e.dataTransfer.setData("text/plain", li.dataset.deviceId);
        li.classList.add("dragging");
    }

    function onDragEnd() {
        if (dragged) dragged.classList.remove("dragging");
        dragged = null;
        document.querySelectorAll(".location-group.drop-target").forEach(g => g.classList.remove("drop-target"));
    }

    function onDragOver(e) {
        const group = e.target.closest(".location-group");
        if (!group || !dragged) return;
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        document.querySelectorAll(".location-group.drop-target").forEach(g => {
            if (g !== group) g.classList.remove("drop-target");
        });
        group.classList.add("drop-target");
    }

    function onDragLeave(e) {
        const group = e.target.closest(".location-group");
        if (!group) return;
        if (!group.contains(e.relatedTarget)) group.classList.remove("drop-target");
    }

    function resortAndCount(group) {
        const ul = group.querySelector("ul.list-unstyled");
        if (ul) {
            const items = Array.from(ul.querySelectorAll("li.location-device"));
            items.sort((a, b) => {
                const an = (a.querySelector("a") || a).textContent.trim().toLowerCase();
                const bn = (b.querySelector("a") || b).textContent.trim().toLowerCase();
                return an.localeCompare(bn);
            });
            items.forEach(it => ul.appendChild(it));
        }
        const badge = group.querySelector(".location-count");
        if (badge) badge.textContent = group.querySelectorAll("li.location-device").length;
    }

    async function onDrop(e) {
        const group = e.target.closest(".location-group");
        if (!group || !dragged) return;
        e.preventDefault();
        group.classList.remove("drop-target");

        const li = dragged;
        const srcGroup = li.closest(".location-group");
        if (srcGroup === group) return;

        const deviceId = parseInt(li.dataset.deviceId, 10);
        const rawLoc = group.dataset.locationId;
        const locationId = rawLoc === "" ? null : parseInt(rawLoc, 10);

        try {
            const resp = await fetch(apiUrl, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({device_id: deviceId, location_id: locationId}),
            });
            const data = await resp.json();
            if (!resp.ok || !data.ok) {
                toast(cfg.errorMsg || "Failed to move device", false);
                return;
            }
            const ul = group.querySelector("ul.list-unstyled");
            if (ul) ul.appendChild(li);
            resortAndCount(group);
            if (srcGroup) resortAndCount(srcGroup);
            toast(cfg.successMsg || "Device moved", true);
        } catch (err) {
            toast(cfg.errorMsg || "Failed to move device", false);
        }
    }

    document.addEventListener("dragstart", onDragStart);
    document.addEventListener("dragend", onDragEnd);
    document.addEventListener("dragover", onDragOver);
    document.addEventListener("dragleave", onDragLeave);
    document.addEventListener("drop", onDrop);
})();
