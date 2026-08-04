# Spendly — Frontend Redesign Fix Pass (Frontend Only)

Scope: **Frontend only**. Do NOT modify backend, routes, DB, auth, or business logic.

## Steps

- [x] Initial redesign — left sidebar app shell, top header, dashboard redesign (welcome banner, filter bar, stat cards, recent transactions, CSS donut chart, quick actions), theme light/dark/system, responsive mobile drawer, collapsible sidebar (done in base.html, style.css, profile.css, profile.html, main.js).
- [x] Restore original Spendly branding in `static/css/style.css` — warm off-white "ghee" body background (`#f7f6f3` / `#f0ede6`), original ink palette, original green `--accent: #1a472a`, restored dark/system tokens, shared `.auth-success`, warm glass header.
- [x] Add shared `.auth-success` styling (in `style.css`).
- [x] Add profile-header styles to `static/css/profile.css`; remove duplicated `.auth-error`/`.auth-success` (now shared via `style.css`).
- [x] Fix broken HTML nesting in `templates/expenses/delete.html` (move actions out of details; close card/container correctly).
- [x] Add `page_title`/`breadcrumb` blocks to `templates/profile_edit.html`.
- [x] Polish expense list header + table (date chips, hover, actions) — frontend only.
- [x] Adapt `static/css/expenses.css` for the new app shell (form/delete centered cards, modern radii/shadows, responsive table).
- [x] JavaScript cleanup — sidebar collapse, mobile drawer, profile dropdown, theme switch (already implemented in `main.js`; verified no console errors).
- [x] Final verification — `pytest` (17 passed), page sweep (200s on all public pages), broken-link check, feature checklist, updated summary.

## Notes

- The `.claude/commands/create-specs.md` file does not exist; the actual command file is `.claude/commands/create-spec.md` (git feature-branch/spec workflow). It was read and its context applied (frontend-only, use CSS variables, Lucide icons, all templates extend base.html, preserve backend).
- `_diag.py` diagnostic script has been deleted (`Remove-Item _diag.py` — `Test-Path` returned `False`).

## Reports Page (Spec 11) — Implemented & Verified

- [x] Backend route `GET /reports` in `app.py` — auth-protected (unauthenticated → 302), filter parsing (date range, category, payment method), sources categories from user's categories table, calls `get_report_data()` with all filters, passes `report`, `categories`, `payment_methods`, `filters`, `query_args`, `has_active_filters` to `reports.html`.
- [x] Template `templates/reports.html` — page header with Generate Report / Export PDF / Export Excel buttons; six summary cards (Total Spending, Total Transactions, Average Monthly Spend, Highest Spending Month, Largest Expense, Potential Savings) with deltas; filter bar; Spending Trends line chart, Monthly Comparison bar chart, By Category donut, By Payment Method donut; Top Expenses table; Monthly Summary table; insights cards; quick-action cards; empty state; export toast. All wired to real DB data via `window.SPENDLY_REPORTS.report`.
- [x] JS `static/js/reports.js` — fixed `ReferenceError` (line chart used undeclared `labels` instead of `labelsGroup`/`monthLabels`); replaced `exportPdf` CSV logic with a real dependency-free PDF generator; made `revealSkeletons()` robust (pair each skeleton to its target, all siblings within `.dashboard-card-body`); loading skeletons resolve into charts/tables; charts/tables consume real DB data only.
- [x] CSS `static/css/reports.css` — added styles for `.filter-input`, `.filter-select`, `.txn-filter-field`, `.txn-filter-label`, `.filter-apply-btn`, `.filter-reset-btn`, `.filter-result-count` to match the Spendly design system, including theme-aware native date-picker indicator (dark/light).
- [x] Sidebar Reports link already enabled in `base.html` (no change needed).
- [x] Verification — real DB data flows through `get_report_data()` (demo user: total 5300, 4 txns, category + payment breakdowns, top expenses, monthly summary, insights); authenticated `/reports` returns 200 with all sections; unauthenticated → 302; 104 tests pass (`python -m pytest -q`).

