// ================================================================== //
// Spendly — Budgets Page Behaviour (vanilla JS)                      //
//                                                                   //
// This module is frontend-only. It renders hardcoded demo budget data
// into progress cards, a Budget vs Actual bar chart, a Budget
// Distribution donut chart, an overview table, alerts/insights, and a
// recent activity timeline. It uses the existing design system (CSS
// variables, Lucide icons, tabular numerals) and adds loading
// skeletons, animated progress bars, filter interactions, and export
// (PDF / Excel) with toast feedback.
// ================================================================== //

(function () {
    'use strict';

/* ------------------------------------------------------------------ */
    /* Data source — server-provided data with realistic demo fallback     */
    /* ------------------------------------------------------------------ */

    var cfg = window.SPENDLY_BUDGETS || {};
    var serverBudget = cfg.budget || {};

    // Color tokens are derived from the shared CSS category chart fills.
    var CATEGORY_COLORS = {
        food: 'var(--bar-food)',
        transport: 'var(--bar-transport)',
        bills: 'var(--bar-bills)',
        health: 'var(--bar-health)',
        entertainment: 'var(--bar-entertainment)',
        shopping: 'var(--bar-shopping)',
        other: 'var(--bar-other)'
    };

    var CATEGORY_ICONS = {
        food: 'utensils',
        transport: 'bus',
        bills: 'zap',
        health: 'heart-pulse',
        entertainment: 'clapperboard',
        shopping: 'shopping-bag',
        other: 'circle-ellipsis'
    };

    // Map a category display name (e.g. "Food & Dining") to its color key.
    function colorKeyForName(name) {
        var n = String(name || '').toLowerCase();
        if (n.indexOf('food') !== -1) return 'food';
        if (n.indexOf('transport') !== -1) return 'transport';
        if (n.indexOf('bills') !== -1) return 'bills';
        if (n.indexOf('health') !== -1) return 'health';
        if (n.indexOf('entertainment') !== -1) return 'entertainment';
        if (n.indexOf('shopping') !== -1) return 'shopping';
        return 'other';
    }

    // Normalize a server budget row into the shape the renderers expect.
    function normalizeBudget(name, limit, spent, period) {
        var key = colorKeyForName(name);
        return {
            id: key,
            name: name,
            icon: CATEGORY_ICONS[key],
            color: key,
            limit: Number(limit) || 0,
            spent: Number(spent) || 0,
            period: period || 'This month'
        };
    }

    // Monthly spending trend used by the Budget vs Actual bar chart.
    var months;

    // Budgets (one per tracked category).
    var budgets;

    // Alerts & insights.
    var alerts;

    // Recent budget activity timeline.
    var timeline;

    // Prefer server data when present; otherwise fall back to demo data so
    // the page always renders something meaningful.
    if (serverBudget && serverBudget.budgets && serverBudget.budgets.length) {
        budgets = serverBudget.budgets.map(function (b) {
            return normalizeBudget(b.name, b.limit, b.spent, b.period);
        });

        months = (serverBudget.monthly_trend && serverBudget.monthly_trend.length)
            ? serverBudget.monthly_trend.map(function (m) {
                return { label: m.label, budget: m.budget, actual: m.actual };
            })
            : [];

        alerts = (serverBudget.insights && serverBudget.insights.length)
            ? serverBudget.insights.map(function (a) {
                return {
                    icon: a.icon || 'lightbulb',
                    accent: a.accent || 'var(--accent)',
                    tone: a.tone || 'track',
                    title: a.title,
                    text: a.text
                };
            })
            : [];

        timeline = (serverBudget.activity && serverBudget.activity.length)
            ? serverBudget.activity.map(function (a) {
                var isAlert = String(a.action || '').toLowerCase() === 'deleted';
                var cls = isAlert ? 'alert' : (String(a.action || 'added').toLowerCase() === 'edited' ? 'edited' : 'added');
                var amountText = a.amount ? ' of \u20B9' + Number(a.amount).toLocaleString('en-IN') : '';
                var desc = a.description || a.category || 'an expense';
                return {
                    icon: cls,
                    cls: cls,
                    text: '<strong>' + (a.category || (a.action || 'Updated')) + '</strong> ' +
                          (isAlert ? 'expense removed' : String(a.action || 'added').toLowerCase() + '') +
                          (a.description ? ' \u2014 ' + String(a.description) : '') +
                          (amountText || ''),
                    meta: a.time_label || 'Recently'
                };
            })
            : [];
    } else {
        months = [
            { label: 'Jul', budget: 32000, actual: 29850 },
            { label: 'Aug', budget: 32000, actual: 31500 },
            { label: 'Sep', budget: 34000, actual: 32740 },
            { label: 'Oct', budget: 34000, actual: 35400 },
            { label: 'Nov', budget: 36000, actual: 33900 },
            { label: 'Dec', budget: 36000, actual: 38500 }
        ];

        budgets = [
            { id: 'food', name: 'Food & Dining', icon: 'utensils', color: 'food', limit: 8000, spent: 6100, period: 'This month' },
            { id: 'bills', name: 'Bills & Utilities', icon: 'zap', color: 'bills', limit: 6000, spent: 3200, period: 'This month' },
            { id: 'transport', name: 'Transport', icon: 'bus', color: 'transport', limit: 4000, spent: 1800, period: 'This month' },
            { id: 'health', name: 'Health', icon: 'heart-pulse', color: 'health', limit: 5000, spent: 5400, period: 'This month' },
            { id: 'entertainment', name: 'Entertainment', icon: 'clapperboard', color: 'entertainment', limit: 3000, spent: 1250, period: 'This month' },
            { id: 'shopping', name: 'Shopping', icon: 'shopping-bag', color: 'shopping', limit: 5000, spent: 2750, period: 'This month' }
        ];

        alerts = [
            { icon: 'alert-triangle', accent: 'var(--danger)', tone: 'over',
              title: 'Health over budget',
              text: 'Health is 8% over its \u20B95,000 limit. Review upcoming appointments to trim costs.' },
            { icon: 'trending-up', accent: 'var(--accent-2)', tone: 'warning',
              title: 'Shopping accelerating',
              text: 'Shopping has used 55% of budget with 12 days left \u2014 trending ~15% above limit.' },
            { icon: 'trophy', accent: 'var(--success)', tone: 'track',
              title: 'Entertainment on track',
              text: 'Entertainment is only 42% used. You have ~\u20B91,750 of headroom this month.' },
            { icon: 'shield-check', accent: 'var(--accent)', tone: 'track',
              title: 'Bills well managed',
              text: 'Bills & Utilities is at 53% \u2014 comfortably within budget so far.' }
        ];

        timeline = [
            { icon: 'alert', cls: 'alert',
              text: '<strong>Health</strong> exceeded its monthly budget by \u20B9400.',
              meta: 'Today \u00B7 9:41 AM' },
            { icon: 'added', cls: 'added',
              text: 'Set an <strong>Entertainment</strong> budget of \u20B93,000.',
              meta: 'Dec 2 \u00B7 6:15 PM' },
            { icon: 'edited', cls: 'edited',
              text: 'Adjusted <strong>Shopping</strong> limit from \u20B96,000 \u2192 \u20B95,000.',
              meta: 'Nov 28 \u00B7 10:03 AM' },
            { icon: 'edited', cls: 'edited',
              text: 'Raised <strong>Food &amp; Dining</strong> budget to \u20B98,000.',
              meta: 'Nov 18 \u00B7 7:32 PM' },
            { icon: 'added', cls: 'added',
              text: 'Created a <strong>Transport</strong> budget of \u20B94,000.',
              meta: 'Nov 5 \u00B7 2:20 PM' },
            { icon: 'alert', cls: 'alert',
              text: '<strong>Bills &amp; Utilities</strong> hit 80% of its limit.',
              meta: 'Oct 25 \u00B7 11:58 AM' }
        ];
    }

    /* ------------------------------------------------------------------ */
    /* Helpers                                                             */
    /* ------------------------------------------------------------------ */

    function getEl(sel) { return document.querySelector(sel); }
    function getAll(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

    function money(n) {
        return '\u20B9' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
    }

    function moneyShort(n) {
        return '\u20B9' + Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 });
    }

    function escapeHtml(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '<')
            .replace(/>/g, '>')
            .replace(/"/g, '"')
            .replace(/'/g, '&#39;');
    }

    function refreshIcons() {
        if (window.lucide) window.lucide.createIcons();
        if (window.Spendly && window.Spendly.refreshIcons) window.Spendly.refreshIcons();
    }

    /* ------------------------------------------------------------------ */
    /* Status helpers                                                      */
    /* ------------------------------------------------------------------ */

    function getStatus(pct) {
        if (pct >= 100) return { key: 'over', label: 'Over Budget', cls: 'over' };
        if (pct >= 75) return { key: 'warning', label: 'At Risk', cls: 'warning' };
        return { key: 'on-track', label: 'On Track', cls: 'on-track' };
    }

    function statusHtml(status) {
        var icon = status.key === 'over' ? 'alert-octagon' : (status.key === 'warning' ? 'alert-circle' : 'check-circle');
        return '<span class="budget-status ' + status.cls + '"><i data-lucide="' + icon + '"></i>' + status.label + '</span>';
    }

    /* ------------------------------------------------------------------ */
    /* Loading skeletons \u2192 reveal content                             */
    /* ------------------------------------------------------------------ */

    function revealSkeletons() {
        getAll('[data-chart-skeleton]').forEach(function (skel) {
            skel.hidden = true;
            skel.classList.add('is-hidden');
            var parent = skel.parentElement;
            if (!parent) return;
            var target = parent.querySelector('[data-bars-chart], [data-category-donut], [data-budget-table]');
            if (target) target.hidden = false;
        });
    }

    /* ------------------------------------------------------------------ */
    /* Summary cards                                                       */
    /* ------------------------------------------------------------------ */

    function updateSummary(list) {
        var totalBudget = 0;
        var totalSpent = 0;
        list.forEach(function (b) {
            totalBudget += b.limit;
            totalSpent += Math.min(b.spent, b.limit);
        });
        var remaining = totalBudget - totalSpent;
        var pct = totalBudget > 0 ? Math.round((totalSpent / totalBudget) * 100) : 0;
        var overCount = list.filter(function (b) { return getStatus((b.spent / b.limit) * 100).key === 'over'; }).length;

        // ~2/3 of the month elapsed, remaining days \u2248 11
        var daysLeft = 11;
        var daily = daysLeft > 0 ? Math.max(0, remaining / daysLeft) : 0;

        var totalBudgetEl = getEl('[data-stat="totalBudget"]');
        var totalSpentEl = getEl('[data-stat="totalSpent"]');
        var spentPctEl = getEl('[data-stat="spentPct"]');
        var remainingEl = getEl('[data-stat="remaining"]');
        var dailyEl = getEl('[data-stat="daily"]');
        var overCountEl = getEl('[data-stat="overCount"]');

        if (totalBudgetEl) totalBudgetEl.textContent = money(totalBudget);
        if (totalSpentEl) totalSpentEl.textContent = money(totalSpent);
        if (spentPctEl) spentPctEl.textContent = pct + '% of budget used';
        if (remainingEl) remainingEl.textContent = money(Math.max(0, remaining));
        if (dailyEl) dailyEl.textContent = money(Math.round(daily)) + ' / day left';
        if (overCountEl) overCountEl.textContent = overCount;
    }

    /* ------------------------------------------------------------------ */
    /* Budget progress cards                                               */
    /* ------------------------------------------------------------------ */

    function buildProgressCards(list) {
        var grid = getEl('#budgetProgressGrid');
        if (!grid) return;
        grid.innerHTML = '';

        list.forEach(function (b) {
            var pct = Math.min((b.spent / b.limit) * 100, 100);
            var status = getStatus((b.spent / b.limit) * 100);
            var left = b.limit - b.spent;
            var colorVar = CATEGORY_COLORS[b.color] || 'var(--accent)';
            var over = status.key === 'over';

            var card = document.createElement('div');
            card.className = 'budget-progress-card';
            card.style.setProperty('--bp-accent', colorVar);

            card.innerHTML =
                '<div class="budget-progress-top">' +
                    '<div class="budget-progress-cat">' +
                        '<span class="budget-progress-swatch"><i data-lucide="' + (CATEGORY_ICONS[b.color] || 'circle') + '"></i></span>' +
                        '<div class="budget-progress-copy">' +
                            '<div class="budget-progress-name">' + escapeHtml(b.name) + '</div>' +
                            '<div class="budget-progress-period">' + escapeHtml(b.period) + '</div>' +
                        '</div>' +
                    '</div>' +
                    '<div class="budget-progress-pct' + (over ? ' is-over' : (status.key === 'warning' ? ' is-warning' : '')) + '">' +
                        Math.round((b.spent / b.limit) * 100) + '%' +
                    '</div>' +
                '</div>' +
                '<div class="budget-progress-track">' +
                    '<div class="budget-progress-fill' + (over ? ' is-over' : '') + '" data-fill data-pct="' + pct + '"></div>' +
                '</div>' +
                '<div class="budget-progress-meta">' +
                    '<span class="budget-progress-spent"><strong>' + money(b.spent) + '</strong> of ' + money(b.limit) + '</span>' +
                    '<span class="budget-progress-left' + (left < 0 ? ' is-neg' : '') + '">' +
                        (left < 0 ? (money(Math.abs(left)) + ' over') : (money(left) + ' left')) +
                    '</span>' +
                '</div>' +
                '<div>' + statusHtml(status) + '</div>';

            grid.appendChild(card);
        });

        refreshIcons();
        animateFills();
    }

    // Animate all progress bars from 0 \u2192 target width.
    function animateFills() {
        getAll('.budget-progress-fill[data-fill], .budget-table-progress .budget-progress-fill[data-fill]').forEach(function (fill) {
            var pct = parseFloat(fill.getAttribute('data-pct')) || 0;
            fill.style.width = pct + '%';
        });
    }

    /* ------------------------------------------------------------------ */
    /* Budget vs Actual bar chart                                          */
    /* ------------------------------------------------------------------ */

    function buildBarChart() {
        var container = getEl('[data-budget-bars]');
        if (!container) return;

        var maxVal = Math.max.apply(null, months.map(function (m) { return Math.max(m.budget, m.actual); })) * 1.1 || 1;

        container.innerHTML = '';

        months.forEach(function (m) {
            var col = document.createElement('div');
            col.className = 'budget-bar-col';

            var pair = document.createElement('div');
            pair.className = 'budget-bar-pair';

            var budgetH = Math.max(4, (m.budget / maxVal) * 100);
            var actualH = Math.max(4, (m.actual / maxVal) * 100);
            var actualOver = m.actual > m.budget;

            var budgetBar = document.createElement('div');
            budgetBar.className = 'budget-bar';
            budgetBar.style.height = budgetH + '%';
            budgetBar.setAttribute('title', 'Budget: ' + money(m.budget));
            budgetBar.innerHTML = '<span class="budget-bar-tooltip">Budget ' + money(m.budget) + '</span>';

            var actualBar = document.createElement('div');
            actualBar.className = 'budget-bar is-actual' + (actualOver ? ' is-over' : '');
            actualBar.style.height = actualH + '%';
            actualBar.setAttribute('title', 'Actual: ' + money(m.actual));
            actualBar.innerHTML = '<span class="budget-bar-tooltip">Actual ' + money(m.actual) + '</span>';

            pair.appendChild(budgetBar);
            pair.appendChild(actualBar);

            var label = document.createElement('div');
            label.className = 'budget-bar-label';
            label.textContent = m.label;

            col.appendChild(pair);
            col.appendChild(label);
            container.appendChild(col);
        });

        refreshIcons();
    }

    /* ------------------------------------------------------------------ */
    /* Budget Distribution donut (CSS conic-gradient)                      */
    /* ------------------------------------------------------------------ */

    function buildDonut(list) {
        var ring = getEl('[data-category-donut-ring]');
        var totalEl = getEl('[data-category-donut-total]');
        var legend = getEl('[data-category-legend]');
        if (!ring || !legend) return;

        var sum = list.reduce(function (a, b) { return a + b.limit; }, 0);
        if (sum <= 0) {
            ring.style.background = 'conic-gradient(var(--border-soft) 0% 100%)';
            if (totalEl) totalEl.textContent = moneyShort(0);
            legend.innerHTML = '';
            return;
        }

        var acc = 0;
        var stops = [];
        list.forEach(function (b) {
            var pct = (b.limit / sum) * 100;
            stops.push(CATEGORY_COLORS[b.color] + ' ' + acc.toFixed(2) + '% ' + (acc + pct).toFixed(2) + '%');
            acc += pct;
        });

        // Animate the donut by setting the gradient after a tick.
        ring.style.background = 'conic-gradient(var(--border-soft) 0% 100%)';
        if (totalEl) totalEl.textContent = moneyShort(sum);

        legend.innerHTML = '';
        list.forEach(function (b) {
            var pct = (b.limit / sum) * 100;
            var li = document.createElement('li');
            li.className = 'report-legend-item';
            li.innerHTML =
                '<span class="report-legend-dot" style="background:' + CATEGORY_COLORS[b.color] + '"></span>' +
                '<span class="report-legend-name">' + escapeHtml(b.name) + '</span>' +
                '<span class="report-legend-pct">' + pct.toFixed(0) + '%</span>' +
                '<span class="report-legend-amount">' + money(b.limit) + '</span>';
            legend.appendChild(li);
        });

        requestAnimationFrame(function () {
            ring.style.background = 'conic-gradient(' + stops.join(', ') + ')';
        });

        refreshIcons();
    }

    /* ------------------------------------------------------------------ */
    /* Budget overview table                                               */
    /* ------------------------------------------------------------------ */

    function buildTable(list) {
        var body = getEl('[data-budget-table-body]');
        if (!body) return;
        body.innerHTML = '';

        list.forEach(function (b) {
            var pct = Math.min((b.spent / b.limit) * 100, 100);
            var status = getStatus((b.spent / b.limit) * 100);
            var left = b.limit - b.spent;
            var colorVar = CATEGORY_COLORS[b.color] || 'var(--accent)';

            var tr = document.createElement('tr');
            tr.innerHTML =
                '<td>' +
                    '<div class="budget-cell">' +
                        '<span class="budget-cell-swatch" style="--bp-accent:' + colorVar + '"><i data-lucide="' + (CATEGORY_ICONS[b.color] || 'circle') + '"></i></span>' +
                        '<span class="budget-cell-name">' + escapeHtml(b.name) + '</span>' +
                    '</div>' +
                '</td>' +
                '<td><span class="budget-period-tag">' + escapeHtml(b.period) + '</span></td>' +
                '<td class="amount-col">' + money(b.limit) + '</td>' +
                '<td class="amount-col' + (status.key === 'over' ? ' budget-table-amount-neg' : '') + '">' + money(b.spent) + '</td>' +
                '<td class="amount-col' + (left < 0 ? ' budget-table-amount-neg' : '') + '">' + (left < 0 ? '-' + money(Math.abs(left)) : money(left)) + '</td>' +
                '<td>' +
                    '<div class="budget-table-progress">' +
                        '<div class="budget-progress-track">' +
                            '<div class="budget-progress-fill' + (status.key === 'over' ? ' is-over' : '') + '" data-fill data-pct="' + pct + '" style="--bp-accent:' + colorVar + '"></div>' +
                        '</div>' +
                        '<span>' + Math.round((b.spent / b.limit) * 100) + '%</span>' +
                    '</div>' +
                '</td>' +
                '<td>' + statusHtml(status) + '</td>';
            body.appendChild(tr);
        });

        refreshIcons();
        animateFills();
    }

    /* ------------------------------------------------------------------ */
    /* Alerts & Insights                                                   */
    /* ------------------------------------------------------------------ */

    function buildAlerts() {
        var grid = getEl('[data-alerts-grid]');
        if (!grid) return;
        grid.innerHTML = '';

        alerts.forEach(function (a) {
            var card = document.createElement('div');
            card.className = 'insight-card';
            card.style.setProperty('--insight-accent', a.accent);
            card.innerHTML =
                '<div class="insight-icon"><i data-lucide="' + a.icon + '" class="insight-icon"></i></div>' +
                '<div class="insight-body">' +
                    '<h3 class="insight-title">' + a.title + '</h3>' +
                    '<p class="insight-text">' + a.text + '</p>' +
                '</div>';
            grid.appendChild(card);
        });

        refreshIcons();
    }

    /* ------------------------------------------------------------------ */
    /* Recent Budget Activity timeline                                     */
    /* ------------------------------------------------------------------ */

    function buildTimeline() {
        var list = getEl('[data-budget-timeline]');
        if (!list) return;
        list.innerHTML = '';

        timeline.forEach(function (item) {
            var li = document.createElement('li');
            var tone = item.cls === 'alert' ? 'is-over' : 'is-warning';
            li.className = 'budget-timeline-item ' + tone;
            li.innerHTML =
                '<span class="budget-timeline-icon ' + item.cls + '"><i data-lucide="' + (item.cls === 'alert' ? 'alert-circle' : 'circle-check') + '"></i></span>' +
                '<div class="budget-timeline-body">' +
                    '<p class="budget-timeline-text">' + item.text + '</p>' +
                    '<div class="budget-timeline-meta">' + item.meta + '</div>' +
                '</div>';
            list.appendChild(li);
        });

        refreshIcons();
    }

    /* ------------------------------------------------------------------ */
    /* Filters (frontend-only demo)                                        */
    /* ------------------------------------------------------------------ */

    function currentFilters() {
        return {
            month: getEl('#budgetMonth') ? getEl('#budgetMonth').value : 'all',
            category: getEl('#budgetCategory') ? getEl('#budgetCategory').value : 'all',
            status: getEl('#budgetStatus') ? getEl('#budgetStatus').value : 'all'
        };
    }

    function filterBudgets(list, filters) {
        return list.filter(function (b) {
            if (filters.category !== 'all' && b.color !== filters.category) return false;
            if (filters.status !== 'all') {
                var status = getStatus((b.spent / b.limit) * 100).key;
                if (status !== filters.status) return false;
            }
            return true;
        });
    }

    function renderAll() {
        var filters = currentFilters();
        var filtered = filterBudgets(budgets, filters);

        var countEl = getEl('#budgetResultCount');
        if (countEl) {
            countEl.textContent = filtered.length === budgets.length
                ? 'Showing all budgets'
                : ('Showing ' + filtered.length + ' of ' + budgets.length + ' budgets');
        }

        buildProgressCards(filtered);
        updateSummary(filtered);
        buildTable(filtered);
        buildAlerts();
        buildTimeline();
    }

    function bindFilters() {
        var form = getEl('#budgetFilterForm');
        if (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                renderAll();
            });
        }

        var resetBtn = getEl('#budgetFilterReset');
        if (resetBtn) {
            resetBtn.addEventListener('click', function () {
                ['#budgetMonth', '#budgetCategory', '#budgetStatus'].forEach(function (sel) {
                    var el = getEl(sel);
                    if (el) el.value = 'all';
                });
                renderAll();
            });
        }
    }

    /* ------------------------------------------------------------------ */
    /* Create Budget modal (demo)                                          */
    /* ------------------------------------------------------------------ */

    function openModal() {
        var modal = getEl('[data-budget-modal]');
        if (modal) modal.hidden = false;
    }

    function closeModal() {
        var modal = getEl('[data-budget-modal]');
        if (modal) modal.hidden = true;
    }

    function bindModal() {
        var createBtn = getEl('[data-budget-create]');
        if (createBtn) createBtn.addEventListener('click', openModal);

        getAll('[data-modal-close]').forEach(function (btn) {
            btn.addEventListener('click', closeModal);
        });

        var form = getEl('#budgetCreateForm');
        if (form) {
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                closeModal();
                showToast('Budget created successfully');
            });
        }

        // Quick-action cards are all demo; open the modal.
        getAll('[data-quick-action]').forEach(function (card) {
            card.addEventListener('click', function (e) {
                e.preventDefault();
                openModal();
            });
        });
    }

    /* ------------------------------------------------------------------ */
    /* Export toast                                                        */
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
    /* Export (CSV for Excel, minimal PDF)                                 */
    /* ------------------------------------------------------------------ */

    function pdfEscape(s) {
        return String(s == null ? '' : s)
            .replace(/\\/g, '\\\\')
            .replace(/\(/g, '\\(')
            .replace(/\)/g, '\\)')
            .replace(/[\r\n]/g, ' ');
    }

    function downloadBlob(blob, filename) {
        var link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
    }

    function buildBudgetPdf() {
        var totalBudget = getEl('[data-stat="totalBudget"]') ? getEl('[data-stat="totalBudget"]').textContent.replace('\u20B9', '') : '0';
        var totalSpent = getEl('[data-stat="totalSpent"]') ? getEl('[data-stat="totalSpent"]').textContent.replace('\u20B9', '') : '0';
        var remaining = getEl('[data-stat="remaining"]') ? getEl('[data-stat="remaining"]').textContent.replace('\u20B9', '') : '0';

        var lines = [
            'Spendly Budget Report',
            'Generated ' + new Date().toLocaleDateString('en-IN'),
            '',
            'MONTHLY SNAPSHOT',
            'Monthly Budget: Rs.' + totalBudget,
            'Total Spent: Rs.' + totalSpent,
            'Remaining: Rs.' + remaining,
            '',
            'BUDGET OVERVIEW'
        ];
        budgets.forEach(function (b) {
            lines.push(
                b.name + '  |  Limit: Rs.' + b.limit.toFixed(2) +
                '  |  Spent: Rs.' + b.spent.toFixed(2)
            );
        });

        var y = 740;
        var content = 'BT /F1 12 Tf 50 760 Td (Spendly Budget Report) Tj ET\n';
        y -= 20;
        content += 'BT /F1 9 Tf 50 ' + y + ' Td (Generated ' +
            pdfEscape(new Date().toLocaleDateString('en-IN')) + ') Tj ET\n';
        y -= 24;
        lines.forEach(function (line) {
            if (y < 40) y = 40;
            content += 'BT /F1 9 Tf 50 ' + y + ' Td (' + pdfEscape(line) + ') Tj ET\n';
            y -= 16;
        });

        var stream = content;
        var objects = [];
        objects.push('<< /Type /Catalog /Pages 2 0 R >>');
        objects.push('<< /Type /Pages /Kids [3 0 R] /Count 1 >>');
        objects.push('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>');
        objects.push('<< /Length ' + stream.length + ' >>\nstream\n' + stream + '\nendstream');
        objects.push('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>');

        var pdf = '%PDF-1.4\n';
        var offsets = [];
        var idx;
        for (idx = 0; idx < objects.length; idx++) {
            offsets.push(pdf.length);
            pdf += (idx + 1) + ' 0 obj\n' + objects[idx] + '\nendobj\n';
        }

        var xrefStart = pdf.length;
        pdf += 'xref\n0 ' + (objects.length + 1) + '\n';
        pdf += '0000000000 65535 f \n';
        offsets.forEach(function (off) {
            pdf += ('0000000000' + off).slice(-10) + ' 00000 n \n';
        });
        pdf += 'trailer\n<< /Size ' + (objects.length + 1) + ' /Root 1 0 R >>\n';
        pdf += 'startxref\n' + xrefStart + '\n%%EOF';

        return new Blob([pdf], { type: 'application/pdf' });
    }

    function exportPdf() {
        downloadBlob(
            buildBudgetPdf(),
            'spendly-budgets-' + new Date().toISOString().slice(0, 10) + '.pdf'
        );
        showToast('Budgets exported as PDF');
    }

    function exportExcel() {
        var rows = budgets.map(function (b) {
            var left = b.limit - b.spent;
            return [b.name, b.period, b.limit.toFixed(2), b.spent.toFixed(2), left.toFixed(2)];
        });
        var csv = 'Budget,Period,Allocated,Spent,Remaining\n';
        rows.forEach(function (r) {
            csv += r.map(function (c) {
                return '"' + String(c).replace(/"/g, '""') + '"';
            }).join(',') + '\n';
        });
        var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        downloadBlob(blob, 'spendly-budgets-' + new Date().toISOString().slice(0, 10) + '.csv');
        showToast('Budgets exported to Excel');
    }

    function bindExport() {
        var pdfBtn = getEl('[data-export-pdf]');
        if (pdfBtn) pdfBtn.addEventListener('click', exportPdf);

        var xlsBtn = getEl('[data-export-excel]');
        if (xlsBtn) xlsBtn.addEventListener('click', exportExcel);
    }

    /* ------------------------------------------------------------------ */
    /* Init                                                                */
    /* ------------------------------------------------------------------ */

    function init() {
        bindFilters();
        bindModal();
        bindExport();

        // Simulate initial load: show skeletons briefly, then render.
        setTimeout(function () {
            revealSkeletons();
            buildBarChart();
            buildDonut(budgets);
            renderAll();
            refreshIcons();
        }, 700);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
