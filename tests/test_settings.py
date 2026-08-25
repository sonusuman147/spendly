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
# =================================================================== #
# Session tracking helpers (unit)                                     #
# =================================================================== #

class TestSessionTrackingHelpers:
    """Verify the user_sessions helpers (create/list/revoke/cleanup)."""

    def test_create_and_list_user_sessions(self, db):
        db.create_user_session(1, "token-aaa", ip_address="10.0.0.1", user_agent="Chrome/Windows")
        db.create_user_session(1, "token-bbb", ip_address="10.0.0.2", user_agent="Firefox/Mac")
        rows = db.get_user_sessions(1)
        assert len(rows) == 2
        # Newest first (higher id).
        assert rows[0]["token"] == "token-bbb"
        assert rows[0]["revoked"] == 0

    def test_sessions_are_scoped_to_user(self, db):
        db.create_user("Second", "second@example.com")
        db.create_user_session(1, "token-aaa")
        db.create_user_session(2, "token-bbb")
        rows = db.get_user_sessions(1)
        assert len(rows) == 1
        assert rows[0]["token"] == "token-aaa"

    def test_get_session_by_token(self, db):
        db.create_user_session(1, "token-aaa")
        row = db.get_user_session_by_token("token-aaa")
        assert row is not None and row["user_id"] == 1 and row["revoked"] == 0
        assert db.get_user_session_by_token("nope") is None

    def test_revoke_user_session_only_owner(self, db):
        db.create_user("Second", "second@example.com")
        sid_own = db.create_user_session(1, "token-own")
        sid_other = db.create_user_session(2, "token-other")
        # Cannot revoke another user's session even with a valid id.
        assert db.revoke_user_session(1, sid_other) is False
        assert db.get_user_session_by_token("token-other")["revoked"] == 0
        # Owner can revoke their own.
        assert db.revoke_user_session(1, sid_own) is True
        assert db.get_user_session_by_token("token-own")["revoked"] == 1

    def test_revoke_user_session_by_token(self, db):
        db.create_user_session(1, "token-aaa")
        assert db.revoke_user_session_by_token("token-aaa") is True
        assert db.get_user_session_by_token("token-aaa")["revoked"] == 1

    def test_delete_account_cleans_sessions(self, db):
        db.create_user_session(1, "token-aaa")
        db.get_user_settings(1)
        assert db.delete_user_account(1) is True
        assert db.get_user_sessions(1) == []
# =================================================================== #
# Theme endpoint — header theme switch persistence                    #
# =================================================================== #

class TestSettingsThemeEndpoint:
    """Verify POST /settings/theme persists per user and validates input."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"

    def test_theme_requires_auth(self, client):
        resp = client.post("/settings/theme", json={"theme": "light"})
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_theme_persists_valid_value(self, client, db):
        self._login(client)
        resp = client.post("/settings/theme", json={"theme": "light"})
        assert resp.status_code == 200
        assert resp.get_json()["ok"] is True
        assert db.get_user_settings(1)["theme"] == "light"

    def test_theme_rejects_invalid_value(self, client, db):
        self._login(client)
        resp = client.post("/settings/theme", json={"theme": "neon"})
        assert resp.status_code == 400
        assert resp.get_json()["ok"] is False
        assert db.get_user_settings(1)["theme"] == "dark"

    def test_theme_accepts_form_encoding(self, client, db):
        self._login(client)
        resp = client.post("/settings/theme", data={"theme": "system"})
        assert resp.status_code == 302
        assert db.get_user_settings(1)["theme"] == "system"

    def test_theme_is_scoped_per_user(self, client, db):
        user2_id = db.create_user("Second", "second@example.com")
        self._login(client)
        client.post("/settings/theme", json={"theme": "light"})
        assert db.get_user_settings(user2_id)["theme"] == "dark"


# =================================================================== #
# Appearance — theme + accent applied across pages                    #
# =================================================================== #

class TestAppearanceAppliedAcrossPages:
    """Verify the persisted theme/accent render on <body> app-wide."""

    def _login(self, client):
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"

    def test_settings_page_renders_persisted_theme_and_accent(self, client, db):
        self._login(client)
        db.update_user_settings(1, theme="light", accent_color="blue")
        resp = client.get("/settings")
        html = resp.get_data(as_text=True)
        # Header theme switch reflects the saved theme...
        assert 'id="theme-light" value="light" checked' in html
        # ...settings theme radio reflects it...
        assert 'name="settings_theme" value="light" checked' in html
        # ...accent is applied to <body>.
        assert 'data-accent="blue"' in html

    def test_other_pages_apply_same_theme_and_accent(self, client, db):
        """Consistency: the saved theme/accent must apply on every page."""
        self._login(client)
        db.update_user_settings(1, theme="system", accent_color="purple")
        for url in ("/", "/profile", "/transactions", "/settings"):
            resp = client.get(url)
            assert resp.status_code in (200, 302), url
            if resp.status_code == 200:
                html = resp.get_data(as_text=True)
                assert 'data-accent="purple"' in html, url
                assert 'id="theme-system" value="system" checked' in html, url

    def test_accent_does_not_leak_between_users(self, client, db):
        user2_id = db.create_user("Second", "second@example.com")
        db.update_user_settings(user2_id, accent_color="rose", theme="light")
        self._login(client)
        resp = client.get("/")
        html = resp.get_data(as_text=True)
        # User 1 keeps the default green accent; user 2's choice is not shown.
        assert 'data-accent="green"' in html
        assert 'data-accent="rose"' not in html
# =================================================================== #
# Active Sessions — list, revoke, invalidation, IDOR                  #
# =================================================================== #

class TestActiveSessions:
    """Verify the Active Sessions feature end-to-end."""

    def _login_client(self, client, db, token="current-token"):
        """Log in as user 1 with a real session row so the guard passes."""
        db.create_user_session(1, token, ip_address="127.0.0.1", user_agent="Chrome on Windows")
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"
            sess["session_id"] = token

    def test_settings_renders_user_sessions(self, client, db):
        self._login_client(client, db)
        db.create_user_session(1, "other-token", ip_address="10.0.0.9", user_agent="Firefox on Mac")
        resp = client.get("/settings")
        html = resp.get_data(as_text=True)
        assert "Chrome on Windows" in html
        assert "This device" in html  # current session badge
        assert "Firefox on Mac" in html
        assert 'data-revoke-session="' in html  # revocable other session
        assert "No active sessions found." not in html

    def test_sessions_never_expose_another_users_devices(self, client, db):
        self._login_client(client, db)
        db.create_user("Second", "second@example.com")
        db.create_user_session(2, "hacker-session", user_agent="Evil on Hacker PC")
        resp = client.get("/settings")
        html = resp.get_data(as_text=True)
        assert "Evil on Hacker PC" not in html

    def test_revoke_requires_auth(self, client):
        resp = client.post("/settings/sessions/revoke", data={"session_id": "1"})
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]

    def test_revoke_marks_session_revoked(self, client, db):
        self._login_client(client, db)
        other = db.create_user_session(1, "victim-device", user_agent="Safari on iPhone")
        resp = client.post("/settings/sessions/revoke", data={"session_id": str(other)})
        assert resp.status_code == 302
        assert db.get_user_session_by_token("victim-device")["revoked"] == 1
        follow = client.get("/settings", follow_redirects=True)
        assert "Session revoked" in follow.get_data(as_text=True)

    def test_revoke_cannot_touch_another_users_session(self, client, db):
        """IDOR: user 1 must not be able to revoke user 2's session."""
        self._login_client(client, db)
        db.create_user("Second", "second@example.com")
        other_user_sid = db.create_user_session(2, "their-device", user_agent="Safari on iPhone")
        resp = client.post("/settings/sessions/revoke", data={"session_id": str(other_user_sid)}, follow_redirects=True)
        assert "Session not found" in resp.get_data(as_text=True)
        assert db.get_user_session_by_token("their-device")["revoked"] == 0

    def test_revoke_rejects_garbage_input(self, client, db):
        self._login_client(client, db)
        resp = client.post("/settings/sessions/revoke", data={"session_id": "abc"}, follow_redirects=True)
        assert "Invalid session" in resp.get_data(as_text=True)

    def test_revoke_blocks_current_session(self, client, db):
        self._login_client(client, db, token="current-token")
        current_id = db.get_user_session_by_token("current-token")["id"]
        resp = client.post("/settings/sessions/revoke", data={"session_id": str(current_id)}, follow_redirects=True)
        assert "cannot revoke your current session" in resp.get_data(as_text=True)
        assert db.get_user_session_by_token("current-token")["revoked"] == 0

    def test_revoked_session_is_invalidated_on_next_request(self, client, db):
        db.create_user_session(1, "stolen-device", user_agent="Chrome on Windows")
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"
            sess["session_id"] = "stolen-device"
        # The legitimate user revokes that device.
        db.revoke_user_session_by_token("stolen-device")
        # The stolen device is now signed out on its next request.
        resp = client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]
        follow = client.get("/login")
        assert b"revoked" in follow.data.lower()

    def test_logout_revokes_the_session(self, client, db):
        self._login_client(client, db, token="goodbye-token")
        client.get("/logout")
        assert db.get_user_session_by_token("goodbye-token")["revoked"] == 1

    def test_unknown_token_is_signed_out(self, client):
        """A session cookie with a token that no longer exists is invalid."""
        with client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["user_name"] = "Demo User"
            sess["session_id"] = "ghost-token"
        resp = client.get("/profile")
        assert resp.status_code == 302
        assert "/login" in resp.headers["Location"]
# =================================================================== #
# Data & Privacy toggles — persistence + per-user isolation            #
# =================================================================== #

class TestDataPrivacyToggles:
    """Personalised Insights & Anonymous Usage Data toggles."""

    def _login(self, client, user_id=1):
        with client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_name"] = "Demo User"

    def test_save_persists_and_renders_after_refresh(self, client, db):
        self._login(client)
        client.post("/settings/save", data={
            "name": "Demo User",
            "email": "demo@spendly.com",
            "personalised_insights_enabled": "on",
            "anonymous_usage_enabled": "on",
        })
        s = db.get_user_settings(1)
        assert s["personalised_insights_enabled"] == 1
        assert s["anonymous_usage_enabled"] == 1
        # "Refresh": re-render the settings page with persisted values.
        html = client.get("/settings").get_data(as_text=True)
        # The Data & Privacy toggles render checked after a refresh.
        toggles = html[html.find("Personalised Insights"):html.find("Download My Data")]
        assert "checked" in toggles

    def test_save_off_values(self, client, db):
        self._login(client)
        db.update_user_settings(1, personalised_insights_enabled=1, anonymous_usage_enabled=1)
        client.post("/settings/save", data={
            "name": "Demo User",
            "email": "demo@spendly.com",
            "personalised_insights_enabled": "",
            "anonymous_usage_enabled": "",
        })
        s = db.get_user_settings(1)
        assert s["personalised_insights_enabled"] == 0
        assert s["anonymous_usage_enabled"] == 0

    def test_preferences_never_leak_between_users(self, client, db):
        user2_id = db.create_user("Second", "second@example.com")
        self._login(client)
        client.post("/settings/save", data={
            "name": "Demo User",
            "email": "demo@spendly.com",
            "personalised_insights_enabled": "on",
            "anonymous_usage_enabled": "on",
        })
        s2 = db.get_user_settings(user2_id)
        # Surprising but correct: the DB default for personalised insights is
        # on; anonymous usage defaults to off. Nothing from user 1 leaks.
        assert s2["personalised_insights_enabled"] == 1
        assert s2["anonymous_usage_enabled"] == 0
    def test_preferences_never_leak_between_users(self, client, db):
        user2_id = db.create_user("Second", "second@example.com")
        self._login(client)
        client.post("/settings/save", data={
            "name": "Demo User",
            "email": "demo@spendly.com",
            "personalised_insights_enabled": "on",
            "anonymous_usage_enabled": "on",
        })
        s2 = db.get_user_settings(user2_id)
        # Surprising but correct: the DB default for personalised insights is
        # on; anonymous usage defaults to off. Nothing from user 1 leaks.
        assert s2["personalised_insights_enabled"] == 1
        assert s2["anonymous_usage_enabled"] == 0


# =================================================================== #
# Personalised Insights enforcement on Reports                        #
# =================================================================== #

class TestPersonalisedInsightsEnforcement:
    """The Reports page must honour the personalised-insights preference."""

    def _login(self, client, user_id=1):
        with client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_name"] = "Demo User"

    def test_reports_shows_insights_when_enabled(self, client, db):
        self._login(client)
        db.update_user_settings(1, personalised_insights_enabled=1)
        resp = client.get("/reports")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert "reports-insights" in html
        # The insights block is not hidden.
        assert 'class="reports-insights"' in html and "hidden" not in html.split("reports-insights")[1][:40]

    def test_reports_hides_insights_when_disabled(self, client, db):
        self._login(client)
        db.update_user_settings(1, personalised_insights_enabled=0)
        resp = client.get("/reports")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        # The block is still present in the DOM but hidden.
        assert 'class="reports-insights" hidden' in html

    def test_reports_insights_scoped_per_user(self, client, db):
        user2_id = db.create_user("Second", "second@example.com")
        # User 2 disabled insights; user 1 keeps them enabled.
        db.update_user_settings(user2_id, personalised_insights_enabled=0)
        self._login(client, user_id=1)
        html = client.get("/reports").get_data(as_text=True)
        assert 'class="reports-insights" hidden' not in html