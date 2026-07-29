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
    link_google_account, CATEGORIES, SECURITY_QUESTIONS,
    update_user_profile, update_password, get_user_by_email_with_security,
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
        security_question = request.form.get("security_question", "").strip()
        security_answer = request.form.get("security_answer", "").strip()

        # Server-side validation
        if not name or not email or "@" not in email or not password or not confirm_password:
            flash("All fields are required.", "error")
            return render_template("register.html", security_questions=SECURITY_QUESTIONS)

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("register.html", security_questions=SECURITY_QUESTIONS)

        if len(password) < 8:
            flash("Password must be at least 8 characters.", "error")
            return render_template("register.html", security_questions=SECURITY_QUESTIONS)

        if not security_question or not security_answer:
            flash("Security question and answer are required.", "error")
            return render_template("register.html", security_questions=SECURITY_QUESTIONS)

        try:
            create_user(
                name, email,
                password_hash=generate_password_hash(password),
                security_question=security_question,
                security_answer_hash=generate_password_hash(security_answer.strip().lower()),
            )
        except sqlite3.IntegrityError:
            flash("Email already registered.", "error")
            return render_template("register.html", security_questions=SECURITY_QUESTIONS)

        # Success — do NOT set session, redirect to login
        flash("Account created successfully! Please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", security_questions=SECURITY_QUESTIONS)


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


# ------------------------------------------------------------------ #
# Profile routes                                                      #
# ------------------------------------------------------------------ #

@app.route("/profile")
def profile():
    """Render the profile page with user info and expense summary.

    Supports optional date filtering via GET query parameters:
      - period: "1m" (this month), "3m" (last 3 months), "6m" (last 6 months), "all"
      - start_date: custom start date (YYYY-MM-DD)
      - end_date: custom end date (YYYY-MM-DD)

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

    # --- Date filter logic ---
    today = date_helper.today()
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    period = request.args.get("period", "all")

    # If a quick filter period is set, compute date range
    if period == "1m":
        start_date = today.replace(day=1).isoformat()
        end_date = today.isoformat()
    elif period == "3m":
        # Go back 3 months from today, set to 1st of that month
        month = today.month - 3
        year = today.year
        while month < 1:
            month += 12
            year -= 1
        from datetime import date as dt_date
        start_date = dt_date(year, month, 1).isoformat()
        end_date = today.isoformat()
    elif period == "6m":
        month = today.month - 6
        year = today.year
        while month < 1:
            month += 12
            year -= 1
        from datetime import date as dt_date
        start_date = dt_date(year, month, 1).isoformat()
        end_date = today.isoformat()
    # Otherwise (period is "all" or unspecified), use custom start_date/end_date from query params as-is

    # Validate date formats if provided
    if start_date:
        try:
            from datetime import datetime as dt_validate
            dt_validate.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            start_date = None
    if end_date:
        try:
            from datetime import datetime as dt_validate
            dt_validate.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            end_date = None

    summary = get_user_expenses_summary(session["user_id"], start_date=start_date, end_date=end_date)
    return render_template(
        "profile.html",
        user=user,
        summary=summary,
        selected_period=period,
        filter_start_date=start_date or "",
        filter_end_date=end_date or "",
    )


@app.route("/profile/update", methods=["POST"])
def profile_update():
    """Update the logged-in user's name and email.

    Requires authentication. Enforces email uniqueness.
    """
    if not session.get("user_id"):
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()

    if not name or not email or "@" not in email:
        flash("Valid name and email are required.", "error")
        return redirect(url_for("profile"))

    try:
        update_user_profile(session["user_id"], name, email)
    except sqlite3.IntegrityError:
        flash("Email is already registered by another user.", "error")
        return redirect(url_for("profile"))

    session["user_name"] = name
    flash("Profile updated successfully!", "success")
    return redirect(url_for("profile"))


@app.route("/profile/change-password", methods=["POST"])
def profile_change_password():
    """Change the logged-in user's password.

    Requires current password verification before accepting a new one.
    """
    if not session.get("user_id"):
        return redirect(url_for("login"))

    current_password = request.form.get("current_password", "").strip()
    new_password = request.form.get("new_password", "").strip()
    confirm_new_password = request.form.get("confirm_new_password", "").strip()

    # Validate inputs
    if not current_password or not new_password or not confirm_new_password:
        flash("All password fields are required.", "error")
        return redirect(url_for("profile"))

    if new_password != confirm_new_password:
        flash("New passwords do not match.", "error")
        return redirect(url_for("profile"))

    if len(new_password) < 8:
        flash("New password must be at least 8 characters.", "error")
        return redirect(url_for("profile"))

    # Verify current password
    user = get_user_by_id(session["user_id"])
    if user is None:
        session.clear()
        return redirect(url_for("login"))

    # We need the full user record with password_hash; fetch via get_user_by_email
    full_user = get_user_by_email(user["email"])
    if full_user is None or not check_password_hash(full_user["password_hash"], current_password):
        flash("Current password is incorrect.", "error")
        return redirect(url_for("profile"))

    # Update password
    update_password(session["user_id"], generate_password_hash(new_password))
    flash("Password changed successfully!", "success")
    return redirect(url_for("profile"))


@app.route("/profile/edit", methods=["GET", "POST"])
def profile_edit():
    """Handle GET (show edit form) and POST (update profile/password).

    Requires authentication. Updates name/email always. If password fields
    are filled, also validates and updates the password.
    """
    if not session.get("user_id"):
        return redirect(url_for("login"))

    user = get_user_by_id(session["user_id"])
    if user is None:
        session.clear()
        flash("Session expired. Please sign in again.", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        current_password = request.form.get("current_password", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_new_password = request.form.get("confirm_new_password", "").strip()

        # Validate name/email
        if not name or not email or "@" not in email:
            flash("Valid name and email are required.", "error")
            return render_template("profile_edit.html", user=user)

        # Update name and email
        try:
            update_user_profile(session["user_id"], name, email)
        except sqlite3.IntegrityError:
            flash("Email is already registered by another user.", "error")
            return render_template("profile_edit.html", user=user)

        session["user_name"] = name

        # If password fields are provided, update password too
        if current_password or new_password or confirm_new_password:
            if not current_password or not new_password or not confirm_new_password:
                flash("All password fields are required to change password.", "error")
                return render_template("profile_edit.html", user=user)

            if new_password != confirm_new_password:
                flash("New passwords do not match.", "error")
                return render_template("profile_edit.html", user=user)

            if len(new_password) < 8:
                flash("New password must be at least 8 characters.", "error")
                return render_template("profile_edit.html", user=user)

            # Verify current password
            current_user = get_user_by_id(session["user_id"])
            full_user = get_user_by_email(current_user["email"])
            if full_user is None or not check_password_hash(full_user.get("password_hash", ""), current_password):
                flash("Current password is incorrect.", "error")
                return render_template("profile_edit.html", user=user)

            update_password(session["user_id"], generate_password_hash(new_password))
            flash("Profile and password updated successfully!", "success")
        else:
            flash("Profile updated successfully!", "success")

        return redirect(url_for("profile"))

    return render_template("profile_edit.html", user=user)


# ------------------------------------------------------------------ #
# Forgot Password routes                                              #
# ------------------------------------------------------------------ #

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Handle GET (show email form) and POST (look up security question).

    On POST: looks up the email and either shows the security question
    or displays a generic message to prevent account enumeration.
    """
    if request.method == "POST":
        email = request.form.get("email", "").strip()

        if not email or "@" not in email:
            flash("Please enter a valid email address.", "error")
            return render_template("forgot_password.html")

        # Look up user — generic handling to prevent enumeration
        user_data = get_user_by_email_with_security(email)

        if user_data is None or not user_data.get("security_question"):
            # Generic message — don't reveal if account exists
            flash("If that email is registered, a security question will be shown.", "success")
            return render_template("forgot_password.html")

        # Store user lookup in session for the reset step
        session["reset_user_id"] = user_data["id"]
        session["security_question"] = user_data["security_question"]
        return redirect(url_for("reset_password"))

    return render_template("forgot_password.html")


@app.route("/forgot-password/reset", methods=["GET", "POST"])
def reset_password():
    """Handle GET (show security question + answer form) and POST (verify & reset).

    On POST: normalizes answer (trim, lowercase), compares hash,
    and if correct allows setting a new password.
    """
    # Must have come from the forgot-password flow
    if not session.get("reset_user_id") or not session.get("security_question"):
        flash("Please start the forgot password process.", "error")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        answer = request.form.get("answer", "").strip().lower()
        new_password = request.form.get("new_password", "").strip()
        confirm_new_password = request.form.get("confirm_new_password", "").strip()

        # Validate answer
        if not answer:
            flash("Please provide your security answer.", "error")
            return render_template(
                "reset_password.html",
                security_question=session["security_question"],
            )

        # Fetch the stored security answer hash directly
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT security_answer_hash FROM users WHERE id = ?",
            (session["reset_user_id"],),
        )
        result = cursor.fetchone()
        conn.close()

        if result is None:
            session.pop("reset_user_id", None)
            session.pop("security_question", None)
            flash("Session expired. Please start again.", "error")
            return redirect(url_for("forgot_password"))

        stored_hash = result["security_answer_hash"]

        if not stored_hash or not check_password_hash(stored_hash, answer):
            flash("Incorrect answer. Please try again.", "error")
            return render_template(
                "reset_password.html",
                security_question=session["security_question"],
            )

        # Answer is correct — validate new password
        if not new_password or not confirm_new_password:
            flash("New password and confirmation are required.", "error")
            return render_template(
                "reset_password.html",
                security_question=session["security_question"],
            )

        if new_password != confirm_new_password:
            flash("New passwords do not match.", "error")
            return render_template(
                "reset_password.html",
                security_question=session["security_question"],
            )

        if len(new_password) < 8:
            flash("New password must be at least 8 characters.", "error")
            return render_template(
                "reset_password.html",
                security_question=session["security_question"],
            )

        # Update the password
        update_password(session["reset_user_id"], generate_password_hash(new_password))

        # Clean up session
        session.pop("reset_user_id", None)
        session.pop("security_question", None)

        flash("Password reset successful! Please sign in.", "success")
        return redirect(url_for("login"))

    return render_template(
        "reset_password.html",
        security_question=session["security_question"],
    )


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
