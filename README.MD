# 💰 Spendly

**Track every rupee. Know where it goes.**

Spendly is a lightweight personal expense tracker built with Flask and SQLite. It supports email/password authentication, Google OAuth sign-in, password recovery via security questions, and full CRUD for expenses with category-based spending breakdowns.

---

## ✨ Features

- **Authentication**
  - Email/password sign-up and sign-in
  - "Continue with Google" OAuth sign-in (auto-links to an existing account by email)
  - Password recovery via a security question flow (no email delivery required)
- **Expense tracking**
  - Add, edit, and delete expenses with amount, category, description, and date
  - Category tags (Food, Travel, Bills, Health, Transport, Other, etc.)
  - Expense list sorted newest-first
- **Profile & insights**
  - Total spent, transaction count, and top category at a glance
  - Spending breakdown by category with proportional bars
  - Date filtering — this month, last 3 months, last 6 months, all time, or a custom range
  - Edit profile (name, email) and change password from one screen
- **Legal pages** — Terms & Conditions and Privacy Policy included

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask (single `app.py`, no blueprints) |
| Database | SQLite (raw `sqlite3`, no ORM) |
| Templates | Jinja2 |
| Frontend | Vanilla HTML/CSS/JS — no frameworks, no npm |
| Auth | Werkzeug password hashing + Authlib (Google OAuth) |
| Config | `python-dotenv` |
| Testing | Pytest |

No React, no SQLAlchemy, no build step — the whole app runs from one Python process.

---

## 📁 Project Structure

```
spendly/
├── app.py                     # All routes — single file, no blueprints
├── requirements.txt           # Flask, werkzeug, pytest, authlib, python-dotenv
├── .env                        # GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET (not committed)
├── database/
│   ├── __init__.py
│   └── db.py                  # All DB logic: schema, queries, helpers, seed data
├── templates/
│   ├── base.html               # Shared layout — all templates extend this
│   ├── landing.html            # Public landing page
│   ├── login.html              # Sign-in (email + Google OAuth)
│   ├── register.html           # Registration with security question
│   ├── forgot_password.html    # Email entry step
│   ├── reset_password.html     # Security answer + new password step
│   ├── profile.html            # Read-only profile overview with stats
│   ├── profile_edit.html       # Edit profile name/email/password
│   ├── privacy.html            # Privacy policy
│   ├── terms.html              # Terms & conditions
│   └── expenses/
│       ├── list.html           # Expense list table
│       ├── form.html           # Add / Edit expense form
│       └── delete.html         # Delete confirmation
├── static/
│   ├── css/
│   │   ├── style.css           # Global styles — variables, layout, navbar, footer
│   │   ├── landing.css         # Landing page hero, features, CTA
│   │   ├── profile.css         # Profile page, edit page, stats cards, category bars
│   │   └── expenses.css        # Expense table, form, delete confirmation, category tags
│   └── js/
│       └── main.js             # Vanilla JS hooks (currently empty)
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Pytest fixtures: app, client, db (temp DB isolation)
│   └── test_backend_connection.py  # Tests covering DB helpers + route behaviour
└── .gitignore                  # Ignores venv, *.db, __pycache__, .env
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+

### Setup

```bash
# Clone the repo
git clone <your-repo-url>
cd spendly

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# Install dependencies
pip install -r requirements.txt
```

### Configure environment variables

Create a `.env` file in the project root (required only for Google sign-in — the app runs without it, but the Google button will fail):

```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

### Run the app

```bash
python app.py
```

The app starts on **http://127.0.0.1:5001**. The SQLite database (`expense_tracker.db`) and its schema are initialized and seeded automatically on first run.

---

## 🧪 Testing

```bash
pytest                                          # run all tests
pytest -v                                       # verbose output
pytest tests/test_backend_connection.py -v      # run a specific file
pytest -k "test_authenticated"                  # run a specific test by name
pytest -s                                       # show stdout (print debugging)
pytest -x                                       # stop on first failure
pytest --cov=app --cov=database                 # with coverage (requires pytest-cov)
```

Tests run against a temporary, isolated SQLite database created via `tempfile.mkstemp()` — they never touch `expense_tracker.db`.

---

## 🗺️ Routes

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

### Legal
| Route | Method | Description |
|---|---|---|
| `/terms` | GET | Terms & conditions |
| `/privacy` | GET | Privacy policy |

---

## 🔒 Security Notes

- Passwords hashed with `werkzeug.security` — never stored in plain text
- Security question answers are hashed and compared case-insensitively
- All SQL queries are parameterized (`?` placeholders) — no string-formatted SQL
- Foreign keys are enforced manually via `PRAGMA foreign_keys = ON` on every connection
- Google OAuth verifies the `email_verified` claim before creating or linking an account
- **Known limitation:** CSRF protection is not currently implemented. Consider adding `flask-wtf` or custom tokens before deploying publicly.

---

## ⚠️ Constraints (by design)

This project intentionally stays minimal:
- Flask only — no FastAPI/Django
- SQLite only — no Postgres/SQLAlchemy
- Vanilla JS only — no React/jQuery/npm packages
- Single-file routing (`app.py`) — no blueprints

---

## 📄 License

Add your license of choice here (e.g. MIT).