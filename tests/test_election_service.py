"""
Unit Tests — ElectionService (Business Layer)

Tests role-based election access in isolation by mocking repositories.
Demonstrates that the business layer correctly routes requests based
on role without any dependency on Flask, HTTP, or a live database.
"""

import unittest
from unittest.mock import patch, MagicMock, ANY

from app.services import election_service


def _session_user(**kwargs):
    defaults = {
        "user_id": 1,
        "society_id": 1,
        "role": "member",
    }
    defaults.update(kwargs)
    return defaults


class TestGetElectionsForUser(unittest.TestCase):

    def _call(self, session_user, elections=None, assigned_ids=None):
        with patch("app.services.election_service.election_repository") as mock_er, \
             patch("app.services.election_service.society_repository") as mock_sr:

            mock_er.list_elections.return_value = elections or []
            mock_sr.get_assigned_society_ids.return_value = assigned_ids or []
            db = MagicMock()
            result = election_service.get_elections_for_user(db, session_user)
            return result, mock_er, mock_sr

    def test_member_filters_by_society_id(self):
        _, mock_er, _ = self._call(_session_user(role="member", society_id=7))
        mock_er.list_elections.assert_called_once_with(ANY, society_id=7)

    def test_officer_filters_by_society_id(self):
        _, mock_er, _ = self._call(_session_user(role="officer", society_id=3))
        mock_er.list_elections.assert_called_once_with(ANY, society_id=3)

    def test_employee_filters_by_assigned_society_ids(self):
        _, mock_er, mock_sr = self._call(
            _session_user(role="employee", user_id=5),
            assigned_ids=[1, 2]
        )
        mock_sr.get_assigned_society_ids.assert_called_once()
        mock_er.list_elections.assert_called_once_with(ANY, society_ids=[1, 2])

    def test_admin_gets_all_elections(self):
        _, mock_er, _ = self._call(_session_user(role="admin"))
        mock_er.list_elections.assert_called_once_with(ANY)

    def test_returns_list(self):
        fake_elections = [{"election_id": 1, "name": "Test"}]
        result, _, _ = self._call(_session_user(), elections=fake_elections)
        self.assertEqual(result, fake_elections)


class TestGetElectionWithBallot(unittest.TestCase):

    def _call(self, election, session_user, assigned_ids=None):
        # No candidate_repository here: candidates come back inside the office
        # rows via a single JOIN, so election_service never imports it.
        with patch("app.services.election_service.election_repository") as mock_er, \
             patch("app.services.election_service.office_repository") as mock_or, \
             patch("app.services.election_service.initiative_repository") as mock_ir, \
             patch("app.services.election_service.society_repository") as mock_sr:

            mock_er.get_election_by_id.return_value = election
            mock_or.get_offices_with_candidates.return_value = []
            mock_ir.get_initiatives_with_options.return_value = []
            mock_sr.get_assigned_society_ids.return_value = assigned_ids or []
            db = MagicMock()
            return election_service.get_election_with_ballot(db, 1, session_user)

    def test_not_found_raises_lookup_error(self):
        with self.assertRaises(LookupError):
            self._call(None, _session_user())

    def test_member_wrong_society_raises_permission_error(self):
        election = {"election_id": 1, "society_id": 99, "name": "X", "status": "active"}
        with self.assertRaises(PermissionError):
            self._call(election, _session_user(role="member", society_id=1))

    def test_member_correct_society_returns_data(self):
        election = {"election_id": 1, "society_id": 1, "name": "X", "status": "active"}
        result = self._call(election, _session_user(role="member", society_id=1))
        self.assertIn("election", result)
        self.assertIn("offices", result)
        self.assertIn("initiatives", result)

    def test_admin_can_access_any_election(self):
        election = {"election_id": 1, "society_id": 99, "name": "X", "status": "active"}
        result = self._call(election, _session_user(role="admin", society_id=None))
        self.assertIn("election", result)

    def test_employee_wrong_society_raises_permission_error(self):
        election = {"election_id": 1, "society_id": 5, "name": "X", "status": "active"}
        with self.assertRaises(PermissionError):
            self._call(election, _session_user(role="employee"), assigned_ids=[1, 2])


if __name__ == "__main__":
    unittest.main()
