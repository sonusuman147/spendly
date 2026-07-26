import os
import sqlite3

from dotenv import load_dotenv
from flask import Flask, render_template, request, session, flash, redirect, url_for, abort
from werkzeug.security import check_password_hash, generate_password_hash
from authlib.integrations.flask_client import OAuth
from database.db import get_db, init_db, seed_db, get_user_by_email, create_user, get_user_by_id, get_user_expenses_summary, get_user_by_google_id, link_google_account

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = "spendly-dev-secret-key"

oauth = OAuth(app)

oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID", ""),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)

# Initialize database on startup
with app.app_context():
    init_db()
    seed_db()


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Handle GET (show form) and POST (create user)."""
    # Redirect already logged-in users to landing
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        # Server-side validation
        if not name or not email or "@" not in email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return render_template("register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("register.html")

        try:
            create_user(name, email, password_hash=generate_password_hash(password))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
            return render_template("register.html")

        # Success — do NOT set session, redirect to login
        flash("Account created successfully! Please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle GET (show form) and POST (authenticate user)."""
    # Redirect already logged-in users to landing
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        # Server-side validation — generic message for all failures
        if not email or "@" not in email or not password:
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        user = get_user_by_email(email)
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid email or password.", "error")
            return render_template("login.html")

        # Success — start session and redirect
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        flash("Welcome back!", "success")
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/login/google")
def google_login():
    """Redirect to Google's OAuth consent screen."""
    redirect_uri = url_for("google_callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


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

    # Fetch user info from Google's userinfo endpoint
    userinfo = oauth.google.userinfo()

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


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("landing"))


@app.route("/profile")
def profile():
    """Render the profile page with user info and expense summary.

    Requires authentication — redirects to /login if session is missing.
    Clears orphaned sessions if the user no longer exists.
    """
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])
    if user is None:
        session.clear()
        flash("Session expired. Please sign in again.", "error")
        return redirect(url_for("login"))

    summary = get_user_expenses_summary(session["user_id"])
    return render_template("profile.html", user=user, summary=summary)


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    app.run(debug=True, port=5001)
