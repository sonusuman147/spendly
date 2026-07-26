# Google Authentication - Implementation Progress

## Implementation Order

- [x] Step 1: `requirements.txt` — Add `authlib>=1.3.0`
- [x] Step 2: `database/db.py` — Refactor `create_user()` signature
- [x] Step 3: `database/db.py` — Update `seed_db()` to use new `create_user()` signature
- [x] Step 4: `database/db.py` — Add `google_id` column migration in `init_db()`
- [x] Step 5: `database/db.py` — Add `get_user_by_google_id()` helper
- [x] Step 6: `database/db.py` — Add `link_google_account()` helper
- [x] Step 7: `app.py` — Add `import os` and `from authlib.integrations.flask_client import OAuth`
- [x] Step 8: `app.py` — Update db helper imports
- [x] Step 9: `app.py` — Add `generate_password_hash` to werkzeug imports
- [x] Step 10: `app.py` — Configure OAuth with Google provider
- [x] Step 11: `app.py` — Update `register()` route to use `password_hash=generate_password_hash(password)`
- [x] Step 12: `app.py` — Add `GET /login/google` route
- [x] Step 13: `app.py` — Add `GET /login/google/callback` route
- [x] Step 14: `templates/login.html` — Add Google sign-in button and divider
- [x] Step 15: `static/css/style.css` — Add `.btn-google` and `.divider` styles
- [x] Step 16: Terminal — Run `pip install authlib`
- [x] Step 17: Terminal — Run `python app.py` to verify

