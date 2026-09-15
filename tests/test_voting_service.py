"""
Unit Tests — VotingService (Business Layer)

Tests submit_vote() business rules in isolation by mocking the
data layer repositories. Verifies that:
  - Only members/officers can vote
  - Election must be active
  - User must belong to the election's society
  - Duplicate votes are rejected
  - The service leaves transaction control to the REST layer
  - Failures propagate so the caller's `with db:` block rolls back
"""

import unittest
from unittest.mock import patch, MagicMock, call

from app.services import voting_service


def _session_user(**kwargs):
    defaults = {
        "user_id": 10,
        "society_id": 1,
        "role": "member",
        "first_name": "Mary",
        "last_name": "Member",
    }
    defaults.update(kwargs)
    return defaults


def _election(**kwargs):
    defaults = {
        "election_id": 5,
        "society_id": 1,
        "name": "IEEE 2026",
        "status": "active",
    }
    defaults.update(kwargs)
    return defaults


VALID_VOTE_DATA = {
    "office_votes": [{"office_id": 1, "candidate_ids": [2]}],
    "initiative_votes": [{"initiative_id": 1, "option_id": 3}],
}


class TestSubmitVote(unittest.TestCase):

    _MISSING = object()  # sentinel so callers can explicitly pass None

    def _patch_repos(self, election=_MISSING, already_voted=False):
        """Returns a context manager that patches all repositories."""
        patches = {
            "election_repository": patch("app.services.voting_service.election_repository"),
            "vote_repository":     patch("app.services.voting_service.vote_repository"),
            "audit_repository":    patch("app.services.voting_service.audit_repository"),
            "society_repository":  patch("app.services.voting_service.society_repository"),
        }
        mocks = {k: p.start() for k, p in patches.items()}

        mocks["election_repository"].get_election_by_id.return_value = (
            _election() if election is self._MISSING else election
        )
        mocks["vote_repository"].has_user_voted.return_value = already_voted
        mocks["vote_repository"].insert_vote.return_value = {"vote_id": 99}

        self._patches = patches
        return mocks

    def _stop_patches(self):
        for p in self._patches.values():
            p.stop()

    # ── Happy path ────────────────────────────────────────────────────────────

    def test_service_leaves_transaction_control_to_caller(self):
        # api_routes.submit_vote wraps this call in `with db:`. A commit here
        # would end that transaction early, so a later failure in the same
        # request could no longer roll the vote back.
        mocks = self._patch_repos()
        db = MagicMock()
        try:
            voting_service.submit_vote(db, 5, _session_user(), VALID_VOTE_DATA)
            db.commit.assert_not_called()
            db.rollback.assert_not_called()
        finally:
            self._stop_patches()

    def test_valid_vote_inserts_candidate_vote(self):
        mocks = self._patch_repos()
        db = MagicMock()
        try:
            voting_service.submit_vote(db, 5, _session_user(), VALID_VOTE_DATA)
            mocks["vote_repository"].insert_candidate_vote.assert_called_once_with(
                db, 99, 1, 2
            )
        finally:
            self._stop_patches()

    def test_valid_vote_inserts_initiative_vote(self):
        mocks = self._patch_repos()
        db = MagicMock()
        try:
            voting_service.submit_vote(db, 5, _session_user(), VALID_VOTE_DATA)
            mocks["vote_repository"].insert_initiative_vote.assert_called_once_with(
                db, 99, 1, 3
            )
        finally:
            self._stop_patches()

    def test_audit_event_logged_on_success(self):
        mocks = self._patch_repos()
        db = MagicMock()
        try:
            voting_service.submit_vote(db, 5, _session_user(), VALID_VOTE_DATA)
            mocks["audit_repository"].insert_audit_event.assert_called_once()
        finally:
            self._stop_patches()

    # ── Role enforcement ──────────────────────────────────────────────────────

    def test_admin_cannot_vote(self):
        mocks = self._patch_repos()
        db = MagicMock()
        try:
            with self.assertRaises(PermissionError):
                voting_service.submit_vote(
                    db, 5, _session_user(role="admin"), VALID_VOTE_DATA
                )
        finally:
            self._stop_patches()

    def test_employee_cannot_vote(self):
        mocks = self._patch_repos()
        db = MagicMock()
        try:
            with self.assertRaises(PermissionError):
                voting_service.submit_vote(
                    db, 5, _session_user(role="employee"), VALID_VOTE_DATA
                )
        finally:
            self._stop_patches()

    # ── Election state enforcement ─────────────────────────────────────────────

    def test_draft_election_raises_value_error(self):
        mocks = self._patch_repos(election=_election(status="draft"))
        db = MagicMock()
        try:
            with self.assertRaises(ValueError):
                voting_service.submit_vote(db, 5, _session_user(), VALID_VOTE_DATA)
        finally:
            self._stop_patches()

    def test_completed_election_raises_value_error(self):
        mocks = self._patch_repos(election=_election(status="completed"))
        db = MagicMock()
        try:
            with self.assertRaises(ValueError):
                voting_service.submit_vote(db, 5, _session_user(), VALID_VOTE_DATA)
        finally:
            self._stop_patches()

    def test_election_not_found_raises_lookup_error(self):
        mocks = self._patch_repos(election=None)  # explicit None → not found
        db = MagicMock()
        try:
            with self.assertRaises(LookupError):
                voting_service.submit_vote(db, 5, _session_user(), VALID_VOTE_DATA)
        finally:
            self._stop_patches()

    # ── Society enforcement ───────────────────────────────────────────────────

    def test_wrong_society_raises_permission_error(self):
        mocks = self._patch_repos(election=_election(society_id=99))
        db = MagicMock()
        try:
            with self.assertRaises(PermissionError):
                voting_service.submit_vote(
                    db, 5, _session_user(society_id=1), VALID_VOTE_DATA
                )
        finally:
            self._stop_patches()

    # ── Duplicate vote prevention ─────────────────────────────────────────────

    def test_already_voted_raises_value_error(self):
        mocks = self._patch_repos(already_voted=True)
        db = MagicMock()
        try:
            with self.assertRaises(ValueError):
                voting_service.submit_vote(db, 5, _session_user(), VALID_VOTE_DATA)
        finally:
            self._stop_patches()

    # ── Transaction rollback on failure ───────────────────────────────────────

    def test_db_error_propagates_to_caller(self):
        # The service must not swallow the error: the caller's `with db:` block
        # is what rolls the partial ballot back, and it only fires on an
        # exception escaping this call.
        mocks = self._patch_repos()
        mocks["vote_repository"].insert_candidate_vote.side_effect = RuntimeError("DB error")
        db = MagicMock()
        try:
            with self.assertRaises(RuntimeError):
                voting_service.submit_vote(db, 5, _session_user(), VALID_VOTE_DATA)
            db.commit.assert_not_called()
        finally:
            self._stop_patches()


if __name__ == "__main__":
    unittest.main()
