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
    PAYMENT_METHODS, DEFAULT_PAYMENT_METHOD, SORT_OPTIONS,
    update_user_profile, update_password, get_user_by_email_with_security,
    create_expense as db_create_expense,
    get_expenses_by_user as db_get_expenses_by_user,
    get_expense_by_id as db_get_expense_by_id,
    update_expense as db_update_expense,
    delete_expense as db_delete_expense,
    get_transactions as db_get_transactions,
    get_expenses_by_ids as db_get_expenses_by_ids,
    delete_expenses_bulk as db_delete_expenses_bulk,
    add_activity as db_add_activity,
    get_recent_activity as db_get_recent_activity,
    # Categories module
    DEFAULT_CATEGORIES, CATEGORY_ICONS, CATEGORY_COLORS,
    CATEGORY_SORT_OPTIONS,
    ensure_default_categories as db_ensure_default_categories,
    backfill_categories as db_backfill_categories,
    get_user_categories as db_get_user_categories,
    create_category as db_create_category,
    get_category_by_id as db_get_category_by_id,
update_category as db_update_category,
    delete_category as db_delete_category,
    get_categories as db_get_categories,
    get_category_stats as db_get_category_stats,
    get_categories_export as db_get_categories_export,
    merge_categories as db_merge_categories,
# Reports module
    get_report_data as db_get_report_data,
    REPORT_DEFAULT_MONTHS,
# Budgets module
    get_budget_data as db_get_budget_data,
    get_budget_months as db_get_budget_months,
    get_user_budgets as db_get_user_budgets,
    get_budget_by_id as db_get_budget_by_id,
    create_budget as db_create_budget,
    update_budget_limit as db_update_budget_limit,
    delete_budget as db_delete_budget,
    reset_budget_defaults as db_reset_budget_defaults,
    BUDGET_STATUSES,
    BUDGET_LIMITS,
    BUDGET_CATEGORY_ICONS,
    BUDGET_CATEGORY_COLORS,
# Goals module
    get_goal_data as db_get_goal_data,
    get_user_goals as db_get_user_goals,
    get_goal_by_id as db_get_goal_by_id,
    create_goal as db_create_goal,
    update_goal as db_update_goal,
    delete_goal as db_delete_goal,
    add_goal_funds as db_add_goal_funds,
    GOAL_STATUSES,
    GOAL_CATEGORY_NAMES,
    GOAL_CATEGORY_ICONS,
    GOAL_CATEGORY_COLORS,
    GOAL_SORT_OPTIONS,
)

# Python standard library
import csv
import io
from datetime import datetime as dt_datetime

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv(
    "SECRET_KEY",
    "spendly-dev-secret-key"
)

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
    # Ensure every user (including pre-existing ones) has default category
    # rows so the Categories module works for all accounts.
    db_backfill_categories()



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


def _parse_transaction_filters(valid_categories=None):
    """Parse and validate the GET filter parameters for the Transactions page.

    `valid_categories` is an optional iterable of accepted category names
    (the logged-in user's categories). Falls back to the static CATEGORIES
    list when not provided.

    Returns a dict with normalized, validated filter values:
      - search: str (trimmed)
      - category: str (must be a valid category, else "")
      - date_from / date_to: str (validated YYYY-MM-DD, else "")
      - amount_min / amount_max: float or None (invalid values are ignored)
      - sort: str (must be in SORT_OPTIONS, else "date-desc")
      - page: int (>= 1)
    """
    if valid_categories is None:
        valid_categories = CATEGORIES
    else:
        valid_categories = set(valid_categories)

    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    if category not in valid_categories:
        category = ""

    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    # Validate date formats — invalid dates are treated as "no filter".
    for key in ("date_from", "date_to"):
        value = request.args.get(key, "").strip()
        if value:
            try:
                dt_datetime.strptime(value, "%Y-%m-%d")
            except ValueError:
                if key == "date_from":
                    date_from = ""
                else:
                    date_to = ""

    # Validate amount range.
    amount_min = None
    amount_max = None
    for key in ("amount_min", "amount_max"):
        value = request.args.get(key, "").strip()
        if value:
            try:
                parsed = float(value)
                if parsed < 0:
                    parsed = None
            except ValueError:
                parsed = None
            if key == "amount_min":
                amount_min = parsed
            else:
                amount_max = parsed

    sort = request.args.get("sort", "date-desc")
    if sort not in SORT_OPTIONS:
        sort = "date-desc"

    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1

    return {
        "search": search,
        "category": category,
        "date_from": date_from,
        "date_to": date_to,
        "amount_min": amount_min,
        "amount_max": amount_max,
        "sort": sort,
        "page": page,
    }


def _transactions_query_args(filters):
    """Build a dict of query params to preserve filter state across pagination.

    Used to build pagination and action links that keep the current filters.
    Excludes the page key so callers can override it.
    """
    args = {}
    if filters["search"]:
        args["search"] = filters["search"]
    if filters["category"]:
        args["category"] = filters["category"]
    if filters["date_from"]:
        args["date_from"] = filters["date_from"]
    if filters["date_to"]:
        args["date_to"] = filters["date_to"]
    if filters["amount_min"] is not None:
        args["amount_min"] = filters["amount_min"]
    if filters["amount_max"] is not None:
        args["amount_max"] = filters["amount_max"]
    if filters["sort"] != "date-desc":
        args["sort"] = filters["sort"]
    return args


@app.route("/transactions")
def transactions():
    """Render the Transactions ledger page with server-side processing.

    Supports search, category filter, date range, amount range, sorting, and
    pagination — all processed in the database via parameterized queries.
    Summary statistics are computed from the *filtered* result set so the five
    stat cards always reflect the currently visible ledger. Recent Activity is
    served from the real activities table.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    # Source category options from the user's categories table so custom
    # categories appear in the filter dropdown.
    user_cats = db_get_user_categories(session["user_id"])
    valid_categories = [c["name"] for c in user_cats] or CATEGORIES

    filters = _parse_transaction_filters(valid_categories)
    result = db_get_transactions(
        session["user_id"],
        search=filters["search"],
        category=filters["category"],
        date_from=filters["date_from"] or None,
        date_to=filters["date_to"] or None,
        amount_min=filters["amount_min"],
        amount_max=filters["amount_max"],
        sort=filters["sort"],
        page=filters["page"],
        per_page=8,
    )

    # Keep the Recent Activity panel coherent with the ledger: when a category
    # filter is active, only activity for that category is shown.
    activity = db_get_recent_activity(
        session["user_id"],
        limit=8,
        category=filters["category"] or None,
    )

    has_active_filters = any([
        filters["search"],
        filters["category"],
        filters["date_from"],
        filters["date_to"],
        filters["amount_min"] is not None,
        filters["amount_max"] is not None,
        filters["sort"] != "date-desc",
    ])

    return render_template(
        "transactions.html",
        transactions=result["items"],
        categories=valid_categories,
        payment_methods=PAYMENT_METHODS,
        summary=result["summary"],
        pagination={
            "page": result["page"],
            "pages": result["pages"],
            "total": result["total"],
            "has_prev": result["has_prev"],
            "has_next": result["has_next"],
        },
        activity=activity,
        filters=filters,
        query_args=_transactions_query_args(filters),
        per_page=result["per_page"],
        has_active_filters=has_active_filters,
    )


@app.route("/transactions/export")
def transactions_export():
    """Export the filtered (or selected) transactions as a CSV file.

    Accepts the same filter query params as GET /transactions. If `ids` is
    provided, only those selected transaction ids are exported (ownership is
    enforced server-side). Otherwise the full filtered set is exported.
    Returns a text/csv attachment.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    user_id = session["user_id"]
    filters = _parse_transaction_filters()

    # If specific ids were selected, export only those (ownership-scoped).
    ids_raw = request.args.get("ids", "")
    if ids_raw:
        try:
            ids = [int(i) for i in ids_raw.split(",") if i.strip().isdigit()]
        except (TypeError, ValueError):
            ids = []
        expenses = db_get_expenses_by_ids(user_id, ids)
    else:
        result = db_get_transactions(
            user_id,
            search=filters["search"],
            category=filters["category"],
            date_from=filters["date_from"] or None,
            date_to=filters["date_to"] or None,
            amount_min=filters["amount_min"],
            amount_max=filters["amount_max"],
            sort=filters["sort"],
            page=1,
            per_page=None,
        )
        expenses = result["items"]

    # Build CSV in memory.
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Description", "Category", "Payment Method", "Amount"])

    payment_label = {
        "card": "Card",
        "upi": "UPI",
        "cash": "Cash",
        "bank": "Bank",
        "wallet": "Wallet",
    }
    for exp in expenses:
        writer.writerow([
            exp["date"],
            exp["description"] or "",
            exp["category"],
            payment_label.get(exp.get("payment_method"), "Cash"),
            f"{exp['amount']:.2f}",
        ])

    csv_data = output.getvalue()

    from flask import Response
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=spendly-transactions.csv"},
    )


@app.route("/transactions/bulk-delete", methods=["POST"])
def transactions_bulk_delete():
    """Delete multiple selected transactions (ownership enforced).

    Accepts a list of expense ids via form field `expense_ids`. Only rows
    owned by the logged-in user are deleted. Records a "deleted" activity
    entry for each deleted transaction and redirects back to /transactions
    preserving the active filters.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    user_id = session["user_id"]
    expense_ids = request.form.getlist("expense_ids")

    # Coerce to ints, dropping anything invalid.
    ids = []
    for raw in expense_ids:
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            continue

    if not ids:
        flash("No transactions selected to delete.", "error")
        return redirect(url_for("transactions"))

    # Record activity for each transaction that actually belongs to the user.
    owned = db_get_expenses_by_ids(user_id, ids)
    for exp in owned:
        db_add_activity(
            user_id,
            action="deleted",
            expense_id=exp["id"],
            category=exp["category"],
            description=exp["description"],
            amount=exp["amount"],
        )

    deleted = db_delete_expenses_bulk(user_id, ids)
    if deleted == 0:
        flash("No matching transactions found to delete.", "error")
    else:
        flash(f"{deleted} transaction(s) deleted successfully!", "success")

    # Preserve the current filters when redirecting back.
    filters = _parse_transaction_filters()
    args = _transactions_query_args(filters)
    return redirect(url_for("transactions", **args))


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    """Handle GET (show add form) and POST (create expense)."""
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    # Source category options from the user's categories table so custom
    # categories are selectable when adding expenses.
    user_cats = db_get_user_categories(session["user_id"])
    valid_categories = [c["name"] for c in user_cats] or CATEGORIES

    if request.method == "POST":
        amount = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        date = request.form.get("date", "").strip()
        payment_method = request.form.get("payment_method", DEFAULT_PAYMENT_METHOD).strip()

        # Validate payment method — fall back to default if invalid.
        if payment_method not in PAYMENT_METHODS:
            payment_method = DEFAULT_PAYMENT_METHOD

        # Validation
        errors = []
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                errors.append("Amount must be a positive number.")
        except (ValueError, TypeError):
            errors.append("Amount is required and must be a valid number.")

        if category not in valid_categories:
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
                categories=valid_categories,
                payment_methods=PAYMENT_METHODS,
                expense={"amount": amount, "category": category, "description": description, "date": date, "payment_method": payment_method},
                today=date_helper.today().isoformat(),
            )

        expense_id = db_create_expense(
            session["user_id"], amount_float, category, date, description, payment_method,
        )
        # Log the "added" event for the Recent Activity feed.
        db_add_activity(
            session["user_id"],
            action="added",
            expense_id=expense_id,
            category=category,
            description=description,
            amount=amount_float,
        )
        flash("Expense added successfully!", "success")
        return redirect(url_for("list_expenses"))

    return render_template(
        "expenses/form.html",
        mode="add",
        categories=valid_categories,
        payment_methods=PAYMENT_METHODS,
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

    # Source category options from the user's categories table so custom
    # categories are selectable when editing expenses.
    user_cats = db_get_user_categories(session["user_id"])
    valid_categories = [c["name"] for c in user_cats] or CATEGORIES

    if request.method == "POST":
        amount = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        date = request.form.get("date", "").strip()
        payment_method = request.form.get("payment_method", DEFAULT_PAYMENT_METHOD).strip()

        # Validate payment method — fall back to default if invalid.
        if payment_method not in PAYMENT_METHODS:
            payment_method = DEFAULT_PAYMENT_METHOD

        # Validation
        errors = []
        try:
            amount_float = float(amount)
            if amount_float <= 0:
                errors.append("Amount must be a positive number.")
        except (ValueError, TypeError):
            errors.append("Amount is required and must be a valid number.")

        if category not in valid_categories:
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
                categories=valid_categories,
                payment_methods=PAYMENT_METHODS,
                expense={"id": id, "amount": amount, "category": category, "description": description, "date": date, "payment_method": payment_method},
                today=date_helper.today().isoformat(),
            )

        updated = db_update_expense(
            id, session["user_id"], amount_float, category, date, description, payment_method,
        )
        if not updated:
            abort(403)

        # Log the "edited" event for the Recent Activity feed.
        db_add_activity(
            session["user_id"],
            action="edited",
            expense_id=id,
            category=category,
            description=description,
            amount=amount_float,
        )
        flash("Expense updated successfully!", "success")
        return redirect(url_for("list_expenses"))

    return render_template(
        "expenses/form.html",
        mode="edit",
        categories=valid_categories,
        payment_methods=PAYMENT_METHODS,
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
        # Log the "deleted" event for the Recent Activity feed.
        db_add_activity(
            session["user_id"],
            action="deleted",
            expense_id=id,
            category=expense["category"],
            description=expense["description"],
            amount=expense["amount"],
        )
        flash("Expense deleted successfully!", "success")
        return redirect(url_for("list_expenses"))

    return render_template("expenses/delete.html", expense=expense)


# ------------------------------------------------------------------ #
# Categories routes                                                    #
# ------------------------------------------------------------------ #

def _parse_category_filters():
    """Parse and validate the GET filter parameters for the Categories page.

    Returns a dict with:
      - search: str (trimmed)
      - sort: str (must be in CATEGORY_SORT_OPTIONS, else "name-asc")
      - page: int (>= 1)
      - per_page: int
    """
    search = request.args.get("search", "").strip()
    sort = request.args.get("sort", "name-asc")
    if sort not in CATEGORY_SORT_OPTIONS:
        sort = "name-asc"
    try:
        page = max(1, int(request.args.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get("per_page", 8))
        if per_page < 1:
            per_page = 8
    except (TypeError, ValueError):
        per_page = 8
    return {"search": search, "sort": sort, "page": page, "per_page": per_page}


def _category_query_args(filters):
    """Build a dict of query params to preserve filter state across pagination."""
    args = {}
    if filters["search"]:
        args["search"] = filters["search"]
    if filters["sort"] != "name-asc":
        args["sort"] = filters["sort"]
    if filters["per_page"] != 8:
        args["per_page"] = filters["per_page"]
    return args


@app.route("/categories")
def categories():
    """Render the Categories dashboard.

    Shows summary cards, a search/filter table with usage stats, a donut
    chart for spending distribution, a Top Categories ranking, and quick
    action cards. Supports search, sort, and pagination via query params.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    user_id = session["user_id"]
    filters = _parse_category_filters()

    result = db_get_categories(
        user_id,
        search=filters["search"],
        sort=filters["sort"],
        page=filters["page"],
        per_page=filters["per_page"],
    )
    stats = db_get_category_stats(user_id)
    all_categories = db_get_user_categories(user_id)

    return render_template(
        "categories/list.html",
        categories=result["items"],
        all_categories=all_categories,
        stats=stats,
        pagination={
            "page": result["page"],
            "pages": result["pages"],
            "total": result["total"],
            "has_prev": result["has_prev"],
            "has_next": result["has_next"],
        },
        filters=filters,
        query_args=_category_query_args(filters),
        sort_options=CATEGORY_SORT_OPTIONS,
        category_colors=CATEGORY_COLORS,
        per_page=result["per_page"],
        has_search=filters["search"] != "",
    )


@app.route("/categories/add", methods=["GET", "POST"])
def add_category():
    """Handle GET (show create form) and POST (create category)."""
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        icon = request.form.get("icon", "tag").strip()
        color = request.form.get("color", "").strip()

        # Validate
        errors = []
        if not name:
            errors.append("Category name is required.")
        elif len(name) > 30:
            errors.append("Category name must be 30 characters or less.")

        if icon not in CATEGORY_ICONS:
            errors.append("Please select a valid icon.")

        if color not in CATEGORY_COLORS:
            errors.append("Please select a valid color.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "categories/form.html",
                mode="add",
                category={"name": name, "description": description, "icon": icon if icon in CATEGORY_ICONS else "tag", "color": color if color in CATEGORY_COLORS else CATEGORY_COLORS[0]},
                icons=CATEGORY_ICONS,
                colors=CATEGORY_COLORS,
            )

        try:
            db_create_category(session["user_id"], name, description, icon, color)
        except sqlite3.IntegrityError:
            flash("A category with this name already exists.", "error")
            return render_template(
                "categories/form.html",
                mode="add",
                category={"name": name, "description": description, "icon": icon, "color": color},
                icons=CATEGORY_ICONS,
                colors=CATEGORY_COLORS,
            )

        flash("Category created successfully!", "success")
        return redirect(url_for("categories"))

    return render_template(
        "categories/form.html",
        mode="add",
        category=None,
        icons=CATEGORY_ICONS,
        colors=CATEGORY_COLORS,
    )


@app.route("/categories/<int:category_id>")
def view_category(category_id):
    """Show a single category with full usage stats."""
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    category = db_get_category_by_id(category_id, session["user_id"])
    if category is None:
        abort(404)

    return render_template("categories/view.html", category=category)


@app.route("/categories/<int:category_id>/edit", methods=["GET", "POST"])
def edit_category(category_id):
    """Handle GET (show edit form) and POST (update category)."""
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    category = db_get_category_by_id(category_id, session["user_id"])
    if category is None:
        abort(404)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        icon = request.form.get("icon", "tag").strip()
        color = request.form.get("color", "").strip()

        errors = []
        if not name:
            errors.append("Category name is required.")
        elif len(name) > 30:
            errors.append("Category name must be 30 characters or less.")

        if icon not in CATEGORY_ICONS:
            errors.append("Please select a valid icon.")

        if color not in CATEGORY_COLORS:
            errors.append("Please select a valid color.")

        if errors:
            for error in errors:
                flash(error, "error")
            return render_template(
                "categories/form.html",
                mode="edit",
                category={"id": category_id, "name": name, "description": description, "icon": icon if icon in CATEGORY_ICONS else category["icon"], "color": color if color in CATEGORY_COLORS else category["color"]},
                icons=CATEGORY_ICONS,
                colors=CATEGORY_COLORS,
            )

        try:
            db_update_category(category_id, session["user_id"], name, description, icon, color)
        except sqlite3.IntegrityError:
            flash("A category with this name already exists.", "error")
            return render_template(
                "categories/form.html",
                mode="edit",
                category={"id": category_id, "name": name, "description": description, "icon": icon, "color": color},
                icons=CATEGORY_ICONS,
                colors=CATEGORY_COLORS,
            )

        flash("Category updated successfully!", "success")
        return redirect(url_for("categories"))

    return render_template(
        "categories/form.html",
        mode="edit",
        category=category,
        icons=CATEGORY_ICONS,
        colors=CATEGORY_COLORS,
    )


@app.route("/categories/<int:category_id>/delete", methods=["GET", "POST"])
def delete_category_view(category_id):
    """Handle GET (show delete confirmation) and POST (execute delete).

    If the category is in use by expenses, deletion is blocked unless the
    user confirms via the form; on confirmed delete the expenses are
    reassigned to "Other".
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    category = db_get_category_by_id(category_id, session["user_id"])
    if category is None:
        abort(404)

    in_use = category["transaction_count"] > 0

    if request.method == "POST":
        confirmed = request.form.get("confirm", "") == "yes"
        if in_use and not confirmed:
            flash("Please confirm deletion of this in-use category.", "error")
            return render_template(
                "categories/delete.html",
                category=category,
                in_use=in_use,
            )

        deleted = db_delete_category(category_id, session["user_id"], reassign=True)
        if not deleted:
            abort(403)
        flash("Category deleted! Any expenses were reassigned to 'Other'.", "success")
        return redirect(url_for("categories"))

    return render_template(
        "categories/delete.html",
        category=category,
        in_use=in_use,
    )


@app.route("/categories/merge", methods=["GET", "POST"])
def merge_categories_view():
    """Handle GET (show merge form) and POST (merge categories)."""
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    if request.method == "POST":
        source_id = request.form.get("source_id", "").strip()
        target_id = request.form.get("target_id", "").strip()

        try:
            source_id = int(source_id)
            target_id = int(target_id)
        except (TypeError, ValueError):
            source_id = None
            target_id = None

        if source_id is None or target_id is None:
            flash("Please select both categories to merge.", "error")
            return redirect(url_for("categories"))

        if source_id == target_id:
            flash("Source and target categories must be different.", "error")
            return redirect(url_for("categories"))

        merged = db_merge_categories(session["user_id"], source_id, target_id)
        if not merged:
            flash("Could not merge — please check the selected categories.", "error")
            return redirect(url_for("categories"))

        flash("Categories merged successfully!", "success")
        return redirect(url_for("categories"))

    return render_template(
        "categories/merge.html",
        categories=db_get_user_categories(session["user_id"]),
    )


@app.route("/categories/export")
def categories_export():
    """Export all categories with usage stats as a CSV file."""
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    rows = db_get_categories_export(session["user_id"])

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Description", "Icon", "Color", "Created Date",
        "Transaction Count", "Total Spent", "Average Expense",
    ])
    for row in rows:
        writer.writerow([
            row["name"],
            row["description"],
            row["icon"],
            row["color"],
            row["created_at"],
            row["transaction_count"],
            f"{row['total_spent']:.2f}",
            f"{row['avg_expense']:.2f}",
        ])

    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=spendly-categories.csv"},
    )


@app.route("/categories/analytics")
def categories_analytics():
    """Render a dedicated analytics page with category insights."""
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    stats = db_get_category_stats(session["user_id"])
    categories = db_get_categories_export(session["user_id"])
    return render_template(
        "categories/analytics.html",
        stats=stats,
        categories=categories,
    )


# ------------------------------------------------------------------ #
# Reports routes                                                       #
# ------------------------------------------------------------------ #

def _parse_report_filters():
    """Parse and validate the GET filter parameters for the Reports page.

    Returns a dict with:
      - date_from / date_to: str (validated YYYY-MM-DD, else "")
      - category: str (trimmed)
      - payment: str (must be in PAYMENT_METHODS, else "")
    """
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    # Validate date formats — invalid dates are treated as no filter.
    try:
        if date_from:
            dt_datetime.strptime(date_from, "%Y-%m-%d")
        else:
            date_from = ""
    except ValueError:
        date_from = ""

    try:
        if date_to:
            dt_datetime.strptime(date_to, "%Y-%m-%d")
        else:
            date_to = ""
    except ValueError:
        date_to = ""

    category = request.args.get("category", "").strip()
    payment = request.args.get("payment", "").strip()
    if payment not in PAYMENT_METHODS:
        payment = ""

    return {
        "date_from": date_from,
        "date_to": date_to,
        "category": category,
        "payment": payment,
    }


def _report_query_args(filters):
    """Build a dict of query params to preserve report filter state."""
    args = {}
    if filters["date_from"]:
        args["date_from"] = filters["date_from"]
    if filters["date_to"]:
        args["date_to"] = filters["date_to"]
    if filters["category"]:
        args["category"] = filters["category"]
    if filters["payment"]:
        args["payment"] = filters["payment"]
    return args


@app.route("/reports")
def reports():
    """Render the Reports dashboard with database-backed analytics.

    Supports optional date range, category, and payment method filters via
    GET query parameters. Returns summary cards, monthly trend, category and
    payment breakdowns, top expenses, monthly summary, and data-driven
    insight cards. All data is computed from the user's real expenses.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    user_id = session["user_id"]
    filters = _parse_report_filters()

    # Source category options from the user's categories table so custom
    # categories appear in the filter dropdown.
    user_cats = db_get_user_categories(user_id)
    valid_categories = [c["name"] for c in user_cats] or CATEGORIES

    date_from = filters["date_from"] or None
    date_to = filters["date_to"] or None
    category = filters["category"] or None
    payment = filters["payment"] or None

    report = db_get_report_data(
        user_id,
        date_from=date_from,
        date_to=date_to,
        category=category,
        payment=payment,
        months=REPORT_DEFAULT_MONTHS,
    )

    return render_template(
        "reports.html",
        report=report,
        categories=valid_categories,
        payment_methods=PAYMENT_METHODS,
        filters=filters,
        query_args=_report_query_args(filters),
        has_active_filters=any([
            filters["date_from"],
            filters["date_to"],
            filters["category"],
            filters["payment"],
        ]),
    )


# ------------------------------------------------------------------ #
# Budgets routes                                                       #
# ------------------------------------------------------------------ #

def _parse_budget_filters():
    """Parse and validate the GET filter parameters for the Budgets page.

    Returns a dict with:
      - month: str (validated "YYYY-MM", else "")
      - category: str (must be a known budget category, else "")
      - status: str (must be in BUDGET_STATUSES, else "")
    """
    month = request.args.get("month", "").strip()
    # Validate the month format (YYYY-MM) — invalid values are ignored.
    if month:
        try:
            dt_datetime.strptime(month, "%Y-%m")
        except ValueError:
            month = ""

    category = request.args.get("category", "").strip()
    if category and category not in BUDGET_LIMITS:
        category = ""

    status = request.args.get("status", "").strip()
    if status not in BUDGET_STATUSES:
        status = ""

    return {"month": month, "category": category, "status": status}


def _budget_query_args(filters):
    """Build a dict of query params to preserve budget filter state."""
    args = {}
    if filters["month"]:
        args["month"] = filters["month"]
    if filters["category"]:
        args["category"] = filters["category"]
    if filters["status"]:
        args["status"] = filters["status"]
    return args


@app.route("/budgets")
def budgets():
    """Render the Budgets dashboard with database-backed analytics.

    Budget limits come from the user's per-category budgets table (falling
    back to the static BUDGET_LIMITS defaults). Actual spending is computed
    from the user's real expense rows. Supports optional month, category,
    and status filters via GET query parameters. Returns budget progress
    cards, Budget vs Actual trend, Budget Distribution donut, an overview
    table, alerts/insights, quick actions, and recent activity.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    user_id = session["user_id"]
    filters = _parse_budget_filters()

    month = filters["month"] or None
    category = filters["category"] or None
    status = filters["status"] or None

    budget_data = db_get_budget_data(
        user_id,
        month=month,
        category=category,
        status=status,
    )

    # The months available for the filter dropdown (distinct expense months).
    all_months = db_get_budget_months(user_id)

    return render_template(
        "budgets.html",
        budget=budget_data,
        months=all_months,
        budget_categories=list(BUDGET_LIMITS.keys()),
        budget_statuses=list(BUDGET_STATUSES),
        budget_icons=BUDGET_CATEGORY_ICONS,
        budget_colors=BUDGET_CATEGORY_COLORS,
        filters=filters,
        query_args=_budget_query_args(filters),
    )


@app.route("/budgets/add", methods=["POST"])
def add_budget():
    """Create (or upsert) a per-user budget for a category.

    Validates the category against BUDGET_LIMITS and the limit as a
    positive number. Uses an upsert so creating a budget for a category
    that already exists simply updates the limit. Redirects back to
    /budgets preserving the active filter state."""
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    user_id = session["user_id"]
    category = request.form.get("category", "").strip()
    limit_raw = request.form.get("limit_amount", "").strip()

    # Validate category.
    if category not in BUDGET_LIMITS:
        flash("Please select a valid category.", "error")
        return redirect(url_for("budgets", **_budget_query_args(_parse_budget_filters())))

    # Validate limit.
    try:
        limit = float(limit_raw)
        if limit <= 0:
            raise ValueError
    except (ValueError, TypeError):
        flash("Budget limit must be a positive number.", "error")
        return redirect(url_for("budgets", **_budget_query_args(_parse_budget_filters())))

    try:
        db_create_budget(user_id, category, limit)
    except sqlite3.IntegrityError:
        flash("Could not save the budget — please try again.", "error")
        return redirect(url_for("budgets", **_budget_query_args(_parse_budget_filters())))

    flash(f"{category} budget set to ₹{limit:,.2f}/month.", "success")
    return redirect(url_for("budgets", **_budget_query_args(_parse_budget_filters())))


@app.route("/budgets/<int:budget_id>/edit", methods=["POST"])
def edit_budget(budget_id):
    """Update an existing per-user budget limit (ownership enforced).

    Validates the limit as a positive number. Returns 404 if the row does
    not exist, 403 if it belongs to another user.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    budget = db_get_budget_by_id(budget_id, session["user_id"])
    if budget is None:
        abort(404)

    limit_raw = request.form.get("limit_amount", "").strip()
    try:
        limit = float(limit_raw)
        if limit <= 0:
            raise ValueError
    except (ValueError, TypeError):
        flash("Budget limit must be a positive number.", "error")
        return redirect(url_for("budgets", **_budget_query_args(_parse_budget_filters())))

    updated = db_update_budget_limit(session["user_id"], budget["category"], limit)
    if not updated:
        abort(403)

    flash(f"{budget['category']} budget updated to ₹{limit:,.2f}/month.", "success")
    return redirect(url_for("budgets", **_budget_query_args(_parse_budget_filters())))


@app.route("/budgets/<int:budget_id>/delete", methods=["POST"])
def delete_budget_view(budget_id):
    """Delete a per-user budget row (ownership enforced).

    After deletion the category falls back to its static default limit.
    Returns 404 if the row does not exist, 403 if it belongs to another user.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    budget = db_get_budget_by_id(budget_id, session["user_id"])
    if budget is None:
        abort(404)

    deleted = db_delete_budget(session["user_id"], budget["category"])
    if not deleted:
        abort(403)

    flash(f"{budget['category']} budget deleted — using default limit.", "success")
    return redirect(url_for("budgets", **_budget_query_args(_parse_budget_filters())))


@app.route("/budgets/reset", methods=["POST"])
def reset_budgets():
    """Reset all per-user budget rows so defaults are used again.

    Removes every user-defined budget row; the page then shows the static
    BUDGET_LIMITS defaults. Returns the number of rows removed.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    removed = db_reset_budget_defaults(session["user_id"])
    if removed == 0:
        flash("Budgets were already using defaults.", "success")
    else:
        flash(f"Reset {removed} budget(s) to defaults.", "success")
    return redirect(url_for("budgets", **_budget_query_args(_parse_budget_filters())))


@app.route("/budgets/export")
def budgets_export():
    """Export the user's budgets (effective limits) as a CSV file.

    For each configured budget category, exports the category, monthly
    limit, spent, remaining, usage percentage, and status. Returns a
    text/csv attachment.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    user_id = session["user_id"]
    budget_data = db_get_budget_data(user_id)
    budgets_list = budget_data["budgets"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Category", "Monthly Limit", "Spent", "Remaining", "Usage %", "Status",
    ])
    for b in budgets_list:
        writer.writerow([
            b["name"],
            f"{b['limit']:.2f}",
            f"{b['spent']:.2f}",
            f"{b['remaining']:.2f}",
            f"{b['pct']:.1f}",
            b["status_label"],
        ])

    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=spendly-budgets.csv"},
    )


# ------------------------------------------------------------------ #
# Goals routes                                                        #
# ------------------------------------------------------------------ #

def _parse_goal_filters():
    """Parse and validate the GET filter parameters for the Goals page.

    Returns a dict with:
      - status: str (must be in GOAL_STATUSES, else "")
      - category: str (must be a known goal category, else "")
      - sort: str (must be in GOAL_SORT_OPTIONS, else "progress-desc")
    """
    status = request.args.get("status", "").strip()
    if status not in GOAL_STATUSES:
        status = ""

    category = request.args.get("category", "").strip()
    if category and category not in GOAL_CATEGORY_NAMES:
        category = ""

    sort = request.args.get("sort", "progress-desc").strip()
    if sort not in GOAL_SORT_OPTIONS:
        sort = "progress-desc"

    return {"status": status, "category": category, "sort": sort}


def _goal_query_args(filters):
    """Build a dict of query params to preserve goal filter state."""
    args = {}
    if filters["status"]:
        args["status"] = filters["status"]
    if filters["category"]:
        args["category"] = filters["category"]
    if filters["sort"] != "progress-desc":
        args["sort"] = filters["sort"]
    return args


def _validate_goal_form():
    """Validate the goal create/edit form fields.

    Returns (data_dict, error_message). data_dict is None on error.
    """
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    target_raw = request.form.get("target_amount", "").strip()
    saved_raw = request.form.get("saved_amount", "").strip()
    deadline = request.form.get("deadline", "").strip()
    status = request.form.get("status", "on-track").strip()

    if not name:
        return None, "Goal name is required."
    if len(name) > 100:
        return None, "Goal name must be 100 characters or less."
    if category not in GOAL_CATEGORY_NAMES:
        return None, "Please select a valid category."
    if status not in GOAL_STATUSES:
        status = "on-track"

    try:
        target = float(target_raw)
        if target <= 0:
            raise ValueError
    except (ValueError, TypeError):
        return None, "Target amount must be a positive number."

    try:
        saved = float(saved_raw) if saved_raw else 0.0
        if saved < 0:
            raise ValueError
    except (ValueError, TypeError):
        return None, "Saved amount must be a non-negative number."

    if saved > target:
        return None, "Saved amount cannot exceed the target amount."

    if not deadline:
        return None, "Deadline is required."
    try:
        dt_datetime.strptime(deadline, "%Y-%m-%d")
    except ValueError:
        return None, "Deadline must be a valid date (YYYY-MM-DD)."

    return {
        "name": name,
        "category": category,
        "target_amount": target,
        "saved_amount": saved,
        "deadline": deadline,
        "status": status,
    }, None


@app.route("/goals")
def goals():
    """Render the Goals dashboard with database-backed data.

    Supports optional status, category, and sort filters via GET query
    parameters. Returns goal cards, summary stats, insights, quick actions,
    and recent activity — all computed from the user's real goal rows.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    user_id = session["user_id"]
    filters = _parse_goal_filters()

    goal_data = db_get_goal_data(
        user_id,
        status=filters["status"] or None,
        category=filters["category"] or None,
        sort=filters["sort"],
    )

    return render_template(
        "goals.html",
        goal=goal_data,
        goal_categories=GOAL_CATEGORY_NAMES,
        goal_statuses=list(GOAL_STATUSES),
        goal_icons=GOAL_CATEGORY_ICONS,
        goal_colors=GOAL_CATEGORY_COLORS,
        goal_sort_options=list(GOAL_SORT_OPTIONS.keys()),
        filters=filters,
        query_args=_goal_query_args(filters),
    )


@app.route("/goals/add", methods=["POST"])
def add_goal():
    """Create a new goal for the logged-in user.

    Validates all form fields, creates the goal row, and redirects back to
    /goals preserving the active filter state.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    data, error = _validate_goal_form()
    if error:
        flash(error, "error")
        return redirect(url_for("goals", **_goal_query_args(_parse_goal_filters())))

    try:
        db_create_goal(
            session["user_id"],
            data["name"],
            data["category"],
            data["target_amount"],
            data["saved_amount"],
            data["deadline"],
            data["status"],
        )
    except sqlite3.IntegrityError:
        flash("Could not save the goal — please try again.", "error")
        return redirect(url_for("goals", **_goal_query_args(_parse_goal_filters())))

    flash(f"Goal '{data['name']}' created successfully!", "success")
    return redirect(url_for("goals", **_goal_query_args(_parse_goal_filters())))


@app.route("/goals/<int:goal_id>/edit", methods=["POST"])
def edit_goal(goal_id):
    """Update an existing goal (ownership enforced).

    Validates all form fields. Returns 404 if the goal does not exist,
    403 if it belongs to another user.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    goal = db_get_goal_by_id(goal_id, session["user_id"])
    if goal is None:
        abort(404)

    data, error = _validate_goal_form()
    if error:
        flash(error, "error")
        return redirect(url_for("goals", **_goal_query_args(_parse_goal_filters())))

    updated = db_update_goal(
        goal_id,
        session["user_id"],
        data["name"],
        data["category"],
        data["target_amount"],
        data["saved_amount"],
        data["deadline"],
        data["status"],
    )
    if not updated:
        abort(403)

    flash(f"Goal '{data['name']}' updated successfully!", "success")
    return redirect(url_for("goals", **_goal_query_args(_parse_goal_filters())))


@app.route("/goals/<int:goal_id>/delete", methods=["POST"])
def delete_goal_view(goal_id):
    """Delete a goal (ownership enforced).

    Returns 404 if the goal does not exist, 403 if it belongs to another user.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    goal = db_get_goal_by_id(goal_id, session["user_id"])
    if goal is None:
        abort(404)

    deleted = db_delete_goal(goal_id, session["user_id"])
    if not deleted:
        abort(403)

    flash(f"Goal '{goal['name']}' deleted.", "success")
    return redirect(url_for("goals", **_goal_query_args(_parse_goal_filters())))


@app.route("/goals/<int:goal_id>/funds", methods=["POST"])
def add_goal_funds_view(goal_id):
    """Add funds to a goal (ownership enforced).

    Validates the amount as a positive number. The saved amount is capped at
    the target; reaching the target marks the goal as completed. Returns 404
    if the goal does not exist, 403 if it belongs to another user.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    goal = db_get_goal_by_id(goal_id, session["user_id"])
    if goal is None:
        abort(404)

    amount_raw = request.form.get("amount", "").strip()
    try:
        amount = float(amount_raw)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        flash("Amount must be a positive number.", "error")
        return redirect(url_for("goals", **_goal_query_args(_parse_goal_filters())))

    updated = db_add_goal_funds(goal_id, session["user_id"], amount)
    if updated is None:
        abort(403)

    flash(f"Added ₹{amount:,.2f} to '{updated['name']}'.", "success")
    return redirect(url_for("goals", **_goal_query_args(_parse_goal_filters())))


@app.route("/goals/export")
def goals_export():
    """Export the user's goals as a CSV file.

    Exports name, category, target, saved, progress %, deadline, and status
    for every goal owned by the user. Returns a text/csv attachment.
    """
    redirect_resp = login_required()
    if redirect_resp:
        return redirect_resp

    user_id = session["user_id"]
    goals_list = db_get_user_goals(user_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Name", "Category", "Target", "Saved", "Progress %", "Deadline", "Status",
    ])
    for g in goals_list:
        writer.writerow([
            g["name"],
            g["category"],
            f"{g['target_amount']:.2f}",
            f"{g['saved_amount']:.2f}",
            f"{g['progress']:.1f}",
            g["deadline"],
            g["effective_status"],
        ])

    from flask import Response
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=spendly-goals.csv"},
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
