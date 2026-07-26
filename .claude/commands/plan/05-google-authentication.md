# Implementation Plan: Google Authentication

Add "Sign in with Google" as an alternative authentication method to Spendly, allowing users to authenticate via Google OAuth 2.0 with Authlib, reusing the existing user model and session pattern.

## Overview

This feature adds OAuth 2.0 authentication via Google alongside the existing email/password flow. The implementation uses Authlib's Flask integration (`authlib.integrations.flask_client.OAuth`) to handle the OAuth dance securely. Google's `sub` claim is stored as `google_id` in the `users` table for account linking. New Google users are created via the existing `create_user()` helper with an optional `google_id` param. Existing email/password users who sign in with Google get their `google_id` linked via a new `link_google_account()` helper. Session shape remains identical (`session["user_id"]`, `session["user_name"]`) to the existing login flow. The Google button on the login page follows the existing CSS variable system.

**Scope:**
- 4 files modified: `database/db.py`, `app.py`, `templates/login.html`, `requirements.txt`
- 1 file modified: `static/css/style.css`
- 0 new files created
- 1 new dependency: `authlib>=1.3.0`

## Files

All changes are to existing files — no new files are created.

### 1. `database/db.py` — Schema migration and new helpers

**Current state:** `init_db()` creates `users` table with `(id, name, email, password_hash, created_at)`. `create_user()` hashes password internally.

**Changes:**

#### 1a. `init_db()` — Add `google_id` column migration
Add at the end of `init_db()`, after the table creation statements:
```python
try:
    cursor.execute("ALTER TABLE users ADD COLUMN google_id TEXT")
except sqlite3.OperationalError:
    pass  # Column already exists — safe on subsequent runs
```

#### 1b. `create_user()` — Refactor signature
Change from:
```python
def create_user(name, email, password):
    password_hash = generate_password_hash(password)
    ...
    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)"
```
To:
```python
def create_user(name, email, password_hash=None, google_id=None):
    if password_hash is None:
        password_hash = ""  # Google users have no password
    ...
    "INSERT INTO users (name, email, password_hash, google_id) VALUES (?, ?, ?, ?)"
```
- `password_hash` param replaces `password` — caller decides whether to hash
- `google_id` param is optional, defaults to `None`
- Remove the internal `generate_password_hash()` call — callers pass pre-hashed value
- INSERT includes all 4 columns

**Impact:** `seed_db()` calls `create_user("Demo User", "demo@spendly.com", password)` — must change to pass `password_hash=generate_password_hash("demo123")`.

#### 1c. `seed_db()` — Adapt to new signature
Change:
```python
password_hash = generate_password_hash("demo123")
cursor.execute("INSERT INTO users ...", ("Demo User", "demo@spendly.com", password_hash))
```
To use the refactored `create_user()`:
```python
from werkzeug.security import generate_password_hash
create_user("Demo User", "demo@spendly.com", password_hash=generate_password_hash("demo123"))
```
(This import already exists at the top of the file.)

#### 1d. New helper: `get_user_by_google_id(google_id)`
```python
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
```
Add after `get_user_by_email()`.

#### 1e. New helper: `link_google_account(user_id, google_id)`
```python
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
```
Add after `get_user_by_google_id()`.

### 2. `app.py` — OAuth config and routes

**Current state:** Imports Flask utilities and db helpers. Has standard login/register/logout routes.

**Changes:**

#### 2a. Add imports
```python
import os
from authlib.integrations.flask_client import OAuth
```
Also add new db helper imports:
```python
from database.db import get_db, init_db, seed_db, get_user_by_email, create_user, get_user_by_id, get_user_expenses_summary, get_user_by_google_id, link_google_account
```

#### 2b. Configure OAuth after `app = Flask(__name__)`
```python
oauth = OAuth(app)

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)
```

#### 2c. New route: `GET /login/google` (alias: `google_login`)
```python
@app.route("/login/google")
def google_login():
    """Redirect to Google's OAuth consent screen."""
    redirect_uri = url_for("google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)
```
Add after the `login()` route. Place before the placeholder routes section.

#### 2d. New route: `GET /login/google/callback` (alias: `google_callback`)
```python
@app.route("/login/google/callback")
def google_callback():
    """Handle the OAuth callback from Google.
    
    Creates a new user or links google_id to an existing account,
    then starts a session identical to email/password login.
    """
    try:
        token = oauth.google.authorize_access_token()
    except Exception:
        flash("Google sign-in failed. Please try again.", "error")
        return redirect(url_for("login"))
    
    # Parse ID token for user info
    userinfo = oauth.google.parse_id_token(token)
    
    # Verify email is verified — security requirement
    if not userinfo.get("email_verified"):
        flash("Please use a Google account with a verified email address.", "error")
        return redirect(url_for("login"))
    
    google_id = userinfo["sub"]
    email = userinfo["email"]
    name = userinfo.get("name", email.split("@")[0])
    
    # Check if google_id already exists
    user = get_user_by_google_id(google_id)
    if user:
        # Existing Google user — login
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        flash("Welcome back!", "success")
        return redirect(url_for("landing"))
    
    # No existing google_id — check by email
    user = get_user_by_email(email)
    if user:
        # Existing email/password user — link google_id
        try:
            link_google_account(user["id"], google_id)
        except ValueError:
            flash("This Google account is already linked to another user.", "error")
            return redirect(url_for("login"))
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        flash("Google account linked! Welcome back.", "success")
        return redirect(url_for("landing"))
    
    # New user — create account via existing helper
    try:
        user_id = create_user(name, email, google_id=google_id)
    except sqlite3.IntegrityError:
        flash("An account with this email already exists. Please sign in.", "error")
        return redirect(url_for("login"))
    
    session["user_id"] = user_id
    session["user_name"] = name
    flash("Account created! Welcome to Spendly.", "success")
    return redirect(url_for("landing"))
```
Add after `google_login()`.

### 3. `templates/login.html` — Google sign-in button

**Current state:** Has email/password form with flash messages.

**Changes:**

Add a Google sign-in button above the `<form>` element, inside `.auth-card`, with a divider:

```html
<!-- After the flash messages block, before the <form> tag -->
<a href="{{ url_for('google_login') }}" class="btn-google">
    <svg class="google-icon" viewBox="0 0 24 24" width="20" height="20">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
    Continue with Google
</a>

<div class="divider"><span>or</span></div>
```

Update the `.auth-card` structure:
```
.auth-card
  └── flash messages (existing)
  └── btn-google (NEW)
  └── divider (NEW)
  └── form (existing)
```

**Note:** The Google button uses an inline SVG for the Google logo to avoid external dependencies. The `btn-google` and `divider` classes are defined in `style.css`.

### 4. `static/css/style.css` — Google button and divider styles

**Current state:** Has all auth page styles, button styles (`.btn-primary`, `.btn-ghost`, `.btn-submit`).

**Changes:**

Add after the `.btn-submit` styles (before `.auth-switch`):

```css
/* ------------------------------------------------------------------ */
/* Google Sign-in Button                                               */
/* ------------------------------------------------------------------ */

.btn-google {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.625rem;
    padding: 0.65rem 1rem;
    background: var(--paper-card);
    color: var(--ink-soft);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-family: var(--font-body);
    font-size: 0.9rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
    margin-bottom: 0;
}

.btn-google:hover {
    background: var(--paper-warm);
    border-color: var(--ink-faint);
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}

.google-icon {
    flex-shrink: 0;
}

.divider {
    display: flex;
    align-items: center;
    margin: 1.25rem 0;
    color: var(--ink-faint);
    font-size: 0.8rem;
    gap: 0.75rem;
}

.divider::before,
.divider::after {
    content: "";
    flex: 1;
    height: 1px;
    background: var(--border-soft);
}

.divider span {
    white-space: nowrap;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
```

### 5. `requirements.txt` — Add authlib

**Current state:**
```
flask==3.1.3
werkzeug==3.1.6
pytest==8.3.5
pytest-flask==1.3.0
```

**Change:** Add `authlib>=1.3.0` on a new line.

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `authlib` | `>=1.3.0` | Flask-compatible OAuth client for Google's OpenID Connect flow |

**Note:** This explicitly overrides CLAUDE.md's "No new pip packages" rule as stated in the spec.

## Testing

No existing tests directory exists. After implementation:

1. **Manual test:** Start server with `python app.py`, verify it runs on port 5001 without errors.
2. **Manual test:** Verify `/login/google` redirects to Google's consent screen (requires valid `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` env vars).
3. **Manual test:** Verify `/login/google/callback` handles success path (creates user, sets session, redirects to landing).
4. **Manual test:** Verify flash error messages for failure cases (unverified email, duplicate google_id, etc.).
5. **Smoke test:** Verify existing email/password login still works unchanged.

## Implementation Order

| Step | File | Description |
|------|------|-------------|
| 1 | `requirements.txt` | Add `authlib>=1.3.0` |
| 2 | `database/db.py` | Refactor `create_user()` to accept optional `password_hash`, `google_id` |
| 3 | `database/db.py` | Update `seed_db()` to use new `create_user()` signature with keyword args |
| 4 | `database/db.py` | Add `google_id` column migration in `init_db()` with try/except |
| 5 | `database/db.py` | Add `get_user_by_google_id()` helper |
| 6 | `database/db.py` | Add `link_google_account()` helper with application-level uniqueness check |
| 7 | `app.py` | Add `import os` and `from authlib.integrations.flask_client import OAuth` |
| 8 | `app.py` | Add new db helper imports |
| 9 | `app.py` | Configure OAuth with Google provider (env vars for client ID/secret) |
| 10 | `app.py` | Add `GET /login/google` route (alias: `google_login`) |
| 11 | `app.py` | Add `GET /login/google/callback` route (alias: `google_callback`) with full decision tree |
| 12 | `templates/login.html` | Add Google sign-in button and divider inside `.auth-card` |
| 13 | `static/css/style.css` | Add `.btn-google` and `.divider` styles |
| 14 | Terminal | Run `pip install authlib` |
| 15 | Terminal | Run `python app.py` to verify no errors |

