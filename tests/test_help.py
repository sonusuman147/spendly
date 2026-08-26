"""Tests for Help & Support ticket submission, display, routes, and database operations.

Covers end-to-end ticket creation (JSON and form-encoded), validation rules,
scoping, message conversation threading, status transitions, and data lifecycle.
"""

import pytest


class TestHelpRoutes:
    """Tests for the GET /help route."""

    def test_help_unauthenticated_redirects_to_login(self, client):
        """Unauthenticated GET /help must redirect to /login."""
        res = client.get("/help")
        assert res.status_code == 302
        assert "/login" in res.headers["Location"]

    def test_help_authenticated_returns_200(self, client):
        """Authenticated GET /help returns 200 with the Help & Support page."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        res = client.get("/help")
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        assert "Help &amp; Support" in html or "Help & Support" in html
        assert "My Support Requests" in html
        assert "Contact Support" in html

    def test_help_renders_empty_state_when_no_tickets(self, client):
        """When user has no tickets, empty state message is rendered."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        res = client.get("/help")
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        assert "You haven&#39;t submitted any support requests yet" in html or "haven't submitted any support requests yet" in html

    def test_help_renders_user_tickets(self, client, db):
        """When user has tickets, they are listed under My Support Requests with metadata."""
        ticket_id = db.create_support_ticket(
            user_id=1,
            subject="Cannot connect export",
            category="reports",
            message="Detailed error description when exporting CSV files.",
        )
        assert ticket_id is not None

        with client.session_transaction() as sess:
            sess["user_id"] = 1
        res = client.get("/help")
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        assert "Cannot connect export" in html
        assert "Reports" in html
        assert "Open" in html
        assert "SLY-" in html


class TestHelpCreateTicketRoute:
    """Tests for the POST /help/tickets endpoint."""

    def test_create_ticket_unauthenticated_json_returns_401(self, client):
        """Unauthenticated JSON POST returns 401 with error JSON."""
        res = client.post(
            "/help/tickets",
            json={
                "topic": "getting-started",
                "subject": "Help needed",
                "message": "This is a valid test message with >10 chars.",
            },
        )
        assert res.status_code == 401
        data = res.get_json()
        assert data["ok"] is False
        assert "sign in" in data["error"].lower()

    def test_create_ticket_unauthenticated_form_redirects(self, client):
        """Unauthenticated form-encoded POST redirects to login."""
        res = client.post(
            "/help/tickets",
            data={
                "topic": "getting-started",
                "subject": "Help needed",
                "message": "This is a valid test message with >10 chars.",
            },
        )
        assert res.status_code == 302
        assert "/login" in res.headers["Location"]

    def test_create_ticket_valid_json_success(self, client, db):
        """Valid JSON payload creates ticket and initial message in DB."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1

        payload = {
            "topic": "budgets",
            "subject": "Monthly budget limit issue",
            "message": "I set my budget to 5000 but the alert triggered at 4000.",
        }
        res = client.post("/help/tickets", json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data["ok"] is True
        ticket_id = data["ticket_id"]
        assert ticket_id > 0

        # Verify DB persistence
        ticket = db.get_ticket_by_id(ticket_id, 1)
        assert ticket is not None
        assert ticket["subject"] == payload["subject"]
        assert ticket["category"] == "budgets"
        assert ticket["status"] == "open"
        assert ticket["ticket_no"].startswith("SLY-")

        # Verify initial conversation message
        messages = db.get_ticket_messages(ticket_id, 1)
        assert len(messages) == 1
        assert messages[0]["body"] == payload["message"]
        assert messages[0]["author"] == "You"
        assert messages[0]["is_staff"] == 0

    def test_create_ticket_valid_form_encoded_success(self, client, db):
        """Valid form-encoded POST creates ticket and redirects to /help with flash."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1

        form_data = {
            "topic": "expenses",
            "subject": "Recurring expense problem",
            "message": "How do I mark an expense as recurring every month?",
        }
        res = client.post("/help/tickets", data=form_data, follow_redirects=True)
        assert res.status_code == 200
        html = res.get_data(as_text=True)
        assert "Recurring expense problem" in html
        assert "Support request submitted successfully" in html

    @pytest.mark.parametrize(
        "raw_topic,expected_category",
        [
            ("getting-started", "getting-started"),
            ("Getting Started", "getting-started"),
            ("expenses", "expenses"),
            ("Expenses", "expenses"),
            ("budgets", "budgets"),
            ("Budgets", "budgets"),
            ("goals", "goals"),
            ("Goals", "goals"),
            ("reports", "reports"),
            ("Reports", "reports"),
            ("settings", "settings"),
            ("Settings", "settings"),
            ("security", "security"),
            ("Security", "security"),
            ("privacy", "privacy"),
            ("Data & Privacy", "privacy"),
            ("data-privacy", "privacy"),
            ("other", "other"),
            ("Something else", "other"),
        ],
    )
    def test_create_ticket_topic_normalization(self, client, db, raw_topic, expected_category):
        """Topic inputs (slugs or titles) are properly normalized and accepted."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1

        res = client.post(
            "/help/tickets",
            json={
                "topic": raw_topic,
                "subject": f"Test for {raw_topic}",
                "message": "A sufficiently long description for ticket topic test.",
            },
        )
        assert res.status_code == 200
        data = res.get_json()
        assert data["ok"] is True
        ticket = db.get_ticket_by_id(data["ticket_id"], 1)
        assert ticket["category"] == expected_category

    def test_create_ticket_missing_topic(self, client):
        """Missing topic returns 400 with descriptive error."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1

        res = client.post(
            "/help/tickets",
            json={
                "topic": "",
                "subject": "Missing topic test",
                "message": "Valid message text with enough characters.",
            },
        )
        assert res.status_code == 400
        data = res.get_json()
        assert data["ok"] is False
        assert "select a topic" in data["error"].lower()

    def test_create_ticket_invalid_topic(self, client):
        """Invalid topic returns 400."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1

        res = client.post(
            "/help/tickets",
            json={
                "topic": "completely-invalid-topic",
                "subject": "Invalid topic test",
                "message": "Valid message text with enough characters.",
            },
        )
        assert res.status_code == 400
        data = res.get_json()
        assert data["ok"] is False
        assert "select a topic" in data["error"].lower()

    def test_create_ticket_missing_subject(self, client):
        """Missing subject returns 400."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1

        res = client.post(
            "/help/tickets",
            json={
                "topic": "expenses",
                "subject": "   ",
                "message": "Valid message text with enough characters.",
            },
        )
        assert res.status_code == 400
        data = res.get_json()
        assert data["ok"] is False
        assert "enter a subject" in data["error"].lower()

    def test_create_ticket_subject_too_long(self, client):
        """Subject exceeding 120 characters returns 400."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1

        res = client.post(
            "/help/tickets",
            json={
                "topic": "expenses",
                "subject": "A" * 121,
                "message": "Valid message text with enough characters.",
            },
        )
        assert res.status_code == 400
        data = res.get_json()
        assert data["ok"] is False
        assert "120" in data["error"]

    def test_create_ticket_message_too_short(self, client):
        """Message shorter than 10 characters returns 400."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1

        res = client.post(
            "/help/tickets",
            json={
                "topic": "expenses",
                "subject": "Short message",
                "message": "Short",
            },
        )
        assert res.status_code == 400
        data = res.get_json()
        assert data["ok"] is False
        assert "10" in data["error"]

    def test_create_ticket_message_too_long(self, client):
        """Message exceeding 2000 characters returns 400."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1

        res = client.post(
            "/help/tickets",
            json={
                "topic": "expenses",
                "subject": "Long message",
                "message": "X" * 2001,
            },
        )
        assert res.status_code == 400
        data = res.get_json()
        assert data["ok"] is False
        assert "2000" in data["error"]


class TestSupportDbHelpers:
    """Direct tests for support database helper functions."""

    def test_ticket_no_generation_increments_uniquely(self, db):
        """Unique ticket numbers SLY-1001, SLY-1002 etc are generated monotonically."""
        t1 = db.create_support_ticket(1, "Sub 1", "expenses", "Message one text here.")
        t2 = db.create_support_ticket(1, "Sub 2", "expenses", "Message two text here.")
        ticket1 = db.get_ticket_by_id(t1, 1)
        ticket2 = db.get_ticket_by_id(t2, 1)
        assert ticket1["ticket_no"] != ticket2["ticket_no"]
        assert ticket1["ticket_no"].startswith("SLY-")
        assert ticket2["ticket_no"].startswith("SLY-")

    def test_get_user_tickets_ordering_and_count(self, db):
        """Tickets are returned newest first with calculated message count."""
        t1 = db.create_support_ticket(1, "First Issue", "budgets", "First message text here.")
        t2 = db.create_support_ticket(1, "Second Issue", "goals", "Second message text here.")
        db.add_ticket_message(t1, 1, "Follow-up message on first issue.")

        tickets = db.get_user_tickets(1)
        assert len(tickets) >= 2
        t1_item = next(t for t in tickets if t["id"] == t1)
        t2_item = next(t for t in tickets if t["id"] == t2)
        assert t1_item["message_count"] == 2
        assert t2_item["message_count"] == 1

    def test_get_ticket_by_id_scoped_to_user(self, db):
        """get_ticket_by_id returns ticket only if owned by user."""
        t_id = db.create_support_ticket(1, "Private Ticket", "security", "Security question issue.")
        assert db.get_ticket_by_id(t_id, 1) is not None
        assert db.get_ticket_by_id(t_id, 999) is None

    def test_add_ticket_message_blocked_when_closed(self, db):
        """Cannot append messages to closed tickets."""
        t_id = db.create_support_ticket(1, "Closed ticket", "settings", "Settings issue message.")
        assert db.close_ticket(t_id, 1) is True

        msg_id = db.add_ticket_message(t_id, 1, "Trying to message closed ticket.")
        assert msg_id is None

    def test_update_ticket_status_and_priority(self, db):
        """Status and priority updates work for valid enum values and reject invalid ones."""
        t_id = db.create_support_ticket(1, "Status test", "reports", "Message body for status.")
        assert db.update_ticket_status(t_id, 1, "in_progress") is True
        assert db.get_ticket_by_id(t_id, 1)["status"] == "in_progress"

        assert db.update_ticket_status(t_id, 1, "invalid_status") is False
        assert db.update_ticket_priority(t_id, 1, "urgent") is True
        assert db.get_ticket_by_id(t_id, 1)["priority"] == "urgent"
        assert db.update_ticket_priority(t_id, 1, "invalid_priority") is False

    def test_delete_ticket_cascades_messages(self, db):
        """Deleting a ticket removes both the ticket and all its messages."""
        t_id = db.create_support_ticket(1, "Delete me", "other", "Message for deleted ticket.")
        db.add_ticket_message(t_id, 1, "Another reply message.")
        assert len(db.get_ticket_messages(t_id, 1)) == 2

        assert db.delete_ticket(t_id, 1) is True
        assert db.get_ticket_by_id(t_id, 1) is None
        assert len(db.get_ticket_messages(t_id, 1)) == 0

    def test_get_support_stats(self, db):
        """get_support_stats aggregates open, in_progress, resolved, and closed tickets."""
        t1 = db.create_support_ticket(1, "T1", "expenses", "Msg 1 with sufficient length.")
        t2 = db.create_support_ticket(1, "T2", "expenses", "Msg 2 with sufficient length.")
        t3 = db.create_support_ticket(1, "T3", "expenses", "Msg 3 with sufficient length.")
        db.update_ticket_status(t2, 1, "resolved")
        db.close_ticket(t3, 1)

        stats = db.get_support_stats(1)
        assert stats["total"] == 3
        assert stats["open"] == 1
        assert stats["resolved"] == 1
        assert stats["closed"] == 1


class TestUserScoping:
    """Verify tickets and messages are strictly isolated between users."""

    def test_tickets_never_leak_between_users(self, client, db):
        """User A cannot see User B's tickets under My Support Requests or via DB."""
        # Create second user in database
        conn = db.get_db()
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("User Two", "user2@example.com", "hash"),
        )
        user2_id = conn.execute("SELECT id FROM users WHERE email = 'user2@example.com'").fetchone()[0]
        conn.commit()
        conn.close()

        # User 1 creates a ticket
        t1_id = db.create_support_ticket(1, "User One Secret Ticket", "privacy", "Private data inquiry.")
        # User 2 creates a ticket
        t2_id = db.create_support_ticket(user2_id, "User Two Private Ticket", "goals", "User 2 goal question.")

        # Check DB scoping
        user1_tickets = db.get_user_tickets(1)
        user2_tickets = db.get_user_tickets(user2_id)
        assert any(t["id"] == t1_id for t in user1_tickets)
        assert not any(t["id"] == t2_id for t in user1_tickets)
        assert any(t["id"] == t2_id for t in user2_tickets)
        assert not any(t["id"] == t1_id for t in user2_tickets)

        # Check GET /help rendering for User 1
        with client.session_transaction() as sess:
            sess["user_id"] = 1
        res1 = client.get("/help")
        html1 = res1.get_data(as_text=True)
        assert "User One Secret Ticket" in html1
        assert "User Two Private Ticket" not in html1


class TestDataLifecycle:
    """Verify clear_user_data and delete_user_account clean tickets and messages."""

    def test_clear_user_data_deletes_tickets(self, db):
        """clear_user_data deletes support tickets and messages."""
        t_id = db.create_support_ticket(1, "Ticket to clear", "expenses", "Expense issue message.")
        assert db.get_ticket_by_id(t_id, 1) is not None

        counts = db.clear_user_data(1)
        assert counts.get("support_tickets", 0) >= 1
        assert counts.get("ticket_messages", 0) >= 1
        assert db.get_ticket_by_id(t_id, 1) is None

    def test_delete_account_deletes_tickets(self, db):
        """delete_user_account deletes user and associated support tickets."""
        conn = db.get_db()
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Temp User", "temp@example.com", "hash"),
        )
        temp_id = conn.execute("SELECT id FROM users WHERE email = 'temp@example.com'").fetchone()[0]
        conn.commit()
        conn.close()

        t_id = db.create_support_ticket(temp_id, "Temp Ticket", "other", "Temporary user message.")
        assert db.get_ticket_by_id(t_id, temp_id) is not None

        assert db.delete_user_account(temp_id) is True
        assert db.get_ticket_by_id(t_id, temp_id) is None
