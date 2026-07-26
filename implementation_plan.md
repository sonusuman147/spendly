# Implementation Plan

## Overview
Refine the existing Step 06 backend implementation for the profile page by fixing two rule deviations (`member_since` formatting, category percentage rounding) and adding the missing automated test suite — without restructuring the existing codebase or creating new files.

## Scope & Context
The core backend functionality for the profile page is already implemented and working. The `GET /profile` route, database helpers in `database/db.py`, template in `templates/profile.html`, and CSS in `static/css/profile.css` are all in place. This plan addresses only the remaining gaps identified in the spec verification:

1. **`member_since` date format** — currently displays raw `created_at` timestamp (e.g. "2026-01-15"), must display "Month YYYY" (e.g. "January 2026")
2. **Category bar percentage rounding** — currently each bar width is independently rounded, which can produce percentages that don't sum to 100. Must use a rounding algorithm (largest-category remainder adjustment) to guarantee a perfect sum.
3. **Missing test suite** — `tests/` directory does not exist. Must create `tests/conftest.py` (pytest-flask fixture setup) and `tests/test_backend_connection.py` with unit tests for DB helpers and route tests for the `/profile` endpoint.

## Types
No new types, classes, or data structures are introduced.

## Files

### Existing files to modify (2 files)
- `database/db.py` — Add a `get_member_since(user_id)` helper that formats `created_at` as "Month YYYY" using Python's `strftime("%B %Y")`. Alternatively, compute the formatted string in the existing `get_user_by_id()` function as an additional field.
- `templates/profile.html` — Update `{{ user.created_at[:10] }}` to `{{ user.member_since }}` to display the formatted date.

### New files to create (2 files)
- `tests/__init__.py` — Empty package init file.
- `tests/conftest.py` — pytest-flask application fixture that creates the Flask app in testing mode, initializes the database, and seeds test data. Provides a `client` fixture for route tests.
- `tests/test_backend_connection.py` — Full test suite with 10+ test cases covering:
  - Unit tests for `get_user_by_id()`, `get_user_expenses_summary()` edge cases
  - Route tests for `GET /profile` (unauthenticated redirect, authenticated rendering, data correctness)

### Files not modified
- `app.py` — No changes needed. The route already works correctly.
- `static/css/profile.css` — No changes needed.
- `.claude/specs/06-backend-routes-for-profile-page.md` — No changes needed.

## Functions

### Modified functions

| Function | File | Change |
|---|---|---|
| `get_user_by_id(user_id)` | `database/db.py` | Add a `member_since` field to the returned dict by formatting `created_at` as "Month YYYY" using `strftime("%B %Y")` |

### New functions

| Function | File | Purpose |
|---|---|---|
| `app()` | `tests/conftest.py` | Pytest-flask fixture that creates and configures the Flask app for testing |
| `client(app)` | `tests/conftest.py` | Pytest-flask client fixture for route testing |
| `test_get_user_by_id_valid()` | `tests/test_backend_connection.py` | Verify valid user returns correct name, email, member_since |
| `test_get_user_by_id_nonexistent()` | `tests/test_backend_connection.py` | Verify non-existent id returns None |
| `test_get_user_by_id_member_since_format()` | `tests/test_backend_connection.py` | Verify member_since is formatted as "Month YYYY" |
| `test_summary_stats_with_expenses()` | `tests/test_backend_connection.py` | Verify seed user has correct totals, count, top_category |
| `test_summary_stats_no_expenses()` | `tests/test_backend_connection.py` | Verify new user gets zeros and empty lists |
| `test_recent_expenses_ordering()` | `tests/test_backend_connection.py` | Verify recent_expenses are newest-first, max 5 |
| `test_category_breakdown_pct_sum()` | `tests/test_backend_connection.py` | Verify pct values are integers summing to 100 |
| `test_profile_redirect_unauthenticated()` | `tests/test_backend_connection.py` | GET /profile without session → 302 to /login |
| `test_profile_authenticated()` | `tests/test_backend_connection.py` | GET /profile as seed user → 200, contains name, email, ₹ |

## Classes
No class changes.

## Dependencies
No new dependencies. The existing `requirements.txt` already includes `flask`, `werkzeug`, `pytest`, and `pytest-flask` — all necessary for testing.

## Testing
The entire deliverable of this plan is the test suite. Key test scenarios:

### DB Helper Tests
1. `get_user_by_id(1)` → returns dict with `name="Demo User"`, `email="demo@spendly.com"`, `member_since` matching `strftime("%B %Y")` format
2. `get_user_by_id(9999)` → returns `None`
3. `get_user_expenses_summary(1)` → `total_expenses` matches seed data sum, `expense_count == 8`, `top_category == "Bills"`
4. `get_user_expenses_summary(new_user_id)` → `total_expenses == 0.0`, `expense_count == 0`, `top_category == "—"`, `category_breakdown == []`, `recent_expenses == []`

### Route Tests
5. `GET /profile` unauthenticated → 302 redirect to `/login`
6. `GET /profile` authenticated as seed user → 200 OK, response body contains "Demo User", "demo@spendly.com", "₹"

## Implementation Order

1. **Step 1: Update `database/db.py`** — Add `member_since` field to the dict returned by `get_user_by_id()`, formatting `created_at` with `strftime("%B %Y")`.

2. **Step 2: Update `templates/profile.html`** — Replace `{{ user.created_at[:10] }}` with `{{ user.member_since }}`.

3. **Step 3: Create `tests/__init__.py`** — Empty file to make `tests/` a Python package.

4. **Step 4: Create `tests/conftest.py`** — Pytest-flask fixture with app instance, DB init, and test client.

5. **Step 5: Create `tests/test_backend_connection.py`** — Full test suite with all unit and route tests.

6. **Step 6: Run tests** — Execute `pytest -v` to verify all tests pass.

7. **Step 7: Run app** — Execute `python app.py` to verify the app starts without errors and the profile page renders correctly.

## Verification

After implementation, run these commands to verify everything works:

```bash
# Start the application and verify no startup errors
python app.py
# (Run in background/separate terminal, then test with curl or browser)

# Run the test suite
pytest -v

# Run a specific test file
pytest tests/test_backend_connection.py -v
```

