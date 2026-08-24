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

# ------------------------------------------------------------------ #
# Goals module constants                                             #
# ------------------------------------------------------------------ #

# Categories supported by the Goals module. Each entry is:
# (name, lucide icon name, hex color)
GOAL_CATEGORIES = [
    ("Emergency Fund", "shield", "#059669"),
    ("Travel", "plane", "#d97706"),
    ("Home", "home", "#4f46e5"),
    ("Education", "graduation-cap", "#7c3aed"),
    ("Health", "heart-pulse", "#dc2626"),
    ("Vehicle", "car", "#6b7280"),
    ("Gadgets", "smartphone", "#db2777"),
    ("Celebration", "party-popper", "#7c3aed"),
    ("Investment", "trending-up", "#059669"),
    ("Other", "target", "#6b7280"),
]

# Whitelist of allowed status keys for the Goals page.
GOAL_STATUSES = ("on-track", "at-risk", "completed", "paused")

# Whitelist of allowed sort keys for server-side goal sorting.
# "progress" is computed as saved_amount / target_amount in SQL.
GOAL_SORT_OPTIONS = {
    "progress-desc": "(saved_amount * 1.0 / target_amount) DESC, id ASC",
    "progress-asc": "(saved_amount * 1.0 / target_amount) ASC, id ASC",
    "deadline-asc": "deadline ASC, id ASC",
    "deadline-desc": "deadline DESC, id ASC",
    "target-desc": "target_amount DESC, id ASC",
    "target-asc": "target_amount ASC, id ASC",
    "name-asc": "name COLLATE NOCASE ASC, id ASC",
}

# Map category name -> (icon, color) for the frontend.
GOAL_CATEGORY_ICONS = {name: icon for name, icon, _ in GOAL_CATEGORIES}
GOAL_CATEGORY_COLORS = {name: color for name, _, color in GOAL_CATEGORIES}
GOAL_CATEGORY_NAMES = [name for name, _, _ in GOAL_CATEGORIES]


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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            target_amount REAL NOT NULL,
            saved_amount REAL NOT NULL DEFAULT 0,
            deadline TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'on-track',
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            currency TEXT NOT NULL DEFAULT 'INR',
            date_format TEXT NOT NULL DEFAULT 'DD-MM-YYYY',
            language TEXT NOT NULL DEFAULT 'en',
            week_start TEXT NOT NULL DEFAULT 'monday',
            budget_alert_threshold INTEGER NOT NULL DEFAULT 80,
            default_payment_method TEXT NOT NULL DEFAULT 'upi',
            theme TEXT NOT NULL DEFAULT 'dark',
            accent_color TEXT NOT NULL DEFAULT 'green',
            interface_density TEXT NOT NULL DEFAULT 'comfortable',
            two_factor_enabled INTEGER NOT NULL DEFAULT 0,
            login_alerts_enabled INTEGER NOT NULL DEFAULT 1,
            expense_reminders_enabled INTEGER NOT NULL DEFAULT 1,
            budget_alerts_enabled INTEGER NOT NULL DEFAULT 1,
            goal_milestones_enabled INTEGER NOT NULL DEFAULT 1,
            weekly_summary_enabled INTEGER NOT NULL DEFAULT 1,
            product_updates_enabled INTEGER NOT NULL DEFAULT 0,
            personalised_insights_enabled INTEGER NOT NULL DEFAULT 1,
            anonymous_usage_enabled INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            UNIQUE (user_id)
        )
    """)

    # Active sessions table — tracks authenticated devices so the Settings
    # page can display and revoke real sessions. Safe to create repeatedly.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL REFERENCES users(id),
            token TEXT NOT NULL,
            user_agent TEXT DEFAULT '',
            ip_address TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            last_seen TEXT DEFAULT (datetime('now'))
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

    # Add phone and bio columns for the Settings profile fields — safe on repeated runs
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # Column already exists

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN bio TEXT DEFAULT ''")
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

    Returns a dictionary of user fields (id, name, email, phone, bio,
    created_at, member_since) if found, or None if no match.
    member_since is formatted as 'Month YYYY' (e.g. 'January 2026').
    Uses a parameterized query — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, name, email, COALESCE(phone, '') AS phone, "
        "COALESCE(bio, '') AS bio, created_at FROM users WHERE id = ?",
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


def update_user_profile(user_id, name, email, phone=None, bio=None):
    """Update a user's name and email, and optionally phone and bio.

    Phone and bio are optional — when provided (including an empty string,
    which clears the field), they are persisted to the users table. When
    omitted the existing values are left untouched. Returns True if the
    update was successful. Raises sqlite3.IntegrityError if the email is
    already taken by another user.

    The write is performed in a single atomic UPDATE inside try/finally
    so the connection is always closed — even when IntegrityError is raised
    by the caller (e.g. a duplicate email). This prevents an open uncommitted
    transaction from holding the SQLite write lock.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    try:
        cursor = conn.cursor()

        if phone is None and bio is None:
            # Backwards-compatible: profile edit only changes name/email.
            cursor.execute(
                "UPDATE users SET name = ?, email = ? WHERE id = ?",
                (name, email, user_id),
            )
        else:
            cursor.execute(
                "UPDATE users SET name = ?, email = ?, phone = ?, bio = ? "
                "WHERE id = ?",
                (
                    name,
                    email,
                    phone if phone is not None else "",
                    bio if bio is not None else "",
                    user_id,
                ),
            )

        affected = cursor.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


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


def delete_expenses_bulk(user_id, ids):
    """Delete multiple expense rows, scoped to the owning user.

    Only rows that belong to `user_id` are deleted — foreign ids are
    silently ignored. Returns the number of rows deleted. Uses parameterized
    queries — safe from SQL injection.
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
# Categories module — DB layer                                       #
# ================================================================== #

def ensure_default_categories(user_id):
    """Insert the default category rows for a user if they don't exist.

    Uses INSERT OR IGNORE so existing rows are never duplicated. Returns
    the number of rows inserted. Uses parameterized queries — safe from
    SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    inserted = 0
    for name, desc, icon, color in DEFAULT_CATEGORIES:
        cursor.execute(
            "INSERT OR IGNORE INTO categories (user_id, name, description, icon, color) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, name, desc, icon, color),
        )
        inserted += cursor.rowcount
    conn.commit()
    conn.close()
    return inserted


def backfill_categories():
    """Ensure every existing user has default category rows.

    Iterates over all users and calls ensure_default_categories for each.
    Safe to call repeatedly. Returns the total number of rows inserted.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users")
    user_ids = [row["id"] for row in cursor.fetchall()]
    conn.close()

    total = 0
    for uid in user_ids:
        total += ensure_default_categories(uid)
    return total


def get_user_categories(user_id):
    """Return all categories for a user, ordered by name.

    Returns a list of dicts with id, name, description, icon, color,
    created_at, transaction_count, total_spent, avg_expense. Empty list
    if none. Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT c.id, c.name, c.description, c.icon, c.color, c.created_at, "
        "COUNT(e.id) AS transaction_count, "
        "COALESCE(SUM(e.amount), 0.0) AS total_spent, "
        "COALESCE(AVG(e.amount), 0.0) AS avg_expense "
        "FROM categories c "
        "LEFT JOIN expenses e ON e.category = c.name AND e.user_id = c.user_id "
        "WHERE c.user_id = ? "
        "GROUP BY c.id "
        "ORDER BY c.name COLLATE NOCASE ASC",
        (user_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def create_category(user_id, name, description, icon, color):
    """Create a new category for a user and return its id.

    Raises sqlite3.IntegrityError if a category with the same name already
    exists for this user. Uses parameterized queries — safe from SQL
    injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO categories (user_id, name, description, icon, color) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, name, description, icon, color),
    )
    category_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return category_id


def get_category_by_id(category_id, user_id):
    """Return a single category scoped to the user, or None if not found/owned.

    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT c.id, c.name, c.description, c.icon, c.color, c.created_at, "
        "COUNT(e.id) AS transaction_count, "
        "COALESCE(SUM(e.amount), 0.0) AS total_spent, "
        "COALESCE(AVG(e.amount), 0.0) AS avg_expense "
        "FROM categories c "
        "LEFT JOIN expenses e ON e.category = c.name AND e.user_id = c.user_id "
        "WHERE c.id = ? AND c.user_id = ? "
        "GROUP BY c.id",
        (category_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def update_category(category_id, user_id, name, description, icon, color):
    """Update a category row WHERE id = ? AND user_id = ?.

    Returns True if a row was updated, False if no matching row found.
    Raises sqlite3.IntegrityError if the new name collides with another
    category for this user. Uses parameterized queries — safe from SQL
    injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE categories SET name = ?, description = ?, icon = ?, color = ? "
        "WHERE id = ? AND user_id = ?",
        (name, description, icon, color, category_id, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def delete_category(category_id, user_id, reassign=True):
    """Delete a category row WHERE id = ? AND user_id = ?.

    When `reassign` is True, any expenses using this category are
    reassigned to 'Other' before the category is deleted. Returns True if
    a row was deleted, False if no matching row found. Uses parameterized
    queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Fetch the category name first (scoped to the user).
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
            "UPDATE expenses SET category = 'Other' WHERE user_id = ? AND category = ?",
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
    """Fetch paginated, server-side filtered categories for a user.

    Returns a dict with items, total, pages, page, per_page, has_prev,
    has_next. `sort` is validated against CATEGORY_SORT_OPTIONS. Uses
    parameterized queries — safe from SQL injection.
    """
    sort_sql = CATEGORY_SORT_OPTIONS.get(sort, CATEGORY_SORT_OPTIONS["name-asc"])

    where = "WHERE c.user_id = ?"
    params = [user_id]
    if search:
        where += " AND (c.name LIKE ? OR c.description LIKE ?)"
        like = f"%{search}%"
        params.append(like)
        params.append(like)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        f"SELECT COUNT(*) AS total FROM categories c {where}",
        tuple(params),
    )
    total = cursor.fetchone()["total"]

    if per_page is None or per_page <= 0:
        per_page = total if total > 0 else 1
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(int(page), pages))

    cursor.execute(
        "SELECT c.id, c.name, c.description, c.icon, c.color, c.created_at, "
        "COUNT(e.id) AS transaction_count, "
        "COALESCE(SUM(e.amount), 0.0) AS total_spent, "
        "COALESCE(AVG(e.amount), 0.0) AS avg_expense "
        f"FROM categories c {where} "
        "LEFT JOIN expenses e ON e.category = c.name AND e.user_id = c.user_id "
        "GROUP BY c.id "
        f"ORDER BY {sort_sql} LIMIT ? OFFSET ?",
        tuple(params) + (per_page, (page - 1) * per_page),
    )
    items = [dict(row) for row in cursor.fetchall()]
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
    """Return summary statistics for the Categories page.

    Returns a dict with total_categories, total_transactions, total_spent,
    top_category, avg_per_category. Uses parameterized queries — safe from
    SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) AS total_categories FROM categories WHERE user_id = ?",
        (user_id,),
    )
    total_categories = cursor.fetchone()["total_categories"]

    cursor.execute(
        "SELECT COUNT(*) AS total_transactions, COALESCE(SUM(amount), 0.0) AS total_spent "
        "FROM expenses WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()
    total_transactions = row["total_transactions"]
    total_spent = row["total_spent"]

    cursor.execute(
        "SELECT category, COALESCE(SUM(amount), 0.0) AS total "
        "FROM expenses WHERE user_id = ? "
        "GROUP BY category ORDER BY total DESC LIMIT 1",
        (user_id,),
    )
    top = cursor.fetchone()
    top_category = top["category"] if top else "—"

    conn.close()

    return {
        "total_categories": total_categories,
        "total_transactions": total_transactions,
        "total_spent": round(total_spent, 2),
        "top_category": top_category,
        "avg_per_category": round(total_spent / total_categories, 2) if total_categories > 0 else 0.0,
    }


def get_categories_export(user_id):
    """Return all categories with usage stats for CSV export.

    Returns a list of dicts with name, description, icon, color, created_at,
    transaction_count, total_spent, avg_expense. Uses parameterized queries.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT c.name, c.description, c.icon, c.color, c.created_at, "
        "COUNT(e.id) AS transaction_count, "
        "COALESCE(SUM(e.amount), 0.0) AS total_spent, "
        "COALESCE(AVG(e.amount), 0.0) AS avg_expense "
        "FROM categories c "
        "LEFT JOIN expenses e ON e.category = c.name AND e.user_id = c.user_id "
        "WHERE c.user_id = ? "
        "GROUP BY c.id "
        "ORDER BY c.name COLLATE NOCASE ASC",
        (user_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def merge_categories(user_id, source_id, target_id):
    """Merge a source category into a target category.

    Reassigns all expenses from the source category to the target category,
    then deletes the source category. Both must belong to the user. Returns
    True on success, False if either category is missing or not owned.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Fetch both category names (scoped to the user).
    cursor.execute(
        "SELECT id, name FROM categories WHERE id IN (?, ?) AND user_id = ?",
        (source_id, target_id, user_id),
    )
    rows = cursor.fetchall()
    if len(rows) != 2:
        conn.close()
        return False

    names = {row["id"]: row["name"] for row in rows}
    source_name = names[source_id]
    target_name = names[target_id]

    # Reassign expenses.
    cursor.execute(
        "UPDATE expenses SET category = ? WHERE user_id = ? AND category = ?",
        (target_name, user_id, source_name),
    )

    # Delete the source category.
    cursor.execute(
        "DELETE FROM categories WHERE id = ? AND user_id = ?",
        (source_id, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


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


def _effective_budget_limits(user_id):
    """Return a dict of category -> effective limit for a user.

    User-defined budget rows override the static defaults. Uses
    parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT category, limit_amount FROM budgets WHERE user_id = ?",
        (user_id,),
    )
    user_budgets = {row["category"]: row["limit_amount"] for row in cursor.fetchall()}
    conn.close()

    limits = dict(BUDGET_LIMITS)
    limits.update(user_budgets)
    return limits


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
        "limit_amount = excluded.limit_amount, period = 'monthly', is_default = 0",
        (user_id, category, limit),
    )
    budget_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return budget_id


def update_budget_limit(user_id, category, limit):
    """Update a per-user budget limit for a category (ownership enforced).

    Uses an upsert so updating a limit for a category that has no row yet
    creates it. Returns True if a row was updated/created, False otherwise.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO budgets (user_id, category, limit_amount, period, is_default) "
        "VALUES (?, ?, ?, 'monthly', 0) "
        "ON CONFLICT(user_id, category) DO UPDATE SET "
        "limit_amount = excluded.limit_amount, period = 'monthly', is_default = 0",
        (user_id, category, limit),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def delete_budget(user_id, category):
    """Delete a per-user budget row (ownership enforced).

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
    """Delete all per-user budget rows so defaults are used again.

    Returns the number of rows removed. Uses parameterized queries.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM budgets WHERE user_id = ?", (user_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected


def get_budget_months(user_id):
    """Return the distinct months (YYYY-MM) that have expenses for a user.

    Used to populate the Budgets page month filter. Returns a list of
    strings ordered newest first. Uses parameterized queries.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT DISTINCT strftime('%Y-%m', date) AS month "
        "FROM expenses WHERE user_id = ? "
        "ORDER BY month DESC",
        (user_id,),
    )
    months = [row["month"] for row in cursor.fetchall()]
    conn.close()
    return months


def get_budget_data(user_id, month=None, category=None, status=None):
    """Return the full Budgets dashboard dataset for a user.

    Computes per-category budget limits (user-defined rows falling back to
    static defaults), actual spending, remaining, usage %, and status.
    Supports optional month, category, and status filters. Returns a dict
    with summary cards, budget rows, trend, distribution, alerts, and
    recent activity. Uses parameterized queries — safe from SQL injection.
    """
    # Base WHERE for expenses (user + optional month/category filters).
    where = "WHERE user_id = ?"
    params = [user_id]
    if month:
        where += " AND strftime('%Y-%m', date) = ?"
        params.append(month)
    if category:
        where += " AND category = ?"
        params.append(category)

    conn = get_db()
    cursor = conn.cursor()

    # ---- Total spent (filtered) ----
    cursor.execute(
        f"SELECT COALESCE(SUM(amount), 0.0) AS total FROM expenses {where}",
        tuple(params),
    )
    total_spent = cursor.fetchone()["total"]

    # ---- Per-category actual spending (filtered) ----
    cursor.execute(
        f"SELECT category, COALESCE(SUM(amount), 0.0) AS spent, COUNT(*) AS count "
        f"FROM expenses {where} GROUP BY category",
        tuple(params),
    )
    actual = {row["category"]: {"spent": row["spent"], "count": row["count"]} for row in cursor.fetchall()}

    # ---- User-defined budget rows ----
    cursor.execute(
        "SELECT category, limit_amount FROM budgets WHERE user_id = ?",
        (user_id,),
    )
    user_budgets = {row["category"]: row["limit_amount"] for row in cursor.fetchall()}

    # ---- Recent activity (for the panel) ----
    cursor.execute(
        "SELECT id, action, category, description, amount, created_at "
        "FROM activities WHERE user_id = ? "
        "ORDER BY created_at DESC, id DESC LIMIT 8",
        (user_id,),
    )
    recent_activity = [dict(row) for row in cursor.fetchall()]

    conn.close()

    # ---- Build the budget rows ----
    all_categories = set(BUDGET_LIMITS.keys()) | set(user_budgets.keys()) | set(actual.keys())
    budgets = []
    for cat in sorted(all_categories):
        limit = user_budgets.get(cat, _budget_limit(cat))
        spent = actual.get(cat, {}).get("spent", 0.0)
        count = actual.get(cat, {}).get("count", 0)
        remaining = max(0.0, limit - spent)
        pct = (spent / limit * 100) if limit > 0 else 0.0
        status_key, status_label = _budget_status(pct)
        budgets.append({
            "name": cat,
            "limit": round(limit, 2),
            "spent": round(spent, 2),
            "remaining": round(remaining, 2),
            "pct": round(pct, 1),
            "count": count,
            "status": status_key,
            "status_label": status_label,
            "is_default": cat not in user_budgets,
            "icon": BUDGET_CATEGORY_ICONS.get(cat, "tag"),
            "color": BUDGET_CATEGORY_COLORS.get(cat, "var(--ink-muted)"),
        })

    # Apply status filter if provided.
    if status:
        budgets = [b for b in budgets if b["status"] == status]

    # ---- Summary cards ----
    total_limit = sum(b["limit"] for b in budgets)
    total_remaining = sum(b["remaining"] for b in budgets)
    over_count = sum(1 for b in budgets if b["status"] == "over")
    warning_count = sum(1 for b in budgets if b["status"] == "warning")
    on_track_count = sum(1 for b in budgets if b["status"] == "on-track")

    # ---- Trend (last N months) ----
    trend = []
    today = date.today()
    for i in range(BUDGET_TREND_MONTHS - 1, -1, -1):
        m = today.month - i
        y = today.year
        while m < 1:
            m += 12
            y -= 1
        label = f"{MONTH_LABELS[m]} {y}"
        key = f"{y:04d}-{m:02d}"
        trend.append({"month": label, "spent": 0.0, "limit": 0.0})

    # Fill trend with actual data.
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT strftime('%Y-%m', date) AS month, COALESCE(SUM(amount), 0.0) AS spent "
        "FROM expenses WHERE user_id = ? "
        "GROUP BY month ORDER BY month ASC",
        (user_id,),
    )
    trend_map = {row["month"]: row["spent"] for row in cursor.fetchall()}
    conn.close()
    for t in trend:
        # Reconstruct YYYY-MM from the label's month name + year.
        parts = t["month"].split()
        month_num = MONTH_LABELS.index(parts[0])
        year_num = int(parts[1])
        key = f"{year_num:04d}-{month_num:02d}"
        t["spent"] = round(trend_map.get(key, 0.0), 2)
        t["limit"] = round(sum(b["limit"] for b in budgets if b["name"] in BUDGET_LIMITS or b["name"] in user_budgets) / max(len(budgets), 1), 2)

    # ---- Distribution (donut) ----
    distribution = [
        {"name": b["name"], "value": round(b["spent"], 2), "color": b["color"]}
        for b in budgets if b["spent"] > 0
    ]

    # ---- Alerts / insights ----
    alerts = []
    for b in budgets:
        if b["status"] == "over":
            alerts.append({
                "type": "danger",
                "icon": "alert-triangle",
                "title": f"{b['name']} is over budget",
                "text": f"You've spent ₹{b['spent']:,.2f} against a ₹{b['limit']:,.2f} limit.",
            })
        elif b["status"] == "warning":
            alerts.append({
                "type": "warning",
                "icon": "alert-circle",
                "title": f"{b['name']} is nearing its limit",
                "text": f"You've used {b['pct']:.0f}% of the ₹{b['limit']:,.2f} budget.",
            })
    if not alerts:
        alerts.append({
            "type": "success",
            "icon": "check-circle",
            "title": "All budgets on track",
            "text": "Great job staying within your budget limits this period.",
        })

    return {
        "summary": {
            "total_limit": round(total_limit, 2),
            "total_spent": round(total_spent, 2),
            "total_remaining": round(total_remaining, 2),
            "over_count": over_count,
            "warning_count": warning_count,
            "on_track_count": on_track_count,
        },
        "budgets": budgets,
        "trend": trend,
        "distribution": distribution,
        "alerts": alerts,
        "recent_activity": recent_activity,
        "has_data": total_spent > 0,
    }


# ================================================================== #
# Goals module — DB layer                                           #
# ================================================================== #

def get_user_goals(user_id):
    """Return all goals for a user, ordered by progress descending.

    Returns a list of dicts with id, name, category, target_amount,
    saved_amount, deadline, status, progress, effective_status, created_at.
    Empty list if none. Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, name, category, target_amount, saved_amount, deadline, status, created_at "
        "FROM goals WHERE user_id = ? "
        "ORDER BY (saved_amount * 1.0 / target_amount) DESC, id ASC",
        (user_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    for g in rows:
        g["progress"] = round(g["saved_amount"] / g["target_amount"] * 100, 1) if g["target_amount"] > 0 else 0.0
        g["effective_status"] = g["status"]
        if g["saved_amount"] >= g["target_amount"] and g["status"] != "paused":
            g["effective_status"] = "completed"
    return rows


def get_goal_by_id(goal_id, user_id):
    """Return a single goal scoped to the user, or None if not found/owned.

    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, name, category, target_amount, saved_amount, deadline, status, created_at "
        "FROM goals WHERE id = ? AND user_id = ?",
        (goal_id, user_id),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        g = dict(row)
        g["progress"] = round(g["saved_amount"] / g["target_amount"] * 100, 1) if g["target_amount"] > 0 else 0.0
        g["effective_status"] = g["status"]
        if g["saved_amount"] >= g["target_amount"] and g["status"] != "paused":
            g["effective_status"] = "completed"
        return g
    return None


def create_goal(user_id, name, category, target_amount, saved_amount, deadline, status="on-track"):
    """Create a new goal for a user and return its id.

    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO goals (user_id, name, category, target_amount, saved_amount, deadline, status) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, name, category, target_amount, saved_amount, deadline, status),
    )
    goal_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return goal_id


def update_goal(goal_id, user_id, name, category, target_amount, saved_amount, deadline, status):
    """Update a goal row WHERE id = ? AND user_id = ?.

    Returns True if a row was updated, False if no matching row found.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE goals SET name = ?, category = ?, target_amount = ?, saved_amount = ?, "
        "deadline = ?, status = ?, updated_at = datetime('now') "
        "WHERE id = ? AND user_id = ?",
        (name, category, target_amount, saved_amount, deadline, status, goal_id, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def delete_goal(goal_id, user_id):
    """Delete a goal row WHERE id = ? AND user_id = ?.

    Returns True if a row was deleted, False if no matching row found.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM goals WHERE id = ? AND user_id = ?",
        (goal_id, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def add_goal_funds(goal_id, user_id, amount):
    """Add funds to a goal (ownership enforced), capping at the target.

    Returns the updated goal dict, or None if the goal does not exist or
    belongs to another user. Uses parameterized queries — safe from SQL
    injection.
    """
    goal = get_goal_by_id(goal_id, user_id)
    if goal is None:
        return None
    new_saved = min(goal["saved_amount"] + amount, goal["target_amount"])
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE goals SET saved_amount = ?, updated_at = datetime('now') "
        "WHERE id = ? AND user_id = ?",
        (new_saved, goal_id, user_id),
    )
    conn.commit()
    conn.close()
    return get_goal_by_id(goal_id, user_id)


def get_goal_data(user_id, status=None, category=None, sort="progress-desc"):
    """Return the full Goals dashboard dataset for a user.

    Computes summary cards, goal cards, insights, and recent activity.
    Supports optional status, category, and sort filters. Uses parameterized
    queries — safe from SQL injection.
    """
    sort_sql = GOAL_SORT_OPTIONS.get(sort, GOAL_SORT_OPTIONS["progress-desc"])

    where = "WHERE user_id = ?"
    params = [user_id]
    if status:
        where += " AND status = ?"
        params.append(status)
    if category:
        where += " AND category = ?"
        params.append(category)

    conn = get_db()
    cursor = conn.cursor()

    # ---- Goals (filtered) ----
    cursor.execute(
        f"SELECT id, user_id, name, category, target_amount, saved_amount, deadline, status, created_at "
        f"FROM goals {where} ORDER BY {sort_sql}",
        tuple(params),
    )
    goals = [dict(row) for row in cursor.fetchall()]
    for g in goals:
        g["progress"] = round(g["saved_amount"] / g["target_amount"] * 100, 1) if g["target_amount"] > 0 else 0.0
        g["effective_status"] = g["status"]
        if g["saved_amount"] >= g["target_amount"] and g["status"] != "paused":
            g["effective_status"] = "completed"

    # ---- Summary ----
    total_saved = sum(g["saved_amount"] for g in goals)
    total_target = sum(g["target_amount"] for g in goals)
    completed = sum(1 for g in goals if g["effective_status"] == "completed")
    active = sum(1 for g in goals if g["effective_status"] in ("on-track", "at-risk"))
    paused = sum(1 for g in goals if g["effective_status"] == "paused")

    # ---- Recent activity ----
    cursor.execute(
        "SELECT id, action, category, description, amount, created_at "
        "FROM activities WHERE user_id = ? "
        "ORDER BY created_at DESC, id DESC LIMIT 8",
        (user_id,),
    )
    recent_activity = [dict(row) for row in cursor.fetchall()]

    conn.close()

    # ---- Insights ----
    insights = []
    if goals:
        top = max(goals, key=lambda g: g["progress"])
        insights.append({
            "icon": "trophy",
            "accent": "var(--accent)",
            "title": f"Best progress: {top['name']}",
            "text": f"You're {top['progress']:.0f}% of the way to your ₹{top['target_amount']:,.2f} goal.",
        })
        if completed:
            insights.append({
                "icon": "party-popper",
                "accent": "var(--success)",
                "title": f"{completed} goal(s) completed",
                "text": "Congratulations on reaching your savings targets!",
            })
        if paused:
            insights.append({
                "icon": "pause",
                "accent": "var(--ink-muted)",
                "title": f"{paused} goal(s) paused",
                "text": "Paused goals are not accruing progress right now.",
            })
    else:
        insights.append({
            "icon": "target",
            "accent": "var(--accent)",
            "title": "No goals yet",
            "text": "Create your first savings goal to start tracking progress.",
        })

    return {
        "summary": {
            "total_saved": round(total_saved, 2),
            "total_target": round(total_target, 2),
            "overall_progress": round((total_saved / total_target * 100), 1) if total_target > 0 else 0.0,
            "completed": completed,
            "active": active,
            "paused": paused,
        },
        "goals": goals,
        "insights": insights,
        "recent_activity": recent_activity,
        "has_data": len(goals) > 0,
    }


# ================================================================== #
# Reports module — DB layer                                          #
# ================================================================== #

REPORT_DEFAULT_MONTHS = 6

REPORT_PAYMENT_LABELS = {
    "card": "Card",
    "upi": "UPI",
    "cash": "Cash",
    "bank": "Bank",
    "wallet": "Wallet",
}

REPORT_PAYMENT_COLORS = {
    "card": "var(--bar-bills)",
    "upi": "var(--bar-health)",
    "cash": "var(--bar-other)",
    "bank": "var(--bar-shopping)",
    "wallet": "var(--bar-entertainment)",
}


def _compute_period_range(months):
    """Return (start, end) ISO date strings for the last ``months`` months."""
    today = date.today()
    end = today
    start_month = today.month - (months - 1)
    start_year = today.year
    while start_month < 1:
        start_month += 12
        start_year -= 1
    start = date(start_year, start_month, 1)
    return start.isoformat(), end.isoformat()


def get_report_data(user_id, date_from=None, date_to=None, category=None,
                    payment=None, months=REPORT_DEFAULT_MONTHS):
    """Return the full Reports dashboard dataset for a user.

    Computes summary cards, monthly trend, category and payment breakdowns,
    top expenses, monthly summary, and data-driven insight cards. Supports
    optional date range, category, and payment method filters. Uses
    parameterized queries — safe from SQL injection.
    """
    # Build WHERE clause.
    where = "WHERE user_id = ?"
    params = [user_id]
    if date_from:
        where += " AND date >= ?"
        params.append(date_from)
    if date_to:
        where += " AND date <= ?"
        params.append(date_to)
    if category:
        where += " AND category = ?"
        params.append(category)
    if payment:
        where += " AND payment_method = ?"
        params.append(payment)

    full_params = tuple(params)

    conn = get_db()
    cursor = conn.cursor()

    # ---- Summary ----
    cursor.execute(
        f"SELECT COALESCE(SUM(amount), 0.0) AS total, COUNT(*) AS count "
        f"FROM expenses {where}",
        full_params,
    )
    summary_row = cursor.fetchone()
    total_spending = summary_row["total"]
    total_transactions = summary_row["count"]

    # ---- Previous period for comparison ----
    prev_from, prev_to = _compute_prev_period(date_from, date_to, months)
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS total, COUNT(*) AS count "
        "FROM expenses WHERE user_id = ? AND date >= ? AND date <= ?",
        (user_id, prev_from, prev_to),
    )
    prev_row = cursor.fetchone()
    prev_total_spending = prev_row["total"]
    prev_total_transactions = prev_row["count"]

    # ---- Monthly trend (current period) ----
    cursor.execute(
        "SELECT strftime('%Y-%m', date) AS month, "
        "COALESCE(SUM(amount), 0.0) AS total, COUNT(*) AS count "
        f"FROM expenses {where} "
        "GROUP BY month ORDER BY month ASC",
        full_params,
    )
    monthly_trend = []
    for row in cursor.fetchall():
        parts = row["month"].split("-")
        label = f"{MONTH_LABELS[int(parts[1])]} {parts[0]}"
        monthly_trend.append({
            "month": label,
            "total": round(row["total"], 2),
            "count": row["count"],
        })

    # ---- Previous monthly trend ----
    cursor.execute(
        "SELECT strftime('%Y-%m', date) AS month, "
        "COALESCE(SUM(amount), 0.0) AS total, COUNT(*) AS count "
        "FROM expenses WHERE user_id = ? AND date >= ? AND date <= ? "
        "GROUP BY month ORDER BY month ASC",
        (user_id, prev_from, prev_to),
    )
    prev_monthly_trend = []
    for row in cursor.fetchall():
        parts = row["month"].split("-")
        label = f"{MONTH_LABELS[int(parts[1])]} {parts[0]}"
        prev_monthly_trend.append({
            "month": label,
            "total": round(row["total"], 2),
            "count": row["count"],
        })

    # ---- Category breakdown ----
    cursor.execute(
        "SELECT category, COALESCE(SUM(amount), 0.0) AS value "
        f"FROM expenses {where} "
        "GROUP BY category ORDER BY value DESC",
        full_params,
    )
    category_breakdown = []
    for row in cursor.fetchall():
        category_breakdown.append({
            "name": row["category"],
            "color": "var(--bar-other)",
            "value": round(row["value"], 2),
        })

    # ---- Payment method breakdown ----
    cursor.execute(
        "SELECT payment_method, COALESCE(SUM(amount), 0.0) AS value "
        f"FROM expenses {where} "
        "GROUP BY payment_method ORDER BY value DESC",
        full_params,
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
        f"FROM expenses {where} "
        "ORDER BY amount DESC LIMIT 10",
        full_params,
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
        f"FROM expenses {where} "
        "GROUP BY month ORDER BY month ASC",
        full_params,
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


# ================================================================== #
# Settings module — DB layer                                        #
# ================================================================== #

# Whitelist of allowed values for settings fields.
SETTINGS_CURRENCIES = ["INR", "USD", "EUR", "GBP", "JPY", "AUD"]
SETTINGS_DATE_FORMATS = ["DD-MM-YYYY", "MM-DD-YYYY", "YYYY-MM-DD"]
SETTINGS_LANGUAGES = ["en", "hi", "bn", "ta", "te"]
SETTINGS_WEEK_STARTS = ["monday", "sunday", "saturday"]
SETTINGS_PAYMENT_METHODS = ["upi", "card", "cash", "bank", "wallet"]
SETTINGS_THEMES = ["light", "dark", "system"]
SETTINGS_ACCENT_COLORS = ["green", "blue", "purple", "amber", "rose"]
SETTINGS_DENSITIES = ["comfortable", "compact"]

# Default settings values (must match the user_settings table defaults).
DEFAULT_USER_SETTINGS = {
    "currency": "INR",
    "date_format": "DD-MM-YYYY",
    "language": "en",
    "week_start": "monday",
    "budget_alert_threshold": 80,
    "default_payment_method": "upi",
    "theme": "dark",
    "accent_color": "green",
    "interface_density": "comfortable",
    "two_factor_enabled": 0,
    "login_alerts_enabled": 1,
    "expense_reminders_enabled": 1,
    "budget_alerts_enabled": 1,
    "goal_milestones_enabled": 1,
    "weekly_summary_enabled": 1,
    "product_updates_enabled": 0,
    "personalised_insights_enabled": 1,
    "anonymous_usage_enabled": 0,
}


def get_user_settings(user_id):
    """Return the settings row for a user, creating defaults if none exist.

    If the user has no settings row yet, one is created with the default
    values from DEFAULT_USER_SETTINGS. Returns a dict of settings fields.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM user_settings WHERE user_id = ?",
        (user_id,),
    )
    row = cursor.fetchone()

    if row is None:
        # Create default settings row for this user.
        cursor.execute(
            "INSERT INTO user_settings (user_id) VALUES (?)",
            (user_id,),
        )
        conn.commit()
        cursor.execute(
            "SELECT * FROM user_settings WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()

    conn.close()
    return dict(row) if row else dict(DEFAULT_USER_SETTINGS)


def update_user_settings(user_id, **kwargs):
    """Update settings fields for a user.

    Only whitelisted keys are accepted; unknown keys are ignored. Values are
    validated against the allowed sets where applicable. Returns True if any
    field was updated. Uses parameterized queries — safe from SQL injection.
    """
    # Build the list of allowed columns and their validated values.
    allowed = {
        "currency": SETTINGS_CURRENCIES,
        "date_format": SETTINGS_DATE_FORMATS,
        "language": SETTINGS_LANGUAGES,
        "week_start": SETTINGS_WEEK_STARTS,
        "default_payment_method": SETTINGS_PAYMENT_METHODS,
        "theme": SETTINGS_THEMES,
        "accent_color": SETTINGS_ACCENT_COLORS,
        "interface_density": SETTINGS_DENSITIES,
    }

    # Integer toggle fields (0/1).
    toggle_fields = [
        "two_factor_enabled",
        "login_alerts_enabled",
        "expense_reminders_enabled",
        "budget_alerts_enabled",
        "goal_milestones_enabled",
        "weekly_summary_enabled",
        "product_updates_enabled",
        "personalised_insights_enabled",
        "anonymous_usage_enabled",
    ]

    # Integer range field.
    int_fields = ["budget_alert_threshold"]

    columns = []
    params = []

    for key, value in kwargs.items():
        if key in allowed:
            if value not in allowed[key]:
                continue  # Invalid value — skip
            columns.append(f"{key} = ?")
            params.append(value)
        elif key in toggle_fields:
            # Accept boolean-like values (True/False, 1/0, "1"/"0", "true"/"false").
            if isinstance(value, bool):
                val = 1 if value else 0
            elif isinstance(value, int) and value in (0, 1):
                val = value
            elif isinstance(value, str) and value.lower() in ("1", "true", "yes", "on"):
                val = 1
            elif isinstance(value, str) and value.lower() in ("0", "false", "no", "off"):
                val = 0
            else:
                continue
            columns.append(f"{key} = ?")
            params.append(val)
        elif key in int_fields:
            try:
                val = int(value)
                if val < 1 or val > 100:
                    continue
            except (TypeError, ValueError):
                continue
            columns.append(f"{key} = ?")
            params.append(val)

    if not columns:
        return False

    columns.append("updated_at = datetime('now')")
    params.append(user_id)

    conn = get_db()
    try:
        cursor = conn.cursor()

        # Make sure a settings row exists (upsert-style) so updates persist
        # even if get_user_settings() was never called for this user.
        cursor.execute(
            "INSERT OR IGNORE INTO user_settings (user_id) VALUES (?)",
            (user_id,),
        )

        cursor.execute(
            "UPDATE user_settings SET " + ", ".join(columns) + " WHERE user_id = ?",
            tuple(params),
        )
        affected = cursor.rowcount
        conn.commit()
        return affected > 0
    finally:
        conn.close()


def reset_user_settings(user_id):
    """Reset a user's settings to the default values.

    Deletes the user's settings row so the next get_user_settings() call
    recreates it with defaults. Returns True if a row was deleted.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM user_settings WHERE user_id = ?",
        (user_id,),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def clear_user_data(user_id):
    """
    Delete all financial data for a user (expenses, activities, budgets,
    goals, categories). The user row itself is left untouched.
    Returns a dict with counts of deleted rows per table.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()

    counts = {}
    for table in ("expenses", "activities", "budgets", "goals", "categories"):
        cursor.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))
        counts[table] = cursor.rowcount

    conn.commit()
    conn.close()
    return counts


def delete_user_account(user_id):
    """
    Permanently delete a user and all associated data.

    Deletes the user's settings, expenses, activities, budgets, goals, and
    categories, then the user row itself. Returns True on success.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()

    # Delete child rows first (foreign key order).
    for table in ("user_settings", "sessions", "expenses", "activities", "budgets", "goals", "categories"):
        cursor.execute(f"DELETE FROM {table} WHERE user_id = ?", (user_id,))

    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


# ================================================================== #
# Sessions module — DB layer                                        #
# ================================================================== #

def create_session(user_id, token, user_agent="", ip_address=""):
    """Record a new authenticated session for a user.

    Returns the new session id. Uses parameterized queries — safe from
    SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sessions (user_id, token, user_agent, ip_address) "
        "VALUES (?, ?, ?, ?)",
        (user_id, token, user_agent, ip_address),
    )
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id


def get_user_sessions(user_id):
    """Return all active sessions for a user, newest first.

    Returns a list of dicts with id, user_id, token, user_agent, ip_address,
    created_at, last_seen. Empty list if none. Uses parameterized queries.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, user_id, token, user_agent, ip_address, created_at, last_seen "
        "FROM sessions WHERE user_id = ? "
        "ORDER BY last_seen DESC, id DESC",
        (user_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def revoke_session(user_id, session_id):
    """Revoke (delete) a session row, scoped to the owning user.

    Returns True if a row was deleted, False if no matching row found.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM sessions WHERE id = ? AND user_id = ?",
        (session_id, user_id),
    )
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def delete_session_by_token(token):
    """Delete a session row by its token (used on logout).

    Returns True if a row was deleted, False if no matching row found.
    Uses parameterized queries — safe from SQL injection.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


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