// ================================================================== //
// Spendly — Transactions Page Behaviour (vanilla JS)                 //
//                                                                   //
// The server renders the ledger with real data. This module adds:   //
//   - auto-submit filter bar (debounced search + instant applies)   //
//   - bulk row selection + bulk CSV export + bulk delete submit     //
//   - View-transaction details modal                                //
//   - human-friendly "time ago" formatting for activity timestamps  //
// ================================================================== //

(function () {
    'use strict';

    var cfg = window.SPENDLY_TRANSACTIONS || {
        transactions: [],
        paymentMethods: [],
        queryArgs: {},
        filters: {},
        urls: {}
    };

    var urls = cfg.urls || {};
    var transactions = cfg.transactions || [];

    /* ------------------------------------------------------------------ */
    /* Small helpers                                                       */
    /* ------------------------------------------------------------------ */

    function getEl(id) { return document.getElementById(id); }

    function money(n) {
        return '\u20B9' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '<')
            .replace(/>/g, '>')
            .replace(/"/g, '"')
            .replace(/'/g, '&#39;');
    }

    function payLabel(method) {
        var labels = { card: 'Card', upi: 'UPI', cash: 'Cash', bank: 'Bank', wallet: 'Wallet' };
        return labels[method] || 'Cash';
    }

    function monthName(m) {
        var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        var idx = parseInt(m, 10) - 1;
        return months[idx] || m;
    }

    function fmtDate(iso) {
        if (!iso) return '—';
        var parts = iso.split('-');
        if (parts.length !== 3) return iso;
        return parts[2] + ' ' + monthName(parts[1]) + ' ' + parts[0];
    }

    function timeAgo(iso) {
        if (!iso) return '';
        var d = new Date(String(iso).replace(' ', 'T') + 'Z');
        if (isNaN(d.getTime())) return '';
        var diff = Date.now() - d.getTime();
        var mins = Math.floor(diff / 60000);
        if (mins < 1) return 'just now';
        if (mins < 60) return mins + 'm ago';
        var hrs = Math.floor(mins / 60);
        if (hrs < 24) return hrs + 'h ago';
        var days = Math.floor(hrs / 24);
        if (days < 7) return days + 'd ago';
        return d.toLocaleDateString();
    }

    function refreshIcons() {
        if (window.Spendly && window.Spendly.refreshIcons) {
            window.Spendly.refreshIcons();
        } else if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    function queryStringFromForm(form) {
        return new URLSearchParams(new FormData(form)).toString();
    }

    /* ------------------------------------------------------------------ */
    /* Filter bar — auto-submit as the user types / changes                */
    /* ------------------------------------------------------------------ */

    function debounce(fn, wait) {
        var t;
        return function () {
            var args = arguments;
            clearTimeout(t);
            t = setTimeout(function () { fn.apply(null, args); }, wait);
        };
    }

    function submitFilters() {
        var form = getEl('filterForm');
        if (!form) return;
        // Preserve the current page when the user only changes the sort.
        var target = form.action ? new URL(form.action, window.location.origin) : new URL(window.location.href);
        var qs = queryStringFromForm(form);
        var params = new URLSearchParams(qs);
        params.set('page', '1'); // any filter change resets to page 1
        window.location.href = target.pathname + '?' + params.toString();
    }

    function bindFilterAutosubmit() {
        var form = getEl('filterForm');
        if (!form) return;

        var debouncedSubmit = debounce(submitFilters, 350);

        // Text inputs (search, amount min/max) — debounced.
        ['filterSearch', 'filterAmountMin', 'filterAmountMax'].forEach(function (id) {
            var el = getEl(id);
            if (el) el.addEventListener('input', debouncedSubmit);
        });

        // Selects and date inputs — submit immediately on change.
        ['filterCategory', 'filterDateFrom', 'filterDateTo', 'filterSort'].forEach(function (id) {
            var el = getEl(id);
            if (el) el.addEventListener('change', submitFilters);
        });

        // Prevent accidental Enter-key submits from adding a "?" without params.
        form.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                submitFilters();
            }
        });

        // Reset filters — clear all fields and navigate to /transactions.
        var resetBtn = getEl('filterReset');
        if (resetBtn) {
            resetBtn.addEventListener('click', function () {
                window.location.href = form.action || '/transactions';
            });
        }
    }

    /* ------------------------------------------------------------------ */
    /* Bulk selection + actions                                            */
    /* ------------------------------------------------------------------ */

    function selectedRowChecks() {
        return Array.prototype.slice.call(document.querySelectorAll('.row-check'));
    }

    function updateBulkBar() {
        var checks = selectedRowChecks();
        var count = checks.filter(function (c) { return c.checked; }).length;
        var bar = getEl('bulkForm');
        if (!bar) return;

        bar.hidden = count === 0;
        getEl('bulkCountLabel').textContent = count + ' selected';

        var allChecked = checks.length > 0 && checks.every(function (c) { return c.checked; });
        var selectAll = getEl('selectAll');
        var bulkSelectAll = getEl('bulkSelectAll');
        if (selectAll) selectAll.checked = allChecked;
        if (bulkSelectAll) bulkSelectAll.checked = allChecked;
    }

    function toggleAll(checked) {
        selectedRowChecks().forEach(function (c) { c.checked = checked; });
        updateBulkBar();
    }

    function bindBulk() {
        var selectAll = getEl('selectAll');
        var bulkSelectAll = getEl('bulkSelectAll');

        if (selectAll) selectAll.addEventListener('change', function (e) {
            toggleAll(e.target.checked);
        });
        if (bulkSelectAll) bulkSelectAll.addEventListener('change', function (e) {
            toggleAll(e.target.checked);
        });

        // Row checkbox changes.
        document.addEventListener('change', function (e) {
            if (e.target.classList && e.target.classList.contains('row-check')) {
                updateBulkBar();
            }
        });

        // Bulk export — download the selected rows as CSV.
        var bulkExport = getEl('bulkExportBtn');
        if (bulkExport) {
            bulkExport.addEventListener('click', function (e) {
                e.preventDefault();
                var ids = selectedRowChecks()
                    .filter(function (c) { return c.checked; })
                    .map(function (c) { return c.value; })
                    .join(',');
                if (!ids) return;
                var separator = (urls.exportBase || '/transactions/export').indexOf('?') === -1 ? '?' : '&';
                window.location.href = (urls.exportBase || '/transactions/export') + separator + 'ids=' + encodeURIComponent(ids);
            });
        }

        // Bulk delete — confirm then submit the POST form with selected ids.
        var bulkDelete = getEl('bulkDeleteBtn');
        if (bulkDelete) {
            bulkDelete.addEventListener('click', function (e) {
                var count = selectedRowChecks().filter(function (c) { return c.checked; }).length;
                if (count === 0) {
                    e.preventDefault();
                    return;
                }
                if (!window.confirm('Delete ' + count + ' selected transaction(s)? This cannot be undone.')) {
                    e.preventDefault();
                }
            });
        }
    }

    /* ------------------------------------------------------------------ */
    /* View modal                                                          */
    /* ------------------------------------------------------------------ */

    function findTransaction(id) {
        for (var i = 0; i < transactions.length; i++) {
            if (transactions[i].id === id) return transactions[i];
        }
        return null;
    }

    function openModal(txn) {
        var body = getEl('txnModalBody');
        if (!body) return;
        function categoryClass(cat) {
            return 'cat-' + String(cat || 'Other').toLowerCase();
        }
        body.innerHTML =
            '<div class="txn-modal-amount">' + money(txn.amount) + '</div>' +
            '<div class="txn-modal-detail"><span class="txn-modal-detail-label">Description</span><span class="txn-modal-detail-value">' + escapeHtml(txn.description || '—') + '</span></div>' +
            '<div class="txn-modal-detail"><span class="txn-modal-detail-label">Category</span><span class="txn-modal-detail-value"><span class="category-tag ' + categoryClass(txn.category) + '">' + escapeHtml(txn.category) + '</span></span></div>' +
            '<div class="txn-modal-detail"><span class="txn-modal-detail-label">Date</span><span class="txn-modal-detail-value">' + escapeHtml(txn.date) + '</span></div>' +
            '<div class="txn-modal-detail"><span class="txn-modal-detail-label">Payment</span><span class="txn-modal-detail-value">' + escapeHtml(payLabel(txn.payment_method)) + '</span></div>' +
            '<div class="txn-modal-detail"><span class="txn-modal-detail-label">Transaction ID</span><span class="txn-modal-detail-value">#' + txn.id + '</span></div>';
        getEl('txnModal').hidden = false;
        document.body.style.overflow = 'hidden';
        refreshIcons();
    }

    function closeModal() {
        var modal = getEl('txnModal');
        if (modal) modal.hidden = true;
        document.body.style.overflow = '';
    }

    function bindModalActions() {
        // View buttons.
        document.addEventListener('click', function (e) {
            var viewBtn = e.target.closest('.row-view');
            if (viewBtn) {
                var id = Number(viewBtn.getAttribute('data-id'));
                var txn = findTransaction(id);
                if (txn) openModal(txn);
                return;
            }

            var modal = getEl('txnModal');
            if (modal && !modal.hidden) {
                var closeTarget = e.target.closest('[data-modal-close]');
                if (closeTarget) closeModal();
            }
        });

        // Escape key.
        document.addEventListener('keydown', function (e) {
            var modal = getEl('txnModal');
            if (e.key === 'Escape' && modal && !modal.hidden) {
                closeModal();
            }
        });
    }

    /* ------------------------------------------------------------------ */
    /* Activity timestamps                                                 */
    /* ------------------------------------------------------------------ */

    function formatActivityTimes() {
        var nodes = document.querySelectorAll('[data-activity-time]');
        Array.prototype.forEach.call(nodes, function (el) {
            var raw = el.getAttribute('data-activity-time');
            var label = timeAgo(raw);
            if (label) {
                el.textContent = label;
                el.title = raw;
            }
        });
    }

    /* ------------------------------------------------------------------ */
    /* Init                                                                */
    /* ------------------------------------------------------------------ */

    function init() {
        bindFilterAutosubmit();
        bindBulk();
        bindModalActions();
        updateBulkBar();
        formatActivityTimes();
        refreshIcons();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

