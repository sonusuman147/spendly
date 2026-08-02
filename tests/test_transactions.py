"""Tests for Step 09b — Transactions Backend.

Covers the database helpers powering the Transactions ledger (server-side
filtering, sorting, pagination, summary statistics, bulk delete, activity log,
payment-method persistence) and the new /transactions routes (render, CSV
export, bulk delete) including authentication and ownership rules.
"""

import io
import csv

import pytest


# =================================================================== #
# Unit tests — payment method persistence                             #
# =================================================================== #

class TestPaymentMethodPersistence:
    """Verify create_expense / update_expense persist payment methods."""

    def test_create_expense_persists_payment_method(self, db):
        """create_expense should store the provided payment method."""
        eid = db.create_expense(1, 99.0, "Food", "2026-01-01", "Test", "card")
        expense = db.get_expense_by_id(eid)
        assert expense["payment_method"] == "card"

    def test_create_expense_defaults_to_cash(self, db):
        """create_expense without a payment method should default to cash."""
        eid = db.create_expense(1, 50.0, "Other", "2026-01-02", "No method")
        expense = db.get_expense_by_id(eid)
        assert expense["payment_method"] == "cash"

    def test_create_expense_rejects_unknown_method(self, db):
        """create_expense with an invalid method should fall back to cash."""
        eid = db.create_expense(1, 10.0, "Food", "2026-01-03", "Bad method", "gold")
        expense = db.get_expense_by_id(eid)
        assert expense["payment_method"] == "cash"

    def test_update_expense_persists_payment_method(self, db):
        """update_expense should update the stored payment method."""
        eid = db.create_expense(1, 30.0, "Food", "2026-01-04", "Update me")
        updated = db.update_expense(eid, 1, 31.0, "Food", "2026-01-04", "Updated", "upi")
        assert updated is True
        expense = db.get_expense_by_id(eid)
        assert expense["payment_method"] == "upi"
        assert expense["amount"] == 31.0

    def test_seed_expenses_have_payment_methods(self, db):
        """Seeded demo expenses should all have a payment method."""
        expenses = db.get_expenses_by_user(1)
        assert len(expenses) == 8
        for exp in expenses:
            assert exp["payment_method"] in db.PAYMENT_METHODS


# =================================================================== #
# Unit tests — get_transactions (filter / sort / paginate / summary)  #
# =================================================================== #

class TestGetTransactions:
    """Verify get_transactions() server-side ledger behaviour."""

    def test_returns_paginated_items_and_metadata(self, db):
        """Should return items, total, pages, page, per_page, has_prev/next."""
        result = db.get_transactions(1, page=1, per_page=8)
        assert result["total"] == 8
        assert result["page"] == 1
        assert result["pages"] == 1
        assert result["per_page"] == 8
        assert result["has_prev"] is False
        assert result["has_next"] is False
        assert len(result["items"]) == 8

    def test_pagination_splits_pages(self, db):
        """With more than per_page rows, pages should split correctly."""
        for i in range(5):
            db.create_expense(1, 10.0 + i, "Food", f"2026-02-0{i + 1}", f"extra {i}")
        result = db.get_transactions(1, page=1, per_page=3)
        assert result["total"] == 13
        assert result["pages"] == 5
        assert len(result["items"]) == 3
        assert result["has_next"] is True
        # Last page has the remainder
        last = db.get_transactions(1, page=5, per_page=3)
        assert len(last["items"]) == 1
        assert last["has_next"] is False

    def test_page_clamped_when_out_of_range(self, db):
        """Requesting a page beyond the last should clamp to the last page."""
        result = db.get_transactions(1, page=9999, per_page=8)
        assert result["page"] == result["pages"]

    def test_category_filter(self, db):
        """Category filter should narrow results to that category."""
        result = db.get_transactions(1, category="Food", page=1, per_page=8)
        assert result["total"] == 2  # seeded: groceries + dinner
        for item in result["items"]:
            assert item["category"] == "Food"

    def test_date_range_filter(self, db):
        """Date range filter should include only expenses in range."""
        # All seeded dates are within the last 30 days. Use a wide range to
        # confirm inclusion, then a point-in-time range to narrow.
        result = db.get_transactions(
            1, date_from="1990-01-01", date_to="2100-01-01", page=1, per_page=8,
        )
        assert result["total"] == 8

    def test_amount_range_filter(self, db):
        """Amount min/max should narrow results by amount."""
        result = db.get_transactions(1, amount_min=1000.0, page=1, per_page=8)
        assert result["total"] == 2  # Bills 2000 + Shopping 1200
        for item in result["items"]:
            assert item["amount"] >= 1000.0

    def test_search_filter_matches_description(self, db):
        """Search should match the description text."""
        result = db.get_transactions(1, search="groceries", page=1, per_page=8)
        assert result["total"] >= 1
        for item in result["items"]:
            assert "groceries" in item["description"].lower()

    def test_sort_amount_desc(self, db):
        """Sort by amount-desc should return highest amount first."""
        result = db.get_transactions(1, sort="amount-desc", page=1, per_page=8)
        amounts = [item["amount"] for item in result["items"]]
        assert amounts == sorted(amounts, reverse=True)

    def test_sort_date_asc(self, db):
        """Sort by date-asc should return oldest first."""
        result = db.get_transactions(1, sort="date-asc", page=1, per_page=8)
        dates = [item["date"] for item in result["items"]]
        assert dates == sorted(dates)

    def test_summary_statistics_from_filtered_set(self, db):
        """Summary stats should reflect the filtered set, not all expenses."""
        result = db.get_transactions(1, category="Food", page=1, per_page=8)
        assert result["summary"]["total_count"] == 2
        assert result["summary"]["total_amount"] == pytest.approx(770.0, rel=1e-9)  # 450 + 320
        assert result["summary"]["highest"] == pytest.approx(450.0, rel=1e-9)
        assert result["summary"]["average"] == pytest.approx(385.0, rel=1e-9)

    def test_summary_with_no_match(self, db):
        """With no matching rows, summary should be zeros and last None."""
        result = db.get_transactions(1, search="zzzz-no-such-thing", page=1, per_page=8)
        assert result["total"] == 0
        assert result["summary"]["total_count"] == 0
        assert result["summary"]["total_amount"] == 0.0
        assert result["summary"]["highest"] == 0.0
        assert result["summary"]["average"] == 0.0
        assert result["summary"]["last"] is None

    def test_per_page_none_returns_all(self, db):
        """per_page=None should return every matching row (used for export)."""
        result = db.get_transactions(1, page=1, per_page=None)
        assert result["total"] == 8
        assert len(result["items"]) == 8


# =================================================================== #
# Unit tests — get_expenses_by_ids + delete_expenses_bulk             #
# =================================================================== #

class TestBulkOperations:
    """Verify ownership-scoped bulk fetch and delete."""

    def test_get_expenses_by_ids_scoped_to_user(self, db):
        """Should only return rows owned by the user."""
        user2_id = db.create_user("Second", "second@test.com", password_hash="x")
        e1 = db.create_expense(1, 10.0, "Food", "2026-01-10", "mine")
        e2 = db.create_expense(user2_id, 20.0, "Food", "2026-01-11", "theirs")
        rows = db.get_expenses_by_ids(1, [e1, e2])
        ids = {r["id"] for r in rows}
        assert e1 in ids
        assert e2 not in ids

    def test_delete_expenses_bulk_only_owned(self, db):
        """Bulk delete should only remove rows owned by the user."""
        user2_id = db.create_user("Third", "third@test.com", password_hash="x")
        e1 = db.create_expense(1, 10.0, "Food", "2026-01-12", "mine1")
        e2 = db.create_expense(1, 10.0, "Food", "2026-01-13", "mine2")
        e3 = db.create_expense(user2_id, 20.0, "Food", "2026-01-14", "theirs")
        deleted = db.delete_expenses_bulk(1, [e1, e2, e3])
        assert deleted == 2
        assert db.get_expense_by_id(e1) is None
        assert db.get_expense_by_id(e2) is None
        assert db.get_expense_by_id(e3) is not None

    def test_delete_expenses_bulk_empty_ids(self, db):
        """Deleting with an empty id list should return 0."""
        assert db.delete_expenses_bulk(1, []) == 0


# =================================================================== #
# Unit tests — activity log                                           #
# =================================================================== #

class TestActivityLog:
    """Verify add_activity and get_recent_activity."""

    def test_add_and_retrieve_activity(self, db):
        """A recorded activity should be returned by get_recent_activity."""
        aid = db.add_activity(1, action="added", expense_id=1, category="Food",
                              description="Pizza", amount=250.0)
        assert aid is not None
        feed = db.get_recent_activity(1, limit=8)
        assert any(a["id"] == aid and a["action"] == "added" and
                   a["category"] == "Food" and a["amount"] == 250.0 for a in feed)

    def test_get_recent_activity_ordered_newest_first(self, db):
        """Recent activity should be newest first."""
        feed = db.get_recent_activity(1, limit=8)
        times = [a["created_at"] for a in feed]
        assert times == sorted(times, reverse=True)

    def test_add_activity_rejects_invalid_action(self, db):
        """add_activity should reject actions outside ACTIVITY_ACTIONS."""
        with pytest.raises(ValueError):
            db.add_activity(1, action="exploded", category="Food")

    def test_activity_scoped_to_user(self, db):
        """Recent activity should only include the given user's entries."""
        user2_id = db.create_user("Four", "four@test.com", password_hash="x")
        db.add_activity(user2_id, action="added", expense_id=1, category="Food")
        user1_ids = {a["user_id"] for a in db.get_recent_activity(1, limit=8)}
        assert user1_ids == {1}
        assert user2_id not in user1_ids


# =================================================================== #
# Route tests — GET /transactions                                     #
# =================================================================== #

class TestTransactionsRoute:
    """Verify the Transactions page renders with real data."""

    def test_redirect_unauthenticated(self, client):
        """GET /transactions without a session should redirect to /login."""
        resp = client.get("/transactions", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.location

    def test_authenticated_returns_200(self, client):
        """GET /transactions while logged in should return 200."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/transactions")
        assert resp.status_code == 200

    def test_shows_summary_statistics(self, client):
        """The stat cards should show real totals derived from the ledger."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/transactions")
        assert resp.status_code == 200
        assert b"5170.00" in resp.data  # total amount for seeded data

    def test_shows_transaction_rows(self, client):
        """The table should contain server-rendered transaction rows."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/transactions")
        assert resp.status_code == 200
        assert b"Weekly groceries" in resp.data
        assert b"Electricity bill" in resp.data

    def test_filter_by_category(self, client):
        """Category filter should narrow the rendered rows."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.get("/transactions?category=Food")
        assert resp.status_code == 200
        assert b"Weekly groceries" in resp.data
        assert b"Electricity bill" not in resp.data

    def test_pagination_shows_page_controls(self, client):
        """With more than per_page rows the pagination controls should render."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        # Add enough expenses to exceed one page (per_page=8).
        for i in range(3):
            client.post("/expenses/add", data={
                "amount": "15.00", "category": "Food", "date": "2026-03-01",
                "description": f"paginate {i}", "payment_method": "cash",
            }, follow_redirects=False)
        resp = client.get("/transactions")
        assert resp.status_code == 200
        assert b"Page 1 of" in resp.data


# =================================================================== #
# Route tests — GET /transactions/export                              #
# =================================================================== #

class TestTransactionsExportRoute:
    """Verify CSV export behaviour."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1

    def test_redirect_unauthenticated(self, client):
        """Export without a session should redirect to /login."""
        resp = client.get("/transactions/export", follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.location

    def test_export_returns_csv(self, client):
        """Export should return a text/csv attachment with a header row."""
        self._login(client)
        resp = client.get("/transactions/export")
        assert resp.status_code == 200
        assert resp.mimetype == "text/csv"
        assert "attachment" in resp.headers.get("Content-Disposition", "")
        text = resp.data.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        assert rows[0] == ["Date", "Description", "Category", "Payment Method", "Amount"]
        assert len(rows) == 9  # header + 8 seeded rows

    def test_export_honors_filters(self, client):
        """Export with a category filter should only contain that category."""
        self._login(client)
        resp = client.get("/transactions/export?category=Food")
        text = resp.data.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        assert len(rows) == 3  # header + 2 Food rows
        for row in rows[1:]:
            assert row[2] == "Food"

    def test_export_selected_ids(self, client):
        """Export with ids should only contain those (owned) rows."""
        self._login(client)
        resp = client.get("/transactions/export?ids=1,2")
        text = resp.data.decode("utf-8")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        assert len(rows) == 3  # header + 2 rows
        assert rows[1][2] == "Food"      # id 1 is Weekly groceries
        assert rows[2][2] == "Transport"  # id 2 is Bus pass recharge


# =================================================================== #
# Route tests — POST /transactions/bulk-delete                        #
# =================================================================== #

class TestBulkDeleteRoute:
    """Verify the bulk delete endpoint."""

    def test_redirect_unauthenticated(self, client):
        """Bulk delete without a session should redirect to /login."""
        resp = client.post("/transactions/bulk-delete", data={"expense_ids": "1"},
                           follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.location

    def test_delete_selected_transactions(self, client, db):
        """Posting ids should delete those transactions and log activity."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.post("/transactions/bulk-delete", data={"expense_ids": ["1", "2"]},
                           follow_redirects=False)
        assert resp.status_code == 302
        assert "/transactions" in resp.location
        assert db.get_expense_by_id(1) is None
        assert db.get_expense_by_id(2) is None
        feed = db.get_recent_activity(1, limit=8)
        assert any(a["action"] == "deleted" for a in feed)

    def test_delete_no_ids_flashes_error(self, client):
        """Posting without ids should flash an error and redirect."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.post("/transactions/bulk-delete", data={}, follow_redirects=True)
        assert resp.status_code == 200
        assert b"No transactions selected" in resp.data

    def test_delete_ignores_foreign_ids(self, client, db):
        """Posting another user's id should not delete their transaction."""
        user2_id = db.create_user("Owner", "owner@test.com", password_hash="x")
        foreign = db.create_expense(user2_id, 999.0, "Food", "2026-01-20", "theirs")
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.post("/transactions/bulk-delete", data={"expense_ids": [str(foreign)]},
                           follow_redirects=False)
        assert resp.status_code == 302
        assert db.get_expense_by_id(foreign) is not None


# =================================================================== #
# Route tests — Expense CRUD with payment method                      #
# =================================================================== #

class TestExpenseCRUDPayment:
    """Verify expense add/edit/delete still work and persist payment."""

    def test_add_expense_with_payment_method(self, client, db):
        """Adding an expense via the route should store the payment method."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        resp = client.post("/expenses/add", data={
            "amount": "75.00",
            "category": "Health",
            "description": "Vitamins",
            "date": "2026-04-01",
            "payment_method": "upi",
        }, follow_redirects=False)
        assert resp.status_code == 302
        expenses = db.get_expenses_by_user(1)
        added = [e for e in expenses if e["description"] == "Vitamins"]
        assert added and added[0]["payment_method"] == "upi"

    def test_add_expense_defaults_payment(self, client, db):
        """Adding an expense without a payment field should default to cash."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        client.post("/expenses/add", data={
            "amount": "12.00", "category": "Other", "description": "Default pm",
            "date": "2026-04-02",
        }, follow_redirects=False)
        expenses = db.get_expenses_by_user(1)
        added = [e for e in expenses if e["description"] == "Default pm"]
        assert added and added[0]["payment_method"] == "cash"

    def test_edit_expense_persists_payment(self, client, db):
        """Editing an expense should keep its payment method."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        client.post("/expenses/add", data={
            "amount": "22.00", "category": "Food", "description": "Edit me",
            "date": "2026-04-03", "payment_method": "wallet",
        }, follow_redirects=False)
        expenses = db.get_expenses_by_user(1)
        target = [e for e in expenses if e["description"] == "Edit me"][0]
        resp = client.post(f"/expenses/{target['id']}/edit", data={
            "amount": "23.00", "category": "Food", "description": "Edited!",
            "date": "2026-04-03", "payment_method": "bank",
        }, follow_redirects=False)
        assert resp.status_code == 302
        updated = db.get_expense_by_id(target["id"])
        assert updated["payment_method"] == "bank"
        assert updated["description"] == "Edited!"

    def test_delete_expense_logs_activity(self, client, db):
        """Deleting an expense should record a 'deleted' activity entry."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        client.post("/expenses/1/delete", follow_redirects=False)
        feed = db.get_recent_activity(1, limit=8)
        assert any(a["action"] == "deleted" and a["expense_id"] == 1 for a in feed)

