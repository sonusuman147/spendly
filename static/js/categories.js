/* ================================================================== */
/* Spendly — Categories Module JS                                      */
/* Vanilla JS only — no frameworks, no jQuery                         */
/* ================================================================== */

(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", function () {

        /* ---------------------------------------------------------- */
        /* Icon picker                                                 */
        /* ---------------------------------------------------------- */
        var iconGrid = document.getElementById("iconGrid");
        var iconInput = document.getElementById("iconInput");

        if (iconGrid && iconInput) {
            iconGrid.addEventListener("click", function (event) {
                var btn = event.target.closest(".cat-icon-option");
                if (!btn) return;

                // Update internal state.
                iconInput.value = btn.getAttribute("data-icon");

                // Update the selected visual state.
                var current = iconGrid.querySelector(".cat-icon-option.is-selected");
                if (current) current.classList.remove("is-selected");
                btn.classList.add("is-selected");

                // Re-draw lucide icons in the picker (lucide only renders on load).
                if (typeof lucide !== "undefined") {
                    lucide.createIcons();
                }
            });
        }

        /* ---------------------------------------------------------- */
        /* Color picker                                                */
        /* ---------------------------------------------------------- */
        var colorGrid = document.getElementById("colorGrid");
        var colorInput = document.getElementById("colorInput");

        if (colorGrid && colorInput) {
            colorGrid.addEventListener("click", function (event) {
                var btn = event.target.closest(".cat-color-option");
                if (!btn) return;

                colorInput.value = btn.getAttribute("data-color");

                var current = colorGrid.querySelector(".cat-color-option.is-selected");
                if (current) current.classList.remove("is-selected");
                btn.classList.add("is-selected");
            });
        }

        /* ---------------------------------------------------------- */
        /* Filter auto-submit (search/sort/per_page)                   */
        /* ---------------------------------------------------------- */
        var filterForm = document.getElementById("categoryFilterForm");
        if (filterForm) {
            var sortSelect = document.getElementById("filterSort");
            var perPageSelect = document.getElementById("filterPerPage");
            var resetBtn = document.getElementById("filterReset");
            var searchInput = document.getElementById("filterSearch");

            function submitFilter() {
                filterForm.submit();
            }

            // Auto-submit on sort / per-page change.
            if (sortSelect) {
                sortSelect.addEventListener("change", submitFilter);
            }
            if (perPageSelect) {
                perPageSelect.addEventListener("change", submitFilter);
            }

            // Debounced search auto-submit.
            if (searchInput) {
                var debounceTimer = null;
                searchInput.addEventListener("input", function () {
                    clearTimeout(debounceTimer);
                    debounceTimer = setTimeout(submitFilter, 450);
                });
            }

            // Reset filters.
            if (resetBtn) {
                resetBtn.addEventListener("click", function () {
                    window.location.href = resetBtn.getAttribute("data-href") ||
                        (filterForm.getAttribute("action") || "/categories");
                });
            }
        }

        /* ---------------------------------------------------------- */
        /* Delete confirmation (in-use category)                       */
        /* ---------------------------------------------------------- */
        var confirmCheckbox = document.getElementById("confirmDelete");
        var deleteBtn = document.getElementById("deleteBtn");

        if (confirmCheckbox && deleteBtn) {
            function updateDeleteState() {
                if (confirmCheckbox.checked) {
                    deleteBtn.removeAttribute("disabled");
                    deleteBtn.classList.remove("is-disabled");
                } else {
                    deleteBtn.setAttribute("disabled", "disabled");
                    deleteBtn.classList.add("is-disabled");
                }
            }

            confirmCheckbox.addEventListener("change", updateDeleteState);
            // Init to disabled.
            updateDeleteState();
        }

        /* ---------------------------------------------------------- */
        /* Lucide icons freshly inserted via JS                        */
        /* ---------------------------------------------------------- */
        if (typeof lucide !== "undefined") {
            lucide.createIcons();
        }
    });
})();

