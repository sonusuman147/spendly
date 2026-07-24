# Spec: Login and Logout

## Overview
This feature implements user authentication for Spendly. It converts the `/login` stub into a functional POST handler that verifies credentials against the database, stores the authenticated user's ID in the session, and redirects to the dashboard (or a suitable landing page). It also implements the `/logout` stub, which clears the session and redirects to the landing page. After this step, the app can distinguish logged-in users from guests, which is a prerequisite for all expense features.

## Depends on
- Step 01 — Database Setup (`users` table must exist)
- Step 02 — Registration (`create_user` and password hashing must be in place; a user must exist to log in against)

## Routes
- `GET /login` — render login form — public
- `POST /login` — validate credentials, set session, redirect — public
- `GET /logout` — clear session, redirect to `/` — public (no login required to log out)

## Database changes
No database changes. The `users` table created in Step 01 already stores `email` and `password_hash`.

## Templates
- **Modify:** `templates/login.html` — add a POST form with `email` and `password` fields, flash message display, and a link to `/register`

## Files to change
- `app.py` — implement `login()` as GET+POST handler and implement `logout()`
- `database/db.py` — add `get_user_by_email(email)` helper that returns a user row or `None`
- `templates/login.html` — add POST form and flash display

## Files to create
No new files.

## New dependencies
No new dependencies. `werkzeug.security.check_password_hash` is already available via the existing `werkzeug` install.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw `sqlite3` via `get_db()`
- Parameterised queries only — never use f-strings in SQL
- Passwords verified with `werkzeug.security.check_password_hash`
- Session key for the logged-in user must be `session["user_id"]` (integer)
- Use `flask.session` — do not roll a custom session mechanism
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Use `url_for()` for every internal link — never hardcode paths
- On failed login show a generic flash error ("Invalid email or password.") — do not reveal which field was wrong
- After successful login redirect to `url_for("landing")` until a dashboard route exists
- `logout()` must call `session.clear()` then redirect to `url_for("landing")`
- `get_user_by_email` belongs in `database/db.py`, not inline in the route

## Definition of done
- [ ] Visiting `GET /login` renders the login form with email and password fields
- [ ] Submitting the form with valid credentials (e.g. demo@spendly.com / demo123) sets `session["user_id"]` and redirects to `/`
- [ ] Submitting with a wrong password shows "Invalid email or password." flash and stays on the login page
- [ ] Submitting with an unregistered email shows the same generic error flash
- [ ] Visiting `GET /logout` clears the session and redirects to `/`
- [ ] After logout, `session["user_id"]` is no longer present
- [ ] The `/logout` route no longer returns the raw stub string