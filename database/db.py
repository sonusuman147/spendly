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


def get_db():
    """Open and return a connection to the SQLite database.

    Sets row_factory to sqlite3.Row for dictionary-like column access
    and enables foreign key enforcement on every connection.
    """
    conn = sqlite3.connect(DATABASE_PATH)
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
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Add google_id column if not already present — safe on repeated runs
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
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

    # Insert demo user using create_user helper
    user_id = create_user("Demo User", "demo@spendly.com", password_hash=generate_password_hash("demo123"))

    today = date.today()

    # Insert 8 sample expenses across multiple categories
    sample_expenses = [
        (user_id, 450.00, "Food", today - timedelta(days=28), "Weekly groceries"),
        (user_id, 150.00, "Transport", today - timedelta(days=25), "Bus pass recharge"),
        (user_id, 2000.00, "Bills", today - timedelta(days=20), "Electricity bill"),
        (user_id, 600.00, "Health", today - timedelta(days=18), "Pharmacy — medicines"),
        (user_id, 350.00, "Entertainment", today - timedelta(days=14), "Movie tickets"),
        (user_id, 1200.00, "Shopping", today - timedelta(days=10), "New headphones"),
        (user_id, 320.00, "Food", today - timedelta(days=5), "Dinner at pizzeria"),
        (user_id, 100.00, "Other", today - timedelta(days=2), "Miscellaneous"),
    ]

    cursor.executemany(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        [
            (uid, amt, cat, d.isoformat(), desc)
            for uid, amt, cat, d, desc in sample_expenses
        ],
    )

    conn.commit()
    conn.close()


def create_user(name, email, password_hash=None, google_id=None):
    """Create a new user with an optional password hash and Google ID.

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
        "INSERT INTO users (name, email, password_hash, google_id) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, google_id),
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


def get_user_expenses_summary(user_id):
    """Return a summary dictionary of a user's expenses.

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

    # Total and count
    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0.0) AS total_expenses, "
        "COUNT(*) AS expense_count "
        "FROM expenses WHERE user_id = ?",
        (user_id,),
    )
    totals = dict(cursor.fetchone())

    # Category breakdown
    cursor.execute(
        "SELECT category, SUM(amount) AS total, COUNT(*) AS count "
        "FROM expenses WHERE user_id = ? "
        "GROUP BY category ORDER BY total DESC",
        (user_id,),
    )
    breakdown = [dict(row) for row in cursor.fetchall()]

    # Recent expenses
    cursor.execute(
        "SELECT amount, category, date, description "
        "FROM expenses WHERE user_id = ? "
        "ORDER BY date DESC, created_at DESC LIMIT 5",
        (user_id,),
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
