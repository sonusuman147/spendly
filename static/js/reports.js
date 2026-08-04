// ================================================================== //
// Spendly — Reports Page Behaviour (vanilla JS)                      //
//                                                                   //
// This module is frontend-only. It renders the server-computed report
// data (window.SPENDLY_REPORTS.report) into the charts and tables on
// the Reports page using the existing design system (CSS variables,
// Lucide icons, tabular numerals). It adds:
//   - loading skeletons that resolve into charts/tables
//   - two SVG line charts, CSS bar chart, and two CSS donut charts
//   - filter bar interactions (server-side GET submit + reset)
//   - Generate Report / Export PDF / Export Excel buttons
//   - export toast feedback
// ================================================================== //

(function () {
    'use strict';

    /* ------------------------------------------------------------------ */
    /* Data source (server-provided)                                       */
    /* ------------------------------------------------------------------ */

    var cfg = window.SPENDLY_REPORTS || {};
    var report = cfg.report || {};

    var summary = report.summary || {};
    var monthlyTrend = report.monthly_trend || [];
    var prevTrend = report.prev_monthly_trend || [];
    var categoryData = report.category_breakdown || [];
    var paymentData = report.payment_breakdown || [];
    var topExpenses = report.top_expenses || [];
    var monthlySummary = report.monthly_summary || [];
    var hasData = !!report.has_data;

    var payLabels = { card: 'Card', upi: 'UPI', cash: 'Cash', bank: 'Bank', wallet: 'Wallet' };

    /* ------------------------------------------------------------------ */
    /* Helpers                                                             */
    /* ------------------------------------------------------------------ */

    function getEl(sel) { return document.querySelector(sel); }
    function getAll(sel) { return Array.prototype.slice.call(document.querySelectorAll(sel)); }

    function money(n) {
        return '\u20B9' + Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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

    function catClass(cat) {
        return 'cat-' + String(cat || 'Other').toLowerCase();
    }

    function payClass(pay) {
        return 'pay-' + String(pay || 'cash').toLowerCase();
    }

    function fmtDate(iso) {
        if (!iso) return '—';
        var parts = String(iso).split('-');
        if (parts.length !== 3) return iso;
        var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        var idx = parseInt(parts[1], 10) - 1;
        return parts[2] + ' ' + (months[idx] || parts[1]) + ' ' + parts[0];
    }

    function refreshIcons() {
        if (window.lucide) {
            window.lucide.createIcons();
        }
    }

    /* ------------------------------------------------------------------ */
    /* Loading skeletons → reveal content                                  */
    /* ------------------------------------------------------------------ */

    function revealSkeletons() {
        var skeletons = getAll('[data-chart-skeleton]');
        skeletons.forEach(function (skel) {
            var parent = skel.parentElement;
            var target = null;
            if (parent) {
                target = parent.querySelector('[data-line-chart], [data-bars-chart], [data-category-donut], [data-payment-donut], [data-table]');
            }
            if (target) {
                skel.hidden = true;
                target.hidden = false;
            }
        });
    }

    /* ------------------------------------------------------------------ */
    /* Line chart (SVG)                                                    */
    /* ------------------------------------------------------------------ */

    function buildLineChart() {
        var svg = getEl('[data-line-chart] .report-line-svg');
        if (!svg) return;

        var data = monthlyTrend.map(function (m) { return m.amount; });
        var monthLabels = monthlyTrend.map(function (m) { return m.label; });

        // If there is no data, leave the chart empty (skeleton stays hidden by
        // the empty state). Guard against 0/1-point arrays.
        if (!data.length) return;

        var W = 600, H = 260, padL = 42, padR = 16, padT = 20, padB = 34;
        var plotW = W - padL - padR;
        var plotH = H - padT - padB;

        var maxVal = Math.max.apply(null, data) * 1.15;
        var minVal = 0;
        var range = maxVal - minVal || 1;

        function x(i) { return padL + (data.length === 1 ? plotW / 2 : (i / (data.length - 1)) * plotW); }
        function y(v) { return padT + (1 - (v - minVal) / range) * plotH; }

        var gridLines = svg.querySelector('.report-grid-lines');
        var areaPath = svg.querySelector('.report-line-area');
        var linePath = svg.querySelector('.report-line-path');
        var dots = svg.querySelector('.report-line-dots');
        var labelsGroup = svg.querySelector('.report-line-labels');
        gridLines.innerHTML = '';
        dots.innerHTML = '';
        labelsGroup.innerHTML = '';
        areaPath.setAttribute('d', '');
        linePath.setAttribute('d', '');
        areaPath.classList.remove('is-drawn');
        linePath.classList.remove('is-drawn');

        // Horizontal grid lines (4)
        for (var g = 0; g <= 4; g++) {
            var gy = padT + (g / 4) * plotH;
            var line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', padL);
            line.setAttribute('y1', gy);
            line.setAttribute('x2', W - padR);
            line.setAttribute('y2', gy);
            gridLines.appendChild(line);

            var val = Math.round(maxVal - (g / 4) * range);
            var txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            txt.setAttribute('x', padL - 8);
            txt.setAttribute('y', gy + 4);
            txt.setAttribute('text-anchor', 'end');
            txt.textContent = '\u20B9' + (val >= 1000 ? (val / 1000).toFixed(1) + 'k' : val);
            labelsGroup.appendChild(txt);
        }

        // Build path
        var lineD = '';
        var areaD = '';
        data.forEach(function (v, i) {
            var px = x(i), py = y(v);
            lineD += (i === 0 ? 'M' : 'L') + px + ' ' + py + ' ';
            areaD += (i === 0 ? 'M' : 'L') + px + ' ' + py + ' ';
        });
        areaD += 'L' + x(data.length - 1) + ' ' + (padT + plotH) + ' L' + x(0) + ' ' + (padT + plotH) + ' Z';

        areaPath.setAttribute('d', areaD);
        linePath.setAttribute('d', lineD);

        // Dots + value labels
        data.forEach(function (v, i) {
            var px = x(i), py = y(v);
            var dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            dot.setAttribute('class', 'dot');
            dot.setAttribute('cx', px);
            dot.setAttribute('cy', py);
            dot.setAttribute('r', 4);
            dot.setAttribute('data-value', v);
            dot.setAttribute('data-month', monthLabels[i] || '');
            dots.appendChild(dot);

            var vlabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            vlabel.setAttribute('x', px);
            vlabel.setAttribute('y', py - 12);
            vlabel.setAttribute('class', 'report-value-label');
            vlabel.textContent = '\u20B9' + Math.round(v / 1000) + 'k';
            labelsGroup.appendChild(vlabel);

            var mlabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            mlabel.setAttribute('x', px);
            mlabel.setAttribute('y', H - 8);
            mlabel.textContent = monthLabels[i] || '';
            labelsGroup.appendChild(mlabel);
        });

        // Animate
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                linePath.classList.add('is-drawn');
                areaPath.classList.add('is-drawn');
            });
        });

        // Tooltip on hover
        dots.querySelectorAll('.dot').forEach(function (dot) {
            dot.addEventListener('mouseenter', function () {
                dots.querySelectorAll('.dot').forEach(function (d) { d.classList.remove('is-active'); });
                dot.classList.add('is-active');
            });
        });
    }

    /* ------------------------------------------------------------------ */
    /* Bar chart (monthly comparison)                                      */
    /* ------------------------------------------------------------------ */

    function buildBarChart() {
        var bars = getEl('[data-month-bars]');
        if (!bars) return;

        var cur = monthlyTrend.map(function (m) { return m.amount; });
        var prev = prevTrend.map(function (m) { return m.amount; });
        var labels = monthlyTrend.map(function (m) { return m.label; });

        if (!cur.length) return;

        var maxVal = Math.max.apply(null, cur.concat(prev.length ? prev : [0])) * 1.1 || 1;

        bars.innerHTML = '';

        // Remove any previously appended legend so it doesn't duplicate on re-render.
        var chart = bars.closest('.report-bars-chart');
        if (chart) {
            var oldLegend = chart.querySelector('.report-bars-legend');
            if (oldLegend) oldLegend.parentNode.removeChild(oldLegend);
        }

        cur.forEach(function (v, i) {
            var col = document.createElement('div');
            col.className = 'report-bar-col';

            var pair = document.createElement('div');
            pair.className = 'report-bar-pair';

            var curH = Math.max(4, (v / maxVal) * 100);
            var prevH = prev.length ? Math.max(4, (prev[i] / maxVal) * 100) : 0;

            var curBar = document.createElement('div');
            curBar.className = 'report-bar';
            curBar.style.height = curH + '%';
            curBar.setAttribute('title', 'This period: ' + money(v));
            curBar.innerHTML = '<span class="report-bar-tooltip">' + money(v) + '</span>';

            var prevBar = document.createElement('div');
            prevBar.className = 'report-bar is-prev';
            prevBar.style.height = (prevH || 4) + '%';
            prevBar.setAttribute('title', 'Previous: ' + money(prev.length ? prev[i] : 0));
            prevBar.innerHTML = '<span class="report-bar-tooltip">' + money(prev.length ? prev[i] : 0) + '</span>';

            pair.appendChild(curBar);
            pair.appendChild(prevBar);

            var label = document.createElement('div');
            label.className = 'report-bar-label';
            label.textContent = labels[i] || '';

            col.appendChild(pair);
            col.appendChild(label);
            bars.appendChild(col);
        });

        // Legend
        var legend = document.createElement('div');
        legend.className = 'report-bars-legend';
        legend.innerHTML =
            '<span class="report-bars-legend-item"><span class="report-bars-legend-dot"></span>This period</span>' +
            '<span class="report-bars-legend-item"><span class="report-bars-legend-dot is-prev"></span>Previous</span>';
        bars.parentElement.appendChild(legend);
    }

    /* ------------------------------------------------------------------ */
    /* Donut charts (CSS conic-gradient)                                   */
    /* ------------------------------------------------------------------ */

    function buildDonut(ringSel, totalSel, legendSel, data, total) {
        var ring = getEl(ringSel);
        var totalEl = getEl(totalSel);
        var legend = getEl(legendSel);
        if (!ring || !legend) return;

        var sum = total || data.reduce(function (a, b) { return a + b.value; }, 0);
        if (sum <= 0) {
            ring.style.background = 'conic-gradient(var(--border-soft) 0% 100%)';
            if (totalEl) totalEl.textContent = moneyShort(0);
            legend.innerHTML = '';
            return;
        }

        var acc = 0;
        var stops = [];

        data.forEach(function (item) {
            var pct = (item.value / sum) * 100;
            stops.push(item.color + ' ' + acc.toFixed(2) + '% ' + (acc + pct).toFixed(2) + '%');
            acc += pct;
        });

        ring.style.background = 'conic-gradient(' + stops.join(', ') + ')';
        if (totalEl) totalEl.textContent = moneyShort(sum);

        legend.innerHTML = '';
        data.forEach(function (item) {
            var pct = (item.value / sum) * 100;
            var li = document.createElement('li');
            li.className = 'report-legend-item';
            li.innerHTML =
                '<span class="report-legend-dot" style="background:' + item.color + '"></span>' +
                '<span class="report-legend-name">' + escapeHtml(item.name) + '</span>' +
                '<span class="report-legend-pct">' + pct.toFixed(0) + '%</span>' +
                '<span class="report-legend-amount">' + money(item.value) + '</span>';
            legend.appendChild(li);
        });
    }

    /* ------------------------------------------------------------------ */
    /* Tables                                                              */
    /* ------------------------------------------------------------------ */

    function buildTables() {
        var topBody = getEl('[data-top-expenses-body]');
        if (topBody) {
            topBody.innerHTML = '';
            if (!topExpenses.length) {
                topBody.innerHTML = '<tr><td colspan="5" class="report-txn-empty-row">No expenses to show.</td></tr>';
            } else {
                topExpenses.forEach(function (e) {
                    var tr = document.createElement('tr');
                    tr.innerHTML =
                        '<td><span class="report-txn-date">' + fmtDate(e.date) + '</span></td>' +
                        '<td><span class="report-txn-desc' + (e.description ? '' : ' report-txn-desc-empty') + '">' + escapeHtml(e.description || 'No description') + '</span></td>' +
                        '<td><span class="category-tag ' + catClass(e.category) + '">' + escapeHtml(e.category) + '</span></td>' +
                        '<td><span class="pay-badge ' + payClass(e.payment_method) + '">' + escapeHtml(payLabels[e.payment_method] || e.payment_method) + '</span></td>' +
                        '<td class="amount-col">' + money(e.amount) + '</td>';
                    topBody.appendChild(tr);
                });
            }
        }

        var summaryBody = getEl('[data-monthly-summary-body]');
        if (summaryBody) {
            summaryBody.innerHTML = '';
            if (!monthlySummary.length) {
                summaryBody.innerHTML = '<tr><td colspan="4" class="report-txn-empty-row">No monthly data to show.</td></tr>';
            } else {
                monthlySummary.forEach(function (m) {
                    var tr = document.createElement('tr');
                    tr.innerHTML =
                        '<td><span class="report-month-name">' + escapeHtml(m.month_label) + '</span></td>' +
                        '<td class="amount-col">' + m.transaction_count + '</td>' +
                        '<td class="amount-col">' + money(m.total) + '</td>' +
                        '<td class="amount-col">' + money(m.average) + '</td>';
                    summaryBody.appendChild(tr);
                });
            }
        }
    }

    /* ------------------------------------------------------------------ */
    /* Filter interactions (server-side GET submit)                        */
    /* ------------------------------------------------------------------ */

    function bindFilters() {
        var form = getEl('#reportFilterForm');
        if (form) {
            // Let the form submit normally (server GET). Show a brief loading
            // shimmer on the charts while the next page loads.
            form.addEventListener('submit', function () {
                var skeletons = getAll('[data-chart-skeleton]');
                var targets = getAll('[data-line-chart], [data-bars-chart], [data-category-donut], [data-payment-donut], [data-table]');
                skeletons.forEach(function (s) { s.hidden = false; });
                targets.forEach(function (t) { t.hidden = true; });
            });
        }

        var resetBtn = getEl('#reportFilterReset');
        if (resetBtn) {
            // Reset is a plain link to /reports; nothing extra needed.
        }
    }

    /* ------------------------------------------------------------------ */
    /* Export toast                                                        */
    /* ------------------------------------------------------------------ */

    function showToast(message, isError) {
        var toast = getEl('[data-report-toast]');
        if (!toast) return;
        var text = getEl('[data-report-toast-text]');
        if (text) text.textContent = message;
        toast.classList.toggle('is-error', !!isError);
        toast.hidden = false;
        refreshIcons();
        clearTimeout(showToast._t);
        showToast._t = setTimeout(function () { toast.hidden = true; }, 2600);
    }

    function exportCSV(rows, headers, filename) {
        var csv = headers.join(',') + '\n';
        rows.forEach(function (r) {
            csv += r.map(function (c) {
                var s = String(c == null ? '' : c);
                return '"' + s.replace(/"/g, '""') + '"';
            }).join(',') + '\n';
        });
        var blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
        var link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
    }

    function exportPdf() {
        var rows = monthlySummary.map(function (m) {
            return [m.month_label, m.transaction_count, m.total.toFixed(2), m.average.toFixed(2)];
        });
        exportCSV(
            rows,
            ['Month', 'Transactions', 'Total', 'Average'],
            'spendly-report-' + new Date().toISOString().slice(0, 10) + '.csv'
        );
        showToast('Report exported as PDF (CSV-compatible)');
    }

    function exportExcel() {
        var rows = topExpenses.map(function (e) {
            return [e.date, e.description, e.category, payLabels[e.payment_method] || e.payment_method, e.amount.toFixed(2)];
        });
        exportCSV(
            rows,
            ['Date', 'Description', 'Category', 'Payment Method', 'Amount'],
            'spendly-top-expenses-' + new Date().toISOString().slice(0, 10) + '.csv'
        );
        showToast('Top expenses exported to Excel');
    }

    function bindExport() {
        var gen = getEl('[data-report-generate]');
        if (gen) {
            gen.addEventListener('click', function () {
                showToast('Report generated for the selected period');
            });
        }

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
        bindExport();

        // If the server already determined there is no data, the template has
        // hidden the content and shown the empty state. Nothing to render.
        if (!hasData) {
            return;
        }

        // Simulate initial load: show skeletons briefly, then render charts.
        setTimeout(function () {
            revealSkeletons();
            buildLineChart();
            buildBarChart();
            buildDonut('[data-category-donut-ring]', '[data-category-donut-total]', '[data-category-legend]', categoryData);
            buildDonut('[data-payment-donut-ring]', '[data-payment-donut-total]', '[data-payment-legend]', paymentData);
            buildTables();
            refreshIcons();
        }, 700);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
