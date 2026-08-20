import sqlite3
from datetime import date, timedelta
from werkzeug.security import generate_password_hash

DATABASE_PATH = "expense_tracker.db"

CATEGORIES = [
    "Food",
    "Transport",
    "Bills",
    "Health",
    "Entertainment",
    "Shopping",
    "Other",
]

SECURITY_QUESTIONS = [
    "What is your father's middle name?",
    "What is your best friend's name?",
    "What village were you born in?",
    "What is your pet's name?",
    "What was the name of your first school?",
]

# Payment methods supported by the Transactions module. Stored as TEXT on
# the expenses table so existing data stays valid (defaults to "cash").
PAYMENT_METHODS = ["card", "upi", "cash", "bank", "wallet"]

DEFAULT_PAYMENT_METHOD = "cash"

# Actions recorded in the activities table (Recent Activity feed).
ACTIVITY_ACTIONS = ("added", "edited", "deleted")

# Whitelist of allowed sort keys for server-side transaction sorting.
SORT_OPTIONS = {
    "date-desc": "date DESC, created_at DESC",
    "date-asc": "date ASC, created_at ASC",
    "amount-desc": "amount DESC, created_at DESC",
    "amount-asc": "amount ASC, created_at ASC",
    "category-asc": "category ASC, date DESC",
}

# ------------------------------------------------------------------ #
# Categories module constants                                        #
# ------------------------------------------------------------------ #

# Default categories seeded for every new user. Each entry is:
# (name, description, lucide icon name, hex color)
DEFAULT_CATEGORIES = [
    ("Food", "Groceries, dining out and everyday meals", "utensils", "#dc2626"),
    ("Transport", "Fuel, bus, cab and travel", "bus", "#d97706"),
    ("Bills", "Electricity, water, internet and utilities", "receipt", "#4f46e5"),
    ("Health", "Medicines, doctor visits and wellness", "heart-pulse", "#059669"),
    ("Entertainment", "Movies, games and fun", "clapperboard", "#db2777"),
    ("Shopping", "Clothes, electronics and retail", "shopping-bag", "#7c3aed"),
    ("Other", "Miscellaneous spending", "circle-ellipsis", "#6b7280"),
]

# Lucide icon names offered by the category icon picker.
CATEGORY_ICONS = [
    "utensils", "car", "bus", "receipt", "heart-pulse", "clapperboard",
    "shopping-bag", "circle-ellipsis", "home", "zap", "book-open",
    "dumbbell", "plane", "gift", "piggy-bank", "credit-card",
    "wifi", "droplets", "phone", "film", "coffee", "baby",
]

# Preset hex palette for category colors (maps to the existing --bar-* spending colors).
CATEGORY_COLORS = [
    "#dc2626", "#d97706", "#4f46e5", "#059669", "#db2777",
    "#7c3aed", "#6b7280", "#1a472a", "#c17f24", "#2563eb",
    "#0891b2", "#ea580c", "#16a34a", "#9333ea", "#e11d48",
]

# Whitelist of allowed sort keys for server-side category sorting.
# "total_spent" / "transaction_count" are aliases computed in the SQL select.
CATEGORY_SORT_OPTIONS = {
    "name-asc": "c.name COLLATE NOCASE ASC, c.id ASC",
    "name-desc": "c.name COLLATE NOCASE DESC, c.id DESC",
    "spent-desc": "total_spent DESC, c.name COLLATE NOCASE ASC",
    "spent-asc": "total_spent ASC, c.name COLLATE NOCASE ASC",
    "count-desc": "transaction_count DESC, c.name COLLATE NOCASE ASC",
"created-desc": "c.created_at DESC, c.id DESC",
    "created-asc": "c.created_at ASC, c.id ASC",
}

# ------------------------------------------------------------------ #
# Budgets module constants                                           #
# ------------------------------------------------------------------ #

# Static monthly budget limits per category (in ₹). There is no dedicated
# budgets table yet, so these constants define the "budget" line for the
# Budgets module. They are configurable here and consumed by
# get_budget_data(). If a dedicated budgets table is added later, replace
# these derived values with user-defined budgets WITHOUT changing the
# frontend contract (the shape of the data returned by get_budget_data()).
BUDGET_LIMITS = {
    "Food": 8000.0,
    "Transport": 4000.0,
    "Bills": 6000.0,
    "Health": 5000.0,
    "Entertainment": 3000.0,
    "Shopping": 5000.0,
    "Other": 2000.0,
}

# Default budget used for any category not present in BUDGET_LIMITS.
DEFAULT_BUDGET_LIMIT = 2000.0

# Whitelist of allowed status keys for the Budgets page filter.
BUDGET_STATUSES = ("on-track", "warning", "over")

# Number of months shown in the Budget vs Actual trend chart.
BUDGET_TREND_MONTHS = 6


def get_db():
    """Open and return a connection to the SQLite database.

    Sets row_factory to sqlite3.Row for dictionary-like column access
    and enables foreign key enforcement on every connection.
    """
    conn = sqlite3.connect(DATABASE_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create both tables using CREATE TABLE IF NOT EXISTS.

    Safe to call multiple times — will not fail on repeated runs.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT,
            payment_method TEXT NOT NULL DEFAULT 'cash',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            action TEXT NOT NULL,
            expense_id INTEGER,
            category TEXT,
            description TEXT,
            amount REAL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            icon TEXT NOT NULL DEFAULT 'tag',
            color TEXT NOT NULL DEFAULT '#1a472a',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE (user_id, name)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            category TEXT NOT NULL,
            limit_amount REAL NOT NULL,
            period TEXT NOT NULL DEFAULT 'monthly',
            is_default INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE (user_id, category)
        )
    """)

    # Add google_id column if not already present — safe on repeated runs
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Add security_question and security_answer_hash columns — safe on repeated runs
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN security_question TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN security_answer_hash TEXT")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Add payment_method column to expenses if not already present — safe on repeated runs
    try:
        cursor.execute("ALTER TABLE expenses ADD COLUMN payment_method TEXT NOT NULL DEFAULT 'cash'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()


def seed_db():
    """Insert demo user and sample expenses if the database is empty.

    Checks if users table already contains data before inserting.
    Safe to call multiple times — will not duplicate records.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Check if data already exists — prevent duplicate inserts
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Insert demo user using create_user helper with a security question
    user_id = create_user(
        "Demo User",
        "demo@spendly.com",
        password_hash=generate_password_hash("demo123"),
        security_question="What is your pet's name?",
        security_answer_hash=generate_password_hash("fido"),
    )

    today = date.today()

    # Insert 8 sample expenses across multiple categories with payment methods
    sample_expenses = [
        (user_id, 450.00, "Food", today - timedelta(days=28), "Weekly groceries", "upi"),
        (user_id, 150.00, "Transport", today - timedelta(days=25), "Bus pass recharge", "cash"),
        (user_id, 2000.00, "Bills", today - timedelta(days=20), "Electricity bill", "bank"),
        (user_id, 600.00, "Health", today - timedelta(days=18), "Pharmacy — medicines", "card"),
        (user_id, 350.00, "Entertainment", today - timedelta(days=14), "Movie tickets", "wallet"),
        (user_id, 1200.00, "Shopping", today - timedelta(days=10), "New headphones", "card"),
        (user_id, 320.00, "Food", today - timedelta(days=5), "Dinner at pizzeria", "upi"),
        (user_id, 100.00, "Other", today - timedelta(days=2), "Miscellaneous", "cash"),
    ]

    cursor.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description, payment_method) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (uid, amt, cat, d.isoformat(), desc, pm)
            for uid, amt, cat, d, desc, pm in sample_expenses
        ],
    )

    # Seed matching "added" activity records so Recent Activity is populated
    # with real data for the demo user on first boot.
    cursor.executemany(
        "INSERT INTO activities (user_id, action, expense_id, category, description, amount) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (user_id, "added", i + 1, cat, desc, amt)
            for i, (uid, amt, cat, d, desc, pm) in enumerate(sample_expenses)
        ],
    )

    # Seed the demo user's default category rows.
    cursor.executemany(
        "INSERT INTO categories (user_id, name, description, icon, color) "
        "VALUES (?, ?, ?, ?, ?)",
        [
            (user_id, name, desc, icon, color)
            for name, desc, icon, color in DEFAULT_CATEGORIES
        ],
    )

    conn.commit()
    conn.close()


def create_user(name, email, password_hash=None, google_id=None, security_question=None, security_answer_hash=None):
    """Create a new user with optional password hash, Google ID, and security question.

    If password_hash is None (Google-only user), stores an empty string.
    Inserts a new row into the users table and returns the new user's id.

    Raises sqlite3.IntegrityError if the email is already taken (UNIQUE constraint).
    Uses parameterized queries — safe from SQL injection.
    """
    if password_hash is None:
        password_hash = ""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, password_hash, google_id, security_question, security_answer_hash) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (name, email, password_hash, google_id, security_question, security_answer_hash),
    )
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return user_id


def get_user_by_email(email):
    """Look up a user by email address.

    Returns a dictionary of user fields if found, or None if no match.
    Uses a parameterized query — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_google_id(google_id):
    """Look up a user by Google ID.

    Returns a dictionary of user fields if found, or None if no match.
    Uses a parameterized query — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE google_id = ?", (google_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def link_google_account(user_id, google_id):
    """Link a Google account to an existing user.

    Sets the google_id column for the given user. Raises ValueError
    if the google_id is already linked to a different account.
    Uses a parameterized query — safe from SQL injection.
    """
    # Application-level uniqueness check
    existing = get_user_by_google_id(google_id)
    if existing and existing["id"] != user_id:
        raise ValueError("This Google account is already linked to another user.")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET google_id = ? WHERE id = ?", (google_id, user_id))
    conn.commit()
    conn.close()


def get_user_by_id(user_id):
    """Look up a user by primary key.

    Returns a dictionary of user fields (id, name, email, created_at,
    member_since) if found, or None if no match.
    member_since is formatted as 'Month YYYY' (e.g. 'January 2026').
    Uses a parameterized query — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    )
    user = cursor.fetchone()
    conn.close()
    if user:
        user = dict(user)
        # Parse the ISO-format date and format as "Month YYYY"
        from datetime import datetime
        try:
            dt = datetime.strptime(user["created_at"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            dt = datetime.strptime(user["created_at"][:10], "%Y-%m-%d")
        user["member_since"] = dt.strftime("%B %Y")
        return user
    return None


def update_user_profile(user_id, name, email):
    """Update a user's name and email.

    Returns True if the update was successful.
    Raises sqlite3.IntegrityError if the email is already taken.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET name = ?, email = ? WHERE id = ?",
        (name, email, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def update_password(user_id, new_password_hash):
    """Update a user's password hash.

    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (new_password_hash, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_user_by_email_with_security(email):
    """Look up a user by email and return only security-related fields.

    Returns dict with {id, security_question, security_answer_hash} if found,
    or None if no match. Used by the forgot-password flow.
    Uses a parameterized query — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, security_question, security_answer_hash FROM users WHERE email = ?",
        (email,),
    )
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def clear_expenses():
    """Delete all records from the expenses table.

    Users table is left untouched — only expense records are removed.
    Uses the existing get_db() helper to obtain a database connection.
    Safe to call multiple times.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses;")
    conn.commit()
    conn.close()


def get_user_expenses_summary(user_id, start_date=None, end_date=None):
    """Return a summary dictionary of a user's expenses, optionally filtered by date range.

    When start_date and/or end_date are provided, only expenses with date >= start_date
    and date <= end_date are included. Dates should be ISO format strings (YYYY-MM-DD).

    Returns a dict with:
      - total_expenses: float — sum of all expense amounts (0.0 if none)
      - expense_count: int — total number of expenses
      - category_breakdown: list of {category, total, count} — grouped
        by category, ordered by total descending
      - recent_expenses: list of {amount, category, date, description}
        — last 5 ordered by date then created_at descending
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Build dynamic WHERE clause for date filtering
    base_where = "WHERE user_id = ?"
    params = [user_id]

    if start_date:
        base_where += " AND date >= ?"
        params.append(start_date)
    if end_date:
        base_where += " AND date <= ?"
        params.append(end_date)

    # Total and count
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS total_expenses, "
        "COUNT(*) AS expense_count "
        f"FROM expenses {base_where}",
        tuple(params),
    )
    totals = dict(cursor.fetchone())

    # Category breakdown
    cursor.execute(
        "SELECT category, SUM(amount) AS total, COUNT(*) AS count "
        f"FROM expenses {base_where} "
        "GROUP BY category ORDER BY total DESC",
        tuple(params),
    )
    breakdown = [dict(row) for row in cursor.fetchall()]

    # Recent expenses
    cursor.execute(
        "SELECT amount, category, date, description "
        f"FROM expenses {base_where} "
        "ORDER BY date DESC, created_at DESC LIMIT 5",
        tuple(params),
    )
    recent = [dict(row) for row in cursor.fetchall()]

    conn.close()

    top_category = breakdown[0]["category"] if breakdown else "—"

    return {
        "total_expenses": totals["total_expenses"],
        "expense_count": totals["expense_count"],
        "top_category": top_category,
        "category_breakdown": breakdown,
        "recent_expenses": recent,
    }


def create_expense(user_id, amount, category, date, description, payment_method=None):
    """Insert a new expense and return its id.

    If payment_method is None or not a known method, DEFAULT_PAYMENT_METHOD
    is used. Uses parameterized queries — safe from SQL injection.
    """
    if payment_method not in PAYMENT_METHODS:
        payment_method = DEFAULT_PAYMENT_METHOD
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description, payment_method) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description, payment_method),
    )
    expense_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return expense_id


def get_expenses_by_user(user_id):
    """Return all expenses for a user, ordered by date then created_at descending.

    Returns a list of dicts. Returns empty list if no expenses exist.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, amount, category, date, description, payment_method, created_at "
        "FROM expenses WHERE user_id = ? "
        "ORDER BY date DESC, created_at DESC",
        (user_id,),
    )
    expenses = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return expenses


def get_expense_by_id(expense_id):
    """Return a single expense by its id, or None if not found.

    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, amount, category, date, description, payment_method, created_at "
        "FROM expenses WHERE id = ?",
        (expense_id,),
    )
    expense = cursor.fetchone()
    conn.close()
    return dict(expense) if expense else None


def update_expense(expense_id, user_id, amount, category, date, description, payment_method=None):
    """Update an expense row WHERE id = ? AND user_id = ?.

    If payment_method is None or not a known method, DEFAULT_PAYMENT_METHOD
    is used. Returns True if a row was updated, False if no matching row found.
    Uses parameterized queries — safe from SQL injection.
    """
    if payment_method not in PAYMENT_METHODS:
        payment_method = DEFAULT_PAYMENT_METHOD
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ?, payment_method = ? "
        "WHERE id = ? AND user_id = ?",
        (amount, category, date, description, payment_method, expense_id, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def delete_expense(expense_id, user_id):
    """Delete an expense row WHERE id = ? AND user_id = ?.

    Returns True if a row was deleted, False if no matching row found.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def _build_transaction_filters(search, category, date_from, date_to,
                               amount_min, amount_max):
    """Build the WHERE clause and parameters for transaction queries.

    All values are bound with `?` placeholders — never interpolated directly
    into SQL. Returns a tuple of (where_clause, params) where params does NOT
    include the user_id (the caller prepends it first).
    """
    clauses = ["WHERE user_id = ?"]
    params = []

    # Search across description, category, and payment method.
    if search:
        clauses.append(
            "(description LIKE ? OR category LIKE ? OR payment_method LIKE ?)"
        )
        like = f"%{search}%"
        params.append(like)
        params.append(like)
        params.append(like)

    if category:
        clauses.append("category = ?")
        params.append(category)

    if date_from:
        clauses.append("date >= ?")
        params.append(date_from)

    if date_to:
        clauses.append("date <= ?")
        params.append(date_to)

    if amount_min is not None:
        clauses.append("amount >= ?")
        params.append(amount_min)

    if amount_max is not None:
        clauses.append("amount <= ?")
        params.append(amount_max)

    return " AND ".join(clauses), params


def get_transactions(user_id, search="", category="", date_from=None, date_to=None,
                     amount_min=None, amount_max=None, sort="date-desc",
                     page=1, per_page=8):
    """Fetch paginated, server-side filtered transactions for a user.

    Returns a dict with:
      - items: list of expense dicts on the requested page
      - total: total number of matching transactions
      - pages: total number of pages
      - page: current page (clamped to valid range)
      - per_page: page size
      - has_prev / has_next: booleans for pagination UI
      - summary: dict with total_count, total_amount, highest, average, last
        computed from the *filtered* set (accurate statistics).

    `sort` is validated against SORT_OPTIONS before being used — anything else
    falls back to "date-desc". Uses parameterized queries — safe from SQL
    injection. When per_page is None, all matching rows are returned (used for
    CSV export).
    """
    sort_sql = SORT_OPTIONS.get(sort, SORT_OPTIONS["date-desc"])
    where, params = _build_transaction_filters(
        search, category, date_from, date_to, amount_min, amount_max,
    )
    full_params = [user_id] + params

    conn = get_db()
    cursor = conn.cursor()

    # Total matching count (unaffected by pagination).
    cursor.execute(f"SELECT COUNT(*) AS total FROM expenses {where}", tuple(full_params))
    total = cursor.fetchone()["total"]

    # Summary statistics over the filtered set.
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS total_amount, "
        "COALESCE(MAX(amount), 0.0) AS highest, "
        "COALESCE(AVG(amount), 0.0) AS average "
        f"FROM expenses {where}",
        tuple(full_params),
    )
    agg = cursor.fetchone()

    # Determine the "last" transaction (most recent by date) in the filtered set.
    cursor.execute(
        "SELECT id, user_id, amount, category, date, description, payment_method, created_at "
        f"FROM expenses {where} "
        "ORDER BY date DESC, created_at DESC LIMIT 1",
        tuple(full_params),
    )
    last_row = cursor.fetchone()

    # Pagination math.
    if per_page is None or per_page <= 0:
        per_page = total if total > 0 else 1
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(int(page), pages))

    # Fetch the page of items.
    cursor.execute(
        "SELECT id, user_id, amount, category, date, description, payment_method, created_at "
        f"FROM expenses {where} "
        f"ORDER BY {sort_sql} LIMIT ? OFFSET ?",
        tuple(full_params) + (per_page, (page - 1) * per_page),
    )
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()

    summary = {
        "total_count": total,
        "total_amount": round(agg["total_amount"], 2),
        "highest": round(agg["highest"], 2),
        "average": round(agg["average"], 2),
        "last": dict(last_row) if last_row else None,
    }

    return {
        "items": items,
        "total": total,
        "pages": pages,
        "page": page,
        "per_page": per_page,
        "has_prev": page > 1,
        "has_next": page < pages,
        "summary": summary,
    }


def get_expenses_by_ids(user_id, ids):
    """Return expense rows for the given ids, scoped to the user.

    Silently ignores ids that do not belong to the user. Returns a list of
    dicts. Uses parameterized queries — safe from SQL injection.
    """
    if not ids:
        return []
    conn = get_db()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in ids)
    cursor.execute(
        f"SELECT id, user_id, amount, category, date, description, payment_method, created_at "
        f"FROM expenses WHERE user_id = ? AND id IN ({placeholders})",
(user_id, *ids),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


# ================================================================== #
# Budgets module — DB layer                                          #
# ================================================================== #

MONTH_LABELS = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]

# Map a category name to a CSS category color token (shared design system).
BUDGET_CATEGORY_COLORS = {
    "Food": "var(--bar-food)",
    "Transport": "var(--bar-transport)",
    "Bills": "var(--bar-bills)",
    "Health": "var(--bar-health)",
    "Entertainment": "var(--bar-entertainment)",
    "Shopping": "var(--bar-shopping)",
    "Other": "var(--bar-other)",
}

# Map a category name to a Lucide icon token used by the budgets UI.
BUDGET_CATEGORY_ICONS = {
    "Food": "utensils",
    "Transport": "bus",
    "Bills": "zap",
    "Health": "heart-pulse",
    "Entertainment": "clapperboard",
    "Shopping": "shopping-bag",
    "Other": "circle-ellipsis",
}


def _budget_limit(category):
    """Return the configured monthly budget for a category (or the default)."""
    return BUDGET_LIMITS.get(category, DEFAULT_BUDGET_LIMIT)


def _budget_status(pct):
    """Return a (key, label) tuple for a budget usage percentage."""
    if pct >= 100:
        return ("over", "Over Budget")
    if pct >= 75:
        return ("warning", "At Risk")
    return ("on-track", "On Track")


def get_user_budgets(user_id):
    """Return all per-user budget rows for a user.

    Returns a list of dicts with id, category, limit_amount, period,
    is_default, created_at, ordered by category name. Empty list if none.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, category, limit_amount, period, is_default, created_at "
        "FROM budgets WHERE user_id = ? "
        "ORDER BY category COLLATE NOCASE ASC",
        (user_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_budget_by_id(budget_id, user_id):
    """Return a single budget row scoped to the user, or None if not found/owned.

    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, category, limit_amount, period, is_default, created_at "
        "FROM budgets WHERE id = ? AND user_id = ?",
        (budget_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def create_budget(user_id, category, limit):
    """Create a per-user budget row for a category and return its id.

    Uses an upsert (INSERT ... ON CONFLICT DO UPDATE) so creating a budget
    for a category that already exists simply updates the limit. Raises
    sqlite3.IntegrityError only on unexpected constraint violations.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO budgets (user_id, category, limit_amount, period, is_default) "
        "VALUES (?, ?, ?, 'monthly', 0) "
        "ON CONFLICT(user_id, category) DO UPDATE SET "
        "limit_amount = excluded.limit_amount, is_default = 0",
        (user_id, category, float(limit)),
    )
    budget_id = cursor.lastrowid
    if budget_id is None:
        # Upsert may not return lastrowid on some builds; fetch it.
        cursor.execute(
            "SELECT id FROM budgets WHERE user_id = ? AND category = ?",
            (user_id, category),
        )
        row = cursor.fetchone()
        budget_id = row["id"] if row else None
    conn.commit()
    conn.close()
    return budget_id


def update_budget_limit(user_id, category, limit):
    """Update a budget's limit for a user/category.

    Creates the row if it does not yet exist (upsert). Returns True if a
    row was affected. Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO budgets (user_id, category, limit_amount, period, is_default) "
        "VALUES (?, ?, ?, 'monthly', 0) "
        "ON CONFLICT(user_id, category) DO UPDATE SET "
        "limit_amount = excluded.limit_amount, is_default = 0",
        (user_id, category, float(limit)),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def delete_budget(user_id, category):
    """Delete a per-user budget row for a category.

    Returns True if a row was deleted, False if no matching row found.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM budgets WHERE user_id = ? AND category = ?",
        (user_id, category),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def reset_budget_defaults(user_id):
    """Remove all per-user budget rows so defaults are used again.

    Returns the number of rows removed. Uses parameterized queries — safe
    from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM budgets WHERE user_id = ?",
        (user_id,),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected


def _effective_budget_limits(user_id):
    """Return a dict of category -> limit merging user rows over defaults.

    For every category in BUDGET_LIMITS, use the user's per-category limit
    if one exists, otherwise fall back to the static default. Any per-user
    rows for categories not in BUDGET_LIMITS are appended with their limit.
    """
    limits = dict(BUDGET_LIMITS)
    user_rows = get_user_budgets(user_id)
    for row in user_rows:
        limits[row["category"]] = float(row["limit_amount"])
    return limits


def get_budget_months(user_id):
    """Return the distinct months (YYYY-MM) that have expenses for a user.

    Used to populate the month filter dropdown on the Budgets page. Ordered
    newest first. Returns a list of {value, label} dicts.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT strftime('%Y-%m', date) AS month "
        "FROM expenses WHERE user_id = ? "
        "ORDER BY month DESC",
        (user_id,),
    )
    months = []
    for row in cursor.fetchall():
        value = row["month"]
        parts = value.split("-")
        label = f"{MONTH_LABELS[int(parts[1])]} {parts[0]}"
        months.append({"value": value, "label": label})
    conn.close()
    return months


def get_budget_data(user_id, month=None, category=None, status=None):
    """Compute the full Budgets module data for a user.

    Budget limits come from the static BUDGET_LIMITS constants (there is no
    dedicated budgets table). Actuals are derived from the user's real expense
    rows, grouped by category and month.

    Args:
        user_id: the owning user.
        month: optional "YYYY-MM" filter (defaults to the current month).
        category: optional category name filter.
        status: optional status key filter ("on-track" | "warning" | "over").

    Returns a dict with:
      - budgets: list of {name, icon, color, limit, spent, remaining, period,
                 pct, status_key, status_label}
      - summary: {total_budget, total_spent, remaining, pct, over_count,
                 daily, days_left}
      - monthly_trend: list of {label, budget, actual} for the last
        BUDGET_TREND_MONTHS months
      - distribution: list of {name, color, limit} for the donut
      - insights: list of {icon, accent, title, text}
      - activity: list of {id, action, category, description, amount,
                 created_at, time_label}
      - months: list of {value, label} distinct expense months
      - filter_info: {month, category, status}
    """
    # Default the month filter to the current calendar month.
    if not month:
        today = date.today()
        month = f"{today.year:04d}-{today.month:02d}"

    # --- Category spending for the selected month (grouped by category) ---
    conn = get_db()
    cursor = conn.cursor()

    where = "WHERE user_id = ? AND strftime('%Y-%m', date) = ?"
    params = [user_id, month]
    if category:
        where += " AND category = ?"
        params.append(category)

    cursor.execute(
        "SELECT category, COALESCE(SUM(amount), 0.0) AS spent "
        f"FROM expenses {where} "
        "GROUP BY category ORDER BY spent DESC",
        tuple(params),
    )
    spent_by_cat = {row["category"]: row["spent"] for row in cursor.fetchall()}

    # --- Monthly actuals for the trend chart (last N months) ---
    cursor.execute(
        "SELECT strftime('%Y-%m', date) AS month, COALESCE(SUM(amount), 0.0) AS actual "
        "FROM expenses WHERE user_id = ? "
        "GROUP BY month ORDER BY month ASC",
        (user_id,),
    )
    actual_by_month = {row["month"]: row["actual"] for row in cursor.fetchall()}

    # --- Recent activity (for the timeline) ---
    cursor.execute(
        "SELECT id, action, category, description, amount, created_at "
        "FROM activities WHERE user_id = ? "
        "ORDER BY created_at DESC, id DESC LIMIT 8",
        (user_id,),
    )
    activity_rows = [dict(r) for r in cursor.fetchall()]
    conn.close()

# --- Build the per-category budget list ---
    # Show every configured budget category, merging any per-user limits
    # over the static defaults. If a category filter is set, only that
    # category is included.
    effective_limits = _effective_budget_limits(user_id)
    budgets = []
    for cat, limit in effective_limits.items():
        if category and cat != category:
            continue
        spent = spent_by_cat.get(cat, 0.0)
        remaining = limit - spent
        pct = (spent / limit * 100) if limit > 0 else 0.0
        s_key, s_label = _budget_status(pct)

        b = {
            "name": cat,
            "icon": BUDGET_CATEGORY_ICONS.get(cat, "circle"),
            "color": BUDGET_CATEGORY_COLORS.get(cat, "var(--accent)"),
            "limit": round(limit, 2),
            "spent": round(spent, 2),
            "remaining": round(remaining, 2),
            "period": "This month",
            "pct": round(pct, 1),
            "status_key": s_key,
            "status_label": s_label,
        }
        budgets.append(b)

    # Apply the status filter if requested.
    if status:
        budgets = [b for b in budgets if b["status_key"] == status]

    # --- Summary cards ---
    total_budget = sum(b["limit"] for b in budgets)
    total_spent = sum(b["spent"] for b in budgets)
    remaining = total_budget - total_spent
    pct = (total_spent / total_budget * 100) if total_budget > 0 else 0.0
    over_count = sum(1 for b in budgets if b["status_key"] == "over")

    if month == f"{date.today().year:04d}-{date.today().month:02d}":
        days_left = date.today().day
        days_left = max(1, date.today().day)
    else:
        days_left = 1
    daily = max(0, remaining / days_left) if days_left > 0 else 0

    summary = {
        "total_budget": round(total_budget, 2),
        "total_spent": round(total_spent, 2),
        "remaining": round(max(0, remaining), 2),
        "pct": round(pct, 1),
        "over_count": over_count,
        "daily": round(daily, 2),
        "days_left": days_left,
    }

    # --- Trend chart (last N months) ---
    trend = []
    today = date.today()
    total_limit = sum(BUDGET_LIMITS.values())
    for i in range(BUDGET_TREND_MONTHS - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m < 1:
            m += 12
            y -= 1
        key = f"{y:04d}-{m:02d}"
        trend.append({
            "label": MONTH_LABELS[m][:3],
            "budget": round(total_limit, 2),
            "actual": round(actual_by_month.get(key, 0.0), 2),
        })

    # --- Distribution (donut) ---
    distribution = [
        {"name": b["name"], "color": b["color"], "limit": b["limit"]}
        for b in budgets
    ]

    # --- Insights (data-driven) ---
    insights = _compute_budget_insights(budgets, summary, trend)

    # --- Activity timeline ---
    activity = []
    for r in activity_rows:
        activity.append({
            "id": r["id"],
            "action": r["action"],
            "category": r["category"],
            "description": r["description"],
            "amount": r["amount"],
            "created_at": r["created_at"],
            "time_label": _format_activity_time(r["created_at"]),
        })

    return {
        "budgets": budgets,
        "summary": summary,
        "monthly_trend": trend,
        "distribution": distribution,
        "insights": insights,
        "activity": activity,
        "months": get_budget_months(user_id),
        "filter_info": {
            "month": month,
            "category": category or "",
            "status": status or "",
        },
    }


def _compute_budget_insights(budgets, summary, trend):
    """Generate data-driven alert/insight cards for the Budgets page.

    Returns a list of dicts with keys: icon, accent, tone, title, text.
    """
    insights = []

    # 1. Over-budget alerts.
    over = [b for b in budgets if b["status_key"] == "over"]
    if over:
        names = ", ".join(b["name"] for b in over[:2])
        insights.append({
            "icon": "alert-triangle",
            "accent": "var(--danger)",
            "tone": "over",
            "title": f"{len(over)} budget{'s' if len(over) > 1 else ''} over limit",
            "text": f"{names} {('have' if len(over) > 1 else 'has')} exceeded their monthly limits. Review upcoming expenses to get back on track.",
        })
    else:
        insights.append({
            "icon": "shield-check",
            "accent": "var(--accent)",
            "tone": "track",
            "title": "No budgets over limit",
            "text": "All categories are within their monthly budgets. Great discipline!",
        })

    # 2. At-risk / warning budgets.
    warn = [b for b in budgets if b["status_key"] == "warning"]
    if warn:
        insights.append({
            "icon": "trending-up",
            "accent": "var(--accent-2)",
            "tone": "warning",
            "title": "Budgets approaching limits",
            "text": ", ".join(b["name"] for b in warn[:3]) + " are at risk of exceeding their budgets. Consider trimming spending.",
        })
    else:
        insights.append({
            "icon": "gauge",
            "accent": "var(--success)",
            "tone": "track",
            "title": "All budgets on track",
            "text": "No category is approaching its limit this month.",
        })

    # 3. Daily spend pace insight.
    if summary["total_budget"] > 0:
        insights.append({
            "icon": "calendar-clock",
            "accent": "var(--bar-bills)",
            "tone": "track",
            "title": f"Daily pace of ₹{summary['daily']:,.0f}",
            "text": f"You can spend about ₹{summary['daily']:,.0f} per day for the rest of the month to stay within budget.",
        })

    # 4. Savings headroom insight.
    if summary["remaining"] > 0:
        insights.append({
            "icon": "piggy-bank",
            "accent": "var(--success)",
            "tone": "track",
            "title": f"₹{summary['remaining']:,.0f} of headroom left",
            "text": f"You have ₹{summary['remaining']:,.0f} unspent across all budgets this month. Saving it could add up quickly.",
        })

    return insights


def _format_activity_time(created_at):
    """Format an activity timestamp as a short relative label."""
    if not created_at:
        return "Recently"
    try:
        from datetime import datetime as dt_parse
        dt = dt_parse.strptime(created_at, "%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        return "Recently"
    now = date.today()
    if dt.date() == now:
        return f"Today · {dt.strftime('%I:%M %p')}"
    if dt.date() == now - timedelta(days=1):
        return f"Yesterday · {dt.strftime('%I:%M %p')}"
    return dt.strftime('%b %d · %I:%M %p')


# ================================================================== #
# Categories module — DB layer                                       #
# ================================================================== #

def ensure_default_categories(user_id):
    """Seed the default categories for a user if they have none.

    Also creates rows for any expense category names that do not yet have a
    category row (migration safety for data created before the categories
    table existed). Idempotent — never duplicates existing rows.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Distinct category names actually used by this user's expenses.
    cursor.execute(
        "SELECT DISTINCT category FROM expenses WHERE user_id = ?",
        (user_id,),
    )
    used_names = {row["category"] for row in cursor.fetchall()}

    # Existing category names for this user.
    cursor.execute(
        "SELECT name FROM categories WHERE user_id = ?",
        (user_id,),
    )
    existing = {row["name"] for row in cursor.fetchall()}

    # Insert defaults + any used-but-missing names.
    inserts = []
    for name, desc, icon, color in DEFAULT_CATEGORIES:
        if name not in existing:
            inserts.append((user_id, name, desc, icon, color))
            existing.add(name)
    for name in used_names:
        if name not in existing and name not in CATEGORIES:
            inserts.append((user_id, name, "", "tag", "#6b7280"))
            existing.add(name)

    cursor.executemany(
        "INSERT INTO categories (user_id, name, description, icon, color) "
        "VALUES (?, ?, ?, ?, ?)",
        inserts,
    )
    conn.commit()
    conn.close()


def backfill_categories():
    """Ensure every existing user has default category rows.

    Called once at app startup after init_db(). Iterates all users and calls
    ensure_default_categories() for each.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users")
    user_ids = [row["id"] for row in cursor.fetchall()]
    conn.close()

    for uid in user_ids:
        ensure_default_categories(uid)


def get_user_categories(user_id):
    """Return all category rows for a user (no usage stats), ordered by name.

    Used for dropdowns (expense form, transactions filter, merge selects).
    Returns a list of dicts with id, name, description, icon, color.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, name, description, icon, color, created_at "
        "FROM categories WHERE user_id = ? "
        "ORDER BY name COLLATE NOCASE ASC",
        (user_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def create_category(user_id, name, description, icon, color):
    """Create a new category for a user and return its id.

    Raises sqlite3.IntegrityError if the name already exists for this user
    (case-insensitive uniqueness enforced via a case-insensitive EXISTS check
    before insert). Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO categories (user_id, name, description, icon, color) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, name, description, icon, color),
        )
        cat_id = cursor.lastrowid
        conn.commit()
        return cat_id
    finally:
        conn.close()


def get_category_by_id(category_id, user_id):
    """Return a single category with usage stats, or None if not found/owned.

    The returned dict includes transaction_count, total_spent and
    avg_expense computed from the user's expenses table. Uses parameterized
    queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT c.id, c.user_id, c.name, c.description, c.icon, c.color, c.created_at, "
        "COALESCE(SUM(e.amount), 0.0) AS total_spent, "
        "COUNT(e.id) AS transaction_count, "
        "COALESCE(AVG(e.amount), 0.0) AS avg_expense "
        "FROM categories c "
        "LEFT JOIN expenses e ON e.user_id = c.user_id AND e.category = c.name "
        "WHERE c.id = ? AND c.user_id = ? "
        "GROUP BY c.id",
        (category_id, user_id),
    )
    cat = cursor.fetchone()
    conn.close()
    if cat:
        cat = dict(cat)
        cat["total_spent"] = round(cat["total_spent"], 2)
        cat["avg_expense"] = round(cat["avg_expense"], 2)
        return cat
    return None


def update_category(category_id, user_id, name, description, icon, color):
    """Update a category row WHERE id = ? AND user_id = ?.

    If the name changes, existing expenses using the old name are renamed to
    the new name so historical data stays coherent. Returns True if a row was
    updated. Raises sqlite3.IntegrityError on duplicate names.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT name FROM categories WHERE id = ? AND user_id = ?",
            (category_id, user_id),
        )
        row = cursor.fetchone()
        if row is None:
            return False

        old_name = row["name"]
        cursor.execute(
            "UPDATE categories SET name = ?, description = ?, icon = ?, color = ? "
            "WHERE id = ? AND user_id = ?",
            (name, description, icon, color, category_id, user_id),
        )
        affected = cursor.rowcount

        # Keep expenses in sync with a renamed category.
        if old_name != name:
            cursor.execute(
                "UPDATE expenses SET category = ? WHERE user_id = ? AND category = ?",
                (name, user_id, old_name),
            )
            # Also keep the activity log coherent.
            cursor.execute(
                "UPDATE activities SET category = ? WHERE user_id = ? AND category = ?",
                (name, user_id, old_name),
            )

        conn.commit()
        return affected > 0
    finally:
        conn.close()


def delete_category(category_id, user_id, reassign=True):
    """Delete a category row WHERE id = ? AND user_id = ?.

    When reassign is True (default), any expenses using this category are first
    reassigned to "Other" so no orphaned expense categories remain. Returns
    True if a row was deleted, False if no matching row found. Uses
    parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name FROM categories WHERE id = ? AND user_id = ?",
        (category_id, user_id),
    )
    row = cursor.fetchone()
    if row is None:
        conn.close()
        return False

    name = row["name"]
    if reassign:
        cursor.execute(
            "UPDATE expenses SET category = 'Other' "
            "WHERE user_id = ? AND category = ?",
            (user_id, name),
        )
        cursor.execute(
            "UPDATE activities SET category = 'Other' "
            "WHERE user_id = ? AND category = ?",
            (user_id, name),
        )

    cursor.execute(
        "DELETE FROM categories WHERE id = ? AND user_id = ?",
        (category_id, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def get_categories(user_id, search="", sort="name-asc", page=1, per_page=8):
    """Fetch paginated categories with usage statistics for a user.

    Returns a dict with items, total, pages, page, per_page, has_prev,
    has_next. Each item includes transaction_count, total_spent and
    avg_expense. `search` matches name/description case-insensitively. `sort`
    is validated against CATEGORY_SORT_OPTIONS. Uses parameterized queries —
    safe from SQL injection.
    """
    sort_sql = CATEGORY_SORT_OPTIONS.get(sort, CATEGORY_SORT_OPTIONS["name-asc"])

    clauses = ["c.user_id = ?"]
    params = [user_id]
    if search:
        clauses.append("(c.name LIKE ? OR c.description LIKE ?)")
        like = f"%{search}%"
        params.append(like)
        params.append(like)
    where = "WHERE " + " AND ".join(clauses)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(DISTINCT c.id) AS total "
        "FROM categories c "
        "LEFT JOIN expenses e ON e.user_id = c.user_id AND e.category = c.name "
        f"{where}",
        tuple(params),
    )
    total = cursor.fetchone()["total"]

    if per_page is None or per_page <= 0:
        per_page = total if total > 0 else 1
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(int(page), pages))

    cursor.execute(
        "SELECT c.id, c.user_id, c.name, c.description, c.icon, c.color, c.created_at, "
        "COALESCE(SUM(e.amount), 0.0) AS total_spent, "
        "COUNT(e.id) AS transaction_count, "
        "COALESCE(AVG(e.amount), 0.0) AS avg_expense "
        "FROM categories c "
        "LEFT JOIN expenses e ON e.user_id = c.user_id AND e.category = c.name "
        f"{where} "
        "GROUP BY c.id "
        f"ORDER BY {sort_sql} "
        "LIMIT ? OFFSET ?",
        tuple(params) + (per_page, (page - 1) * per_page),
    )
    items = []
    for row in cursor.fetchall():
        item = dict(row)
        item["total_spent"] = round(item["total_spent"], 2)
        item["avg_expense"] = round(item["avg_expense"], 2)
        items.append(item)
    conn.close()

    return {
        "items": items,
        "total": total,
        "pages": pages,
        "page": page,
        "per_page": per_page,
        "has_prev": page > 1,
        "has_next": page < pages,
    }


def get_category_stats(user_id):
    """Compute the aggregate statistics for the Categories dashboard.

    Returns a dict with:
      - total_categories: int
      - most_used_category: str or None (by transaction count)
      - highest_spending_category: str or None (by total spent)
      - unused_categories: int (categories with zero transactions)
      - total_spent: float (sum of all expenses)
      - distribution: list of {name, color, total, count, pct} ordered by
        total descending (only categories with expenses)
      - conic_gradient: str — CSS conic-gradient() value built from the
        distribution colors for the donut chart
      - ranking: list of {id, name, icon, color, total_spent, pct} ordered by
        total spent descending (all categories, capped at 8)
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()

    # All categories with usage stats.
    cursor.execute(
        "SELECT c.id, c.name, c.icon, c.color, "
        "COALESCE(SUM(e.amount), 0.0) AS total_spent, "
        "COUNT(e.id) AS transaction_count "
        "FROM categories c "
        "LEFT JOIN expenses e ON e.user_id = c.user_id AND e.category = c.name "
        "WHERE c.user_id = ? "
        "GROUP BY c.id "
        "ORDER BY total_spent DESC, c.name COLLATE NOCASE ASC",
        (user_id,),
    )
    cats = [dict(r) for r in cursor.fetchall()]

    # Grand total spent (all expenses).
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS total_spent, "
        "COUNT(*) AS expense_count FROM expenses WHERE user_id = ?",
        (user_id,),
    )
    grand = dict(cursor.fetchone())
    conn.close()

    total_categories = len(cats)
    used = [c for c in cats if c["transaction_count"] > 0]
    unused_count = total_categories - len(used)

    most_used = max(cats, key=lambda c: c["transaction_count"]) if cats and cats[0]["transaction_count"] > 0 else None
    if most_used is None:
        # No category has transactions; fall back to None.
        most_used = None
    else:
        most_used = most_used["name"]

    highest = used[0]["name"] if used else None

    grand_total = grand["total_spent"] or 0.0

    distribution = []
    for c in used:
        pct = (c["total_spent"] / grand_total * 100) if grand_total > 0 else 0.0
        distribution.append({
            "name": c["name"],
            "color": c["color"],
            "total": round(c["total_spent"], 2),
            "count": c["transaction_count"],
            "pct": round(pct, 1),
        })

    # Build a CSS conic-gradient string for the donut chart.
    if distribution:
        segments = []
        cumulative = 0.0
        for d in distribution:
            start = cumulative
            end = cumulative + d["pct"]
            cumulative = end
            segments.append(f"{d['color']} {start:.1f}% {end:.1f}%")
        # Ensure the last segment reaches 100%.
        if segments:
            segments[-1] = segments[-1].rsplit(" ", 1)[0] + f" 100%"
        conic_gradient = f"conic-gradient({', '.join(segments)})"
    else:
        conic_gradient = "conic-gradient(var(--border-soft) 0% 100%)"

    ranking = []
    for c in cats[:8]:
        pct = (c["total_spent"] / grand_total * 100) if grand_total > 0 else 0.0
        ranking.append({
            "id": c["id"],
            "name": c["name"],
            "icon": c["icon"],
            "color": c["color"],
            "total_spent": round(c["total_spent"], 2),
            "transaction_count": c["transaction_count"],
            "pct": round(pct, 1),
        })

    return {
        "total_categories": total_categories,
        "most_used_category": most_used,
        "highest_spending_category": highest,
        "unused_categories": unused_count,
        "total_spent": round(grand_total, 2),
        "distribution": distribution,
        "conic_gradient": conic_gradient,
        "ranking": ranking,
    }


def get_categories_export(user_id):
    """Return flat rows for CSV export: category + usage stats.

    Returns a list of dicts with name, description, icon, color, created_at,
    transaction_count, total_spent, avg_expense. Uses parameterized queries —
    safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT c.name, c.description, c.icon, c.color, c.created_at, "
        "COALESCE(SUM(e.amount), 0.0) AS total_spent, "
        "COUNT(e.id) AS transaction_count, "
        "COALESCE(AVG(e.amount), 0.0) AS avg_expense "
        "FROM categories c "
        "LEFT JOIN expenses e ON e.user_id = c.user_id AND e.category = c.name "
        "WHERE c.user_id = ? "
        "GROUP BY c.id "
        "ORDER BY c.name COLLATE NOCASE ASC",
        (user_id,),
    )
    rows = []
    for row in cursor.fetchall():
        item = dict(row)
        item["total_spent"] = round(item["total_spent"], 2)
        item["avg_expense"] = round(item["avg_expense"], 2)
        rows.append(item)
    conn.close()
    return rows


def merge_categories(user_id, source_id, target_id):
    """Merge source category into target category.

    All expenses (and activity entries) using the source category name are
    reassigned to the target category name, then the source category row is
    deleted. Returns True on success, False if either id is invalid or the
    source == target. Uses parameterized queries — safe from SQL injection.
    """
    if source_id == target_id:
        return False

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, name FROM categories WHERE id IN (?, ?) AND user_id = ?",
        (source_id, target_id, user_id),
    )
    rows = {r["id"]: r["name"] for r in cursor.fetchall()}
    if source_id not in rows or target_id not in rows:
        conn.close()
        return False

    source_name = rows[source_id]
    target_name = rows[target_id]

    cursor.execute(
        "UPDATE expenses SET category = ? WHERE user_id = ? AND category = ?",
        (target_name, user_id, source_name),
    )
    cursor.execute(
        "UPDATE activities SET category = ? WHERE user_id = ? AND category = ?",
        (target_name, user_id, source_name),
    )
    cursor.execute(
        "DELETE FROM categories WHERE id = ? AND user_id = ?",
        (source_id, user_id),
    )
    conn.commit()
    conn.close()
    return True


def delete_expenses_bulk(user_id, ids):
    """Delete multiple expenses owned by the user.

    Returns the number of rows actually deleted. Uses parameterized queries —
    safe from SQL injection.
    """
    if not ids:
        return 0
    conn = get_db()
    cursor = conn.cursor()
    placeholders = ",".join("?" for _ in ids)
    cursor.execute(
        f"DELETE FROM expenses WHERE user_id = ? AND id IN ({placeholders})",
        (user_id, *ids),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected


# ================================================================== #
# Reports module — DB layer                                          #
# ================================================================== #

REPORT_PAYMENT_LABELS = {
    "card": "Card",
    "upi": "UPI",
    "cash": "Cash",
    "bank": "Bank",
    "wallet": "Wallet",
}

REPORT_PAYMENT_COLORS = {
    "card": "var(--cat-bills-text)",
    "upi": "var(--cat-health-text)",
    "cash": "var(--cat-other-text)",
    "bank": "var(--cat-shopping-text)",
    "wallet": "var(--cat-entertainment-text)",
}

REPORT_DEFAULT_MONTHS = 6


def _build_report_filters(date_from, date_to, category, payment):
    """Build WHERE-clause fragments and parameter list for report queries.

    Returns (where_clauses, params) where params does NOT include user_id
    (the caller prepends it). All bound via ``?`` placeholders.
    """
    clauses = ["user_id = ?"]
    params = []

    if date_from:
        clauses.append("date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("date <= ?")
        params.append(date_to)
    if category:
        clauses.append("category = ?")
        params.append(category)
    if payment:
        clauses.append("payment_method = ?")
        params.append(payment)

    return clauses, params


def _compute_period_range(months_back):
    """Return (start_date, end_date) ISO strings for the last N months."""
    today = date.today()
    end = today.isoformat()
    month = today.month - months_back
    year = today.year
    while month < 1:
        month += 12
        year -= 1
    from datetime import date as dt_date
    start = dt_date(year, month, 1).isoformat()
    return start, end


def get_report_data(user_id, date_from=None, date_to=None, category=None,
                    payment=None, months=REPORT_DEFAULT_MONTHS):
    """Compute full report data for a user with optional filtering.

    When date_from/date_to are not provided, defaults to the last ``months``
    months (default 6). Supports optional category and payment method filters.

    Returns a dict with:
      - summary: {total_spending, total_transactions, avg_monthly,
                  highest_month_name, highest_month_amount,
                  largest_expense_amount, largest_expense_desc,
                  largest_expense_category, potential_savings,
                  prev_total_spending, prev_total_transactions}
      - monthly_trend: list of {month, label, amount} for each month
        in the period (chronological)
      - prev_monthly_trend: list of {month, label, amount} for the
        previous period of the same length (for comparison)
      - category_breakdown: list of {name, color, value} ordered by
        value descending
      - payment_breakdown: list of {name, color, value} ordered by
        value descending
      - top_expenses: list of {id, date, description, category,
        payment_method, amount} ordered by amount descending (limit 10)
      - monthly_summary: list of {month_label, transaction_count,
        total, average} ordered chronologically
      - insights: list of {icon, accent, title, text}
      - filter_info: {date_from, date_to, category, payment}
    """
    # Default date range = last N months.
    if not date_from and not date_to:
        date_from, date_to = _compute_period_range(months)

    clauses, params = _build_report_filters(date_from, date_to, category, payment)
    where = " AND ".join(clauses)
    full_params = [user_id] + params

    conn = get_db()
    cursor = conn.cursor()

    # ---- Summary cards ----
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS total_spending, "
        "COUNT(*) AS total_transactions "
        f"FROM expenses WHERE {where}",
        tuple(full_params),
    )
    cur_totals = dict(cursor.fetchone())

    total_spending = round(cur_totals["total_spending"], 2)
    total_transactions = cur_totals["total_transactions"]

    # Average monthly spend.
    cursor.execute(
        "SELECT COUNT(DISTINCT strftime('%Y-%m', date)) AS month_count "
        f"FROM expenses WHERE {where}",
        tuple(full_params),
    )
    month_count = max(cursor.fetchone()["month_count"], 1)
    avg_monthly = round(total_spending / month_count, 2) if month_count else 0.0

    # Highest spending month.
    cursor.execute(
        "SELECT strftime('%Y-%m', date) AS month, "
        "COALESCE(SUM(amount), 0.0) AS total "
        f"FROM expenses WHERE {where} "
        "GROUP BY month ORDER BY total DESC LIMIT 1",
        tuple(full_params),
    )
    highest_row = cursor.fetchone()
    if highest_row and highest_row["total"] > 0:
        ym = highest_row["month"]
        parts = ym.split("-")
        month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                       "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        highest_month_name = f"{month_names[int(parts[1])]} {parts[0]}"
        highest_month_amount = round(highest_row["total"], 2)
    else:
        highest_month_name = "—"
        highest_month_amount = 0.0

    # Largest single expense.
    cursor.execute(
        "SELECT amount, description, category "
        f"FROM expenses WHERE {where} "
        "ORDER BY amount DESC LIMIT 1",
        tuple(full_params),
    )
    largest = cursor.fetchone()
    largest_expense = dict(largest) if largest else None
    largest_expense_amount = round(largest_expense["amount"], 2) if largest_expense else 0.0
    largest_expense_desc = largest_expense["description"] or "—" if largest_expense else "—"
    largest_expense_category = largest_expense["category"] if largest_expense else "—"

    # Potential savings: 11% of total (static heuristic).
    potential_savings = round(total_spending * 0.11, 2)

    # ---- Previous period (for comparison) ----
    prev_from, prev_to = _compute_prev_period(date_from, date_to, months)
    prev_clauses, prev_params = _build_report_filters(prev_from, prev_to, category, payment)
    prev_where = " AND ".join(prev_clauses)
    prev_full_params = [user_id] + prev_params

    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS total, COUNT(*) AS count "
        f"FROM expenses WHERE {prev_where}",
        tuple(prev_full_params),
    )
    prev_totals = dict(cursor.fetchone())
    prev_total_spending = round(prev_totals["total"], 2)
    prev_total_transactions = prev_totals["count"]

    # ---- Monthly trend (current period, chronological) ----
    cursor.execute(
        "SELECT strftime('%Y-%m', date) AS month, "
        "COALESCE(SUM(amount), 0.0) AS amount "
        f"FROM expenses WHERE {where} "
        "GROUP BY month ORDER BY month ASC",
        tuple(full_params),
    )
    monthly_trend = []
    month_names = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    for row in cursor.fetchall():
        parts = row["month"].split("-")
        label = f"{month_names[int(parts[1])]} {parts[0]}"
        monthly_trend.append({
            "month": row["month"],
            "label": label,
            "amount": round(row["amount"], 2),
        })

    # ---- Previous period monthly trend ----
    cursor.execute(
        "SELECT strftime('%Y-%m', date) AS month, "
        "COALESCE(SUM(amount), 0.0) AS amount "
        f"FROM expenses WHERE {prev_where} "
        "GROUP BY month ORDER BY month ASC",
        tuple(prev_full_params),
    )
    prev_monthly_trend = []
    for row in cursor.fetchall():
        parts = row["month"].split("-")
        label = f"{month_names[int(parts[1])]} {parts[0]}"
        prev_monthly_trend.append({
            "month": row["month"],
            "label": label,
            "amount": round(row["amount"], 2),
        })

    # ---- Category breakdown (with colors from categories table) ----
    cursor.execute(
        "SELECT e.category AS name, "
        "COALESCE((SELECT color FROM categories WHERE user_id = e.user_id AND name = e.category), '#6b7280') AS color, "
        "COALESCE(SUM(e.amount), 0.0) AS value "
        f"FROM expenses e WHERE {where} "
        "GROUP BY e.category ORDER BY value DESC",
        tuple(full_params),
    )
    category_breakdown = []
    for row in cursor.fetchall():
        category_breakdown.append({
            "name": row["name"],
            "color": row["color"],
            "value": round(row["value"], 2),
        })

    # ---- Payment method breakdown ----
    cursor.execute(
        "SELECT payment_method, COALESCE(SUM(amount), 0.0) AS value "
        f"FROM expenses WHERE {where} "
        "GROUP BY payment_method ORDER BY value DESC",
        tuple(full_params),
    )
    payment_breakdown = []
    for row in cursor.fetchall():
        pm = row["payment_method"]
        payment_breakdown.append({
            "name": REPORT_PAYMENT_LABELS.get(pm, pm.capitalize()),
            "color": REPORT_PAYMENT_COLORS.get(pm, "var(--ink-muted)"),
            "value": round(row["value"], 2),
        })

    # ---- Top expenses (by amount, limit 10) ----
    cursor.execute(
        "SELECT id, date, description, category, payment_method, amount "
        f"FROM expenses WHERE {where} "
        "ORDER BY amount DESC LIMIT 10",
        tuple(full_params),
    )
    top_expenses = []
    for row in cursor.fetchall():
        top_expenses.append({
            "id": row["id"],
            "date": row["date"],
            "description": row["description"] or "",
            "category": row["category"],
            "payment_method": row["payment_method"],
            "amount": round(row["amount"], 2),
        })

    # ---- Monthly summary table (chronological) ----
    cursor.execute(
        "SELECT strftime('%Y-%m', date) AS month, "
        "COUNT(*) AS transaction_count, "
        "COALESCE(SUM(amount), 0.0) AS total, "
        "COALESCE(AVG(amount), 0.0) AS average "
        f"FROM expenses WHERE {where} "
        "GROUP BY month ORDER BY month ASC",
        tuple(full_params),
    )
    monthly_summary = []
    for row in cursor.fetchall():
        parts = row["month"].split("-")
        label = f"{month_names[int(parts[1])]} {parts[0]}"
        monthly_summary.append({
            "month_label": label,
            "transaction_count": row["transaction_count"],
            "total": round(row["total"], 2),
            "average": round(row["average"], 2),
        })

    conn.close()

    # ---- Insights (data-driven) ----
    insights = _compute_insights(
        total_spending, prev_total_spending,
        total_transactions, prev_total_transactions,
        avg_monthly, highest_month_name, highest_month_amount,
        largest_expense_amount, largest_expense_desc,
        largest_expense_category, potential_savings,
        category_breakdown, monthly_trend,
    )

    # Whether any expenses matched the current filters (drives the empty state).
    has_data = total_transactions > 0

    return {
        "summary": {
            "total_spending": total_spending,
            "total_transactions": total_transactions,
            "avg_monthly": avg_monthly,
            "highest_month_name": highest_month_name,
            "highest_month_amount": highest_month_amount,
            "largest_expense_amount": largest_expense_amount,
            "largest_expense_desc": largest_expense_desc,
            "largest_expense_category": largest_expense_category,
            "potential_savings": potential_savings,
            "prev_total_spending": prev_total_spending,
            "prev_total_transactions": prev_total_transactions,
        },
        "monthly_trend": monthly_trend,
        "prev_monthly_trend": prev_monthly_trend,
        "category_breakdown": category_breakdown,
        "payment_breakdown": payment_breakdown,
        "top_expenses": top_expenses,
        "monthly_summary": monthly_summary,
        "insights": insights,
        "has_data": has_data,
        "filter_info": {
            "date_from": date_from,
            "date_to": date_to,
            "category": category or "",
            "payment": payment or "",
        },
    }


def _compute_prev_period(date_from, date_to, months):
    """Return (prev_from, prev_to) ISO strings shifting the period back by ``months``."""
    if not date_from and not date_to:
        # Default period: shift back by months.
        p_from, p_to = _compute_period_range(months * 2)
        # p_from is (months*2) back, p_to is months back.
        # We need the period [months_back .. 0) from p_to's perspective.
        # Simpler: shift the default range back.
        today = date.today()
        end_month = today.month - months
        end_year = today.year
        while end_month < 1:
            end_month += 12
            end_year -= 1
        from datetime import date as dt_date
        import calendar
        last_day = calendar.monthrange(end_year, end_month)[1]
        prev_to = dt_date(end_year, end_month, last_day).isoformat()

        start_month = end_month - months + 1
        start_year = end_year
        while start_month < 1:
            start_month += 12
            start_year -= 1
        prev_from = dt_date(start_year, start_month, 1).isoformat()
        return prev_from, prev_to

    # Custom dates: shift both back by the same span.
    try:
        from datetime import datetime as dt_parse, timedelta
        d_from = dt_parse.strptime(date_from, "%Y-%m-%d").date()
        d_to = dt_parse.strptime(date_to, "%Y-%m-%d").date()
        span = (d_to - d_from).days + 1
        prev_to = d_from - timedelta(days=1)
        prev_from = prev_to - timedelta(days=span - 1)
        return prev_from.isoformat(), prev_to.isoformat()
    except (ValueError, TypeError):
        # Fallback: shift both by months.
        today = date.today()
        end_month = today.month - months
        end_year = today.year
        while end_month < 1:
            end_month += 12
            end_year -= 1
        import calendar
        last_day = calendar.monthrange(end_year, end_month)[1]
        prev_to = date(end_year, end_month, last_day).isoformat()
        start_month = end_month - months + 1
        start_year = end_year
        while start_month < 1:
            start_month += 12
            start_year -= 1
        prev_from = date(start_year, start_month, 1).isoformat()
        return prev_from, prev_to


def _compute_insights(total_spending, prev_total_spending,
                      total_transactions, prev_total_transactions,
                      avg_monthly, highest_month_name, highest_month_amount,
                      largest_expense_amount, largest_expense_desc,
                      largest_expense_category, potential_savings,
                      category_breakdown, monthly_trend):
    """Generate data-driven insight cards for the Reports page.

    Returns a list of dicts with keys: icon, accent (CSS var), title, text.
    """
    insights = []

    # 1. Spending trend insight.
    if prev_total_spending > 0 and total_spending > 0:
        pct_change = round((total_spending - prev_total_spending) / prev_total_spending * 100, 1)
        if pct_change < 0:
            insights.append({
                "icon": "trending-down",
                "accent": "var(--accent)",
                "title": f"Spending decreased by {abs(pct_change)}%",
                "text": f"Your spending dropped from ₹{prev_total_spending:,.2f} to ₹{total_spending:,.2f} compared to the previous period. Keep it up!",
            })
        elif pct_change > 0:
            insights.append({
                "icon": "trending-up",
                "accent": "var(--danger)",
                "title": f"Spending increased by {pct_change}%",
                "text": f"Your spending rose from ₹{prev_total_spending:,.2f} to ₹{total_spending:,.2f}. Review your expenses to identify areas to cut back.",
            })
        else:
            insights.append({
                "icon": "minus",
                "accent": "var(--ink-muted)",
                "title": "Spending held steady",
                "text": f"Your spending of ₹{total_spending:,.2f} matches the previous period. Consistency is key!",
            })
    else:
        insights.append({
            "icon": "bar-chart-3",
            "accent": "var(--accent)",
            "title": "Start tracking to see trends",
            "text": "Add expenses to unlock spending insights and trends over time.",
        })

    # 2. Top category insight.
    if category_breakdown:
        top_cat = category_breakdown[0]
        top_pct = round(top_cat["value"] / total_spending * 100, 1) if total_spending > 0 else 0
        insights.append({
            "icon": "shopping-bag",
            "accent": "var(--accent-2)",
            "title": f"{top_cat['name']} is your top category",
            "text": f"{top_cat['name']} accounts for {top_pct}% of total spend at ₹{top_cat['value']:,.2f}. Trimming 10% here could save ~₹{round(top_cat['value'] * 0.1, 2):,.2f}.",
        })
    else:
        insights.append({
            "icon": "shopping-bag",
            "accent": "var(--accent-2)",
            "title": "No category data yet",
            "text": "Add expenses across different categories to see your spending breakdown here.",
        })

    # 3. Savings opportunity insight.
    if potential_savings > 0:
        pct_of_total = round(potential_savings / total_spending * 100, 1) if total_spending > 0 else 0
        insights.append({
            "icon": "piggy-bank",
            "accent": "var(--success)",
            "title": f"Potential savings of ₹{potential_savings:,.2f}",
            "text": f"By optimising recurring expenses and setting category budgets, you could save ~{pct_of_total}% of your total spend (≈₹{round(potential_savings / avg_monthly if avg_monthly > 0 else 1, 0):,.0f}/month).",
        })
    else:
        insights.append({
            "icon": "piggy-bank",
            "accent": "var(--success)",
            "title": "Track to unlock savings insights",
            "text": "Once you have enough expense data, we'll show personalised saving opportunities.",
        })

    # 4. Peak month insight.
    if highest_month_name != "—" and highest_month_amount > 0:
        insights.append({
            "icon": "calendar-check",
            "accent": "var(--bar-bills)",
            "title": f"{highest_month_name} was your peak month",
            "text": f"Your highest spending month was {highest_month_name} at ₹{highest_month_amount:,.2f}. Large one-off purchases can skew your monthly averages.",
        })
    else:
        insights.append({
            "icon": "calendar-check",
            "accent": "var(--bar-bills)",
            "title": "Track monthly to find patterns",
            "text": "Add expenses regularly so we can identify your peak spending months.",
        })

    return insights


def add_activity(user_id, action, expense_id=None, category=None,
                 description=None, amount=None):
    """Record an activity entry for the Recent Activity feed.

    `action` must be one of ACTIVITY_ACTIONS ("added", "edited", "deleted").
    Invalid actions are rejected with a ValueError. Uses parameterized queries —
    safe from SQL injection.
    """
    if action not in ACTIVITY_ACTIONS:
        raise ValueError(f"Invalid activity action: {action!r}")
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO activities (user_id, action, expense_id, category, description, amount) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, action, expense_id, category, description, amount),
    )
    activity_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return activity_id


def get_recent_activity(user_id, limit=8, category=None):
    """Return the most recent activity entries for a user.

    Ordered by created_at descending (most recent first), limited to `limit`
    rows. When `category` is provided, only activity rows for that category
    are returned (used to keep the panel coherent with the Transactions page's
    active category filter). Returns a list of dicts. Uses parameterized
    queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    if category:
        cursor.execute(
            "SELECT id, user_id, action, expense_id, category, description, amount, created_at "
            "FROM activities WHERE user_id = ? AND category = ? "
            "ORDER BY created_at DESC, id DESC LIMIT ?",
            (user_id, category, limit),
        )
    else:
        cursor.execute(
            "SELECT id, user_id, action, expense_id, category, description, amount, created_at "
            "FROM activities WHERE user_id = ? "
            "ORDER BY created_at DESC, id DESC LIMIT ?",
            (user_id, limit),
        )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows
