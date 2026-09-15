"""
Unit Tests — UserService (Business Layer)

Covers admin-only access and the paging rules applied before the query runs.
The roster is large enough that an unbounded page size is a real problem, so
the clamping behaviour is asserted rather than assumed.
"""

import unittest
from unittest.mock import MagicMock, patch

from app.services import user_service


def _admin(**kwargs):
    defaults = {"user_id": 1, "society_id": None, "role": "admin"}
    defaults.update(kwargs)
    return defaults


class TestListUsers(unittest.TestCase):

    def _call(self, session_user, **kwargs):
        with patch("app.services.user_service.user_repository") as repo:
            repo.list_users.return_value = ([], 0)
            db = MagicMock()
            result = user_service.list_users(db, session_user, **kwargs)
            return result, repo

    # ── Access ────────────────────────────────────────────────────────────────

    def test_non_admin_is_rejected(self):
        for role in ("member", "officer", "employee"):
            with self.subTest(role=role):
                with self.assertRaises(PermissionError):
                    self._call(_admin(role=role))

    def test_admin_is_allowed(self):
        result, _ = self._call(_admin())
        self.assertEqual(result["total"], 0)
        self.assertEqual(result["users"], [])

    # ── Paging ────────────────────────────────────────────────────────────────

    def test_default_page_size_applied(self):
        _, repo = self._call(_admin())
        self.assertEqual(repo.list_users.call_args.kwargs["limit"], 50)
        self.assertEqual(repo.list_users.call_args.kwargs["offset"], 0)

    def test_oversized_limit_is_clamped(self):
        # Without a ceiling this endpoint could be used to pull all 20,000 rows
        # in one request.
        _, repo = self._call(_admin(), limit=100000)
        self.assertEqual(repo.list_users.call_args.kwargs["limit"],
                         user_service.MAX_PAGE_SIZE)

    def test_zero_and_negative_limits_become_one(self):
        for value in (0, -5):
            with self.subTest(limit=value):
                _, repo = self._call(_admin(), limit=value)
                self.assertEqual(repo.list_users.call_args.kwargs["limit"], 1)

    def test_negative_offset_becomes_zero(self):
        _, repo = self._call(_admin(), offset=-10)
        self.assertEqual(repo.list_users.call_args.kwargs["offset"], 0)

    def test_numeric_strings_are_accepted(self):
        # Query string values arrive as text.
        _, repo = self._call(_admin(), limit="25", offset="50")
        self.assertEqual(repo.list_users.call_args.kwargs["limit"], 25)
        self.assertEqual(repo.list_users.call_args.kwargs["offset"], 50)

    # ── Filters ───────────────────────────────────────────────────────────────

    def test_blank_search_is_dropped(self):
        # An empty box must not filter everything out.
        _, repo = self._call(_admin(), search="   ")
        self.assertIsNone(repo.list_users.call_args.kwargs["search"])

    def test_search_is_trimmed(self):
        _, repo = self._call(_admin(), search="  khoury ")
        self.assertEqual(repo.list_users.call_args.kwargs["search"], "khoury")

    def test_role_filter_passed_through(self):
        _, repo = self._call(_admin(), role="officer")
        self.assertEqual(repo.list_users.call_args.kwargs["role"], "officer")

    def test_total_is_returned_for_paging(self):
        with patch("app.services.user_service.user_repository") as repo:
            repo.list_users.return_value = ([{"user_id": 7}], 20024)
            result = user_service.list_users(MagicMock(), _admin())
        self.assertEqual(result["total"], 20024)
        self.assertEqual(len(result["users"]), 1)


class TestListEmployees(unittest.TestCase):

    def test_non_admin_is_rejected(self):
        with self.assertRaises(PermissionError):
            user_service.list_employees(MagicMock(), _admin(role="employee"))

    def test_admin_gets_employees(self):
        with patch("app.services.user_service.user_repository") as repo:
            repo.list_employees.return_value = [{"user_id": 3, "role": "employee"}]
            result = user_service.list_employees(MagicMock(), _admin())
        self.assertEqual(result, [{"user_id": 3, "role": "employee"}])


if __name__ == "__main__":
    unittest.main()
