"""Pytest fixtures for Spendly backend tests.

Overrides DATABASE_PATH to use a temporary test database
so that tests never touch the real expense_tracker.db.
"""

import os
import sys
import tempfile

import pytest

# Ensure the project root is on sys.path so imports work
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Override DATABASE_PATH *before* any app or db module is imported
_tmp_fd, _tmp_path = tempfile.mkstemp(suffix=".db")
os.close(_tmp_fd)

# Patch DATABASE_PATH in the database module
import database.db as db_module
db_module.DATABASE_PATH = _tmp_path


@pytest.fixture
def app():
    """Create a Flask app instance configured for testing.

    Drops and recreates all tables, then seeds fresh demo data so every
    test starts from an identical, isolated database state. This prevents
    tests from mutating shared rows and invalidating later assertions.
    """
    from app import app as flask_app

    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
    )

    # Reset the database to a pristine, freshly-seeded state per test.
    # init_db() runs first so the schema always exists (the previous test
    # may have unlinked the temp file). Row-level DELETE is used instead of
    # DROP TABLE because DROP requires an exclusive lock and can fail with
    # "database is locked" if a previous test left a connection open.
    with flask_app.app_context():
        db_module.init_db()

        conn = db_module.get_db()
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute("DELETE FROM activities")
        conn.execute("DELETE FROM expenses")
        conn.execute("DELETE FROM categories")
        conn.execute("DELETE FROM goals")
        conn.execute("DELETE FROM budgets")
        conn.execute("DELETE FROM user_sessions")
        conn.execute("DELETE FROM user_settings")
        conn.execute("DELETE FROM users")
        # Reset AUTOINCREMENT counters so the fresh seed assigns id=1 to the
        # demo user, keeping the `user_id == 1` convention used by the tests.
        conn.execute("DELETE FROM sqlite_sequence")
        conn.commit()
        conn.close()

        db_module.seed_db()

    yield flask_app

    # Clean up the temporary database after tests
    try:
        os.unlink(_tmp_path)
    except OSError:
        pass


@pytest.fixture
def client(app):
    """A Flask test client for making requests."""
    return app.test_client()


@pytest.fixture
def db(app):
    """Provide direct access to the database module for unit tests.

    Depends on the app fixture so the database is initialised and seeded
    before any unit test runs.
    """
    return db_module

