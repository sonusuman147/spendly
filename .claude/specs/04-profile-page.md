# Spec: Profile Page — Edit Profile, Security Questions & Forgot Password

## Overview
Extend the existing profile page with authenticated editing capabilities, add a security question step to the registration flow, and implement a complete forgot-password recovery flow. Users can update their name and email, change their password (requiring current password verification), set a security question during registration, and recover access via that security question if they forget their password.

## Depends on
- Step 1: Database setup (`users` table must exist)
- Step 2: Registration (`create_user()` helper exists)
- Step 3: Login / Logout (`session["user_id"]` set on login, `check_password_hash` used)
- Step 4a: Profile page basic UI (template, route, CSS exist)

## Routes

| Method | Path | Description | Access |
|--------|------|-------------|--------|
| GET | `/profile` | View profile page (existing) | Logged-in only |
| POST | `/profile/update` | Update name and email | Logged-in only |
| POST | `/profile/change-password` | Change password (requires current password) | Logged-in only |
| GET | `/forgot-password` | Show forgot password form (enter email) | Public |
| POST | `/forgot-password` | Submit email, show security question | Public |
| GET | `/forgot-password/reset` | Show reset password form (with token/session) | Public |
| POST | `/forgot-password/reset` | Verify answer and set new password | Public |

## Database changes

### 1. Add columns to `users` table
Add two new columns via `ALTER TABLE` in `init_db()` (safe to run multiple times):

```sql
ALTER TABLE users ADD COLUMN security_question TEXT;
ALTER TABLE users ADD COLUMN security_answer_hash TEXT;
```

- `security_question`: Stores the question text the user selected (e.g. "What is your pet's name?")
- `security_answer_hash`: Stores the werkzeug-generated hash of the user's answer

### 2. Security questions constant
Add to `database/db.py`:

```python
SECURITY_QUESTIONS = [
    "What is your father's middle name?",
    "What is your best friend's name?",
    "What village were you born in?",
    "What is your pet's name?",
    "What was the name of your first school?",
]
```

## Templates

- **Modify:** `templates/register.html` — Add a security question dropdown and answer field to the registration form
- **Modify:** `templates/profile.html` — Add inline-edit sections for name/email (expandable fields) and a change-password form
- **Create:** `templates/forgot_password.html` — Forgot password flow with email entry, security question display, and answer submission
- **Create:** `templates/reset_password.html` — New password form after successful security question verification

## Files to change

- `database/db.py` — Add `SECURITY_QUESTIONS` constant, add security question columns migration, add `update_user_profile()`, `update_password()`, `get_user_by_email_with_security()`, `get_user_by_email_for_reset()` helpers
- `app.py` — Add imports for new helpers, add `/profile/update`, `/profile/change-password`, `/forgot-password`, `/forgot-password/reset` routes
- `templates/register.html` — Add security question dropdown + answer field
- `templates/profile.html` — Add edit profile section and change password form
- `templates/login.html` — Add "Forgot Password?" link below the sign-in form
- `static/css/profile.css` — Add styles for edit forms, change password section
- `static/css/style.css` — Add global styles for forgot-password page (or link a new CSS file)

## Files to create

- `templates/forgot_password.html` — Forgot password flow template
- `templates/reset_password.html` — Reset password template

## New dependencies
No new dependencies. Uses existing `werkzeug` for password/answer hashing.

## Rules for implementation
- No SQLAlchemy or ORMs — parameterised SQL queries only
- Passwords and security answers both hashed with `werkzeug.security.generate_password_hash`
- Answer verification uses `werkzeug.security.check_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- No inline styles
- Answer normalization before hash comparison: trim whitespace, lowercase
- Security question display must not reveal whether the account exists (generic error for both "email not found" and "wrong answer")
- Parameterised queries only — never string-format values into SQL
- `get_db()` must run `PRAGMA foreign_keys = ON` on every connection (already done)
- Current password must be verified before allowing password change
- New password must be at least 8 characters
- Session-based approach for forgot-password flow: store `reset_user_id` in session temporarily

## Definition of done

### Profile Editing
- [ ] Logged-in user can update their full name via the profile page
- [ ] Logged-in user can update their email address via the profile page
- [ ] Email uniqueness is enforced — duplicate email shows an error
- [ ] Logged-in user can change their password by entering current + new password
- [ ] Current password must be correct — wrong current password shows error
- [ ] New password must be at least 8 characters
- [ ] Unauthenticated users cannot access profile update endpoints (redirect to /login)

### Security Question at Registration
- [ ] Registration form includes a security question dropdown with predefined questions
- [ ] Registration form includes a security answer input field
- [ ] Both security question and answer are required during registration
- [ ] Security answer is hashed with werkzeug before storage
- [ ] Stored answer is never in plaintext in the database
- [ ] Existing seed user (`demo@spendly.com`) has a default security question set during seed (or can be set manually)

### Forgot Password Flow
- [ ] Login page shows a "Forgot Password?" link
- [ ] Clicking the link navigates to `/forgot-password`
- [ ] User can enter their email address on the forgot password page
- [ ] If the email exists, the security question is displayed
- [ ] If the email does NOT exist, a generic message is shown (no account enumeration)
- [ ] User submits their answer — it is normalized (trimmed, lowercased) before hash comparison
- [ ] Correct answer allows setting a new password (at least 8 characters)
- [ ] Wrong answer shows a generic error message
- [ ] After successful password reset, user is redirected to login
- [ ] New password works for signing in
