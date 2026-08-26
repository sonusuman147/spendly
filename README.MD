# 💰 Spendly

**Track every rupee. Know where it goes.**

Spendly is a modern, lightweight personal finance and expense tracking web application built with **Flask** and **SQLite**. It features secure authentication (including Google OAuth and security-question password recovery), full expense lifecycle management, a high-performance Transactions ledger, custom category management with visual analytics, monthly budget tracking with threshold alerts, milestone-driven savings goals, comprehensive reports with interactive charts, extensive user settings (including active session management and per-user appearance customization), a searchable Help & Support center with ticket submission, and legal compliance pages — all wrapped in a responsive, theme-switchable UI.

---

## ✨ Features

### 🔐 Authentication & Session Security
- **Email & Password Authentication**: Secure registration and login using industry-standard password hashing via `werkzeug.security`.
- **Google OAuth 2.0**: "Continue with Google" sign-in via Authlib with automatic account creation and email-based account linking.
- **Security Question Password Recovery**: Self-serve password reset without requiring an SMTP email delivery service.
- **Active Session Tracking**: Server-side `user_sessions` tracking recording device user-agents, IP addresses, and timestamps with remote single-device session revocation and automated invalidation via `@app.before_request`.
- **User Profile Management**: Update personal profile details (name, email, phone, bio) and change passwords with current-password verification.

### 📊 Dashboard (Profile)
- **Financial KPI Cards**: Instant visibility into Total Spent, Transaction Count, and Top Category.
- **Time Range Filtering**: Switch seamlessly between All Time, This Month (`1m`), Last 3 Months (`3m`), Last 6 Months (`6m`), or a custom date range.
- **Visual Category Breakdown**: Proportional spending distribution bars styled with dynamic category colors.
- **Recent Transactions & Quick Actions**: View recent activity and access direct shortcuts across the application.

### 💸 Expense Management (CRUD)
- **Full CRUD Support**: Add, view, edit, and delete expenses with amount, category, date, description/notes, and payment method.
- **Payment Methods**: Tag expenses by payment channel — **UPI**, **Card**, **Cash**, **Bank**, or **Wallet**.
- **Visual Category Badges**: Distinct, accessible color tags and icons for instant scanning.
- **Activity Logging**: Automated audit trail logging of all expense actions (`added`, `edited`, `deleted`) to the `activities` table.

### 🔄 Transactions Ledger
- **Five Summary Metric Cards**: Real-time aggregation of Total Transactions, Total Amount, Highest Expense, Average Expense, and Last Transaction date dynamically recalculated based on active filters.
- **Multi-Criteria Filter Bar**: Real-time search query matching descriptions/categories, category selector, date range, amount range, and multi-field sorting (`date-desc`, `date-asc`, `amount-desc`, `amount-asc`, `category-asc`).
- **Bulk Operations**: Multi-row selection with "select all on page" and secure bulk deletion.
- **Server-Side Pagination**: Efficient pagination (8 items per page) with query-parameter preservation.
- **Transaction Details Modal**: Quick-view popup displaying full transaction metadata and timestamps.
- **Recent Activity Sidebar**: Live feed of recent modifications across the user's ledger.
- **Filtered CSV Export**: Download filtered or selected transactions directly as CSV (`/transactions/export`).

### 🗂️ Categories Module
- **Category Summary Cards**: Total Categories, Most Used Category, Highest Spending Category, and Unused Categories count.
- **Rich Data Table**: Icon, color badge, name, description, transaction count, total spent, average expense, created date, and action triggers.
- **Interactive Visualizations**: Donut chart displaying spending distribution and top-categories ranking bars.
- **Custom Category Builder**: Add and edit custom categories with a choice of 22 Lucide icons and 15 preset color themes.
- **Protected Deletion**: Safe deletion workflow that warns if a category is in use and seamlessly reassigns existing expenses to "Other".
- **Category Merge**: Transfer all expenses from a source category to a target category in one action.
- **Dedicated Category Analytics**: Deep-dive analytics page (`/categories/analytics`) with distribution breakdown and usage metrics.
- **Category Export**: Export all category statistics and metadata to CSV (`/categories/export`).

### 🎯 Budgets Module
- **Monthly Budget Limits**: Set and customize monthly spending caps per category stored in the `budgets` table with intelligent defaults.
- **Budget Health Tracking**: Real-time status badges categorized as **On Track** (<80%), **Warning** (80–100%), and **Over Budget** (>100%).
- **Budget vs Actual Visualizations**: Side-by-side comparison charts and spending distribution donut charts.
- **6-Month Historical Trends**: Analyze spending trajectory against budget allocations over a 6-month window.
- **Reset & Export**: Reset budgets to system defaults (`/budgets/reset`) or export budget performance to CSV (`/budgets/export`).

### 🏆 Goals Module
- **Savings Goals**: Create structured financial targets with name, category, target amount, saved amount, and target deadline.
- **Goal Status Engine**: Dynamic status tracking (**On Track**, **At Risk**, **Completed**, **Paused**) based on target pacing and elapsed time.
- **Quick Fund Allocations**: Add savings with one-click quick increment buttons (+₹500, +₹1,000, +₹5,000) or custom amounts.
- **Pacing & Milestone Indicators**: Track required daily/monthly savings rate to hit targets on schedule.
- **Goal Export**: Export all active and archived goals to CSV (`/goals/export`).

### 📈 Reports & Analytics
- **Financial Summary Metrics**: Total Spending, Total Transactions, Average Daily Spend, Highest Spending Day, Net Savings/Balance indicator, and Top Category.
- **Interactive Visualizations**: Powered by Chart.js and CSS charts:
  - Monthly spending trend line & bar chart
  - Category spending distribution donut chart
  - Payment method distribution chart (UPI, Card, Cash, Bank, Wallet)
- **Detailed Data Tables**: Top 10 largest expenses and monthly financial breakdown.
- **Personalized Financial Insights**: Context-aware recommendations generated dynamically from user spending patterns.
- **Export & Print**: Native browser print/PDF styling and spreadsheet-compatible data summaries.

### ⚙️ Settings Module
- **Profile Configuration**: Manage display name, email, phone number, bio, and visual avatar initials.
- **Regional & Preferences**: Customize Currency (INR ₹, USD $, EUR €, GBP £, JPY ¥, CAD $, AUD $), Date Format (`DD-MM-YYYY`, `YYYY-MM-DD`, `MM/DD/YYYY`), Language (`en`, `hi`, `es`, `fr`, `de`), Week Start day, and Budget Alert Threshold (50%–100%).
- **Security & Active Sessions**: Toggle Two-Factor Authentication and Login Alerts, view all active devices with IP/browser details, and revoke individual sessions remotely.
- **Notification Toggles**: Granular email preference toggles for budget alerts, expense reminders, goal milestones, and weekly digests.
- **Appearance & Personalization**: Light, Dark, or System theme switcher, Accent Color picker (Emerald Green, Ocean Blue, Royal Violet, Amber Gold, Rose Red, Electric Cyan), and Interface Density (Comfortable vs Compact).
- **Data & Privacy Controls**: Toggle personalized insights and anonymous telemetry, export complete financial data as a unified CSV, clear all ledger records, or permanently delete the user account.

### 💡 Help & Support Center
- **Knowledge Base & FAQ Search**: Instant keyboard shortcut (`/` to focus) with live search and filter matching.
- **Topic Filter Chips**: Filter by topic — Getting Started, Expenses, Budgets, Goals, Reports, Settings, Security, Data & Privacy, or Other.
- **Interactive FAQ Accordion**: Expandable Q&A items answering common operational and security questions.
- **Live System Status**: Real-time status checks for core services (API & Data Sync, Reports & Exports, Support & Notifications).
- **Support Ticket Submission**: In-app ticket submission modal with subject, category, priority (`low`, `normal`, `high`, `urgent`), and message body, creating trackable records in `support_tickets`.
- **Direct Resource Links**: Direct navigation to [Privacy Policy](/privacy), [Terms & Conditions](/terms), Reports, and Budgets.

### ⚖️ Legal Pages
- Dedicated, beautifully styled [Terms & Conditions](/terms) and [Privacy Policy](/privacy) pages accessible from the footer, help center, and legal links.

---

## 🛠️ Tech Stack

| Layer | Technology | Details |
|---|---|---|
| **Backend Framework** | [Flask](https://flask.palletsprojects.com/) | Version `3.1.3` — clean single-file routing in `app.py` |
| **Database** | SQLite | Raw `sqlite3` with foreign keys enabled (`PRAGMA foreign_keys = ON`) |
| **Template Engine** | Jinja2 | Modular templating extending `base.html` |
| **Frontend** | Vanilla HTML5 / CSS3 / JavaScript | Modern CSS variables, responsive flex/grid layouts, no npm or frontend frameworks |
| **Icons** | [Lucide Icons](https://lucide.dev/) | Loaded via CDN (`unpkg.com/lucide@latest`) |
| **Charts** | [Chart.js](https://www.chartjs.org/) & CSS Conic Gradients | Dynamic visual charts on Reports and Categories |
| **Typography** | Google Fonts | DM Serif Display + DM Sans |
| **Authentication & Crypto** | `werkzeug.security` & [Authlib](https://authlib.org/) | Secure password hashing, OAuth 2.0 OpenID Connect |
| **Configuration** | `python-dotenv` | Loads environment variables from `.env` |
| **Testing Suite** | [pytest](https://pytest.org/) & `pytest-flask` | 7 test suites, **294 passing tests** |
| **Production WSGI** | [Gunicorn](https://gunicorn.org/) | Version `23.0.0` |

---

## 📁 Project Structure

```
spendly/
├── app.py                     # All routes, middleware, session checks, and context processors
├── requirements.txt           # Python dependencies (Flask, authlib, pytest, etc.)
├── README.MD                  # Project documentation & overview
├── PROJECT_DOCUMENTATION.md   # Comprehensive code-level architectural reference
├── CLAUDE.md                  # Project maintenance instructions & conventions
├── .env                       # Environment variables (SECRET_KEY, GOOGLE OAuth credentials)
├── database/
│   ├── __init__.py
│   └── db.py                  # Database schema, migrations, queries, and seed logic
├── templates/
│   ├── base.html              # Core app shell layout, navigation sidebar, and footer
│   ├── landing.html           # Public landing / marketing page
│   ├── login.html             # User login page (Email + Google OAuth)
│   ├── register.html          # User registration with security questions
│   ├── forgot_password.html   # Password reset request step
│   ├── reset_password.html    # Security question answer & new password step
│   ├── profile.html           # Dashboard with summary stats, category bars, and recent txns
│   ├── profile_edit.html      # Edit user profile and change password
│   ├── transactions.html      # Transactions ledger, filter bar, bulk selection, view modal
│   ├── budgets.html           # Budgets dashboard, monthly limits, and trend visualizations
│   ├── goals.html             # Savings goals tracker, add funds modal, and progress bars
│   ├── reports.html           # Comprehensive reporting, charts, insights, and data tables
│   ├── settings.html          # User settings (Preferences, Security, Sessions, Appearance, Data)
│   ├── help.html              # Help & support center, knowledge base, FAQs, and ticket modal
│   ├── privacy.html           # Privacy Policy page
│   ├── terms.html             # Terms & Conditions page
│   ├── expenses/
│   │   ├── list.html          # Simple expense list view
│   │   ├── form.html          # Add / Edit expense form
│   │   └── delete.html        # Expense deletion confirmation
│   └── categories/
│       ├── list.html          # Categories management dashboard
│       ├── form.html          # Add / Edit category form (with icon & color pickers)
│       ├── view.html          # Single category detail page
│       ├── delete.html        # Category deletion confirmation (with usage protection)
│       ├── merge.html         # Category merge form
│       └── analytics.html     # Dedicated category analytics page
├── static/
│   ├── css/
│   │   ├── style.css          # Core design system, CSS variables, app shell, themes
│   │   ├── landing.css        # Public landing page styling
│   │   ├── profile.css        # Dashboard & profile styling
│   │   ├── expenses.css       # Expense CRUD styling
│   │   ├── transactions.css   # Transactions ledger & modal styling
│   │   ├── categories.css     # Categories dashboard & analytics styling
│   │   ├── budgets.css        # Budgets module styling
│   │   ├── goals.css          # Goals module styling
│   │   ├── reports.css        # Reports & analytics styling
│   │   ├── settings.css       # Settings tabs & form styling
│   │   ├── help.css           # Help center, FAQs, status, and modal styling
│   │   └── controls.css       # Reusable UI controls and component utilities
│   └── js/
│       ├── main.js            # App shell interactions, theme switching, drawer navigation
│       ├── transactions.js    # Transactions ledger UX, bulk actions, detail modal
│       ├── categories.js      # Category pickers, search auto-submit, deletion confirm
│       ├── budgets.js         # Budgets UX, limit editing, modal management
│       ├── goals.js           # Goals UX, add funds calculator, progress interactions
│       ├── reports.js         # Reports Chart.js initialization & filter interactions
│       ├── settings.js        # Settings tab switching, session revocation, theme preview
│       └── help.js            # Help search filter, FAQ accordions, ticket submission
└── tests/
    ├── __init__.py
    ├── conftest.py            # Pytest fixtures and isolated temporary database setup
    ├── test_backend_connection.py  # Core DB helpers, schema validation, profile routes
    ├── test_transactions.py        # Transactions filtering, sorting, pagination, bulk delete
    ├── test_categories.py          # Category CRUD, stats, merge, protected deletion, analytics
    ├── test_budgets.py             # Budgets CRUD, calculations, month filters, trend charts
    ├── test_goals.py               # Goals CRUD, status calculation, add funds, deadlines
    ├── test_reports.py             # Reports calculations, summary statistics, chart data
    ├── test_settings.py            # Settings persistence, sessions, appearance, privacy, deletion
    └── test_help.py                # Help center rendering, FAQs, ticket creation & isolation
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- `pip` package manager

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sonusuman147/spendly.git
   cd spendly
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**:
   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secure-secret-key
   # Optional: Google OAuth Credentials (for "Continue with Google")
   GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   ```

5. **Start the application**:
   ```bash
   python app.py
   ```
   The application will start at **http://127.0.0.1:5001** (or `$PORT`).

The database (`expense_tracker.db`) is automatically initialized and seeded on first run with a demo user, 8 sample expenses across categories with payment methods, matching activity logs, 7 default categories, default support articles, and FAQs.

**Default Demo Credentials:**
- **Email:** `demo@spendly.com`
- **Password:** `demo123`
- **Security Answer:** `fido` (Question: *What is your pet's name?*)

---

## 🧪 Testing

The test suite runs against an isolated, temporary SQLite database and verifies all backend functionality, database functions, security constraints, and UI route responses.

```bash
# Run all tests (294 tests across 7 suites)
pytest

# Run tests with verbose output
pytest -v

# Run a specific test suite
pytest tests/test_help.py -v
pytest tests/test_settings.py -v
pytest tests/test_budgets.py -v
pytest tests/test_goals.py -v
pytest tests/test_categories.py -v
pytest tests/test_transactions.py -v

# Run with keyword filter
pytest -k "test_sessions"
```

---

## 🗺️ Application Routes

### Public & Authentication Routes
| Route | Method | Description |
|---|---|---|
| `/` | GET | Public landing page |
| `/register` | GET, POST | User registration with security questions |
| `/login` | GET, POST | User sign-in with email & password |
| `/login/google` | GET | Initiate Google OAuth 2.0 flow |
| `/login/google/callback` | GET | Google OAuth callback handler |
| `/forgot-password` | GET, POST | Step 1: Submit email to locate account |
| `/forgot-password/reset` | GET, POST | Step 2: Answer security question and set new password |
| `/logout` | GET | Terminate user session and redirect to landing |

### Dashboard & Profile
| Route | Method | Description |
|---|---|---|
| `/profile` | GET | Main dashboard with financial summary, category bars, and recent txns |
| `/profile/edit` | GET, POST | Edit name, email, phone, bio, and change password |
| `/profile/update` | POST | Update user profile fields |
| `/profile/change-password` | POST | Change password with current password verification |

### Expenses (CRUD)
| Route | Method | Description |
|---|---|---|
| `/expenses` | GET | List all user expenses |
| `/expenses/add` | GET, POST | Create a new expense with payment method |
| `/expenses/<id>/edit` | GET, POST | Edit an existing expense |
| `/expenses/<id>/delete` | GET, POST | Delete an expense (records activity log) |

### Transactions Ledger
| Route | Method | Description |
|---|---|---|
| `/transactions` | GET | Filterable, sortable, paginated transaction ledger |
| `/transactions/export` | GET | Download filtered or selected transactions as CSV |
| `/transactions/bulk-delete` | POST | Bulk delete selected transactions |

### Categories
| Route | Method | Description |
|---|---|---|
| `/categories` | GET | Categories dashboard with summary cards and data table |
| `/categories/add` | GET, POST | Create a new custom category with icon and color |
| `/categories/<id>` | GET | View details and statistics for a single category |
| `/categories/<id>/edit` | GET, POST | Edit category name, description, icon, or color |
| `/categories/<id>/delete` | GET, POST | Delete category (protected when associated expenses exist) |
| `/categories/merge` | GET, POST | Merge all expenses from source category into target category |
| `/categories/export` | GET | Export all categories and usage metrics as CSV |
| `/categories/analytics` | GET | Dedicated category spending distribution and analytics |

### Budgets
| Route | Method | Description |
|---|---|---|
| `/budgets` | GET | Budgets dashboard, category limit cards, and trend charts |
| `/budgets/add` | POST | Add or set a category monthly budget limit |
| `/budgets/<id>/edit` | POST | Update an existing category budget limit |
| `/budgets/<id>/delete` | POST | Remove a custom budget override |
| `/budgets/reset` | POST | Reset all category budgets to default values |
| `/budgets/export` | GET | Export budget status and actuals to CSV |

### Goals
| Route | Method | Description |
|---|---|---|
| `/goals` | GET | Goals dashboard, savings targets, and progress indicators |
| `/goals/add` | POST | Create a new savings goal |
| `/goals/<id>/edit` | POST | Update target amount, deadline, or goal details |
| `/goals/<id>/delete` | POST | Delete a savings goal |
| `/goals/<id>/funds` | POST | Add funds to a savings goal |
| `/goals/export` | GET | Export all savings goals to CSV |

### Reports & Analytics
| Route | Method | Description |
|---|---|---|
| `/reports` | GET | Comprehensive reporting dashboard with charts and insights |

### Settings & User Preferences
| Route | Method | Description |
|---|---|---|
| `/settings` | GET | Settings center (Preferences, Security, Sessions, Appearance, Data) |
| `/settings/save` | POST | Save profile, preferences, and notification toggles |
| `/settings/theme` | POST | Update theme and accent color preference |
| `/settings/sessions/revoke` | POST | Remotely revoke a specific active device session |
| `/settings/change-password` | POST | Change account password |
| `/settings/reset` | POST | Reset user settings to defaults |
| `/settings/export` | GET | Download complete financial data backup as a structured CSV |
| `/settings/clear-data` | POST | Wipe all expenses, budgets, goals, and categories for user |
| `/settings/delete-account` | POST | Permanently delete user account and all associated data |

### Help & Support
| Route | Method | Description |
|---|---|---|
| `/help` | GET | Help center, searchable knowledge base, FAQs, and system status |
| `/help/tickets` | POST | Submit a new support ticket |

### Legal Pages
| Route | Method | Description |
|---|---|---|
| `/terms` | GET | Terms & Conditions |
| `/privacy` | GET | Privacy Policy |

---

## 🗄️ Database Schema

The database consists of **12 structured tables** in SQLite:

1. **`users`**: User identity, hashed credentials, Google ID, security question/hash, phone, bio, and timestamps.
2. **`expenses`**: Financial transactions linked to users with amount, category, date, description, payment method, and creation timestamp.
3. **`activities`**: Automated audit trail logging all expense modifications (`added`, `edited`, `deleted`).
4. **`categories`**: Per-user custom categories with name, description, Lucide icon name, color hex code (`UNIQUE(user_id, name)`).
5. **`budgets`**: Monthly category budget limits per user (`UNIQUE(user_id, category)`).
6. **`goals`**: Savings goals with target amount, saved amount, deadline, category, and status.
7. **`user_sessions`**: Server-side active session tracker storing unique session tokens, client IP, user-agent, and revocation flags (`revoked`).
8. **`user_settings`**: Per-user preferences for currency, date format, language, week start, alert thresholds, theme, accent color, density, notification flags, and privacy toggles (`UNIQUE(user_id)`).
9. **`support_tickets`**: User-submitted support tickets with unique ticket numbers (`SP-XXXXX`), subject, topic, priority, message, and status.
10. **`ticket_messages`**: Message history associated with support tickets.
11. **`support_articles`**: Knowledge base articles seeded by topic with ordering and public visibility flags.
12. **`support_faqs`**: Frequently asked questions grouped by topic with answers.

---

## 🔒 Security Architecture

- **Password Protection**: Passwords are never stored in plain text; hashed with Werkzeug (`scrypt`/`pbkdf2`).
- **Security Question Validation**: Security answers are lowercased, stripped, and cryptographically verified against stored hashes.
- **SQL Injection Prevention**: 100% of database interactions use parameterized SQL statements (`?` placeholders).
- **Foreign Key Integrity**: `PRAGMA foreign_keys = ON` is enforced on every database connection.
- **Session Token Verification**: Signed cookie tokens are checked against the `user_sessions` table on every request; revoked sessions are immediately invalidated.
- **Insecure Direct Object Reference (IDOR) Protection**: Every database query and modification enforces user ownership (`WHERE user_id = ?`).
- **Protected Category Deletion**: Prevents orphan transactions by enforcing reclassification to "Other" before deleting categories in active use.

---

## 📄 License

This project is licensed under the MIT License. Feel free to use, modify, and distribute for personal and commercial projects.
