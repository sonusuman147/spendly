# Spec: Transactions Module

## Overview

Adds a full **Transactions** page to Spendly's authenticated app shell. It presents every
expense as a transaction in a professional, filterable, paginated ledger with a page
header (**Add Transaction** / **Export**), five summary cards (Total Transactions, Total
Amount, Highest Expense, Average Expense, Last Transaction), an advanced filter section
(search, category, date range, amount range, sorting, reset), bulk selection, per-row
View / Edit / Delete actions, payment-method badges, category chips, and a **Recent
Activity** panel. The page is frontend-only in spirit: it reuses existing backend data and
existing CRUD routes, and only adds one minimal read-only route to render the template so
the page is reachable and consistent with the rest of the app.

## Depends on

- Completed app shell redesign (sidebar + header) in `base.html` / `style.css`.
- Existing expense CRUD routes in `app.py` (`add_expense`, `edit_expense`,
  `delete_expense_view`) — reused for the View/Edit/Delete actions.
- `get_expenses_by_user()` in `database/db.py` — reused to fetch transaction data.

## Routes

- `GET /transactions` — render the Transactions page — **logged-in**
  - Read-only. Calls `login_required()`, reuses `db_get_expenses_by_user()` and
    `CATEGORIES`, computes lightweight summary stats, and renders `transactions.html`.
  - No new queries, no schema changes, no auth changes, no business-logic changes.

## Database changes

No database changes. The `expenses` table already stores `id, user_id, amount, category,
date, description, created_at`. Payment method, export, bulk delete, and an activity log
are **not** stored — they are frontend placeholders.

## Templates

- **Create:** `templates/transactions.html` — extends `base.html`; uses `page_title`,
  `breadcrumb`, `head`, `content`, and `scripts` blocks.
- **Modify:** `templates/base.html` — enable the previously-disabled Transactions sidebar
  link (`url_for('transactions')`, active-state class, "Soon" badge removed).

## Files to change

- `templates/base.html` — sidebar link activation.

## Files to create

- `templates/transactions.html` — page markup.
- `static/css/transactions.css` — page-specific styles using existing CSS variables.
- `static/js/transactions.js` — rendering, filters, sorting, pagination, bulk selection,
  CSV export, view modal, activity feed, placeholder payment methods.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs.
- Parameterised queries only (existing helpers are reused as-is; no new SQL).
- Passwords hashed with werkzeug (unaffected).
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- Vanilla JS only — no frameworks, no npm.
- Do not modify existing backend logic, routes, database schema, or authentication.

## Definition of done

- `GET /transactions` renders for an authenticated user and redirects to `/login` otherwise.
- Sidebar "Transactions" link is active on the page and no longer shows "Soon".
- Five summary cards show totals derived from real expense data.
- Filters (search, category, date range, amount range, sort) narrow the table; Reset clears them.
- Pagination works when more than 8 transactions match.
- Row bulk-selection shows the bulk bar; "Select all" selects all filtered rows.
- View opens a details modal; Edit and Delete link to the existing expense routes.
- Payment badges render deterministically per transaction (frontend placeholder).
- Recent Activity shows real "added" events plus clearly-labelled demo edited/deleted entries.
- Export downloads a CSV of the currently filtered (or selected) transactions.
- Page is responsive (5 → 3 → 2 → 1 stat columns; table scrolls; layout stacks).
- `pytest` still passes with the existing test suite.

