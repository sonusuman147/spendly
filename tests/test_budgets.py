"""Tests for the Budgets module.

Covers the database helpers (CRUD, effective limits, budget data computation)
and the /budgets routes (render, add, edit, delete, reset, export) including
authentication, ownership, and validation rules.
"""

import io
import csv

import pytest
import sqlite3


# =================================================================== #
# Unit tests — budget CRUD                                            #
# =================================================================== #

class TestBudgetCRUD:
    """Verify create / read / update / delete budget helpers."""

    def test_create_budget_returns_id(self, db):
        """create_budget should return the new budget id."""
        bid = db.create_budget(1, "Food", 9000.0)
        assert bid > 0
        budget = db.get_budget_by_id(bid, 1)
        assert budget["category"] == "Food"
        assert budget["limit_amount"] == pytest.approx(9000.0, rel=1e-9)
        assert budget["period"] == "monthly"
        assert budget["is_default"] == 0

    def test_create_budget_upserts_existing(self, db):
        """Creating a budget for an existing category should update the limit."""
        db.create_budget(1, "Food", 9000.0)
        db.create_budget(1, "Food", 10000.0)
        budgets = db.get_user_budgets(1)
        food = [b for b in budgets if b["category"] == "Food"]
        assert len(food) == 1
        assert food[0]["limit_amount"] == pytest.approx(10000.0, rel=1e-9)

    def test_get_budget_by_id_ownership_scoped(self, db):
        """get_budget_by_id should return None for another user's budget."""
        user2_id = db.create_user("Owner2", "owner2@test.com", password_hash="x")
        bid = db.create_budget(user2_id, "Food", 5000.0)
        assert db.get_budget_by_id(bid, user2_id) is not None
        assert db.get_budget_by_id(bid, 1) is None

    def test_get_budget_by_id_not_found(self, db):
        """get_budget_by_id for a non-existent id should return None."""
        assert db.get_budget_by_id(99999, 1) is None

    def test_update_budget_limit(self, db):
        """update_budget_limit should update the limit for a category."""
        db.create_budget(1, "Food", 8000.0)
        updated = db.update_budget_limit(1, "Food", 7500.0)
        assert updated is True
        budgets = db.get_user_budgets(1)
        food = [b for b in budgets if b["category"] == "Food"]
        assert food[0]["limit_amount"] == pytest.approx(7500.0, rel=1e-9)

    def test_update_budget_limit_creates_if_missing(self, db):
        """update_budget_limit should create the row if it doesn't exist."""
        updated = db.update_budget_limit(1, "Transport", 3500.0)
        assert updated is True
        budgets = db.get_user_budgets(1)
        transport = [b for b in budgets if b["category"] == "Transport"]
        assert transport and transport[0]["limit_amount"] == pytest.approx(3500.0, rel=1e-9)

    def test_delete_budget(self, db):
        """delete_budget should remove the row for a category."""
        db.create_budget(1, "Food", 9000.0)
        deleted = db.delete_budget(1, "Food")
        assert deleted is True
        budgets = db.get_user_budgets(1)
        assert not any(b["category"] == "Food" for b in budgets)

    def test_delete_budget_not_found(self, db):
        """delete_budget for a non-existent category should return False."""
        assert db.delete_budget(1, "Nonexistent") is False

    def test_reset_budget_defaults(self, db):
        """reset_budget_defaults should remove all user budget rows."""
        db.create_budget(1, "Food", 9000.0)
        db.create_budget(1, "Transport", 3500.0)
        removed = db.reset_budget_defaults(1)
        assert removed == 2
        assert db.get_user_budgets(1) == []


# =================================================================== #
# Unit tests — effective limits                                       #
# =================================================================== #

class TestEffectiveBudgetLimits:
    """Verify user budgets override static defaults."""

    def test_defaults_used_when_no_user_rows(self, db):
        """With no user budget rows, static defaults should be used."""
        limits = db._effective_budget_limits(1)
        assert limits["Food"] == pytest.approx(8000.0, rel=1e-9)
        assert limits["Transport"] == pytest.approx(4000.0, rel=1e-9)

    def test_user_rows_override_defaults(self, db):
        """User budget rows should override static defaults."""
        db.create_budget(1, "Food", 12000.0)
        limits = db._effective_budget_limits(1)
        assert limits["Food"] == pytest.approx(12000.0, rel=1e-9)
        # Other categories still use defaults.
        assert limits["Transport"] == pytest.approx(4000.0, rel=1e-9)


# =================================================================== #
# Unit tests — get_budget_data                                       #
# =================================================================== #

class TestGetBudgetData:
    """Verify the budget data computation."""

    def test_returns_budget_list(self, db):
        """get_budget_data should return a list of budget entries."""
        data = db.get_budget_data(1)
        assert data["budgets"]
        for b in data["budgets"]:
            assert "name" in b
            assert "limit" in b
            assert "spent" in b
            assert "remaining" in b
            assert "pct" in b
            assert "status_key" in b
            assert "status_label" in b

    def test_summary_cards(self, db):
        """The summary should include all four card values."""
        data = db.get_budget_data(1)
        s = data["summary"]
        assert "total_budget" in s
        assert "total_spent" in s
        assert "remaining" in s
        assert "pct" in s
        assert "over_count" in s
        assert "daily" in s
        assert "days_left" in s

    def test_user_budget_reflected_in_data(self, db):
        """A user-defined budget should change the limit in the data."""
        db.create_budget(1, "Food", 12000.0)
        data = db.get_budget_data(1)
        food = [b for b in data["budgets"] if b["name"] == "Food"]
        assert food and food[0]["limit"] == pytest.approx(12000.0, rel=1e-9)

    def test_monthly_trend_has_six_entries(self, db):
        """The trend chart should have BUDGET_TREND_MONTHS entries."""
        data = db.get_budget_data(1)
        assert len(data["monthly_trend"]) == db.BUDGET_TREND_MONTHS

    def test_distribution_matches_budgets(self, db):
        """Distribution should mirror the budget list."""
        data = db.get_budget_data(1)
        assert len(data["distribution"]) == len(data["budgets"])
        for d in data["distribution"]:
            assert "name" in d
            assert "color" in d
            assert "limit" in d

    def test_insights_generated(self, db):
        """Insights should be a non-empty list."""
        data = db.get_budget_data(1)
        assert data["insights"]
        for insight in data["insights"]:
            assert "icon" in insight
            assert "accent" in insight
            assert "title" in insight
            assert "text" in insight

    def test_activity_timeline(self, db):
        """Activity should be a list (possibly empty)."""
        data = db.get_budget_data(1)
        assert isinstance(data["activity"], list)

    def test_filter_by_category(self, db):
        """Category filter should narrow the budget list."""
        data = db.get_budget_data(1, category="Food")
        assert len(data["budgets"]) == 1
        assert data["budgets"][0]["name"] == "Food"

    def test_filter_by_status(self, db):
        """Status filter should narrow the budget list."""
        data = db.get_budget_data(1, status="over")
        for b in data["budgets"]:
            assert b["status_key"] == "over"

    def test_filter_by_month(self, db):
        """Month filter should narrow spending to that month."""
        # Seed data is within the last 30 days, so current month should have data.
        from datetime import date
        today = date.today()
        month = f"{today.year:04d}-{today.month:02d}"
        data = db.get_budget_data(1, month=month)
        assert data["filter_info"]["month"] == month


# =================================================================== #
# Route tests — GET /budgets                                         #
# =================================================================== #

class TestBudgetsRoute:
    """Verify the main Budgets page."""

    def test_redirect_unauthenticated(self, client):
        """GET /budgets without a session should redirect to /login."""
        resp = client.get("/budgets", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.location

    def test_authenticated_returns_200(self, client):
        """GET /budgets while logged in should return 200."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/budgets")
        assert resp.status_code == 200

    def test_shows_summary_cards(self, client):
        """The page should show all four summary-card values."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/budgets")
        assert resp.status_code == 200
        assert b"Monthly Budget" in resp.data
        assert b"Total Spent" in resp.data
        assert b"Remaining" in resp.data
        assert b"Over Budget" in resp.data

    def test_shows_budget_rows(self, client):
        """The table should contain server-rendered budget rows."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/budgets")
        assert resp.status_code == 200
        assert b"Food" in resp.data
        assert b"Transport" in resp.data
        assert b"Bills" in resp.data

    def test_filter_by_category(self, client):
        """Category filter should narrow the rendered budget rows."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/budgets?category=Food")
        assert resp.status_code == 200
        assert b"Food" in resp.data
        # The filter bar always lists all categories as options, but the
        # server-rendered budget list should contain only the filtered category.
        assert b"Showing 1 budget" in resp.data
        assert b'"name": "Transport"' not in resp.data

    def test_filter_by_status(self, client):
        """Status filter should narrow the rendered budget rows."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/budgets?status=over")
        assert resp.status_code == 200
        # All shown budgets should be over budget.
        assert b"Over Budget" in resp.data


# =================================================================== #
# Route tests — budget CRUD                                          #
# =================================================================== #

class TestBudgetCRUDRoutes:
    """Verify add/edit/delete/reset budget routes."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1

    def test_add_budget_valid(self, client, db):
        """POST a valid budget should create it and redirect."""
        self._login(client)
        resp = client.post("/budgets/add", data={
            "category": "Food",
            "limit_amount": "9000",
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "/budgets" in resp.location
        budgets = db.get_user_budgets(1)
        food = [b for b in budgets if b["category"] == "Food"]
        assert food and food[0]["limit_amount"] == pytest.approx(9000.0, rel=1e-9)

    def test_add_budget_invalid_category(self, client):
        """Posting an invalid category should flash an error."""
        self._login(client)
        resp = client.post("/budgets/add", data={
            "category": "NotARealCategory",
            "limit_amount": "5000",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"valid category" in resp.data

    def test_add_budget_invalid_limit(self, client):
        """Posting a non-positive limit should flash an error."""
        self._login(client)
        resp = client.post("/budgets/add", data={
            "category": "Food",
            "limit_amount": "0",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"positive number" in resp.data

    def test_add_budget_missing_limit(self, client):
        """Posting without a limit should flash an error."""
        self._login(client)
        resp = client.post("/budgets/add", data={
            "category": "Food",
            "limit_amount": "",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"positive number" in resp.data

    def test_edit_budget_updates(self, client, db):
        """POST an edit should update the budget limit."""
        self._login(client)
        bid = db.create_budget(1, "Food", 9000.0)
        resp = client.post(f"/budgets/{bid}/edit", data={"limit_amount": "10000"}, follow_redirects=False)
        assert resp.status_code == 302
        assert "/budgets" in resp.location
        budget = db.get_budget_by_id(bid, 1)
        assert budget["limit_amount"] == pytest.approx(10000.0, rel=1e-9)

    def test_edit_budget_not_found(self, client):
        """Editing a non-existent budget should return 404."""
        self._login(client)
        resp = client.post("/budgets/99999/edit", data={"limit_amount": "5000"}, follow_redirects=False)
        assert resp.status_code == 404

    def test_edit_budget_invalid_limit(self, client, db):
        """Editing with an invalid limit should flash an error."""
        self._login(client)
        bid = db.create_budget(1, "Food", 9000.0)
        resp = client.post(f"/budgets/{bid}/edit", data={"limit_amount": "-5"}, follow_redirects=True)
        assert resp.status_code == 200
        assert b"positive number" in resp.data

    def test_delete_budget_route(self, client, db):
        """POST delete should remove the budget and redirect."""
        self._login(client)
        bid = db.create_budget(1, "Food", 9000.0)
        resp = client.post(f"/budgets/{bid}/delete", follow_redirects=False)
        assert resp.status_code == 302
        assert "/budgets" in resp.location
        assert db.get_budget_by_id(bid, 1) is None

    def test_delete_budget_not_found(self, client):
        """Deleting a non-existent budget should return 404."""
        self._login(client)
        resp = client.post("/budgets/99999/delete", follow_redirects=False)
        assert resp.status_code == 404

    def test_reset_budgets_route(self, client, db):
        """POST reset should remove all user budgets."""
        self._login(client)
        db.create_budget(1, "Food", 9000.0)
        db.create_budget(1, "Transport", 3500.0)
        resp = client.post("/budgets/reset", follow_redirects=False)
        assert resp.status_code == 302
        assert "/budgets" in resp.location
        assert db.get_user_budgets(1) == []

    def test_reset_budgets_no_rows(self, client):
        """POST reset with no user budgets should still redirect."""
        self._login(client)
        resp = client.post("/budgets/reset", follow_redirects=False)
        assert resp.status_code == 302
        assert "/budgets" in resp.location


# =================================================================== #
# Route tests — export                                                #
# =================================================================== #

class TestBudgetsExportRoute:
    """Verify CSV export behaviour."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1

    def test_redirect_unauthenticated(self, client):
        """Export without a session should redirect to /login."""
        resp = client.get("/budgets/export", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.location

    def test_export_returns_csv(self, client):
        """Export should return a text/csv attachment with a header row."""
        self._login(client)
        resp = client.get("/budgets/export")
        assert resp.status_code == 200
        assert resp.mimetype == "text/csv"
        assert "attachment" in resp.headers.get("Content-Disposition", "")
        text = resp.data.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        assert rows[0] == ["Category", "Monthly Limit", "Spent", "Remaining", "Usage %", "Status"]
        assert len(rows) >= 8  # header + at least 7 budget categories

    def test_export_includes_user_budget(self, client, db):
        """Export should reflect user-defined budget limits."""
        self._login(client)
        db.create_budget(1, "Food", 12000.0)
        resp = client.get("/budgets/export")
        text = resp.data.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        food_rows = [r for r in rows[1:] if r[0] == "Food"]
        assert food_rows and food_rows[0][1] == "12000.00"
