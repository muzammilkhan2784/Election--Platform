"""
Business Layer — VotingService

Responsibility: Enforces all voting rules before writes happen.

Rules enforced here (not in the data layer):
  - Only members and officers may vote
  - Election must be active
  - User must belong to the election's society
  - One vote per user per election (duplicate check)

Transaction management: This service does NOT call db.commit() or
db.rollback(). Transaction boundaries are owned by the REST layer
(api_routes.py) using psycopg3's `with db:` context manager, which
commits on success and rolls back on any exception automatically.
The business layer has no knowledge of how data is stored or committed.

Loose coupling: This service does not import Flask or touch HTTP.
It receives plain Python dicts and raises plain exceptions.
"""

from app.repositories import election_repository, vote_repository, audit_repository, society_repository


def submit_vote(db, election_id, session_user, vote_data):
    role = session_user["role"]
    user_id = session_user["user_id"]

    if role not in ("member", "officer"):
        raise PermissionError("Only members and officers may vote.")

    election = election_repository.get_election_by_id(db, election_id)
    if not election:
        raise LookupError("Election not found.")

    if election["status"] != "active":
        raise ValueError("This election is not currently active.")

    if election["society_id"] != session_user["society_id"]:
        raise PermissionError("You are not a member of this election's society.")

    if vote_repository.has_user_voted(db, user_id, election_id):
        raise ValueError("You have already voted in this election.")

    office_votes = vote_data.get("office_votes", [])
    initiative_votes = vote_data.get("initiative_votes", [])

    vote_row = vote_repository.insert_vote(db, user_id, election_id)
    vote_id = vote_row["vote_id"]

    for ov in office_votes:
        office_id = ov["office_id"]
        candidate_ids = ov.get("candidate_ids", [])
        write_in_name = ov.get("write_in_name")

        for cid in candidate_ids:
            vote_repository.insert_candidate_vote(db, vote_id, office_id, cid)

        if write_in_name:
            vote_repository.insert_write_in_vote(db, vote_id, office_id, write_in_name)

    for iv in initiative_votes:
        vote_repository.insert_initiative_vote(
            db, vote_id, iv["initiative_id"], iv["option_id"]
        )

    audit_repository.insert_audit_event(
        db, election_id, user_id, "vote_submitted", None
    )
