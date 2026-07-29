# CLAUDE.md

## Project overview

Spendly is a lightweight personal expense tracker built with Flask and SQLite.
Supports email/password auth, Google OAuth, password reset via security questions,
and full CRUD for expenses with category breakdowns.

---

## Architecture

```
spendly/
├── app.py                     # All routes — single file, no blueprints
├── requirements.txt           # Flask, werkzeug, pytest, authlib, python-dotenv
├── .env                       # GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET (not committed)
├── database/
│   ├── __init__.py
│   └── db.py                  # All DB logic: schema, queries, helpers, seed data
├── templates/
│   ├── base.html              # Shared layout — all templates extend this
│   ├── landing.html           # Public landing page
│   ├── login.html             # Sign-in (email + Google OAuth)
│   ├── register.html          # Registration with security question
│   ├── forgot_password.html   # Email entry step
│   ├── reset_password.html    # Security answer + new password step
│   ├── profile.html           # Read-only profile overview with stats
│   ├── profile_edit.html      # Edit profile name/email/password
│   ├── privacy.html           # Privacy policy
│   ├── terms.html             # Terms & conditions
│   └── expenses/
│       ├── list.html          # Expense list table
│       ├── form.html          # Add / Edit expense form
│       └── delete.html        # Delete confirmation
├── static/
│   ├── css/
│   │   ├── style.css          # Global styles — variables, layout, navbar, footer
│   │   ├── landing.css        # Landing page hero, features, CTA
│   │   ├── profile.css        # Profile page, edit page, stats cards, category bars
│   │   └── expenses.css       # Expense table, form, delete confirmation, category tags
│   └── js/
│       └── main.js            # Vanilla JS only (currently empty — hooks for future features)
├── tests/
│   ├── __init__.py            # Package marker
│   ├── conftest.py            # Pytest fixtures: app, client, db (temp DB isolation)
│   └── test_backend_connection.py  # 14 tests covering DB helpers + route behaviour
└── .gitignore                 # Ignores venv, *.db, __pycache__, .env, .claude/plans/
```

**Where things belong:**
- New routes → `app.py` only, no blueprints
- DB logic → `database/db.py` only, never inline in routes
- New pages → new `.html` file extending `base.html`
- Page-specific styles → new `.css` file in `static/css/`, not inline `<style>` tags
- Tests → new `.py` file in `tests/` following existing patterns

---

## Code style

- **Python**: PEP 8, `snake_case` for variables and functions
- **Templates**: Jinja2 with `url_for()` for every internal link — never hardcode URLs
- **Route functions**: one responsibility only — fetch data, render template, done
- **DB queries**: always use parameterized queries (`?` placeholders) — never f-strings in SQL
- **Error handling**: use `abort()` for HTTP errors (404, 403), not bare `return "error string"`
- **Validation**: server-side validation on every POST; flash messages for user feedback

---

## Tech constraints

- **Flask only** — no FastAPI, no Django, no other web frameworks
- **SQLite only** — no PostgreSQL, no SQLAlchemy ORM, no external DB
- **Vanilla JS only** — no React, no jQuery, no npm packages
- **No new pip packages** — work within `requirements.txt` as-is unless explicitly told otherwise
- **Python 3.10+ assumed** — f-strings and `match` statements are fine

---

## Routes (all implemented)

### Public / Auth
| Route | Method | Description |
|---|---|---|
| `/` | GET | Landing page |
| `/register` | GET, POST | Create account with security question |
| `/login` | GET, POST | Sign in with email/password |
| `/login/google` | GET | Redirect to Google OAuth consent |
| `/login/google/callback` | GET | OAuth callback — create or link account |
| `/logout` | GET | Clear session, redirect to landing |

### Password Reset
| Route | Method | Description |
|---|---|---|
| `/forgot-password` | GET, POST | Enter email to start reset |
| `/forgot-password/reset` | GET, POST | Answer security question, set new password |

### Profile
| Route | Method | Description |
|---|---|---|
| `/profile` | GET | View profile with expense summary, stats, recent transactions |
| `/profile/edit` | GET, POST | Edit name/email and optionally change password |
| `/profile/update` | POST | Update name/email (legacy endpoint) |
| `/profile/change-password` | POST | Change password with current password verification |

### Expense CRUD
| Route | Method | Description |
|---|---|---|
| `/expenses` | GET | List all expenses (newest first) |
| `/expenses/add` | GET, POST | Add a new expense |
| `/expenses/<id>/edit` | GET, POST | Edit an existing expense |
| `/expenses/<id>/delete` | GET, POST | Delete confirmation + execution |

### Legal / Static
| Route | Method | Description |
|---|---|---|
| `/terms` | GET | Terms & conditions |
| `/privacy` | GET | Privacy policy |

---

## Security features

- **Password hashing**: `werkzeug.security.generate_password_hash()` / `check_password_hash()` — never plain text
- **Security questions**: answer hashed before storage; compared case-insensitively via `.strip().lower()`
- **Google OAuth**: requires `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`; verifies `email_verified` claim
- **Session management**: `session.clear()` on logout; orphaned session detection (profile route clears non-existent user IDs)
- **SQL injection prevention**: 100% parameterized queries (`?` placeholders)
- **CSRF protection**: not implemented (Flask's default session-based CSRF is absent; forms use GET for sensitive actions like logout — be aware)

---

## Environment variables (`.env`)

```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

Both are required for Google OAuth to work. If absent, the Google sign-in button
will redirect to an error page. The app itself still starts without them.

---

## Testing patterns

- **Temp DB isolation**: `conftest.py` overrides `DATABASE_PATH` with `tempfile.mkstemp()` — tests never touch `expense_tracker.db`
- **Fixtures**:
  - `app` — Flask app instance with `TESTING=True`, DB initialised and seeded
  - `client` — Flask test client for route-level tests
  - `db` — Direct reference to `database.db` module for unit tests
- **Test categories**:
  - `TestGetUserById` — `get_user_by_id()` for valid, non-existent, and format checks
  - `TestGetUserExpensesSummary` — totals, counts, ordering, breakdown, edge cases
  - `TestProfileRoute` — unauthenticated redirect, authenticated rendering, orphaned sessions

---

## Warnings and things to avoid

- **Never hardcode URLs** in templates — always use `url_for()`
- **Never put DB logic in route functions** — it belongs in `database/db.py`
- **Never install new packages** mid-feature without flagging it — keep `requirements.txt` in sync
- **Never use JS frameworks** — the frontend is intentionally vanilla
- **Never use raw string returns for routes** — always render a template or redirect
- **FK enforcement is manual** — SQLite foreign keys are off by default; `get_db()` runs `PRAGMA foreign_keys = ON` on every connection
- **Test DB isolation** — `conftest.py` patches `DATABASE_PATH` at module import time; never rely on the real `expense_tracker.db` in tests
- **Google OAuth requires `.env`** — the app runs without it, but Google sign-in will fail if `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` are not set
- **CSRF is not enforced** — forms are vulnerable to cross-site request forgery; add `flask-wtf` or a custom token check if this becomes a requirement

---

## Commands

```bash
# Setup
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux
pip install -r requirements.txt

# Run dev server (port 5001)
python app.py

# Run all tests
pytest

# Run all tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_backend_connection.py -v

# Run a specific test by name
pytest -k "test_authenticated"

# Run tests with stdout visible (e.g. for print debugging)
pytest -s

# Run tests, stop on first failure
pytest -x

# Run tests with coverage (if pytest-cov is installed)
pytest --cov=app --cov=database
```

---

## Subagent Policy

- Always use a builtin explore subagent for codebase exploration
  before implementing any new feature
- Always use a subagent to verify test results
  after any implementation
- When asked to plan, delegate codebase research
  to a subagent before presenting the plan
- Always use a builtin plan subagent in plan mode

