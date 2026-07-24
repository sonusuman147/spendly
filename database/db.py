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

    # Insert demo user
    password_hash = generate_password_hash("demo123")
    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        ("Demo User", "demo@spendly.com", password_hash),
    )
    user_id = cursor.lastrowid

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


def create_user(name, email, password):
    """Create a new user with a hashed password.

    Hashes the password using werkzeug.security.generate_password_hash,
    inserts a new row into the users table, and returns the new user's id.

    Raises sqlite3.IntegrityError if the email is already taken (UNIQUE constraint).
    Uses parameterized queries — safe from SQL injection.
    """
    password_hash = generate_password_hash(password)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
        (name, email, password_hash),
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
