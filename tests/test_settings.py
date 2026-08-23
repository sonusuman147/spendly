"""Tests for the Settings module — persistence, routes, and security.

Covers the database helpers (get/update/reset user settings, clear data,
delete account) and the authenticated /settings routes (render, save,
change password, reset, export, clear data, delete account) including
auth-required and ownership rules.
"""

import csv
import io

import pytest


# =================================================================== #
# Unit tests — settings DB helpers                                    #
# =================================================================== #

class TestUserSettingsPersistence:
    """Verify get_user_settings / update_user_settings / reset_user_settings."""

    def test_get_user_settings_creates_defaults(self, db):
        """A user with no settings row should get default values."""
        settings = db.get_user_settings(1)
        assert settings["currency"] == "INR"
        assert settings["theme"] == "dark"
        assert settings["accent_color"] == "green"
        assert settings["interface_density"] == "comfortable"
        assert settings["two_factor_enabled"] == 0
        assert settings["weekly_summary_enabled"] == 1

    def test_update_user_settings_persists_values(self, db):
        """Valid whitelisted values should be stored."""
        ok = db.update_user_settings(
            1,
            currency="USD",
            theme="light",
            accent_color="blue",
            interface_density="compact",
            budget_alert_threshold=65,
        )
        assert ok is True
        settings = db.get_user_settings(1)
        assert settings["currency"] == "USD"
        assert settings["theme"] == "light"
        assert settings["accent_color"] == "blue"
        assert settings["interface_density"] == "compact"
        assert settings["budget_alert_threshold"] == 65

    def test_update_user_settings_ignores_invalid_whitelist_values(self, db):
        """Out-of-whitelist values should be silently skipped."""
        db.update_user_settings(1, currency="BTC", theme="neon")
        settings = db.get_user_settings(1)
        assert settings["currency"] == "INR"
        assert settings["theme"] == "dark"

    def test_update_user_settings_toggle_on(self, db):
        """Boolean-like toggle values should persist as 1."""
        db.update_user_settings(1, two_factor_enabled=True, login_alerts_enabled=0)
        settings = db.get_user_settings(1)
        assert settings["two_factor_enabled"] == 1
        assert settings["login_alerts_enabled"] == 0

    def test_update_user_settings_ignores_unknown_keys(self, db):
        """Unknown field names should be ignored without error."""
        ok = db.update_user_settings(1, totally_fake_field="x", currency="EUR")
        assert ok is True
        settings = db.get_user_settings(1)
        assert settings["currency"] == "EUR"

    def test_reset_user_settings(self, db):
        """reset_user_settings should delete the row so defaults return."""
        db.update_user_settings(1, currency="JPY", theme="light")
        reset = db.reset_user_settings(1)
        assert reset is True
        settings = db.get_user_settings(1)
        assert settings["currency"] == "INR"
        assert settings["theme"] == "dark"

    def test_settings_are_per_user(self, db):
        """Settings for user A must never affect user B."""
        user2_id = db.create_user("Second", "second@example.com")
        db.update_user_settings(1, currency="USD")
        settings2 = db.get_user_settings(user2_id)
        assert settings2["currency"] == "INR"


class TestClearUserDataAndDeleteAccount:
    """Verify clear_user_data and delete_user_account helpers."""

    def test_clear_user_data_keeps_user(self, db):
        """clear_user_data removes financial rows but keeps the account.

        The seeded demo user starts with 8 expenses and 7 default category
        rows, so clear_user_data must remove those plus any rows the test
        adds.
        """
        db.create_expense(1, 10.0, "Food", "2026-01-01", "x")
        db.create_category(1, "Custom", "", "tag", "#000000")
        counts = db.clear_user_data(1)
        assert counts["expenses"] == 9  # 8 seeded + 1 added
        assert db.get_user_by_id(1) is not None
        assert db.get_expenses_by_user(1) == []
        assert db.get_user_categories(1) == []

    def test_clear_user_data_scoped_to_user(self, db):
        """clear_user_data should only remove the owning user's rows."""
        user2_id = db.create_user("Second", "second@example.com")
        db.create_expense(1, 10.0, "Food", "2026-01-01", "mine")
        db.create_expense(user2_id, 20.0, "Food", "2026-01-02", "theirs")
        db.clear_user_data(1)
        assert db.get_expenses_by_user(user2_id) != []

    def test_delete_user_account_removes_everything(self, db):
        """delete_user_account removes the user and all child rows."""
        db.create_expense(1, 10.0, "Food", "2026-01-01", "x")
        db.get_user_settings(1)  # creates the settings row
        assert db.delete_user_account(1) is True
        assert db.get_user_by_id(1) is None


# =================================================================== #
# Route tests — Settings page rendering                               #
# =================================================================== #

class TestSettingsPage:
    """Verify GET /settings renders the logged-in user's persisted data."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"

    def test_settings_requires_auth(self, client):
        """GET /settings without a session should redirect to /login."""
        resp = client.get("/settings")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_settings_renders_persisted_profile(self, client, db):
        self._login(client)
        db.update_user_profile(1, "Demo User", "demo@spendly.com", phone="+91 9876543210", bio="Hello!")
        resp = client.get("/settings")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "Demo User" in html
        assert "demo@spendly.com" in html
        assert "+91 9876543210" in html
        assert "Hello!" in html

    def test_settings_renders_persisted_preferences(self, client, db):
        self._login(client)
        db.update_user_settings(1, currency="USD", theme="light", accent_color="blue")
        resp = client.get("/settings")
        html = resp.get_data(as_text=True)
        # Select/radio server-side rendering of persisted values.
        assert 'value="USD" selected' in html
        assert 'value="light" checked' in html
        assert 'name="settings_accent" value="blue" checked' in html


# =================================================================== #
# Route tests — save/change password/reset/export/clear/delete        #
# =================================================================== #

class TestSettingsSave:
    """Verify POST /settings/save persists profile + settings."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"

    def test_save_requires_auth(self, client):
        resp = client.post("/settings/save", data={"name": "X"}, follow_redirects=False)
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_save_persists_profile_fields(self, client, db):
        self._login(client)
        resp = client.post("/settings/save", data={
            "name": "Updated Name",
            "email": "new@spendly.com",
            "phone": "+91 1111111111",
            "bio": "New bio",
        })
        assert resp.status_code == 302
        user = db.get_user_by_id(1)
        assert user["name"] == "Updated Name"
        assert user["email"] == "new@spendly.com"
        assert user["phone"] == "+91 1111111111"
        assert user["bio"] == "New bio"

    def test_save_persists_preferences_and_toggles(self, client, db):
        self._login(client)
        resp = client.post("/settings/save", data={
            "name": "Demo User",
            "email": "demo@spendly.com",
            "currency": "EUR",
            "date_format": "MM-DD-YYYY",
            "language": "en",
            "week_start": "sunday",
            "default_payment_method": "card",
            "interface_density": "compact",
            "budget_alert_threshold": "70",
            "theme": "system",
            "accent_color": "purple",
            "two_factor_enabled": "on",
            "login_alerts_enabled": "",
            "expense_reminders_enabled": "on",
            "budget_alerts_enabled": "on",
            "goal_milestones_enabled": "",
            "weekly_summary_enabled": "on",
            "product_updates_enabled": "",
            "personalised_insights_enabled": "on",
            "anonymous_usage_enabled": "",
        })
        assert resp.status_code == 302
        s = db.get_user_settings(1)
        assert s["currency"] == "EUR"
        assert s["date_format"] == "MM-DD-YYYY"
        assert s["week_start"] == "sunday"
        assert s["default_payment_method"] == "card"
        assert s["interface_density"] == "compact"
        assert s["budget_alert_threshold"] == 70
        assert s["theme"] == "system"
        assert s["accent_color"] == "purple"
        assert s["two_factor_enabled"] == 1
        assert s["login_alerts_enabled"] == 0
        assert s["expense_reminders_enabled"] == 1
        assert s["goal_milestones_enabled"] == 0
        assert s["weekly_summary_enabled"] == 1
        assert s["product_updates_enabled"] == 0
        assert s["personalised_insights_enabled"] == 1
        assert s["anonymous_usage_enabled"] == 0

    def test_save_rejects_invalid_values(self, client, db):
        """Invalid whitelist values should be ignored server-side."""
        self._login(client)
        client.post("/settings/save", data={
            "name": "Demo User",
            "email": "demo@spendly.com",
            "currency": "BTC",
            "theme": "neon",
            "budget_alert_threshold": "999",
            "two_factor_enabled": "on",
        })
        s = db.get_user_settings(1)
        assert s["currency"] == "INR"
        assert s["theme"] == "dark"
        assert s["budget_alert_threshold"] == 80
        # two_factor_enabled is a valid boolean so it should save.
        assert s["two_factor_enabled"] == 1

    def test_save_cannot_take_another_users_email(self, client, db):
        """Updating to an existing email should flash an error and not save."""
        user2_id = db.create_user("Second", "second@example.com")
        self._login(client)
        resp = client.post("/settings/save", data={
            "name": "Demo User",
            "email": "second@example.com",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert "already registered" in resp.get_data(as_text=True)
        assert db.get_user_by_id(1)["email"] == "demo@spendly.com"
        assert db.get_user_by_id(user2_id)["email"] == "second@example.com"


class TestChangePassword:
    """Verify POST /settings/change-password."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"

    def test_change_password_success(self, client, db):
        self._login(client)
        resp = client.post("/settings/change-password", data={
            "current_password": "demo123",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        })
        assert resp.status_code == 302
        from werkzeug.security import check_password_hash
        user = db.get_user_by_email("demo@spendly.com")
        assert check_password_hash(user["password_hash"], "newpassword123")

    def test_change_password_wrong_current(self, client, db):
        self._login(client)
        resp = client.post("/settings/change-password", data={
            "current_password": "wrongpass",
            "new_password": "newpassword123",
            "confirm_password": "newpassword123",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert "Current password is incorrect" in resp.get_data(as_text=True)
        from werkzeug.security import check_password_hash
        user = db.get_user_by_email("demo@spendly.com")
        assert check_password_hash(user["password_hash"], "demo123")

    def test_change_password_mismatch(self, client):
        self._login(client)
        resp = client.post("/settings/change-password", data={
            "current_password": "demo123",
            "new_password": "newpassword123",
            "confirm_password": "different123",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert "do not match" in resp.get_data(as_text=True)


class TestSettingsReset:
    """Verify POST /settings/reset restores defaults."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"

    def test_reset_restores_defaults(self, client, db):
        self._login(client)
        db.update_user_settings(1, currency="USD", theme="light")
        resp = client.post("/settings/reset")
        assert resp.status_code == 302
        s = db.get_user_settings(1)
        assert s["currency"] == "INR"
        assert s["theme"] == "dark"

    def test_reset_requires_auth(self, client):
        resp = client.post("/settings/reset")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


class TestSettingsExport:
    """Verify GET /settings/export returns a CSV download."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"

    def test_export_requires_auth(self, client):
        resp = client.get("/settings/export")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_export_returns_csv_with_user_data(self, client):
        self._login(client)
        resp = client.get("/settings/export")
        assert resp.status_code == 200
        assert resp.mimetype == "text/csv"
        assert "spendly-data-export" in resp.headers["Content-Disposition"]
        text = resp.get_data(as_text=True)
        assert "=== TRANSACTIONS ===" in text
        assert "=== BUDGETS ===" in text
        assert "=== GOALS ===" in text
        assert "=== CATEGORIES ===" in text


class TestClearData:
    """Verify POST /settings/clear-data removes financial data only."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"

    def test_clear_data(self, client, db):
        self._login(client)
        resp = client.post("/settings/clear-data")
        assert resp.status_code == 302
        assert db.get_user_by_id(1) is not None
        assert db.get_expenses_by_user(1) == []

    def test_clear_data_requires_auth(self, client):
        resp = client.post("/settings/clear-data")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]


class TestDeleteAccount:
    """Verify POST /settings/delete-account permanently removes the user."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"

    def test_delete_account(self, client, db):
        self._login(client)
        resp = client.post("/settings/delete-account", follow_redirects=True)
        assert resp.status_code == 200
        assert db.get_user_by_id(1) is None

    def test_delete_account_requires_auth(self, client):
        resp = client.post("/settings/delete-account")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]