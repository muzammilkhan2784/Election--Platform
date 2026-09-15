"""
Unit Tests — AuthService (Business Layer)

Tests the login() business function in isolation by mocking the
data layer (user_repository). No real database connection is needed,
which demonstrates that the business layer is loosely coupled from
the data layer — they can be tested independently.
"""

import unittest
from unittest.mock import patch, MagicMock
import bcrypt

from app.services import auth_service


def _make_user(**kwargs):
    """Helper: build a fake user dict as the repository would return."""
    pw_hash = bcrypt.hashpw(b"password123", bcrypt.gensalt(10)).decode()
    defaults = {
        "user_id": 1,
        "society_id": 1,
        "email": "member@example.com",
        "password_hash": pw_hash,
        "first_name": "Mary",
        "last_name": "Member",
        "role": "member",
        "status": "active",
    }
    defaults.update(kwargs)
    return defaults


class TestLogin(unittest.TestCase):

    def _call(self, email, password, user_row):
        """Patch user_repository and call auth_service.login()."""
        with patch("app.services.auth_service.user_repository") as mock_repo:
            mock_repo.get_user_by_email.return_value = user_row
            db = MagicMock()
            return auth_service.login(db, email, password)

    # ── Happy path ────────────────────────────────────────────────────────────

    def test_valid_credentials_returns_session_user(self):
        user = _make_user()
        result = self._call("member@example.com", "password123", user)

        self.assertEqual(result["user_id"], 1)
        self.assertEqual(result["role"], "member")
        self.assertEqual(result["first_name"], "Mary")

    def test_returns_correct_society_id(self):
        user = _make_user(society_id=42)
        result = self._call("member@example.com", "password123", user)
        self.assertEqual(result["society_id"], 42)

    # ── Validation errors ─────────────────────────────────────────────────────

    def test_empty_email_raises_value_error(self):
        db = MagicMock()
        with self.assertRaises(ValueError):
            auth_service.login(db, "", "password123")

    def test_empty_password_raises_value_error(self):
        db = MagicMock()
        with self.assertRaises(ValueError):
            auth_service.login(db, "member@example.com", "")

    # ── Auth failures ─────────────────────────────────────────────────────────

    def test_unknown_email_raises_permission_error(self):
        with patch("app.services.auth_service.user_repository") as mock_repo:
            mock_repo.get_user_by_email.return_value = None
            db = MagicMock()
            with self.assertRaises(PermissionError):
                auth_service.login(db, "nobody@example.com", "password123")

    def test_wrong_password_raises_permission_error(self):
        user = _make_user()
        with self.assertRaises(PermissionError):
            self._call("member@example.com", "wrongpassword", user)

    def test_inactive_user_raises_permission_error(self):
        user = _make_user(status="disabled")
        with self.assertRaises(PermissionError):
            self._call("member@example.com", "password123", user)


if __name__ == "__main__":
    unittest.main()
