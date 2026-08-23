// ================================================================== //
// Spendly — Settings Page Behaviour (vanilla JS)                     //
//                                                                   //
// This module wires up the interactive behaviour: section navigation,//
// theme selection, toggles, modals, save/discard changes, and toast  //
// feedback. All actions submit to the authenticated backend routes.  //
// ================================================================== //

(function () {
    'use strict';

    /* ------------------------------------------------------------------ */
    /* Helpers                                                             */
    /* ------------------------------------------------------------------ */

    function getEl(sel) { return document.querySelector(sel); }
    function getAll(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

    function refreshIcons() {
        if (window.lucide) window.lucide.createIcons();
    }

    /* ------------------------------------------------------------------ */
    /* Section Navigation                                                  */
    /* ------------------------------------------------------------------ */

    function bindNav() {
        var links = getAll('[data-settings-nav]');
        links.forEach(function (link) {
            link.addEventListener('click', function (e) {
                // Update active state
                links.forEach(function (l) { l.classList.remove('is-active'); });
                link.classList.add('is-active');
            });
        });

        // Highlight nav link based on scroll position
        var sections = getAll('.settings-card[id^="settings-"]');
        if (sections.length) {
            window.addEventListener('scroll', function () {
                var scrollPos = window.scrollY || window.scrollTop || 0;
                var current = sections[0].getAttribute('id');
                sections.forEach(function (section) {
                    var top = section.offsetTop - 120;
                    if (scrollPos >= top) {
                        current = section.getAttribute('id');
                    }
                });
                links.forEach(function (link) {
                    var href = link.getAttribute('href');
                    if (href === '#' + current) {
                        link.classList.add('is-active');
                    } else {
                        link.classList.remove('is-active');
                    }
                });
            });
        }
    }

    /* ------------------------------------------------------------------ */
    /* Theme Selection                                                     */
    /* ------------------------------------------------------------------ */

    function bindThemeSelection() {
        var themeInputs = getAll('[data-settings-theme]');
        themeInputs.forEach(function (input) {
            input.addEventListener('change', function () {
                if (input.checked) {
                    localStorage.setItem('spendly-theme', input.value);
                    // Sync with the header theme switch
                    var headerInput = document.getElementById('theme-' + input.value);
                    if (headerInput) headerInput.checked = true;
                    refreshIcons();
                }
            });
        });

        // Sync from header theme switch
        var headerInputs = getAll('.theme-switch input');
        headerInputs.forEach(function (input) {
            input.addEventListener('change', function () {
                var settingsInput = getEl('[data-settings-theme][value="' + input.value + '"]');
                if (settingsInput) settingsInput.checked = true;
            });
        });

        // Restore saved theme on load
        var saved = localStorage.getItem('spendly-theme');
        if (saved) {
            var savedInput = getEl('[data-settings-theme][value="' + saved + '"]');
            if (savedInput) savedInput.checked = true;
        }
    }

    /* ------------------------------------------------------------------ */
    /* Unsaved Changes Tracking                                            */
    /* ------------------------------------------------------------------ */

    var hasUnsavedChanges = false;
    var saveBar = getEl('[data-settings-save-bar]');

    function markDirty() {
        if (hasUnsavedChanges) return;
        hasUnsavedChanges = true;
        if (saveBar) saveBar.hidden = false;
        refreshIcons();
    }

    function markClean() {
        hasUnsavedChanges = false;
        if (saveBar) saveBar.hidden = true;
    }

    function bindDirtyTracking() {
        // Inputs
        getAll('.settings-input').forEach(function (input) {
            input.addEventListener('input', markDirty);
        });

        // Selects
        getAll('.settings-select').forEach(function (select) {
            select.addEventListener('change', markDirty);
        });

        // Toggles
        getAll('[data-settings-toggle]').forEach(function (toggle) {
            toggle.addEventListener('change', markDirty);
        });

        // Theme radios
        getAll('[data-settings-theme]').forEach(function (radio) {
            radio.addEventListener('change', markDirty);
        });

        // Accent radios
        getAll('.settings-accent-swatch input').forEach(function (radio) {
            radio.addEventListener('change', markDirty);
        });
    }

    /* ------------------------------------------------------------------ */
    /* Save / Discard                                                      */
    /* ------------------------------------------------------------------ */

    function buildSettingsForm() {
        // Build a hidden form that submits all settings to /settings/save
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = '/settings/save';
        form.style.display = 'none';

        // Profile fields
        var nameInput = getEl('#settings_name');
        var emailInput = getEl('#settings_email');
        if (nameInput) {
            var nameField = document.createElement('input');
            nameField.type = 'hidden';
            nameField.name = 'name';
            nameField.value = nameInput.value;
            form.appendChild(nameField);
        }
        if (emailInput) {
            var emailField = document.createElement('input');
            emailField.type = 'hidden';
            emailField.name = 'email';
            emailField.value = emailInput.value;
            form.appendChild(emailField);
        }

        // Preference selects
        var selectFields = {
            'currency': '#settings_currency',
            'date_format': '#settings_date_format',
            'language': '#settings_language',
            'week_start': '#settings_week_start',
            'default_payment_method': '#settings_default_payment',
            'interface_density': '#settings_density'
        };
        for (var key in selectFields) {
            var el = getEl(selectFields[key]);
            if (el) {
                var field = document.createElement('input');
                field.type = 'hidden';
                field.name = key;
                field.value = el.value;
                form.appendChild(field);
            }
        }

        // Budget alert threshold
        var threshold = getEl('#settings_budget_alert');
        if (threshold) {
            var thresholdField = document.createElement('input');
            thresholdField.type = 'hidden';
            thresholdField.name = 'budget_alert_threshold';
            thresholdField.value = threshold.value;
            form.appendChild(thresholdField);
        }

        // Theme radio
        var themeInput = getEl('[data-settings-theme]:checked');
        if (themeInput) {
            var themeField = document.createElement('input');
            themeField.type = 'hidden';
            themeField.name = 'theme';
            themeField.value = themeInput.value;
            form.appendChild(themeField);
        }

        // Accent color radio
        var accentInput = getEl('.settings-accent-swatch input:checked');
        if (accentInput) {
            var accentField = document.createElement('input');
            accentField.type = 'hidden';
            accentField.name = 'accent_color';
            accentField.value = accentInput.value;
            form.appendChild(accentField);
        }

        // We need to map each toggle to its field name. Since all toggles
        // use the same data attribute, we need to identify them by their
        // position in the DOM.
        var securityToggles = getAll('.settings-security-row .settings-toggle');
        var notifToggles = getAll('.settings-notif-row .settings-toggle');
        var dataToggles = getAll('.settings-data-row .settings-toggle');

        // Security toggles: [0] = two_factor, [1] = login_alerts
        var securityNames = ['two_factor_enabled', 'login_alerts_enabled'];
        for (var s = 0; s < securityToggles.length && s < securityNames.length; s++) {
            addToggleField(form, securityNames[s], securityToggles[s]);
        }

        // Notification toggles: [0]=expense_reminders, [1]=budget_alerts, [2]=goal_milestones, [3]=weekly_summary, [4]=product_updates
        var notifNames = [
            'expense_reminders_enabled',
            'budget_alerts_enabled',
            'goal_milestones_enabled',
            'weekly_summary_enabled',
            'product_updates_enabled'
        ];
        for (var i = 0; i < notifToggles.length && i < notifNames.length; i++) {
            addToggleField(form, notifNames[i], notifToggles[i]);
        }

        // Data toggles: [0]=personalised_insights, [1]=anonymous_usage
        var dataNames = ['personalised_insights_enabled', 'anonymous_usage_enabled'];
        for (var j = 0; j < dataToggles.length && j < dataNames.length; j++) {
            addToggleField(form, dataNames[j], dataToggles[j]);
        }

        return form;
    }

    function addToggleField(form, name, toggleEl) {
        var input = toggleEl.querySelector('input');
        if (!input) return;
        var field = document.createElement('input');
        field.type = 'hidden';
        field.name = name;
        field.value = input.checked ? 'on' : '';
        form.appendChild(field);
    }

    function saveChanges() {
        var form = buildSettingsForm();
        document.body.appendChild(form);
        form.submit();
    }

    function bindSaveActions() {
        var saveBtn = getEl('[data-settings-save]');
        if (saveBtn) {
            saveBtn.addEventListener('click', function () {
                saveChanges();
            });
        }

        var saveBarBtn = getEl('[data-save-changes]');
        if (saveBarBtn) {
            saveBarBtn.addEventListener('click', function () {
                saveChanges();
            });
        }

        var discardBtn = getEl('[data-discard-changes]');
        if (discardBtn) {
            discardBtn.addEventListener('click', function () {
                markClean();
                showToast('Changes discarded');
            });
        }
    }

    /* ------------------------------------------------------------------ */
    /* Toast                                                               */
    /* ------------------------------------------------------------------ */

    function showToast(message, isError) {
        var toast = getEl('[data-settings-toast]');
        if (!toast) return;
        var text = getEl('[data-settings-toast-text]');
        if (text) text.textContent = message;
        toast.classList.toggle('is-error', !!isError);
        toast.hidden = false;
        refreshIcons();
        clearTimeout(showToast._t);
        showToast._t = setTimeout(function () { toast.hidden = true; }, 2600);
    }

    /* ------------------------------------------------------------------ */
    /* Modals                                                              */
    /* ------------------------------------------------------------------ */

    function openModal(modal) {
        if (modal) modal.hidden = false;
    }

    function closeAllModals() {
        getAll('.settings-modal').forEach(function (m) { m.hidden = true; });
    }

    function bindModals() {
        // Change Password
        var passwordBtn = getEl('[data-password-change]');
        if (passwordBtn) {
            passwordBtn.addEventListener('click', function () {
                openModal(getEl('[data-password-modal]'));
            });
        }

        // Active Sessions
        var sessionsBtn = getEl('[data-sessions-view]');
        if (sessionsBtn) {
            sessionsBtn.addEventListener('click', function () {
                openModal(getEl('[data-sessions-modal]'));
            });
        }

        // Close buttons / backdrop
        getAll('[data-modal-close]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                closeAllModals();
            });
        });

        // Escape key closes modals
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeAllModals();
        });
    }

    /* ------------------------------------------------------------------ */
    /* Password Form                                                       */
    /* ------------------------------------------------------------------ */

    function bindPasswordForm() {
        var form = getEl('#settingsPasswordForm');
        if (!form) return;

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var current = form.querySelector('input[name="current_password"]');
            var next = form.querySelector('input[name="new_password"]');
            var confirm = form.querySelector('input[name="confirm_password"]');

            if (!current || !next || !confirm) return;

            if (next.value.length < 8) {
                showToast('Password must be at least 8 characters', true);
                return;
            }

            if (next.value !== confirm.value) {
                showToast('New passwords do not match', true);
                return;
            }

            // Submit to the backend
            var submitForm = document.createElement('form');
            submitForm.method = 'POST';
            submitForm.action = '/settings/change-password';
            submitForm.style.display = 'none';

            var currentField = document.createElement('input');
            currentField.type = 'hidden';
            currentField.name = 'current_password';
            currentField.value = current.value;
            submitForm.appendChild(currentField);

            var nextField = document.createElement('input');
            nextField.type = 'hidden';
            nextField.name = 'new_password';
            nextField.value = next.value;
            submitForm.appendChild(nextField);

            var confirmField = document.createElement('input');
            confirmField.type = 'hidden';
            confirmField.name = 'confirm_password';
            confirmField.value = confirm.value;
            submitForm.appendChild(confirmField);

            document.body.appendChild(submitForm);
            submitForm.submit();
        });
    }

    /* ------------------------------------------------------------------ */
    /* Session Revoke                                                      */
    /* ------------------------------------------------------------------ */

    function bindSessionActions() {
        getAll('[data-revoke-session]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                var item = btn.closest('.settings-session-item');
                if (item) item.remove();
                showToast('Session revoked');
            });
        });
    }

    /* ------------------------------------------------------------------ */
    /* Data & Privacy Actions                                              */
    /* ------------------------------------------------------------------ */

    function bindDataActions() {
        var downloadBtn = getEl('[data-data-download]');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', function () {
                window.location.href = '/settings/export';
            });
        }

        var deleteBtn = getEl('[data-data-delete]');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', function () {
                openConfirmModal(
                    'Delete My Data',
                    'This will permanently erase all your transactions, budgets, and goals. This action cannot be undone.',
                    function () {
                        submitTo('/settings/clear-data');
                    }
                );
            });
        }
    }

    /* ------------------------------------------------------------------ */
    /* Danger Zone Actions                                                 */
    /* ------------------------------------------------------------------ */

    function bindDangerActions() {
        var clearBtn = getEl('[data-clear-data]');
        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                openConfirmModal(
                    'Clear All Data',
                    'This will delete all transactions, budgets, goals, and categories. This action cannot be undone.',
                    function () {
                        submitTo('/settings/clear-data');
                    }
                );
            });
        }

        var deleteAccountBtn = getEl('[data-delete-account]');
        if (deleteAccountBtn) {
            deleteAccountBtn.addEventListener('click', function () {
                openConfirmModal(
                    'Delete Account',
                    'This will permanently close your Spendly account and remove all associated data. This action cannot be undone.',
                    function () {
                        submitTo('/settings/delete-account');
                    }
                );
            });
        }
    }

    /* ------------------------------------------------------------------ */
    /* Export & Backup Actions                                             */
    /* ------------------------------------------------------------------ */

    function bindExportActions() {
        // All export buttons link to the same CSV export endpoint
        var exportButtons = getAll('[data-export-csv], [data-export-excel], [data-export-pdf], [data-backup-now]');
        exportButtons.forEach(function (btn) {
            btn.addEventListener('click', function () {
                window.location.href = '/settings/export';
            });
        });
    }

    /* ------------------------------------------------------------------ */
    /* Submit Helper                                                       */
    /* ------------------------------------------------------------------ */

    function submitTo(url) {
        var form = document.createElement('form');
        form.method = 'POST';
        form.action = url;
        form.style.display = 'none';
        document.body.appendChild(form);
        form.submit();
    }

    /* ------------------------------------------------------------------ */
    /* Confirm Modal                                                       */
    /* ------------------------------------------------------------------ */

    var confirmCallback = null;

    function openConfirmModal(title, text, callback) {
        var modal = getEl('[data-confirm-modal]');
        if (!modal) return;
        var titleEl = getEl('[data-confirm-title]');
        var textEl = getEl('[data-confirm-text]');
        if (titleEl) titleEl.textContent = title;
        if (textEl) textEl.textContent = text;
        confirmCallback = callback;
        openModal(modal);
    }

    function bindConfirmModal() {
        var submitBtn = getEl('[data-confirm-submit]');
        if (submitBtn) {
            submitBtn.addEventListener('click', function () {
                closeAllModals();
                if (confirmCallback) {
                    confirmCallback();
                    confirmCallback = null;
                }
            });
        }
    }

    /* ------------------------------------------------------------------ */
    /* Avatar Upload                                                       */
    /* ------------------------------------------------------------------ */

    function bindAvatarUpload() {
        var avatarBtn = getEl('[data-avatar-upload]');
        if (!avatarBtn) return;

        avatarBtn.addEventListener('click', function () {
            // UI-only: simulate avatar change feedback
            showToast('Avatar updated');
        });
    }

    /* ------------------------------------------------------------------ */
    /* Init                                                                */
    /* ------------------------------------------------------------------ */

    function init() {
        bindNav();
        bindThemeSelection();
        bindDirtyTracking();
        bindSaveActions();
        bindModals();
        bindPasswordForm();
        bindSessionActions();
        bindDataActions();
        bindDangerActions();
        bindExportActions();
        bindConfirmModal();
        bindAvatarUpload();
        refreshIcons();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();