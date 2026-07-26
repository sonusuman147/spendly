# Spec: Expense CRUD

## Overview
This step implements full CRUD (Create, Read, Update, Delete) for expenses — the
core feature of Spendly. Logged-in users can add expenses with amount, category,
description, and date; view all their own expenses in a list sorted newest-first;
edit their own expenses via a pre-populated form; and delete their own expenses
after a confirmation step. This completes the primary user workflow of
register → login → track expenses, and every mutation is scoped strictly to the
owning user.

## Depends on
- Step 1: Database setup (`expenses` table exists, `get_db()` works)
- Step 2: Registration (users can log in and have a `user_id`)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 4: Profile page (expense summary established)
- Step 5: Backend Connection (expense query helpers exist in the codebase)
- Step 6: Google Authentication (session auth pattern is solid)

## Routes
- `GET /expenses` — list all expenses for the logged-in user, newest first — logged-in
- `GET /expenses/add` — render the add expense form — logged-in
- `POST /expenses/add` — validate and create a new expense, redirect to `/expenses` — logged-in
- `GET /expenses/<int:id>/edit` — render the edit form pre-populated with existing values — logged-in, own only
- `POST /expenses/<int:id>/edit` — validate and update the expense, redirect to `/expenses` — logged-in, own only
- `GET /expenses/<int:id>/delete` — render the delete confirmation page — logged-in, own only
- `POST /expenses/<int:id>/delete` — execute the delete, redirect to `/expenses` — logged-in, own only

Non-existent `<id>` on any of the above returns 404. An `<id>` that exists but
belongs to another user returns 403.

## Database changes
No new tables or columns. The `expenses` table already has all required columns:
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `user_id` (INTEGER NOT NULL REFERENCES users(id))
- `amount` (REAL NOT NULL)
- `category` (TEXT NOT NULL)
- `date` (TEXT NOT NULL)
- `description` (TEXT)
- `created_at` (TEXT DEFAULT datetime('now'))

New helper functions in `database/db.py`:
- `create_expense(user_id, amount, category, date, description)` → inserts and returns the new expense `id`
- `get_expenses_by_user(user_id)` → returns list of dicts ordered by `date DESC, created_at DESC`
- `get_expense_by_id(expense_id)` → returns a single expense dict or `None`
- `update_expense(expense_id, user_id, amount, category, date, description)` → updates the row `WHERE id = ? AND user_id = ?`, returns `True`/`False` based on rows affected
- `delete_expense(expense_id, user_id)` → deletes the row `WHERE id = ? AND user_id = ?`, returns `True`/`False` based on rows affected

## Templates
- **Create:** `templates/expenses/list.html` — full list of user's expenses with edit/delete action buttons and an empty state
- **Create:** `templates/expenses/form.html` — reusable form for both add and edit, driven by a `mode` variable ("add"/"edit")
- **Create:** `templates/expenses/delete.html` — confirmation page showing expense details before deletion
- **Modify:** `templates/base.html` — add an "Expenses" nav link if not already present

## Files to change
- `database/db.py` — add `create_expense()`, `get_expenses_by_user()`, `get_expense_by_id()`, `update_expense()`, `delete_expense()`; export `CATEGORIES` for reuse in `app.py`
- `app.py` — add the 7 CRUD routes; import expense helpers and `CATEGORIES` from `database/db.py`; apply the existing `@login_required` decorator to every route
- `static/css/expenses.css` — page-specific styles for list, form, and delete pages

## Files to create
- `templates/expenses/list.html`
- `templates/expenses/form.html`
- `templates/expenses/delete.html`
- `static/css/expenses.css`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All 7 routes require authentication — redirect to `/login` with a flash message if `session["user_id"]` is missing
- Ownership must be enforced in two layers: (1) the route fetches the expense via `get_expense_by_id()` and calls `abort(403)` if `expense["user_id"] != session["user_id"]`, and `abort(404)` if the expense doesn't exist at all; (2) `update_expense()` and `delete_expense()` also filter by `user_id = ?` in their SQL WHERE clause as a backstop — never rely on either layer alone
- Amount: required, must be a positive number ( > 0 ), max 2 decimal places
- Category: required, must be one of the values in `CATEGORIES` (the single source of truth, imported from `database/db.py`)
- Description: optional, max 200 characters, stripped of leading/trailing whitespace
- Date: required, valid `YYYY-MM-DD` string, cannot be in the future; defaults to today via `datetime.date.today().isoformat()` on the add form
- Currency always displays as ₹, amounts formatted to 2 decimal places via `"%.2f"|format(exp.amount)`
- Category tags use the CSS class pattern `cat-{{ category.lower() }}` established in `profile.html`
- No inline styles

## Definition of done
- [ ] Visiting `/expenses` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Logged-in user sees all their expenses listed newest-first on `/expenses`
- [ ] Logged-in user with no expenses sees an empty state with a link to add one
- [ ] `POST /expenses/add` with valid data inserts the row and redirects to `/expenses` with a success flash
- [ ] `POST /expenses/add` with invalid data (empty/negative amount, empty category, empty/future date) re-renders the form with validation errors and does not insert a row
- [ ] Clicking Edit navigates to `/expenses/<id>/edit` with the form pre-populated with that expense's values
- [ ] `POST /expenses/<id>/edit` with valid data updates the row and redirects to `/expenses` with a success flash
- [ ] Editing another user's expense by crafting the URL directly returns 403
- [ ] Editing a non-existent expense id returns 404
- [ ] Clicking Delete navigates to `/expenses/<id>/delete` showing the confirmation with that expense's details
- [ ] Confirming delete removes the row and redirects to `/expenses` with a success flash
- [ ] Deleting another user's expense by crafting the URL directly returns 403
- [ ] Deleting a non-existent expense id returns 404
- [ ] All amounts display with ₹ and 2 decimal places
- [ ] Category dropdown matches the `CATEGORIES` list exactly
- [ ] App runs on port 5001 without errors