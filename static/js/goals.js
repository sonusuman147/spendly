// ================================================================== //
// Spendly — Goals Page Behaviour (vanilla JS)                        //
//                                                                   //
// This module is frontend-only. It reads the server-computed goal    //
// data (window.SPENDLY_GOALS.goal) and wires up the interactive      //
// behaviour: modals (create/edit/delete/add funds), quick actions,   //
// animated progress bars, and toast feedback. Filters and sorting    //
// are handled server-side via GET query params.                      //
// ================================================================== //

(function () {
    'use strict';

    /* ------------------------------------------------------------------ */
    /* Data source (server-provided)                                       */
    /* ------------------------------------------------------------------ */

    var cfg = window.SPENDLY_GOALS || {};
    var goal = cfg.goal || {};
    var urls = cfg.urls || {};

    /* ------------------------------------------------------------------ */
    /* Helpers                                                             */
    /* ------------------------------------------------------------------ */

    function getEl(sel) { return document.querySelector(sel); }
    function getAll(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

    function money(n) {
        return '\u20B9' + Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });
    }

    function refreshIcons() {
        if (window.lucide) window.lucide.createIcons();
    }

    /* ------------------------------------------------------------------ */
    /* Animate progress bars from 0 → target width                         */
    /* ------------------------------------------------------------------ */

    function animateFills() {
        getAll('.goal-progress-fill[data-fill]').forEach(function (fill) {
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

    function closeAllModals() {
        getAll('.goal-modal').forEach(function (m) { m.hidden = true; });
    }

    /* ------------------------------------------------------------------ */
    /* Create / Edit Goal modal                                            */
    /* ------------------------------------------------------------------ */

    function openCreateModal() {
        var modal = getEl('[data-goal-modal]');
        if (!modal) return;
        var title = getEl('[data-goal-modal-title]');
        var submit = getEl('[data-goal-submit]');
        var form = getEl('#goalForm');
        var name = getEl('#goalFormName');
        var category = getEl('#goalFormCategory');
        var target = getEl('#goalFormTarget');
        var saved = getEl('#goalFormSaved');
        var deadline = getEl('#goalFormDeadline');
        var status = getEl('#goalFormStatus');

        if (title) title.textContent = 'Create Goal';
        if (submit) submit.textContent = 'Create Goal';
        if (form) form.action = urls.add || '';
        if (name) name.value = '';
        if (category) category.value = 'Travel';
        if (target) target.value = '';
        if (saved) saved.value = '';
        if (deadline) deadline.value = '';
        if (status) status.value = 'on-track';

        openModal(modal);
    }

    function openEditModal(id) {
        var g = (goal.goals || []).find(function (x) { return x.id === id; });
        if (!g) return;
        var modal = getEl('[data-goal-modal]');
        if (!modal) return;
        var title = getEl('[data-goal-modal-title]');
        var submit = getEl('[data-goal-submit]');
        var form = getEl('#goalForm');
        var name = getEl('#goalFormName');
        var category = getEl('#goalFormCategory');
        var target = getEl('#goalFormTarget');
        var saved = getEl('#goalFormSaved');
        var deadline = getEl('#goalFormDeadline');
        var status = getEl('#goalFormStatus');

        if (title) title.textContent = 'Edit ' + g.name;
        if (submit) submit.textContent = 'Update Goal';
        if (form) form.action = (urls.edit || '').replace('0', String(id));
        if (name) name.value = g.name;
        if (category) category.value = g.category;
        if (target) target.value = g.target_amount;
        if (saved) saved.value = g.saved_amount;
        if (deadline) deadline.value = g.deadline;
        if (status) status.value = g.status;

        openModal(modal);
    }

    /* ------------------------------------------------------------------ */
    /* Add Funds modal                                                     */
    /* ------------------------------------------------------------------ */

    function openFundsModal(id) {
        var g = (goal.goals || []).find(function (x) { return x.id === id; });
        if (!g) return;
        var modal = getEl('[data-goal-funds-modal]');
        if (!modal) return;
        var text = getEl('[data-goal-funds-text]');
        var form = getEl('#goalFundsForm');
        var amount = getEl('#goalFundsAmount');

        if (text) text.textContent = 'Add funds to "' + g.name + '". Current saved: ' + money(g.saved_amount) + ' of ' + money(g.target_amount) + '.';
        if (form) form.action = (urls.funds || '').replace('0', String(id));
        if (amount) amount.value = '';

        openModal(modal);
    }

    /* ------------------------------------------------------------------ */
    /* Delete Goal modal                                                   */
    /* ------------------------------------------------------------------ */

    function openDeleteModal(id) {
        var g = (goal.goals || []).find(function (x) { return x.id === id; });
        if (!g) return;
        var modal = getEl('[data-goal-delete-modal]');
        if (!modal) return;
        var text = getEl('[data-goal-delete-text]');
        var form = getEl('#goalDeleteForm');

        if (text) text.textContent = 'Are you sure you want to delete "' + g.name + '"? This cannot be undone.';
        if (form) form.action = (urls.delete || '').replace('0', String(id));

        openModal(modal);
    }

    /* ------------------------------------------------------------------ */
    /* Toast                                                               */
    /* ------------------------------------------------------------------ */

    function showToast(message, isError) {
        var toast = getEl('[data-goal-toast]');
        if (!toast) return;
        var text = getEl('[data-goal-toast-text]');
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

    function bindEvents() {
        // Create buttons (header + quick action)
        getAll('[data-goal-create]').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                openCreateModal();
            });
        });

        // Quick action: add funds to first goal
        var addFunds = getEl('[data-goal-add-funds]');
        if (addFunds) {
            addFunds.addEventListener('click', function (e) {
                e.preventDefault();
                var first = (goal.goals || [])[0];
                if (first) openFundsModal(first.id);
                else showToast('No goals yet. Create one first!', true);
            });
        }

        // Quick action: edit first goal
        var editFirst = getEl('[data-goal-edit-first]');
        if (editFirst) {
            editFirst.addEventListener('click', function (e) {
                e.preventDefault();
                var first = (goal.goals || [])[0];
                if (first) openEditModal(first.id);
                else openCreateModal();
            });
        }

        // Close buttons / backdrop
        getAll('[data-modal-close]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                closeAllModals();
            });
        });

        // Goal form submit feedback
        var form = getEl('#goalForm');
        if (form) {
            form.addEventListener('submit', function () {
                closeAllModals();
                showToast('Goal saved successfully');
            });
        }

        // Add funds form submit feedback
        var fundsForm = getEl('#goalFundsForm');
        if (fundsForm) {
            fundsForm.addEventListener('submit', function () {
                closeAllModals();
                showToast('Funds added successfully');
            });
        }

        // Delete form submit feedback
        var deleteForm = getEl('#goalDeleteForm');
        if (deleteForm) {
            deleteForm.addEventListener('submit', function () {
                closeAllModals();
                showToast('Goal deleted');
            });
        }

        // Event delegation for card action buttons
        var grid = getEl('#goalProgressGrid');
        if (grid) {
            grid.addEventListener('click', function (e) {
                var btn = e.target.closest('[data-goal-fund], [data-goal-edit], [data-goal-delete]');
                if (!btn) return;
                var id = parseInt(btn.getAttribute('data-goal-fund') || btn.getAttribute('data-goal-edit') || btn.getAttribute('data-goal-delete'), 10);
                if (btn.hasAttribute('data-goal-fund')) openFundsModal(id);
                else if (btn.hasAttribute('data-goal-edit')) openEditModal(id);
                else if (btn.hasAttribute('data-goal-delete')) openDeleteModal(id);
            });
        }

        // Escape key closes modals
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeAllModals();
        });
    }

    /* ------------------------------------------------------------------ */
    /* Init                                                                */
    /* ------------------------------------------------------------------ */

    function init() {
        bindEvents();
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