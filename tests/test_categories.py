"""Tests for the Categories module.

Covers the database helpers (CRUD, stats, merge, export, delete-with-reassign)
and the /categories routes (render, add, edit, view, delete, merge, export,
analytics) including authentication, ownership, and validation rules.
"""

import io
import csv

import pytest
import sqlite3


# =================================================================== #
# Unit tests — ensure_default_categories / backfill                   #
# =================================================================== #

class TestDefaultCategories:
    """Verify default category seeding and migration safety."""

    def test_seed_creates_default_categories(self, db):
        """The demo user should have the 7 default category rows seeded."""
        cats = db.get_user_categories(1)
        names = {c["name"] for c in cats}
        assert {"Food", "Transport", "Bills", "Health",
                "Entertainment", "Shopping", "Other"} <= names

    def test_ensure_default_categories_idempotent(self, db):
        """Calling ensure_default_categories twice should not duplicate rows."""
        db.ensure_default_categories(1)
        before = len(db.get_user_categories(1))
        db.ensure_default_categories(1)
        after = len(db.get_user_categories(1))
        assert before == after

    def test_ensure_default_categories_adds_missing_used_names(self, db):
        """A user with an expense category missing a row should get one."""
        user_id = db.create_user("Cat Owner", "cat@test.com", password_hash="x")
        db.create_expense(user_id, 10.0, "Travel", "2026-01-01", "")
        db.ensure_default_categories(user_id)
        names = {c["name"] for c in db.get_user_categories(user_id)}
        assert "Travel" in names

    def test_backfill_categories_all_users(self, db):
        """backfill_categories shold seed defaults for every user."""
        db.create_user("Two", "two@test.com", password_hash="x")
        db.create_user("Three", "three@test.com", password_hash="x")
        db.backfill_categories()
        # Demo user (1) + two new users each get defaults.
        for uid in (1, 2, 3):
            cats = db.get_user_categories(uid)
            assert len(cats) >= 7


# =================================================================== #
# Unit tests — category CRUD                                          #
# =================================================================== #

class TestCategoryCRUD:
    """Verify create / read / update / delete category helpers."""

    def test_create_category_returns_id(self, db):
        """create_category should return the new category id."""
        cid = db.create_category(1, "Rent", "Housing", "home", "#2563eb")
        assert cid > 0
        cat = db.get_category_by_id(cid, 1)
        assert cat["name"] == "Rent"
        assert cat["description"] == "Housing"
        assert cat["icon"] == "home"
        assert cat["color"] == "#2563eb"

    def test_create_category_duplicate_raises(self, db):
        """Creating a category with a duplicate name should raise IntegrityError."""
        db.create_category(1, "Rent", "Housing", "home", "#2563eb")
        with pytest.raises(sqlite3.IntegrityError):
            db.create_category(1, "Rent", "Dup", "home", "#2563eb")

    def test_get_category_ownership_scoped(self, db):
        """get_category_by_id should return None for another user's category."""
        user_id = db.create_user("Owner2", "owner2@test.com", password_hash="x")
        cid = db.create_category(user_id, "Secret", "private", "lock", "#e11d48")
        assert db.get_category_by_id(cid, user_id) is not None
        assert db.get_category_by_id(cid, 1) is None

    def test_update_category_rename_keeps_expenses(self, db):
        """Renaming a category should rename its expenses too."""
        cid = db.create_category(1, "OldName", "desc", "tag", "#6b7280")
        db.create_expense(1, 50.0, "OldName", "2026-01-05", "test expense")
        updated = db.update_category(cid, 1, "NewName", "desc", "tag", "#6b7280")
        assert updated is True
        cat = db.get_category_by_id(cid, 1)
        assert cat["name"] == "NewName"
        expenses = db.get_expenses_by_user(1)
        assert any(e["category"] == "NewName" for e in expenses)

    def test_update_category_not_owned(self, db):
        """Updating another user's category should return False."""
        user_id = db.create_user("Owner3", "owner3@test.com", password_hash="x")
        cid = db.create_category(user_id, "Their", "d", "tag", "#6b7280")
        assert db.update_category(cid, 1, "Mine", "d", "tag", "#6b7280") is False

    def test_delete_category_reassigns_to_other(self, db):
        """Deleting a category should reassign expenses to Other."""
        cid = db.create_category(1, "DeleteMe", "desc", "tag", "#6b7280")
        db.create_expense(1, 20.0, "DeleteMe", "2026-01-06", "reassign me")
        assert db.get_category_by_id(cid, 1) is not None
        deleted = db.delete_category(cid, 1, reassign=True)
        assert deleted is True
        assert db.get_category_by_id(cid, 1) is None
        expenses = db.get_expenses_by_user(1)
        assert any(e["category"] == "Other" for e in expenses)


# =================================================================== #
# Unit tests — get_categories (search/sort/pagination/stats)          #
# =================================================================== #

class TestGetCategories:
    """Verify the paginated category listing with usage stats."""

    def test_returns_items_with_stats(self, db):
        """Each category item should include usage statistics."""
        result = db.get_categories(1, page=1, per_page=8)
        assert result["total"] >= 7
        assert result["page"] == 1
        assert result["has_prev"] is False
        for cat in result["items"]:
            assert "transaction_count" in cat
            assert "total_spent" in cat
            assert "avg_expense" in cat

    def test_search_by_name(self, db):
        """Search should match category names case-insensitively."""
        result = db.get_categories(1, search="food", page=1, per_page=8)
        assert any("food" in c["name"].lower() for c in result["items"])

    def test_search_by_description(self, db):
        """Search should match description text."""
        result = db.get_categories(1, search="electricity", page=1, per_page=8)
        assert any("electricity" in (c["description"] or "").lower() for c in result["items"])

    def test_sort_by_spent_desc(self, db):
        """Sort by spent-desc should put highest total first."""
        result = db.get_categories(1, sort="spent-desc", page=1, per_page=8)
        totals = [c["total_spent"] for c in result["items"]]
        assert totals == sorted(totals, reverse=True)

    def test_pagination_splits(self, db):
        """Adding many categories should split pages correctly."""
        for i in range(10):
            db.create_category(1, f"Custom {i}", f"cat {i}", "tag", "#6b7280")
        result = db.get_categories(1, page=1, per_page=8)
        assert result["total"] >= 17
        assert len(result["items"]) == 8
        assert result["has_next"] is True
        page2 = db.get_categories(1, page=2, per_page=8)
        assert len(page2["items"]) == 8
        assert page2["has_prev"] is True

    def test_stats_accurate(self, db):
        """Transaction count and totals should reflect real expenses."""
        # Seed data: Food has 2 expenses = 450 + 320 = 770.
        result = db.get_categories(1, search="Food", page=1, per_page=8)
        food = [c for c in result["items"] if c["name"] == "Food"]
        assert food
        assert food[0]["transaction_count"] == 2
        assert food[0]["total_spent"] == pytest.approx(770.0, rel=1e-9)
        assert food[0]["avg_expense"] == pytest.approx(385.0, rel=1e-9)


# =================================================================== #
# Unit tests — get_category_stats                                     #
# =================================================================== #

class TestCategoryStats:
    """Verify aggregate summary statistics."""

    def test_summary_cards(self, db):
        """The stats dict should include all four summary-card values."""
        stats = db.get_category_stats(1)
        assert stats["total_categories"] >= 7
        assert stats["most_used_category"] == "Food"
        assert stats["highest_spending_category"] == "Bills"
        assert stats["unused_categories"] >= 0
        assert stats["total_spent"] == pytest.approx(5170.0, rel=1e-9)

    def test_distribution_has_pcts(self, db):
        """Distribution entries should include colors and percentages."""
        stats = db.get_category_stats(1)
        assert stats["distribution"]
        total_pct = sum(d["pct"] for d in stats["distribution"])
        assert 99.0 <= total_pct <= 100.0 + 1e-6
        for d in stats["distribution"]:
            assert d["color"].startswith("#")
            assert d["total"] > 0

    def test_conic_gradient_built(self, db):
        """The conic-gradient string should be valid CSS."""
        stats = db.get_category_stats(1)
        assert stats["conic_gradient"].startswith("conic-gradient(")

    def test_ranking_ordered(self, db):
        """Ranking should be ordered by total spent descending."""
        stats = db.get_category_stats(1)
        totals = [r["total_spent"] for r in stats["ranking"]]
        assert totals == sorted(totals, reverse=True)


# =================================================================== #
# Unit tests — get_categories_export + merge                          #
# =================================================================== #

class TestCategoryExportAndMerge:
    """Verify CSV export rows and merge behaviour."""

    def test_export_rows(self, db):
        """Export should include name + usage stats per category."""
        rows = db.get_categories_export(1)
        assert len(rows) >= 7
        for row in rows:
            assert "name" in row
            assert "transaction_count" in row
            assert "total_spent" in row
            assert "avg_expense" in row

    def test_merge_expenses_reassigned(self, db):
        """Merging source into target should move expenses to target."""
        src = db.create_category(1, "Source", "src", "tag", "#6b7280")
        tgt = db.create_category(1, "Target", "tgt", "tag", "#6b7280")
        db.create_expense(1, 30.0, "Source", "2026-01-07", "move me")
        merged = db.merge_categories(1, src, tgt)
        assert merged is True
        assert db.get_category_by_id(src, 1) is None
        assert db.get_category_by_id(tgt, 1) is not None
        expenses = db.get_expenses_by_user(1)
        assert any(e["category"] == "Target" for e in expenses)

    def test_merge_same_ids_rejected(self, db):
        """Merging a category into itself should return False."""
        cid = db.create_category(1, "Solo", "d", "tag", "#6b7280")
        assert db.merge_categories(1, cid, cid) is False

    def test_merge_missing_ids_rejected(self, db):
        """Merging with invalid ids should return False."""
        assert db.merge_categories(1, 99999, 1) is False


# =================================================================== #
# Route tests — GET /categories                                      #
# =================================================================== #

class TestCategoriesRoute:
    """Verify the main Categories page."""

    def test_redirect_unauthenticated(self, client):
        """GET /categories without a session should redirect to /login."""
        resp = client.get("/categories", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.location

    def test_authenticated_returns_200(self, client):
        """GET /categories while logged in should return 200."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/categories")
        assert resp.status_code == 200

    def test_shows_summary_cards(self, client):
        """The page should show all four summary-card values."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/categories")
        assert resp.status_code == 200
        assert b"Total Categories" in resp.data
        assert b"Most Used Category" in resp.data
        assert b"Highest Spending Category" in resp.data
        assert b"Unused Categories" in resp.data
        assert b"Food" in resp.data  # most used category
        assert b"Bills" in resp.data  # highest spending

    def test_shows_category_rows(self, client):
        """The table should contain server-rendered category rows."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/categories")
        assert resp.status_code == 200
        assert b"Weekly groceries" not in resp.data  # expense desc, not category desc
        assert b"5170.00" in resp.data  # total spent across all categories

    def test_search_filters_rows(self, client):
        """Search should narrow the rendered category rows."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/categories?search=Food")
        assert resp.status_code == 200
        assert b"Food" in resp.data
        assert b"Electricity bill" not in resp.data


# =================================================================== #
# Route tests — category CRUD                                        #
# =================================================================== #

class TestCategoryCRUDRoutes:
    """Verify add/edit/delete category routes."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1

    def test_add_page_renders(self, client):
        """GET /categories/add should render the form."""
        self._login(client)
        resp = client.get("/categories/add")
        assert resp.status_code == 200
        assert b"Add Category" in resp.data

    def test_add_category_valid(self, client, db):
        """POST a valid category should create it and redirect."""
        self._login(client)
        resp = client.post("/categories/add", data={
            "name": "Rent",
            "description": "Housing",
            "icon": "home",
            "color": "#2563eb",
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert "/categories" in resp.location
        cat = db.create_category  # sanity import
        cats = db.get_user_categories(1)
        assert any(c["name"] == "Rent" for c in cats)

    def test_add_category_duplicate_name(self, client):
        """Posting a duplicate name should flash an error."""
        self._login(client)
        # Food already exists from seed.
        resp = client.post("/categories/add", data={
            "name": "Food",
            "description": "dup",
            "icon": "utensils",
            "color": "#dc2626",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"already exists" in resp.data

    def test_add_category_invalid_icon(self, client):
        """Posting an invalid icon should flash an error."""
        self._login(client)
        resp = client.post("/categories/add", data={
            "name": "BadIcon",
            "description": "",
            "icon": "not-a-real-icon",
            "color": "#2563eb",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"valid icon" in resp.data

    def test_add_category_missing_name(self, client):
        """Posting without a name should flash an error."""
        self._login(client)
        resp = client.post("/categories/add", data={
            "name": "",
            "description": "",
            "icon": "tag",
            "color": "#2563eb",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"name is required" in resp.data

    def test_edit_page_renders(self, client):
        """GET /categories/<id>/edit should render the form."""
        self._login(client)
        # Find the demo user's Food category id.
        from database.db import get_user_categories
        cats = get_user_categories(1)
        food = [c for c in cats if c["name"] == "Food"][0]
        resp = client.get(f"/categories/{food['id']}/edit")
        assert resp.status_code == 200
        assert b"Edit Category" in resp.data
        assert b"Food" in resp.data

    def test_edit_category_updates(self, client, db):
        """POST an edit should update the category."""
        self._login(client)
        from database.db import get_user_categories
        food = [c for c in get_user_categories(1) if c["name"] == "Food"][0]
        resp = client.post(f"/categories/{food['id']}/edit", data={
            "name": "Food & Dining",
            "description": "Updated description",
            "icon": "utensils",
            "color": "#dc2626",
        }, follow_redirects=False)
        assert resp.status_code == 302
        updated = db.get_category_by_id(food["id"], 1)
        assert updated["name"] == "Food & Dining"
        assert updated["description"] == "Updated description"

    def test_view_category_page(self, client, db):
        """GET /categories/<id> should render category details."""
        self._login(client)
        cid = db.get_user_categories(1)[0]["id"]
        resp = client.get(f"/categories/{cid}")
        assert resp.status_code == 200
        assert b"Category Details" in resp.data

    def test_view_category_not_found(self, client):
        """GET /categories/999999 should return 404."""
        self._login(client)
        resp = client.get("/categories/999999")
        assert resp.status_code == 404

    def test_delete_unused_category(self, client, db):
        """Deleting an unused category should not require confirmation."""
        self._login(client)
        cid = db.create_category(1, "UnusedCat", "d", "tag", "#6b7280")
        resp = client.get(f"/categories/{cid}/delete")
        assert resp.status_code == 200
        assert b"Delete Category" in resp.data
        # POST without confirm should still delete because it's not in use.
        resp = client.post(f"/categories/{cid}/delete", data={}, follow_redirects=False)
        assert resp.status_code == 302
        assert db.get_category_by_id(cid, 1) is None

    def test_delete_in_use_requires_confirmation(self, client, db):
        """Deleting an in-use category should require the confirm checkbox."""
        self._login(client)
        from database.db import get_user_categories
        food = [c for c in get_user_categories(1) if c["name"] == "Food"][0]
        # Without confirm — should flash error and NOT delete.
        resp = client.post(f"/categories/{food['id']}/delete", data={},
                           follow_redirects=True)
        assert resp.status_code == 200
        assert b"confirm" in resp.data.lower()
        assert db.get_category_by_id(food["id"], 1) is not None
        # With confirm — should delete and reassign.
        resp = client.post(f"/categories/{food['id']}/delete", data={"confirm": "yes"},
                           follow_redirects=False)
        assert resp.status_code == 302
        assert db.get_category_by_id(food["id"], 1) is None
        # Expenses previously in Food should now be in Other.
        expenses = db.get_expenses_by_user(1)
        assert any(e["category"] == "Other" for e in expenses)
        assert not any(e["category"] == "Food" for e in expenses)


# =================================================================== #
# Route tests — merge / export / analytics                           #
# =================================================================== #

class TestCategoryMergeExportAnalytics:
    """Verify merge, export, and analytics routes."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1

    def test_merge_page_renders(self, client):
        """GET /categories/merge should render the form."""
        self._login(client)
        resp = client.get("/categories/merge")
        assert resp.status_code == 200
        assert b"Merge Categories" in resp.data

    def test_merge_success(self, client, db):
        """POST a valid merge should reassign and redirect."""
        self._login(client)
        src = db.create_category(1, "SrcCat", "d", "tag", "#6b7280")
        tgt = db.create_category(1, "TgtCat", "d", "tag", "#6b7280")
        db.create_expense(1, 12.0, "SrcCat", "2026-02-01", "moved")
        resp = client.post("/categories/merge", data={
            "source_id": str(src),
            "target_id": str(tgt),
        }, follow_redirects=False)
        assert resp.status_code == 302
        assert db.get_category_by_id(src, 1) is None
        assert db.get_category_by_id(tgt, 1) is not None
        assert any(e["category"] == "TgtCat" for e in db.get_expenses_by_user(1))

    def test_merge_same_ids_flashes_error(self, client):
        """Merging a category into itself should flash an error."""
        self._login(client)
        from database.db import get_user_categories
        cat = get_user_categories(1)[0]
        resp = client.post("/categories/merge", data={
            "source_id": str(cat["id"]),
            "target_id": str(cat["id"]),
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"must be different" in resp.data

    def test_export_returns_csv(self, client):
        """Export should return a text/csv attachment with headers."""
        self._login(client)
        resp = client.get("/categories/export")
        assert resp.status_code == 200
        assert resp.mimetype == "text/csv"
        assert "attachment" in resp.headers.get("Content-Disposition", "")
        reader = csv.reader(io.StringIO(resp.data.decode("utf-8")))
        rows = list(reader)
        assert rows[0][0] == "Name"
        assert rows[0][6] == "Total Spent"
        assert len(rows) >= 8  # header + 7 seeded categories

    def test_analytics_page_renders(self, client):
        """GET /categories/analytics should render."""
        self._login(client)
        resp = client.get("/categories/analytics")
        assert resp.status_code == 200
        assert b"Category Analytics" in resp.data
        assert b"Spending Distribution" in resp.data
        assert b"Top Categories" in resp.data

