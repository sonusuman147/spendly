# Spec: Categories Module

## Overview

Adds a complete **Categories** module to Spendly's authenticated app shell. Users get a
dedicated `/categories` page with a header (**Add Category**), four summary cards (Total
Categories, Most Used Category, Highest Spending Category, Unused Categories), a search +
filter section, a professional categories table (icon, color, name, description,
transaction count, total spent, average expense, created date, and View/Edit/Delete
actions), a donut chart for spending distribution, a Top Categories ranking panel, and
four quick-action cards (Create Category, Merge Categories, Export Categories, Category
Analytics). Categories become a first-class, user-scoped entity backed by a real SQLite
table with validation, colors/icons, usage statistics, search, sorting, pagination, and
protected deletion (a category in use by expenses can only be deleted after explicit
confirmation, which reassigns its expenses to "Other"). Expense forms and the Transactions
ledger filters are updated to source category options from the user's categories table so
custom categories work consistently across the app.

## Depends on

- Completed app shell redesign (sidebar + header) in `base.html` / `style.css`.
- Existing expense CRUD (`create_expense`, `update_expense`, `get_expenses_by_user`) and
  the transactions ledger (`get_transactions`, `_build_transaction_filters`) in
  `database/db.py` / `app.py` — reused so category changes stay consistent everywhere.
- The `CATEGORIES` fallback list — kept so the app continues to work for databases that
  predate the categories table (e.g. existing seeded expenses reference these names).

## Routes

- `GET /categories` — render the Categories page — **logged-in**
  - Summary cards, search/sort/pagination table, donut distribution, top categories
    ranking, quick-action cards. Supports `search`, `sort`, `page` query params.
- `GET/POST /categories/add` — create a category — **logged-in**
  - Validation: required name (≤ 30 chars), case-insensitive uniqueness per user,
    valid Lucide icon name, valid hex color. Redirects to `/categories` on success.
- `GET/POST /categories/<int:id>/edit` — edit a category — **logged-in** (owner only, 403)
  - Rejects name collisions with other categories (excluding itself). If the name changes,
    existing expenses using the old name are updated to the new name.
- `GET/POST /categories/<int:id>/delete` — delete a category — **logged-in** (owner only, 403)
  - If the category is in use by expenses, deletion is blocked unless the user confirms;
    on confirmed delete, the category's expenses are reassigned to "Other".
- `GET/POST /categories/merge` — merge source into target — **logged-in**
  - Source expenses are reassigned to the target category, then the source is deleted.
- `GET /categories/export` — export categories + usage stats as CSV — **logged-in**
- `GET /categories/analytics` — dedicated analytics page — **logged-in**

## Database changes

New table `categories`:

```sql
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    icon TEXT NOT NULL DEFAULT 'tag',
    color TEXT NOT NULL DEFAULT '#1a472a',
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE (user_id, name)
);
```

New module constants:

- `CATEGORY_ICONS` — whitelist of Lucide icon names offered by the icon picker.
- `CATEGORY_COLORS` — preset hex palette (safe, theme-independent brand greens/accents
  that map to the existing `--bar-*` spending colors).
- `CATEGORY_SORT_OPTIONS` — whitelisted sort keys for server-side category sorting.

New DB helpers (all parameterised, ownership-scoped):

- `ensure_default_categories(user_id)` — seeds the 7 defaults + rows for any expense
  categories missing a row (safe migration for existing data).
- `backfill_categories()` — ensures every existing user has category rows (startup).
- `create_category(user_id, name, description, icon, color)` — returns new id; raises
  `sqlite3.IntegrityError` on duplicate name.
- `get_category_by_id(category_id, user_id)` — category row + usage stats, or None.
- `update_category(category_id, user_id, name, description, icon, color)` — renames
  existing expenses when the name changes; returns bool.
- `delete_category(category_id, user_id, reassign=True)` — reassigns the category's
  expenses to "Other" then deletes the row; returns bool.
- `get_categories(user_id, search, sort, page, per_page)` — paginated list joined with
  expense usage stats (`transaction_count`, `total_spent`, `avg_expense`).
- `get_category_stats(user_id)` — aggregate summary cards + spending distribution +
  conic-gradient string (CSS) + top-categories ranking.
- `get_categories_export(user_id)` — flat rows for CSV export.
- `merge_categories(user_id, source_id, target_id)` — reassigns expenses then deletes
  the source category; returns bool.

`seed_db()` is updated to also create the 7 category rows for the demo user.

## Templates

- **Create:**
  - `templates/categories/list.html` — main page (extends `base.html`)
  - `templates/categories/form.html` — add/edit form with icon + color pickers
  - `templates/categories/delete.html` — delete confirmation (usage warning)
  - `templates/categories/merge.html` — merge source→target form
  - `templates/categories/analytics.html` — analytics page
- **Modify:**
  - `templates/base.html` — activate the previously-disabled Categories sidebar link
    (`url_for('categories')`, active state, remove "Soon" badge).

## Files to change

- `database/db.py` — schema, constants, category helpers, seed + backfill.
- `app.py` — category routes + updated expense/transaction category sourcing.
- `templates/base.html` — sidebar link activation.
- `templates/transactions.html` — category filter sourced from user categories.

## Files to create

- `templates/categories/list.html`, `form.html`, `delete.html`, `merge.html`,
  `analytics.html`
- `static/css/categories.css` — page-specific styles using existing CSS variables only.
- `static/js/categories.js` — filter auto-submit, icon/color pickers, view modal,
  delete/merge confirm (vanilla JS).
- `tests/test_categories.py` — DB unit tests + route tests.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs — parameterised queries only.
- Passwords hashed with werkzeug (unaffected).
- Use CSS variables — never hardcode hex values in CSS (category color values are stored
  data, applied via inline style where the template needs the user's chosen color).
- All templates extend `base.html`; all internal links use `url_for()`.
- Vanilla JS only — no frameworks, no npm.
- Do not modify authentication, existing routes, or business logic unless required for
  category CRUD consistency (expense form/ledger category sourcing is an allowed change).

## Definition of done

- `GET /categories` renders for an authenticated user and redirects to `/login` otherwise.
- Sidebar "Categories" link is active on the page and no longer shows "Soon".
- Four summary cards show real totals (total, most used, highest spending, unused).
- Search, sort, and pagination work on the categories table.
- The table shows icon, color, name, description, transaction count, total spent, average
  expense, created date, and View/Edit/Delete actions.
- Donut chart + legend reflect real spending distribution; Top Categories panel ranks by
  total spent.
- Create / Edit / Delete / Merge / Export / Analytics all work with server-side validation
  and ownership checks.
- Deleting an in-use category requires confirmation and reassigns its expenses to "Other".
- Custom categories are selectable in the expense add/edit form and the Transactions
  ledger category filter.
- Page is responsive (cards 4 → 2 → 1, table scrolls, donut stacks on mobile) and honors
  light/dark/system themes.
- Existing test suite plus the new `tests/test_categories.py` all pass (`pytest`).

