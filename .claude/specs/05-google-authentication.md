# Spec: Google Authentication

## Overview
Add "Sign in with Google" as an alternative authentication method. Users who already have a Spendly account with the same email address will be linked; new users will have an account created automatically. This reduces friction for new sign-ups and provides a familiar, one-click login flow alongside the existing email/password method.

## Depends on
- Step 02 — Registration (user table exists, `create_user()` helper exists)
- Step 03 — Login and Logout (session management pattern established)

## Routes
- `GET /login/google` — redirect to Google's OAuth consent screen — public
- `GET /login/google/callback` — handle the OAuth callback from Google, create/link user, start session — public

## Database changes
Add a `google_id TEXT` column to the `users` table to store Google's stable user ID for linking accounts.

**Migration SQL**:
```sql
ALTER TABLE users ADD COLUMN google_id TEXT;
```

SQLite does not allow adding a `UNIQUE` constraint via `ALTER TABLE ... ADD COLUMN`, so uniqueness is **not** enforced at the schema level. Instead, application code must check whether a `google_id` already exists before inserting or updating (see `get_user_by_google_id()` below). This must be wrapped in `init_db()` with a simple try/except around the `ALTER TABLE` call to handle the case where the column already exists.

## Templates
- **Modify:** `templates/login.html` — add a "Sign in with Google" button above the email/password form

## Files to change
- `database/db.py` — add `google_id` column to `init_db()`; add `get_user_by_google_id(google_id)` helper; add `link_google_account(user_id, google_id)` helper; extend `create_user()` to accept optional `password_hash` and `google_id` arguments
- `app.py` — add `/login/google` and `/login/google/callback` routes; add OAuth config to `app.config`
- `templates/login.html` — add Google sign-in button
- `requirements.txt` — add `authlib` dependency

## Files to create
No new files.

## New dependencies
- **authlib** (`>=1.3.0`) — Flask-compatible OAuth client library. Provides the `OAuth` class used to register Google as an OAuth provider and handle the token exchange / userinfo fetch.

**Important:** This conflicts with CLAUDE.md's "No new pip packages" rule. This feature **requires** `authlib` because manually implementing OAuth 2.0 (PKCE, token exchange, ID token verification) would be error-prone and a security risk. The existing `requirements.txt` only has `flask`, `werkzeug`, `pytest`, and `pytest-flask`.

## Account creation and linking

Instead of a separate `create_google_user()` helper, reuse the existing `create_user()` from Step 02 by making `password_hash` and `google_id` optional parameters:

```python
create_user(
    name,
    email,
    password_hash=None,
    google_id=None
)
```

For a new user signing in via Google, call it with `password_hash=None` (or `""`, whichever `create_user()` already expects for the password column) and `google_id` set to Google's `sub` claim. This avoids duplicating insertion logic between the two auth methods.

For an existing email/password user who later signs in with Google, add a dedicated update helper rather than duplicating SQL inline:

```python
link_google_account(user_id, google_id)
```

### OAuth callback flow
```
User clicks "Continue with Google"
            │
            ▼
GET /login/google
            │
            ▼
Google OAuth Consent Screen
            │
            ▼
GET /login/google/callback
            │
            ▼
Read user info
            │
            ▼
Find by google_id?
      │             │
     Yes            No
      │              │
      ▼              ▼
 Login        Find by email?
                    │
           ┌────────┴────────┐
           │                 │
         Yes                No
           │                 │
 Link google_id      Create user
   (link_google_account)  (create_user)
           │                 │
           └────────┬────────┘
                    ▼
          session["user_id"] = user["id"]
                    ▼
        redirect(url_for("landing"))
```

## Profile picture
Google's userinfo response includes `name`, `email`, `picture`, `sub`, and `email_verified`. `picture` is not stored for now — out of scope for this step, can be added later if avatars are introduced.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (email/password flow only — Google-created accounts have no password)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- OAuth client ID and secret must be loaded from environment variables (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`), never hardcoded
- Use `os.getenv()` with sensible defaults for development
- The Google OAuth redirect URI must be generated dynamically with `url_for("google_callback", _external=True)` — do not hardcode a host/port, so this works in any environment
- Store Google's `sub` claim as `google_id` in the users table
- Never store access tokens in the session — only the user ID
- Session must be populated identically to the existing email/password login in Step 03 (currently `session["user_id"]` only — confirm against Step 03 before implementing, and do not introduce a second field like `user_name` unless Step 03 already sets one). Google and email/password logins must leave the session in the same shape.

## Definition of done
- [ ] `pip install authlib` and add to `requirements.txt`
- [ ] `database/db.py` `init_db()` adds `google_id TEXT` column (no `UNIQUE` constraint; graceful if column already exists)
- [ ] `database/db.py` exports `get_user_by_google_id(google_id)` helper
- [ ] `database/db.py` exports `link_google_account(user_id, google_id)` helper
- [ ] `database/db.py` `create_user()` extended with optional `password_hash` and `google_id` parameters (no separate `create_google_user()`)
- [ ] `app.py` configures Authlib `OAuth` with Google provider
- [ ] Visiting `/login/google` redirects to Google's consent screen
- [ ] After Google consent, callback at `/login/google/callback` creates a new user or links `google_id` to an existing email match, checking for an existing `google_id` before insert/update to preserve uniqueness at the application level
- [ ] Session is populated the same way as the existing email/password login (see Rules above)
- [ ] Successful Google login redirects to `url_for("landing")`
- [ ] Google callback redirect URI is generated via `url_for("google_callback", _external=True)`, not hardcoded
- [ ] Login page shows a "Sign in with Google" button with a Google-branded style
- [ ] App runs on port 5001 without errors