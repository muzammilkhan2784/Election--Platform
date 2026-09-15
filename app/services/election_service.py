"""
Business Layer — ElectionService

Responsibility: Role-based access control for elections and ballot data.

Separation of concerns:
  - The data layer (repositories) fetches raw rows with no filtering.
  - This service decides WHICH elections a user may see based on their
    role (member → own society only, employee → assigned societies,
    admin → all), then delegates the actual SQL to the repositories.
  - The REST layer (api_routes.py) only calls this service and never
    queries the database directly.
"""

from app.repositories import election_repository, office_repository, initiative_repository, society_repository


def get_elections_for_user(db, session_user):
    role = session_user["role"]

    if role in ("member", "officer"):
        return election_repository.list_elections(db, society_id=session_user["society_id"])
    elif role == "employee":
        society_ids = society_repository.get_assigned_society_ids(db, session_user["user_id"])
        return election_repository.list_elections(db, society_ids=society_ids)
    else:  # admin
        return election_repository.list_elections(db)


def get_election_with_ballot(db, election_id, session_user):
    election = election_repository.get_election_by_id(db, election_id)

    if not election:
        raise LookupError("Election not found.")

    _check_society_access(db, election, session_user)

    # Single JOIN query per collection — no queries in loops
    offices = office_repository.get_offices_with_candidates(db, election_id)
    initiatives = initiative_repository.get_initiatives_with_options(db, election_id)

    return {
        "election": dict(election),
        "offices": offices,
        "initiatives": initiatives,
    }


def _check_society_access(db, election, session_user):
    role = session_user["role"]

    if role == "admin":
        return

    if role in ("member", "officer"):
        if election["society_id"] != session_user["society_id"]:
            raise PermissionError("Not authorized to view this election.")

    elif role == "employee":
        assigned = society_repository.get_assigned_society_ids(db, session_user["user_id"])
        if election["society_id"] not in assigned:
            raise PermissionError("Not authorized to view this election.")
