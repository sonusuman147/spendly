# Spec: Reports Module

## Overview

Adds a full **Reports** module to Spendly's authenticated app shell. A new
sidebar page renders a header with **Generate Report**, **Export PDF**, and
**Export Excel** buttons, a filter bar (date range, category, payment method),
six summary cards (Total Spending, Total Transactions, Average Monthly Spend,
Highest Spending Month, Largest Expense, Potential Savings), a line chart for
spending trends, a monthly comparison bar chart, a category donut chart, a
payment-method donut chart, a Top Expenses table, a Monthly Summary table,
insight cards, and quick-action cards. The module ships with a read-only
`GET /reports` route and database helpers in `database/db.py` that compute all
report data (summary cards, chart series, tables, insights) from the user's
real expense rows using **parameterized SQL**. Filters (date range, category,
payment method) are validated server-side and preserved in the filter bar.

## Depends on

- Completed app shell redesign (sidebar + header) in `base.html` / `style.css`.
- Completed Transactions module (`09-transactions`) for the filter/table patterns.
- Completed Categories module (`10-categories`) for the `categories` table
  (used to resolve category colors for the donut chart) and the
  `get_user_categories` helper used for the category filter dropdown.
- Existing expense CRUD (`create_expense`, `get_expenses_by_user`) and the
  payment-method constants (`PAYMENT_METHODS`) in `database/db.py` / `app.py`.

## Routes

- `GET /reports` — render the Reports page — **logged-in**
  - Computes all report data from the user's expenses filtered by optional
    `date_from`, `date_to`, `category`, and `payment` query params.
  - Invalid dates are treated as "no filter"; invalid category/payment values
    are ignored. Filter state is preserved in the rendered filter bar.

## Database changes

No new tables or columns. Two new module helpers in `database/db.py`:

- `_build_report_filters(date_from, date_to, category, payment_method)` —
  builds the `WHERE` clause + bound params (excluding `user_id`, which the
  caller prepends first), mirroring `_build_transaction_filters`.
- `get_report_data(user_id, date_from, date_to, category, payment_method)` —
  computes everything the page needs in one pass:
  - `summary`: total spending, transaction count, average monthly spend,
    highest spending month (+ total), largest expense (+ category/date),
    potential savings (10% of top category) + savings percentage.
  - `monthly_trend`: per-month `{month, label, short, total, count, average}`
    ordered chronologically.
  - `previous_trend`: same-length window immediately before the report period,
    aligned by index for the current-vs-previous bar chart.
  - `category_breakdown`: `{name, color (from categories table), total, count,
    pct}` ordered by total desc.
  - `payment_breakdown`: `{name, total, count, pct}` ordered by total desc.
  - `top_expenses`: top 6 expenses by amount (with date/description/category/
    payment).
  - `insights`: computed, data-driven insight cards.
  - `has_data`: boolean for the empty state.

The default report period is the last six months (including the current
month). A custom date range is used as-is; the "previous" period is the
same-length window immediately before it.

## Templates

- **Create:** none (the page template already exists as `templates/reports.html`
  from the earlier frontend pass; it is modified below to render real data).
- **Modify:**
  - `templates/reports.html` — render summary cards, insights, filter values,
    and category/payment options from server data; add a `window.SPENDLY_REPORTS`
    config for the chart/tables JS; add an empty state when `report.has_data`
    is false.
  - `templates/base.html` — activate the previously-disabled Reports sidebar
    link (`url_for('reports')`, active state, remove "Soon" badge).

## Files to change

- `database/db.py` — add the two report helpers.
- `app.py` — import `get_report_data`, add the `GET /reports` route.
- `templates/base.html` — enable the Reports sidebar link.
- `templates/reports.html` — replace demo/static values with real data.
- `static/js/reports.js` — read real data from `window.SPENDLY_REPORTS` instead
  of hardcoded demo arrays; export buttons use real data.
- `README.md` — document the Reports feature, route, and test count.
- `PROJECT_DOCUMENTATION.md` — document the Reports module (helpers, route,
  file list, test inventory).

## Files to create

- `.claude/specs/11-report.md` — this spec.
- `.claude/plans/11-report.md` — implementation plan.
- `.claude/plans/TODO-11-report.md` — implementation tracking checklist.
- `tests/test_reports.py` — unit tests for `get_report_data` + route tests for
  `GET /reports` (auth, rendering, filters, preservation, empty state).

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — parameterised queries only (`?` placeholders).
- Passwords hashed with werkzeug (unaffected).
- Use CSS variables — never hardcode hex values in CSS (category colors come
  from the stored `categories.color` value and are applied via inline style).
- All templates extend `base.html`; all internal links use `url_for()`.
- Vanilla JS only — no frameworks, no npm.
- The route is read-only (GET only) — no mutations to expenses, categories,
  activities, or users.
- Preserve filter state in the rendered filter bar (date inputs + selects).

## Definition of done

- `GET /reports` renders for an authenticated user and redirects to `/login`
  otherwise.
- Sidebar "Reports" link is active on the page and no longer shows "Soon".
- Six summary cards show real values derived from the user's expenses.
- Line chart, monthly comparison bar chart, category donut, and payment donut
  are populated from real data.
- Top Expenses and Monthly Summary tables render real rows.
- Insights cards are computed from real data (or show an empty-state card).
- Date range, category, and payment-method filters narrow the report and their
  values are preserved in the filter bar after applying.
- No expenses matching the filters → a clear empty state is shown.
- Page is responsive and honors light/dark/system themes (unchanged design).
- Existing test suite plus the new `tests/test_reports.py` all pass (`pytest`).

