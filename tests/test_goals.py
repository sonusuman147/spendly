"""Tests for the Goals module.

Covers the database helpers (CRUD, progress computation, add funds, goal data)
and the /goals routes (render, add, edit, delete, funds, export) including
authentication, ownership, and validation rules.
"""

import io
import csv

import pytest


# =================================================================== #
# Unit tests — goal CRUD                                              #
# =================================================================== #

class TestGoalCRUD:
    """Verify create / read / update / delete goal helpers."""

    def test_create_goal_returns_id(self, db):
        """create_goal should return the new goal id."""
        gid = db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        assert gid > 0
        goal = db.get_goal_by_id(gid, 1)
        assert goal["name"] == "Goa Trip"
        assert goal["category"] == "Travel"
        assert goal["target_amount"] == pytest.approx(60000.0, rel=1e-9)
        assert goal["saved_amount"] == pytest.approx(10000.0, rel=1e-9)
        assert goal["deadline"] == "2026-12-31"
        assert goal["status"] == "on-track"

    def test_get_goal_by_id_ownership_scoped(self, db):
        """get_goal_by_id should return None for another user's goal."""
        user2_id = db.create_user("Owner2", "owner2@test.com", password_hash="x")
        gid = db.create_goal(user2_id, "Goal2", "Travel", 10000, 0, "2026-12-31", "on-track")
        assert db.get_goal_by_id(gid, user2_id) is not None
        assert db.get_goal_by_id(gid, 1) is None

    def test_get_goal_by_id_not_found(self, db):
        """get_goal_by_id for a non-existent id should return None."""
        assert db.get_goal_by_id(99999, 1) is None

    def test_update_goal(self, db):
        """update_goal should update the goal fields."""
        gid = db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        updated = db.update_goal(gid, 1, "Goa Trip 2026", "Travel", 70000, 20000, "2027-01-15", "at-risk")
        assert updated is True
        goal = db.get_goal_by_id(gid, 1)
        assert goal["name"] == "Goa Trip 2026"
        assert goal["target_amount"] == pytest.approx(70000.0, rel=1e-9)
        assert goal["saved_amount"] == pytest.approx(20000.0, rel=1e-9)
        assert goal["deadline"] == "2027-01-15"
        assert goal["status"] == "at-risk"

    def test_update_goal_not_found(self, db):
        """update_goal for a non-existent goal should return False."""
        assert db.update_goal(99999, 1, "X", "Travel", 100, 0, "2026-12-31", "on-track") is False

    def test_delete_goal(self, db):
        """delete_goal should remove the row."""
        gid = db.create_goal(1, "Goa Trip", "Travel", 60000, 0, "2026-12-31", "on-track")
        deleted = db.delete_goal(gid, 1)
        assert deleted is True
        assert db.get_goal_by_id(gid, 1) is None

    def test_delete_goal_not_found(self, db):
        """delete_goal for a non-existent goal should return False."""
        assert db.delete_goal(99999, 1) is False


# =================================================================== #
# Unit tests — progress & status                                      #
# =================================================================== #

class TestGoalProgress:
    """Verify progress computation and effective status."""

    def test_progress_computed(self, db):
        """get_user_goals should include a progress percentage."""
        gid = db.create_goal(1, "Goa Trip", "Travel", 60000, 30000, "2026-12-31", "on-track")
        goals = db.get_user_goals(1)
        g = [x for x in goals if x["id"] == gid][0]
        assert g["progress"] == pytest.approx(50.0, rel=1e-9)

    def test_effective_status_completed_when_saved_equals_target(self, db):
        """A goal with saved == target should be completed."""
        gid = db.create_goal(1, "Laptop", "Gadgets", 50000, 50000, "2026-12-31", "on-track")
        goal = db.get_goal_by_id(gid, 1)
        assert goal["effective_status"] == "completed"

    def test_effective_status_at_risk_below_40(self, db):
        """A goal below 40% progress should be at-risk."""
        gid = db.create_goal(1, "Home", "Home", 100000, 30000, "2026-12-31", "on-track")
        goal = db.get_goal_by_id(gid, 1)
        assert goal["effective_status"] == "at-risk"

    def test_effective_status_on_track(self, db):
        """A goal at 50% should be on-track."""
        gid = db.create_goal(1, "Trip", "Travel", 100000, 50000, "2026-12-31", "on-track")
        goal = db.get_goal_by_id(gid, 1)
        assert goal["effective_status"] == "on-track"

    def test_paused_status_preserved(self, db):
        """A paused goal should stay paused regardless of progress."""
        gid = db.create_goal(1, "Paused Goal", "Travel", 100000, 50000, "2026-12-31", "paused")
        goal = db.get_goal_by_id(gid, 1)
        assert goal["effective_status"] == "paused"


# =================================================================== #
# Unit tests — add funds                                              #
# =================================================================== #

class TestAddGoalFunds:
    """Verify the add_goal_funds helper."""

    def test_add_funds_increases_saved(self, db):
        """Adding funds should increase saved_amount."""
        gid = db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        updated = db.add_goal_funds(gid, 1, 5000)
        assert updated["saved_amount"] == pytest.approx(15000.0, rel=1e-9)

    def test_add_funds_caps_at_target(self, db):
        """Adding funds beyond the target should cap at the target."""
        gid = db.create_goal(1, "Goa Trip", "Travel", 60000, 55000, "2026-12-31", "on-track")
        updated = db.add_goal_funds(gid, 1, 10000)
        assert updated["saved_amount"] == pytest.approx(60000.0, rel=1e-9)

    def test_add_funds_marks_completed(self, db):
        """Reaching the target should mark the goal as completed."""
        gid = db.create_goal(1, "Goa Trip", "Travel", 60000, 55000, "2026-12-31", "on-track")
        updated = db.add_goal_funds(gid, 1, 5000)
        assert updated["status"] == "completed"
        assert updated["effective_status"] == "completed"

    def test_add_funds_not_found(self, db):
        """Adding funds to a non-existent goal should return None."""
        assert db.add_goal_funds(99999, 1, 1000) is None

    def test_add_funds_ownership(self, db):
        """Adding funds to another user's goal should return None."""
        user2_id = db.create_user("Owner2", "owner2@test.com", password_hash="x")
        gid = db.create_goal(user2_id, "Goal2", "Travel", 10000, 0, "2026-12-31", "on-track")
        assert db.add_goal_funds(gid, 1, 1000) is None


# =================================================================== #
# Unit tests — get_goal_data                                          #
# =================================================================== #

class TestGetGoalData:
    """Verify the goal data computation."""

    def test_returns_goal_list(self, db):
        """get_goal_data should return a list of goals."""
        db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        data = db.get_goal_data(1)
        assert data["goals"]
        for g in data["goals"]:
            assert "name" in g
            assert "category" in g
            assert "target_amount" in g
            assert "saved_amount" in g
            assert "deadline" in g
            assert "status" in g
            assert "progress" in g
            assert "effective_status" in g

    def test_summary_cards(self, db):
        """The summary should include all five card values."""
        db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        db.create_goal(1, "Laptop", "Gadgets", 50000, 50000, "2026-12-31", "on-track")
        data = db.get_goal_data(1)
        s = data["summary"]
        assert "total_goals" in s
        assert "on_track" in s
        assert "completed" in s
        assert "total_saved" in s
        assert "remaining" in s
        assert s["total_goals"] == 2
        assert s["completed"] == 1
        assert s["total_saved"] == pytest.approx(60000.0, rel=1e-9)

    def test_insights_generated(self, db):
        """Insights should be a non-empty list."""
        db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        data = db.get_goal_data(1)
        assert data["insights"]
        for insight in data["insights"]:
            assert "icon" in insight
            assert "accent" in insight
            assert "title" in insight
            assert "text" in insight

    def test_activity_timeline(self, db):
        """Activity should be a list (possibly empty)."""
        data = db.get_goal_data(1)
        assert isinstance(data["activity"], list)

    def test_filter_by_category(self, db):
        """Category filter should narrow the goal list."""
        db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        db.create_goal(1, "Laptop", "Gadgets", 50000, 50000, "2026-12-31", "on-track")
        data = db.get_goal_data(1, category="Travel")
        assert len(data["goals"]) == 1
        assert data["goals"][0]["category"] == "Travel"

    def test_filter_by_status(self, db):
        """Status filter should narrow the goal list."""
        db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        db.create_goal(1, "Laptop", "Gadgets", 50000, 50000, "2026-12-31", "on-track")
        data = db.get_goal_data(1, status="completed")
        assert len(data["goals"]) == 1
        assert data["goals"][0]["effective_status"] == "completed"

    def test_sort_by_target_desc(self, db):
        """Sort by target descending should order goals correctly."""
        db.create_goal(1, "Small", "Travel", 10000, 0, "2026-12-31", "on-track")
        db.create_goal(1, "Large", "Travel", 90000, 0, "2026-12-31", "on-track")
        data = db.get_goal_data(1, sort="target-desc")
        assert data["goals"][0]["name"] == "Large"
        assert data["goals"][1]["name"] == "Small"


# =================================================================== #
# Route tests — GET /goals                                            #
# =================================================================== #

class TestGoalsRoute:
    """Verify the main Goals page."""

    def test_redirect_unauthenticated(self, client):
        """GET /goals without a session should redirect to /login."""
        resp = client.get("/goals", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.location

    def test_authenticated_returns_200(self, client):
        """GET /goals while logged in should return 200."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/goals")
        assert resp.status_code == 200

    def test_shows_summary_cards(self, client):
        """The page should show all five summary-card values."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/goals")
        assert resp.status_code == 200
        assert b"Total Goals" in resp.data
        assert b"On Track" in resp.data
        assert b"Completed" in resp.data
        assert b"Total Saved" in resp.data
        assert b"Remaining" in resp.data

    def test_shows_empty_state(self, client):
        """With no goals, the page should show the empty state."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/goals")
        assert resp.status_code == 200
        assert b"No goals match your filters" in resp.data

    def test_shows_goal_rows(self, client, db):
        """The page should contain server-rendered goal rows."""
        db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/goals")
        assert resp.status_code == 200
        assert b"Goa Trip" in resp.data
        assert b"Travel" in resp.data

    def test_filter_by_category(self, client, db):
        """Category filter should narrow the rendered goal rows."""
        db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        db.create_goal(1, "Laptop", "Gadgets", 50000, 50000, "2026-12-31", "on-track")
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/goals?category=Travel")
        assert resp.status_code == 200
        # The rendered card section should contain only the filtered goal.
        assert b'data-goal-id="1"' in resp.data
        assert b'data-goal-id="2"' not in resp.data
        assert b"Showing 1 goal" in resp.data

    def test_filter_by_status(self, client, db):
        """Status filter should narrow the rendered goal rows."""
        db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        db.create_goal(1, "Laptop", "Gadgets", 50000, 50000, "2026-12-31", "on-track")
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/goals?status=completed")
        assert resp.status_code == 200
        # The rendered card section should contain only the completed goal.
        assert b'data-goal-id="2"' in resp.data
        assert b'data-goal-id="1"' not in resp.data
        assert b"Showing 1 goal" in resp.data


# =================================================================== #
# Route tests — goal CRUD                                             #
# =================================================================== #

class TestGoalCRUDRoutes:
    """Verify add/edit/delete/funds goal routes."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1

    def test_add_goal_valid(self, client, db):
        """POST a valid goal should create it and redirect."""
        self._login(client)
        resp = client.post("/goals/add", data={
            "name": "Goa Trip",
            "category": "Travel",
            "target_amount": "60000",
            "saved_amount": "10000",
            "deadline": "2026-12-31",
            "status": "on-track",
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "/goals" in resp.location
        goals = db.get_user_goals(1)
        assert any(g["name"] == "Goa Trip" for g in goals)

    def test_add_goal_missing_name(self, client):
        """Posting without a name should flash an error."""
        self._login(client)
        resp = client.post("/goals/add", data={
            "name": "",
            "category": "Travel",
            "target_amount": "60000",
            "saved_amount": "0",
            "deadline": "2026-12-31",
            "status": "on-track",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Goal name is required" in resp.data

    def test_add_goal_invalid_category(self, client):
        """Posting an invalid category should flash an error."""
        self._login(client)
        resp = client.post("/goals/add", data={
            "name": "Test",
            "category": "NotARealCategory",
            "target_amount": "60000",
            "saved_amount": "0",
            "deadline": "2026-12-31",
            "status": "on-track",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"valid category" in resp.data

    def test_add_goal_invalid_target(self, client):
        """Posting a non-positive target should flash an error."""
        self._login(client)
        resp = client.post("/goals/add", data={
            "name": "Test",
            "category": "Travel",
            "target_amount": "0",
            "saved_amount": "0",
            "deadline": "2026-12-31",
            "status": "on-track",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"positive number" in resp.data

    def test_add_goal_saved_exceeds_target(self, client):
        """Posting saved > target should flash an error."""
        self._login(client)
        resp = client.post("/goals/add", data={
            "name": "Test",
            "category": "Travel",
            "target_amount": "10000",
            "saved_amount": "20000",
            "deadline": "2026-12-31",
            "status": "on-track",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"cannot exceed" in resp.data

    def test_add_goal_invalid_deadline(self, client):
        """Posting an invalid deadline should flash an error."""
        self._login(client)
        resp = client.post("/goals/add", data={
            "name": "Test",
            "category": "Travel",
            "target_amount": "10000",
            "saved_amount": "0",
            "deadline": "not-a-date",
            "status": "on-track",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"valid date" in resp.data

    def test_edit_goal_updates(self, client, db):
        """POST an edit should update the goal."""
        self._login(client)
        gid = db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        resp = client.post(f"/goals/{gid}/edit", data={
            "name": "Goa Trip 2026",
            "category": "Travel",
            "target_amount": "70000",
            "saved_amount": "20000",
            "deadline": "2027-01-15",
            "status": "at-risk",
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "/goals" in resp.location
        goal = db.get_goal_by_id(gid, 1)
        assert goal["name"] == "Goa Trip 2026"
        assert goal["target_amount"] == pytest.approx(70000.0, rel=1e-9)

    def test_edit_goal_not_found(self, client):
        """Editing a non-existent goal should return 404."""
        self._login(client)
        resp = client.post("/goals/99999/edit", data={
            "name": "X", "category": "Travel", "target_amount": "100",
            "saved_amount": "0", "deadline": "2026-12-31", "status": "on-track",
        }, follow_redirects=False)
        assert resp.status_code == 404

    def test_delete_goal_route(self, client, db):
        """POST delete should remove the goal and redirect."""
        self._login(client)
        gid = db.create_goal(1, "Goa Trip", "Travel", 60000, 0, "2026-12-31", "on-track")
        resp = client.post(f"/goals/{gid}/delete", follow_redirects=False)
        assert resp.status_code == 302
        assert "/goals" in resp.location
        assert db.get_goal_by_id(gid, 1) is None

    def test_delete_goal_not_found(self, client):
        """Deleting a non-existent goal should return 404."""
        self._login(client)
        resp = client.post("/goals/99999/delete", follow_redirects=False)
        assert resp.status_code == 404

    def test_add_funds_route(self, client, db):
        """POST funds should increase saved_amount."""
        self._login(client)
        gid = db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        resp = client.post(f"/goals/{gid}/funds", data={"amount": "5000"}, follow_redirects=False)
        assert resp.status_code == 302
        assert "/goals" in resp.location
        goal = db.get_goal_by_id(gid, 1)
        assert goal["saved_amount"] == pytest.approx(15000.0, rel=1e-9)

    def test_add_funds_invalid_amount(self, client, db):
        """Posting a non-positive amount should flash an error."""
        self._login(client)
        gid = db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        resp = client.post(f"/goals/{gid}/funds", data={"amount": "0"}, follow_redirects=True)
        assert resp.status_code == 200
        assert b"positive number" in resp.data

    def test_add_funds_not_found(self, client):
        """Adding funds to a non-existent goal should return 404."""
        self._login(client)
        resp = client.post("/goals/99999/funds", data={"amount": "1000"}, follow_redirects=False)
        assert resp.status_code == 404


# =================================================================== #
# Route tests — export                                                #
# =================================================================== #

class TestGoalsExportRoute:
    """Verify CSV export behaviour."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1

    def test_redirect_unauthenticated(self, client):
        """Export without a session should redirect to /login."""
        resp = client.get("/goals/export", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.location

    def test_export_returns_csv(self, client, db):
        """Export should return a text/csv attachment with a header row."""
        db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        self._login(client)
        resp = client.get("/goals/export")
        assert resp.status_code == 200
        assert resp.mimetype == "text/csv"
        assert "attachment" in resp.headers.get("Content-Disposition", "")
        text = resp.data.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        assert rows[0] == ["Name", "Category", "Target", "Saved", "Progress %", "Deadline", "Status"]
        assert len(rows) >= 2  # header + at least 1 goal

    def test_export_includes_goal(self, client, db):
        """Export should reflect the user's goals."""
        db.create_goal(1, "Goa Trip", "Travel", 60000, 10000, "2026-12-31", "on-track")
        self._login(client)
        resp = client.get("/goals/export")
        text = resp.data.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        goal_rows = [r for r in rows[1:] if r[0] == "Goa Trip"]
        assert goal_rows and goal_rows[0][1] == "Travel"
        assert goal_rows[0][2] == "60000.00"
        assert goal_rows[0][3] == "10000.00"