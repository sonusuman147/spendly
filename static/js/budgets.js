// ================================================================== //
// Spendly — Budgets Page Behaviour (vanilla JS)                      //
//                                                                   //
// This module is frontend-only. It renders the server-computed budget
// data (window.SPENDLY_BUDGETS.budget) into the charts and tables on
// the Budgets page using the existing design system (CSS variables,
// Lucide icons, tabular numerals). It adds:
//   - animated progress bars
//   - create / edit / delete budget modals (server-side POST)
//   - reset-to-defaults confirmation
//   - quick-action shortcuts
//   - export toast feedback
// ================================================================== //

(function () {
    'use strict';

    /* ------------------------------------------------------------------ */
    /* Data source (server-provided)                                       */
    /* ------------------------------------------------------------------ */

    var cfg = window.SPENDLY_BUDGETS || {};
    var budget = cfg.budget || {};
    var urls = cfg.urls || {};

    /* ------------------------------------------------------------------ */
    /* Helpers                                                             */
    /* ------------------------------------------------------------------ */

    function getEl(sel) { return document.querySelector(sel); }
    function getAll(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

    function money(n) {
        return '\u20B9' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function refreshIcons() {
        if (window.lucide) window.lucide.createIcons();
    }

    // Build an action URL from a "/…/0/…" template by replacing the zero
    // placeholder *segment* with the real record id. Returns "" when the id
    // is missing or invalid so we never POST to /budgets/0/delete (404).
    function buildActionUrl(template, id) {
        var n = parseInt(id, 10);
        if (!template || isNaN(n) || n <= 0) return '';
        return template.replace(/\/0(?=\/|$)/, '/' + n);
    }

    /* ------------------------------------------------------------------ */
    /* Animate progress bars from 0 → target width                         */
    /* ------------------------------------------------------------------ */

    function animateFills() {
        getAll('.budget-progress-fill[data-fill], .budget-table-progress .budget-progress-fill[data-fill]').forEach(function (fill) {
            var pct = parseFloat(fill.getAttribute('data-pct')) || 0;
            fill.style.width = pct + '%';
        });
    }

    /* ------------------------------------------------------------------ */
    /* Modal helpers                                                       */
    /* ------------------------------------------------------------------ */

    function openModal(modal) {
        if (modal) modal.hidden = false;
    }

    function closeModal(modal) {
        if (modal) modal.hidden = true;
    }

    function closeAllModals() {
        getAll('.budget-modal').forEach(function (m) { m.hidden = true; });
    }

    /* ------------------------------------------------------------------ */
    /* Create / Edit Budget modal                                          */
    /* ------------------------------------------------------------------ */

    function openCreateModal() {
        var modal = getEl('[data-budget-modal]');
        if (!modal) return;
        var title = getEl('[data-budget-modal-title]');
        var submit = getEl('[data-budget-submit]');
        var form = getEl('#budgetForm');
        var category = getEl('#budgetFormCategory');
        var limit = getEl('#budgetFormLimit');

        if (title) title.textContent = 'Create Budget';
        if (submit) submit.textContent = 'Create Budget';
        if (form) form.action = urls.add || '';
        if (category) category.disabled = false;
        if (limit) limit.value = '';

        openModal(modal);
    }

    function openEditModal(name, id, limit) {
        var modal = getEl('[data-budget-modal]');
        if (!modal) return;
        var title = getEl('[data-budget-modal-title]');
        var submit = getEl('[data-budget-submit]');
        var form = getEl('#budgetForm');
        var category = getEl('#budgetFormCategory');
        var limitInput = getEl('#budgetFormLimit');

        var action = buildActionUrl(urls.edit, id);
        if (!action) return; // No valid id — never submit to an invalid URL

        if (title) title.textContent = 'Edit ' + name + ' Budget';
        if (submit) submit.textContent = 'Update Budget';
        if (form) form.action = action;
        if (category) {
            category.value = name;
            category.disabled = true; // Category is fixed when editing
        }
        if (limitInput) limitInput.value = limit;

        openModal(modal);
    }

    /* ------------------------------------------------------------------ */
    /* Delete Budget modal                                                 */
    /* ------------------------------------------------------------------ */

    function openDeleteModal(name, id) {
        var modal = getEl('[data-budget-delete-modal]');
        if (!modal) return;
        var text = getEl('[data-budget-delete-text]');
        var form = getEl('#budgetDeleteForm');

        var action = buildActionUrl(urls.delete, id);
        if (!action) return; // No valid id — never submit to an invalid URL

        if (text) text.textContent = 'Are you sure you want to delete the ' + name + ' budget? It will fall back to its default limit.';
        if (form) form.action = action;

        openModal(modal);
    }

    /* ------------------------------------------------------------------ */
    /* Reset confirmation                                                  */
    /* ------------------------------------------------------------------ */

    function confirmReset() {
        if (window.confirm('Reset all budgets to their default limits? This cannot be undone.')) {
            var form = getEl('[data-budget-reset]');
            if (form) form.submit();
        }
    }

    /* ------------------------------------------------------------------ */
    /* Toast                                                               */
    /* ------------------------------------------------------------------ */

    function showToast(message, isError) {
        var toast = getEl('[data-budget-toast]');
        if (!toast) return;
        var text = getEl('[data-budget-toast-text]');
        if (text) text.textContent = message;
        toast.classList.toggle('is-error', !!isError);
        toast.hidden = false;
        refreshIcons();
        clearTimeout(showToast._t);
        showToast._t = setTimeout(function () { toast.hidden = true; }, 2600);
    }

    /* ------------------------------------------------------------------ */
    /* Bind events                                                         */
    /* ------------------------------------------------------------------ */

    function bindModals() {
        // Create button (header + empty state + quick action)
        getAll('[data-budget-create]').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                openCreateModal();
            });
        });

        // Edit buttons in the table
        getAll('[data-budget-edit]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var name = btn.getAttribute('data-budget-edit') || '';
                var id = btn.getAttribute('data-budget-id') || '0';
                var limit = btn.getAttribute('data-budget-limit') || '0';
                openEditModal(name, id, limit);
            });
        });

        // Delete buttons in the table
        getAll('[data-budget-delete]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var name = btn.getAttribute('data-budget-delete') || '';
                var id = btn.getAttribute('data-budget-id') || '0';
                openDeleteModal(name, id);
            });
        });

        // Close buttons / backdrop
        getAll('[data-modal-close]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                closeAllModals();
            });
        });

        // Quick action: edit first budget
        var editFirst = getEl('[data-budget-edit-first]');
        if (editFirst) {
            editFirst.addEventListener('click', function (e) {
                e.preventDefault();
                var firstEdit = getEl('[data-budget-edit]');
                if (firstEdit) {
                    firstEdit.click();
                } else {
                    openCreateModal();
                }
            });
        }

        // Quick action: reset defaults
        var resetQuick = getEl('[data-budget-reset-quick]');
        if (resetQuick) {
            resetQuick.addEventListener('click', function (e) {
                e.preventDefault();
                confirmReset();
            });
        }

        // Reset form in header
        var resetForm = getEl('[data-budget-reset]');
        if (resetForm) {
            resetForm.addEventListener('submit', function (e) {
                if (!window.confirm('Reset all budgets to their default limits? This cannot be undone.')) {
                    e.preventDefault();
                }
            });
        }

        // Form submit feedback
        var form = getEl('#budgetForm');
        if (form) {
            form.addEventListener('submit', function () {
                closeAllModals();
                showToast('Budget saved successfully');
            });
        }

        var deleteForm = getEl('#budgetDeleteForm');
        if (deleteForm) {
            deleteForm.addEventListener('submit', function () {
                closeAllModals();
                showToast('Budget deleted');
            });
        }
    }

    /* ------------------------------------------------------------------ */
    /* Init                                                                */
    /* ------------------------------------------------------------------ */

    function init() {
        bindModals();
        // Animate progress bars after a short delay so the page paints first.
        setTimeout(function () {
            animateFills();
            refreshIcons();
        }, 100);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();