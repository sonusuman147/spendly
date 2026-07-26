# Spec: Expense CRUD Operations

## Overview
Step 7 implements full CRUD (Create, Read, Update, Delete) for expenses — the core feature of Spendly. Logged-in users can add new expenses with amount, category, description, and date; view all their expenses in a sortable list; edit only their own expenses; and delete only their own expenses with a confirmation step. This completes the primary user workflow: register → login → track expenses.

## Depends on
- Step 1: Database setup (`expenses` table exists, `get_db()` works)
- Step 2: Registration (users can log in and have a `user_id`)
- Step 3: Login / Logout (`session["user_id"]` is set on login)
- Step 4: Profile page (expense summary established)
- Step 5: Backend Connection (expense query helpers exist in the codebase)
- Step 6: Google Authentication (session auth pattern is solid)

## User Stories
- **As a logged-in user**, I want to add a new expense with amount, category, description, and date so that I can track my spending.
- **As a logged-in user**, I want to see all my expenses in one place so that I can review my spending history.
- **As a logged-in user**, I want to edit any of my own expenses so that I can correct mistakes or update details.
- **As a logged-in user**, I want to delete an expense with a confirmation prompt so that I can remove erroneous entries without accidentally losing data.

## Functional Requirements
1. **Create Expense**: A logged-in user can submit a form with amount (required, positive number), category (required, from predefined list), description (optional, text), and date (required, date format). Submitting inserts a row into the `expenses` table linked to the user's `id`.
2. **Read/List Expenses**: A logged-in user can view all their expenses sorted by date (newest first) in a table with columns: Date, Description, Category, Amount, and action buttons (Edit, Delete).
3. **Update Expense**: A logged-in user can edit any expense where `user_id` matches their `session["user_id"]`. The edit form is pre-populated with the existing values. On submit, the row is updated. Attempting to edit another user's expense returns 403 Forbidden.
4. **Delete Expense**: A logged-in user can delete any expense where `user_id` matches their `session["user_id"]`. A confirmation page is shown before executing the delete. On confirm, the row is removed. Attempting to delete another user's expense returns 403 Forbidden.

## Validation Rules
- **Amount**: Required; must be a positive number ( > 0 ); max 2 decimal places accepted
- **Category**: Required; must be one of: Food, Transport, Bills, Health, Entertainment, Shopping, Other
- **Description**: Optional; max 200 characters; stripped of leading/trailing whitespace
- **Date**: Required; must be a valid date string (YYYY-MM-DD); cannot be in the future (optional but recommended)
- **Ownership**: All mutations (update, delete) must verify `expense.user_id == session["user_id"]` before proceeding; return `abort(403)` if mismatched

## Routes
- `GET /expenses` — render a list of all expenses for the logged-in user — **logged-in**
- `GET /expenses/add` — render the add expense form — **logged-in**
- `POST /expenses/add` — validate and create a new expense, redirect to `/expenses` — **logged-in**
- `GET /expenses/<int:id>/edit` — render the edit form pre-populated with existing values — **logged-in**, own only
- `POST /expenses/<int:id>/edit` — validate and update the expense, redirect to `/expenses` — **logged-in**, own only
- `GET /expenses/<int:id>/delete` — render the delete confirmation page — **logged-in**, own only
- `POST /expenses/<int:id>/delete` — execute the delete, redirect to `/expenses` — **logged-in**, own only

## Database changes
**No new tables or columns.** The `expenses` table already has all required columns:
- `id` (INTEGER PRIMARY KEY AUTOINCREMENT)
- `user_id` (INTEGER NOT NULL REFERENCES users(id))
- `amount` (REAL NOT NULL)
- `category` (TEXT NOT NULL)
- `date` (TEXT NOT NULL)
- `description` (TEXT)
- `created_at` (TEXT DEFAULT datetime('now'))

**New helper functions in `database/db.py`:**
- `create_expense(user_id, amount, category, date, description)` → inserts and returns the new expense `id`
- `get_expenses_by_user(user_id)` → returns list of dicts ordered by `date DESC, created_at DESC`
- `get_expense_by_id(expense_id)` → returns a single expense dict or `None`
- `update_expense(expense_id, amount, category, date, description)` → updates the row, returns `True`
- `delete_expense(expense_id)` → deletes the row, returns `True`

## Templates
- **Create:** `templates/expenses/list.html` — full list of user's expenses with edit/delete action buttons
- **Create:** `templates/expenses/form.html` — reusable form for both add and edit operations
- **Create:** `templates/expenses/delete.html` — confirmation page showing expense details before deletion

## Files to change
- `database/db.py` — add `create_expense()`, `get_expenses_by_user()`, `get_expense_by_id()`, `update_expense()`, `delete_expense()` helpers
- `app.py` — add the 7 new routes for CRUD operations; update imports from `database/db.py`

## Files to create
- `templates/expenses/list.html` — expense list page
- `templates/expenses/form.html` — add/edit expense form
- `templates/expenses/delete.html` — delete confirmation page
- `static/css/expenses.css` — page-specific styles for expense pages

## New dependencies
No new dependencies.

## UI Requirements
- **Expense List Page** (`/expenses`):
  - Header with "Your Expenses" title and an "Add Expense" button
  - Table with columns: Date, Description, Category, Amount, Actions
  - Each row has Edit (pencil icon) and Delete (trash icon) action buttons
  - Empty state: "No expenses yet. Add your first expense!" with a link/button to `/expenses/add`
  - Flash messages for success/error feedback

- **Add/Edit Expense Form** (`/expenses/add`, `/expenses/<id>/edit`):
  - Card layout matching the auth card design pattern
  - Fields: Amount (number input), Category (select dropdown), Description (textarea), Date (date input)
  - Submit button: "Add Expense" for create, "Update Expense" for edit
  - Cancel link back to `/expenses`
  - Validation errors displayed per-field or as flash messages

- **Delete Confirmation** (`/expenses/<id>/delete`):
  - Warning card with the expense details (amount, category, description, date)
  - "Are you sure you want to delete this expense?" prompt
  - "Yes, delete" button (red/danger style) and "Cancel" link back to `/expenses`

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only via `get_db()`
- Parameterised queries only — never string-format values into SQL
- Foreign keys PRAGMA must be enabled on every connection (already done in `get_db()`)
- All CRUD routes must require authentication — redirect to `/login` with flash message if `session["user_id"]` is missing
- Ownership check: `update_expense()` and `delete_expense()` must include `user_id = ?` in the WHERE clause so the database enforces ownership — never rely on application-level checks alone
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Currency must always display as ₹ (Indian Rupee)
- Amounts must be formatted to 2 decimal places via `"%.2f"|format(exp.amount)`
- Category tags use the same CSS class pattern as profile.html: `cat-{{ category.lower() }}`
- The `CATEGORIES` list in `database/db.py` (`["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]`) must be the single source of truth for the category dropdown — import it into `app.py` and pass to templates
- Date input must default to today's date via `datetime.date.today().isoformat()` in the route for new expenses

## Acceptance Criteria
- [ ] Visiting `/expenses` as an unauthenticated user redirects to `/login`
- [ ] Visiting `/expenses/add` as an unauthenticated user redirects to `/login`
- [ ] Logged-in user sees all their expenses listed newest-first on `/expenses`
- [ ] Logged-in user with no expenses sees the empty state message with a link to add an expense
- [ ] Submitting a valid expense via `POST /expenses/add` inserts the row and shows a success flash
- [ ] Submitting an invalid expense (empty amount, negative amount, empty category, empty date) shows validation errors and re-renders the form
- [ ] Clicking Edit on an expense row navigates to `/expenses/<id>/edit` with the form pre-populated
- [ ] Submitting an edit updates the row and redirects to `/expenses` with a success flash
- [ ] Editing another user's expense by manually crafting the URL returns a 403 Forbidden
- [ ] Clicking Delete on an expense row navigates to `/expenses/<id>/delete` showing the confirmation with expense details
- [ ] Confirming the delete removes the row and redirects to `/expenses` with a success flash
- [ ] Deleting another user's expense by manually crafting the URL returns a 403 Forbidden
- [ ] All amounts display with ₹ symbol and 2 decimal places
- [ ] Category dropdown in the form matches the predefined list from `database/db.py`
- [ ] Date input defaults to today for new expenses
- [ ] App runs on port 5001 without errors
