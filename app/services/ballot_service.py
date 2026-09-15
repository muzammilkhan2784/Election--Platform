"""
Business Layer — BallotService

Responsibility: Ballot creation, editing, and publishing rules.

Rules enforced here:
  - Only employees (assigned to the society) and admins may edit ballots
  - Ballots can only be edited when the election is in draft state
  - Each office must have votes_allowed >= 1
  - Each initiative must have at least 2 options
  - Publishing requires at least one office or initiative on the ballot

Transaction management: This service does NOT call db.commit().
The REST layer owns the transaction boundary via `with db:`.
The SELECT FOR UPDATE in save_ballot locks the election row for the
duration of the transaction, preventing two employees from overwriting
each other's ballot changes concurrently.
"""

from app.repositories import (
    election_repository, office_repository, candidate_repository,
    initiative_repository, audit_repository, society_repository
)


def create_election(db, session_user, data):
    role = session_user["role"]
    user_id = session_user["user_id"]

    if role not in ("employee", "admin"):
        raise PermissionError("Only employees and admins can create elections.")

    society_id = data.get("society_id")
    if not society_id:
        raise ValueError("society_id is required.")

    if role == "employee":
        assigned = society_repository.get_assigned_society_ids(db, user_id)
        if society_id not in assigned:
            raise PermissionError("You are not assigned to this society.")

    name = data.get("name", "").strip()
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not name:
        raise ValueError("Election name is required.")
    if not start_date or not end_date:
        raise ValueError("start_date and end_date are required.")
    if start_date > end_date:
        raise ValueError("start_date must be before end_date.")

    election = election_repository.insert_election(
        db, society_id, user_id, name, start_date, end_date,
        data.get("description"), data.get("instructions")
    )

    audit_repository.insert_audit_event(
        db, election["election_id"], user_id, "election_created", name
    )

    return dict(election)


def save_ballot(db, election_id, session_user, ballot_data):
    """
    Replaces the entire ballot for a draft election in one operation.
    Deletes existing offices/initiatives first, then inserts new ones.

    Uses SELECT FOR UPDATE to lock the election row — if two employees try
    to save at the same time, the second one blocks until the first commits,
    preventing a lost-update race. No commit here — the route layer wraps
    this in `with db:`.
    """
    role = session_user["role"]
    user_id = session_user["user_id"]

    if role not in ("employee", "admin"):
        raise PermissionError("Only employees and admins can edit ballots.")

    # Lock the row — prevents concurrent saves from racing
    election = election_repository.get_election_for_update(db, election_id)
    if not election:
        raise LookupError("Election not found.")

    if election["status"] != "draft":
        raise ValueError("Ballot can only be edited while the election is in draft state.")

    if role == "employee":
        assigned = society_repository.get_assigned_society_ids(db, user_id)
        if election["society_id"] not in assigned:
            raise PermissionError("You are not assigned to this election's society.")

    offices = ballot_data.get("offices", [])
    initiatives = ballot_data.get("initiatives", [])

    # Validate before touching the DB
    for i, office in enumerate(offices):
        if not office.get("title", "").strip():
            raise ValueError(f"Office {i + 1} is missing a title.")
        if int(office.get("votes_allowed", 1)) < 1:
            raise ValueError(f"votes_allowed must be >= 1 for office '{office['title']}'.")
        if not office.get("allow_write_in") and not office.get("candidates"):
            raise ValueError(f"Office '{office['title']}' needs at least one candidate.")

    for i, initiative in enumerate(initiatives):
        if not initiative.get("title", "").strip():
            raise ValueError(f"Initiative {i + 1} is missing a title.")
        if len(initiative.get("options", [])) < 2:
            raise ValueError(f"Initiative '{initiative['title']}' needs at least 2 options.")

    # Replace ballot atomically (cascade deletes candidates and options)
    office_repository.delete_offices_for_election(db, election_id)
    initiative_repository.delete_initiatives_for_election(db, election_id)

    for order, office in enumerate(offices, start=1):
        office_id = office_repository.insert_office(
            db, election_id,
            office["title"].strip(),
            int(office.get("votes_allowed", 1)),
            bool(office.get("allow_write_in", False)),
            order
        )
        for c_order, candidate in enumerate(office.get("candidates", []), start=1):
            candidate_repository.insert_candidate(
                db, office_id,
                candidate["name"].strip(),
                candidate.get("title_position", ""),
                candidate.get("biography", ""),
                candidate.get("photo_url", ""),
                c_order
            )

    for order, initiative in enumerate(initiatives, start=1):
        initiative_id = initiative_repository.insert_initiative(
            db, election_id,
            initiative["title"].strip(),
            initiative.get("description", ""),
            order
        )
        for o_order, option in enumerate(initiative.get("options", []), start=1):
            initiative_repository.insert_option(
                db, initiative_id,
                option["label"].strip(),
                o_order
            )

    audit_repository.insert_audit_event(
        db, election_id, user_id, "ballot_saved",
        f"{len(offices)} offices, {len(initiatives)} initiatives"
    )


def publish_election(db, election_id, session_user):
    role = session_user["role"]
    user_id = session_user["user_id"]

    if role not in ("employee", "admin"):
        raise PermissionError("Only employees and admins can publish elections.")

    # Lock the row during publish to prevent race conditions
    election = election_repository.get_election_for_update(db, election_id)
    if not election:
        raise LookupError("Election not found.")

    if election["status"] != "draft":
        raise ValueError("Only draft elections can be published.")

    if role == "employee":
        assigned = society_repository.get_assigned_society_ids(db, user_id)
        if election["society_id"] not in assigned:
            raise PermissionError("You are not assigned to this election's society.")

    offices = office_repository.get_offices_for_election(db, election_id)
    initiatives = initiative_repository.get_initiatives_for_election(db, election_id)
    if not offices and not initiatives:
        raise ValueError("Cannot publish an election with an empty ballot.")

    election_repository.update_election_status(db, election_id, "active")

    audit_repository.insert_audit_event(
        db, election_id, user_id, "election_published",
        "Election published — status changed from draft to active."
    )
