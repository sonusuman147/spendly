# 💰 Spendly

**Track every rupee. Know where it goes.**

Spendly is a lightweight personal expense tracker built with **Flask** and **SQLite**. It supports email/password authentication, Google OAuth sign-in, password recovery via security questions, full CRUD for expenses and categories, a filterable/paginated Transactions ledger, category analytics with visual charts, CSV export, and a responsive app-shell UI with light/dark/system theming.

---

## ✨ Features

### 🔐 Authentication
- Email/password sign-up and sign-in
- "Continue with Google" OAuth sign-in (auto-links to an existing account by email)
- Password recovery via a security question flow (no email delivery required)
- Session-based auth with orphaned-session cleanup

### 📊 Dashboard (Profile)
- Total spent, transaction count, and top category at a glance
- Spending breakdown by category with proportional bars
- Date filtering — this month, last 3 months, last 6 months, all time, or a custom range
- Recent 5 transactions
- Edit profile (name, email) and change password from one screen

### 💸 Expenses CRUD
- Add, edit, and delete expenses with amount, category, description, date, and payment method
- Payment methods: Card, UPI, Cash, Bank, Wallet
- Category tags with per-category colors
- Expense list sorted newest-first, with payment badges
- Activity logging for every added / edited / deleted expense

### 🔄 Transactions Ledger
- Every expense presented as a transaction in a professional ledger
- **Five summary cards** — Total Transactions, Total Amount, Highest Expense, Average Expense, Last Transaction (computed from the *filtered* set)
- **Advanced filter bar** — search, category, date range, amount range, sorting, and reset
- **Bulk selection** with "select all on page" and bulk delete
- **Server-side pagination** (8 per page)
- **View modal** with full transaction details
- **Recent Activity panel** fed by the real activity log
- **CSV export** of the filtered (or selected) transactions

### 🗂️ Categories Module
- **Four summary cards** — Total Categories, Most Used Category, Highest Spending Category, Unused Categories
- **Search + filter bar** — case-insensitive search by name/description, sorting (name, total spent, transaction count, created date), and page-size selector
- **Professional table** — icon, color, name, description, transaction count, total spent, average expense, created date, and View / Edit / Delete actions
- **Add / Edit form** with icon picker and color picker (Lucide icons + preset palette)
- **Donut chart** for spending distribution (CSS `conic-gradient`, server-computed)
- **Top Categories ranking** panel with proportional bars
- **Quick actions** — Create Category, Merge Categories, Export Categories, Category Analytics
- **Category Analytics page** — full distribution chart, ranking, and breakdown table
- **Protected deletion** — a category currently used by expenses requires explicit confirmation and explains reassignment to **Other**
- **Merge Categories** — reassign all expenses from a source category into a target category
- **CSV export** of all categories with usage statistics
- Default categories (Food, Transport, Bills, Health, Entertainment, Shopping, Other) are seeded for every user and backfilled for existing accounts; renaming a category keeps expense history coherent

### 🎨 Design System
- Left sidebar app shell with Dashboard / Expenses / Transactions / Categories navigation
- Green accent palette, warm off-white background, DM Serif Display + DM Sans typography
- Light / Dark / System theme switcher (persisted in `localStorage`)
- Fully responsive — sticky sidebar, mobile drawer, collapsible panels, stacking tables
- Vanilla JS only, Lucide icons, CSS variables (no hardcoded hex)

### ⚖️ Legal
- Terms & Conditions and Privacy Policy pages included

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Flask (single `app.py`, no blueprints) |
| Database | SQLite (raw `sqlite3`, no ORM) |
| Templates | Jinja2 |
| Frontend | Vanilla HTML/CSS/JS — no frameworks, no npm |
| Icons | Lucide (CDN) |
| Fonts | Google Fonts — DM Serif Display + DM Sans |
| Auth | Werkzeug password hashing + Authlib (Google OAuth) |
| Config | `python-dotenv` |
| Testing | Pytest (3 suites, 104 tests) |

No React, no SQLAlchemy, no build step — the whole app runs from one Python process.

---

## 📁 Project Structure

```
spendly/
├── app.py                     # All routes — single file, no blueprints
├── requirements.txt           # Flask, werkzeug, pytest, authlib, python-dotenv
├── README.MD                  # Project readme (this file)
├── PROJECT_DOCUMENTATION.md   # Full code-derived developer reference
├── CLAUDE.md                  # Agent/maintenance notes & conventions
├── TODO.md                    # Task tracking
├── implementation_plan.md     # Historical implementation plan (Step 06)
├── .env                        # GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET (not committed)
├── database/
│   ├── __init__.py
│   └── db.py                  # All DB logic: schema, seed, queries, helpers
├── templates/
│   ├── base.html              # Shared app-shell layout — all templates extend this
│   ├── landing.html           # Public landing page
│   ├── login.html             # Sign-in (email + Google OAuth)
│   ├── register.html          # Registration with security question
│   ├── forgot_password.html   # Email entry step
│   ├── reset_password.html    # Security answer + new password step
│   ├── profile.html           # Dashboard: stats, filter bar, recent txns, category bars
│   ├── profile_edit.html      # Edit profile name/email/password
│   ├── privacy.html           # Privacy policy
│   ├── terms.html             # Terms & conditions
│   ├── transactions.html      # Transactions ledger (filter, table, activity panel)
│   ├── expenses/
│   │   ├── list.html          # Expense list table
│   │   ├── form.html          # Add / Edit expense form
│   │   └── delete.html        # Delete confirmation
│   └── categories/
│       ├── list.html          # Categories dashboard (summary cards, table, donut, ranking, quick actions)
│       ├── form.html          # Add / Edit category form (icon + color pickers)
│       ├── view.html          # Single-category detail page with usage stats
│       ├── delete.html        # Delete confirmation (protected when in use)
│       ├── merge.html         # Merge source → target category form
│       └── analytics.html     # Category analytics (distribution, ranking, breakdown)
├── static/
│   ├── css/
│   │   ├── style.css          # Global styles — variables, app shell, themes, navbar, footer
│   │   ├── landing.css        # Landing page hero, features, CTA
│   │   ├── profile.css        # Dashboard/profile page, edit page, stats cards, category bars
│   │   ├── expenses.css       # Expense table, form, delete confirmation, category tags
│   │   ├── transactions.css   # Transactions ledger, filter bar, table, activity panel, modal
│   │   └── categories.css     # Categories dashboard, forms, donut, ranking, analytics, merge
│   └── js/
│       ├── main.js            # App shell JS — sidebar, drawer, profile dropdown, theme switch
│       ├── transactions.js    # Transactions UX — view modal, bulk selection, export link
│       └── categories.js      # Categories UX — icon/color pickers, filter auto-submit, delete confirm
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # Pytest fixtures: app, client, db (temp DB isolation)
│   ├── test_backend_connection.py  # DB helpers + /profile route behaviour
│   ├── test_transactions.py        # Transactions backend (filters, sort, pagination, export, bulk delete)
│   └── test_categories.py          # Categories backend (CRUD, stats, merge, export, analytics, routes)
└── .gitignore                 # Ignores venv, *.db, __pycache__, .env, .claude/plans
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
SECRET_KEY=change-me-in-production
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

### Run the app

```bash
python app.py
```

The app starts on **http://127.0.0.1:5001** (or `$PORT`). The SQLite database (`expense_tracker.db`) and its schema are initialized and seeded automatically on first run — including the demo user, 8 sample expenses, matching activity records, and the 7 default category rows.

**Demo login:** `demo@spendly.com` / `demo123`

---

## 🧪 Testing

```bash
pytest                                          # run all tests (104 tests)
pytest -v                                       # verbose output
pytest tests/test_backend_connection.py -v      # run a specific file
pytest -k "test_categories"                     # run a specific test name / class
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

### Profile / Dashboard
| Route | Method | Description |
|---|---|---|
| `/profile` | GET | View dashboard with expense summary, stats, recent transactions |
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

### Transactions
| Route | Method | Description |
|---|---|---|
| `/transactions` | GET | Filterable, sortable, paginated ledger of all expenses |
| `/transactions/export` | GET | CSV export of filtered or selected transactions |
| `/transactions/bulk-delete` | POST | Delete multiple selected transactions (ownership enforced) |

### Categories
| Route | Method | Description |
|---|---|---|
| `/categories` | GET | Categories dashboard (summary cards, table, donut, ranking, quick actions) |
| `/categories/add` | GET, POST | Add a new category (icon + color picker) |
| `/categories/<id>` | GET | View a single category with usage stats |
| `/categories/<id>/edit` | GET, POST | Edit a category |
| `/categories/<id>/delete` | GET, POST | Delete confirmation (blocked unless confirmed when in use) |
| `/categories/merge` | GET, POST | Merge source category into target category |
| `/categories/export` | GET | CSV export of all categories with usage stats |
| `/categories/analytics` | GET | Category analytics page |

### Legal / Static
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
- **Ownership scoping** — expenses and categories are scoped by `user_id` in SQL and route checks; cross-user access returns `abort(403)`
- **Protected category deletion** — a category used by expenses can only be deleted after the user confirms; expenses are reassigned to **Other**
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

