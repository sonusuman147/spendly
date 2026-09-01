"""Tests for Step 06 — Backend Routes for Profile Page.

Tests are divided into two groups:
  1. Unit tests — verify database helper functions directly.
  2. Route tests — verify the /profile endpoint behaviour.
"""

import pytest


# =================================================================== #
# Unit tests — get_user_by_id                                         #
# =================================================================== #

class TestGetUserById:
    """Verify get_user_by_id() behaviour."""

    def test_valid_user_returns_expected_fields(self, db):
        """get_user_by_id(1) should return name, email, member_since."""
        user = db.get_user_by_id(1)
        assert user is not None
        assert user["name"] == "Demo User"
        assert user["email"] == "demo@spendly.com"

    def test_valid_user_has_member_since(self, db):
        """member_since should be formatted as 'Month YYYY'."""
        user = db.get_user_by_id(1)
        assert user is not None
        assert "member_since" in user
        # Matches patterns like "January 2026", "Dec 2026" — any valid month + year
        import re
        assert re.match(r"^[A-Z][a-z]+ \d{4}$", user["member_since"]), \
            f"Expected 'Month YYYY' format, got '{user['member_since']}'"

    def test_nonexistent_user_returns_none(self, db):
        """get_user_by_id(9999) should return None."""
        user = db.get_user_by_id(9999)
        assert user is None


# =================================================================== #
# Unit tests — get_user_expenses_summary                              #
# =================================================================== #

class TestGetUserExpensesSummary:
    """Verify get_user_expenses_summary() behaviour."""

    def test_summary_with_expenses(self, db):
        """Seed user should have correct totals."""
        summary = db.get_user_expenses_summary(1)
        assert summary["total_expenses"] == pytest.approx(5170.0, rel=1e-9)
        assert summary["expense_count"] == 8
        assert summary["top_category"] == "Bills"

    def test_recent_expenses_ordered_newest_first(self, db):
        """Recent expenses should be ordered by date descending, max 5."""
        summary = db.get_user_expenses_summary(1)
        recent = summary["recent_expenses"]
        assert len(recent) <= 5
        if len(recent) > 1:
            dates = [exp["date"] for exp in recent]
            assert dates == sorted(dates, reverse=True), \
                "Recent expenses not in newest-first order"

    def test_recent_expenses_have_required_fields(self, db):
        """Each recent expense should have amount, category, date, description."""
        summary = db.get_user_expenses_summary(1)
        for exp in summary["recent_expenses"]:
            assert "amount" in exp
            assert "category" in exp
            assert "date" in exp
            assert "description" in exp

    def test_category_breakdown_ordered_by_total_desc(self, db):
        """Category breakdown should be ordered by total descending."""
        summary = db.get_user_expenses_summary(1)
        breakdown = summary["category_breakdown"]
        totals = [cat["total"] for cat in breakdown]
        assert totals == sorted(totals, reverse=True), \
            "Category breakdown not in descending order"

    def test_category_breakdown_contains_expected_categories(self, db):
        """Seed user should have expenses across expected categories."""
        summary = db.get_user_expenses_summary(1)
        categories = {cat["category"] for cat in summary["category_breakdown"]}
        assert "Food" in categories
        assert "Bills" in categories
        assert "Transport" in categories

    def test_summary_no_expenses(self, db):
        """A user with no expenses should get zeros and empty lists."""
        # Create a new user with no expenses
        user_id = db.create_user("Empty User", "empty@test.com", password_hash="x")
        summary = db.get_user_expenses_summary(user_id)
        assert summary["total_expenses"] == 0.0
        assert summary["expense_count"] == 0
        assert summary["top_category"] == "—"
        assert summary["category_breakdown"] == []
        assert summary["recent_expenses"] == []

    def test_category_breakdown_pct_approximation(self, db):
        """Category bar widths (computed in template) should be reasonable."""
        summary = db.get_user_expenses_summary(1)
        total = summary["total_expenses"]
        for cat in summary["category_breakdown"]:
            pct = round(cat["total"] / total * 100) if total > 0 else 0
            assert 0 <= pct <= 100
            assert isinstance(pct, int)


# =================================================================== #
# Route tests — GET /profile                                          #
# =================================================================== #

class TestProfileRoute:
    """Verify GET /profile endpoint behaviour."""

    def test_redirect_unauthenticated(self, client):
        """GET /profile without session should redirect to /login."""
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.location.endswith("/login") or "/login" in resp.location

    def test_authenticated_returns_200(self, client):
        """GET /profile while logged in should return 200."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/dashboard")
        assert resp.status_code == 200

    def test_authenticated_shows_user_name(self, client):
        """Profile page should display the logged-in user's name."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert b"Demo User" in resp.data

    def test_authenticated_shows_user_email(self, client):
        """Profile page should display the logged-in user's email."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert b"demo@spendly.com" in resp.data

    def test_authenticated_shows_rupee_symbol(self, client):
        """Profile page should display the ₹ symbol on amounts."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert b"\xe2\x82\xb9" in resp.data  # UTF-8 bytes for ₹

    def test_authenticated_shows_member_since(self, client):
        """Profile page should show 'Member since' with formatted date."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert b"Member since" in resp.data

    def test_orphaned_session_cleared(self, client):
        """A session with a non-existent user_id should be cleared."""
        with client.session_transaction() as sess:
            sess["user_id"] = 9999
        resp = client.get("/dashboard", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.location



class TestInsightsRoute:
    def test_unauthenticated_redirect(self, client):
        resp = client.get('/insights', follow_redirects=False)
        assert resp.status_code == 302
        assert '/login' in resp.location

    def test_authenticated_returns_200(self, client):
        with client.session_transaction() as sess:
            sess['user_id'] = 1
        resp = client.get('/insights')
        assert resp.status_code == 200
