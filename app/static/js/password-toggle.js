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

