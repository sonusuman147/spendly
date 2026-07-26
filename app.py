import os
import sqlite3

from datetime import date as date_helper
from dotenv import load_dotenv
from flask import Flask, render_template, request, session, flash, redirect, url_for, abort
from werkzeug.security import check_password_hash, generate_password_hash
from authlib.integrations.flask_client import OAuth
from database.db import (
    get_db, init_db, seed_db, get_user_by_email, create_user,
    get_user_by_id, get_user_expenses_summary, get_user_by_google_id,
    link_google_account, CATEGORIES,
    create_expense as db_create_expense,
    get_expenses_by_user as db_get_expenses_by_user,
    get_expense_by_id as db_get_expense_by_id,
    update_expense as db_update_expense,
    delete_expense as db_delete_expense,
)

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
# General routes                                                      #
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


# ------------------------------------------------------------------ #
# Expense CRUD routes                                                  #
# ------------------------------------------------------------------ #

def login_required():
    """Check if user is logged in; redirect to /login if not."""
    if not session.get("user_id"):
        flash("Please sign in to access this page.", "error")
        return redirect(url_for("login"))
    return None


@app.route("/expenses")
def list_expenses():
    """List all expenses for the logged-in user, newest first."""
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    expenses = db_get_expenses_by_user(session["user_id"])
    return render_template("expenses/list.html", expenses=expenses)


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    """Handle GET (show add form) and POST (create expense)."""
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    if request.method == "POST":
        amount = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        date = request.form.get("date", "").strip()

        # Validation
        errors = []
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                errors.append("Amount must be a positive number.")
        except (ValueError, TypeError):
            errors.append("Amount is required and must be a valid number.")

        if category not in CATEGORIES:
            errors.append("Please select a valid category.")

        if not date:
            errors.append("Date is required.")

        if len(description) > 200:
            errors.append("Description must be 200 characters or less.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "expenses/form.html",
                mode="add",
                categories=CATEGORIES,
                expense={"amount": amount, "category": category, "description": description, "date": date},
                today=date_helper.today().isoformat(),
            )

        db_create_expense(session["user_id"], amount_float, category, date, description)
        flash("Expense added successfully!", "success")
        return redirect(url_for("list_expenses"))

    return render_template(
        "expenses/form.html",
        mode="add",
        categories=CATEGORIES,
        expense=None,
        today=date_helper.today().isoformat(),
    )


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    """Handle GET (show edit form) and POST (update expense)."""
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    expense = db_get_expense_by_id(id)
    if expense is None:
        abort(404)
    if expense["user_id"] != session["user_id"]:
        abort(403)

    if request.method == "POST":
        amount = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        date = request.form.get("date", "").strip()

        # Validation
        errors = []
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                errors.append("Amount must be a positive number.")
        except (ValueError, TypeError):
            errors.append("Amount is required and must be a valid number.")

        if category not in CATEGORIES:
            errors.append("Please select a valid category.")

        if not date:
            errors.append("Date is required.")

        if len(description) > 200:
            errors.append("Description must be 200 characters or less.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "expenses/form.html",
                mode="edit",
                categories=CATEGORIES,
                expense={"id": id, "amount": amount, "category": category, "description": description, "date": date},
                today=date_helper.today().isoformat(),
            )

        updated = db_update_expense(id, session["user_id"], amount_float, category, date, description)
        if not updated:
            abort(403)

        flash("Expense updated successfully!", "success")
        return redirect(url_for("list_expenses"))

    return render_template(
        "expenses/form.html",
        mode="edit",
        categories=CATEGORIES,
        expense=expense,
        today=date_helper.today().isoformat(),
    )


@app.route("/expenses/<int:id>/delete", methods=["GET", "POST"])
def delete_expense_view(id):
    """Handle GET (show delete confirmation) and POST (execute delete)."""
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    expense = db_get_expense_by_id(id)
    if expense is None:
        abort(404)
    if expense["user_id"] != session["user_id"]:
        abort(403)

    if request.method == "POST":
        deleted = db_delete_expense(id, session["user_id"])
        if not deleted:
            abort(403)
        flash("Expense deleted successfully!", "success")
        return redirect(url_for("list_expenses"))

    return render_template("expenses/delete.html", expense=expense)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
