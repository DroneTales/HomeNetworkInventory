// Home Network Inventory
// Show/hide password inputs.
//
// Copyright (C) Mike Petrichenko
// e-mail: btframework@gmail.com
// Project repository: https://github.com/DroneTales/HomeNetworkInventory
//
// SPDX-License-Identifier: AGPL-3.0-or-later

(function () {
    "use strict";

    document.querySelectorAll(".toggle-password").forEach(function (btn) {
        btn.addEventListener("click", function () {
            const wrapper = btn.closest(".password-cell");
            if (!wrapper) return;

            const mask = wrapper.querySelector(".password-mask");
            if (!mask) return;

            const realPassword = wrapper.dataset.password || "";
            const isMasked = mask.textContent.indexOf("•") !== -1;

            if (isMasked) {
                mask.textContent = realPassword;
                btn.textContent = "hide";
            } else {
                mask.textContent = "••••••••";
                btn.textContent = "show";
            }
        });
    });
})();

