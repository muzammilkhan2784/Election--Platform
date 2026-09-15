"""
Business Layer — ResultsService

Reads election results from the materialized views (mv_candidate_results,
mv_initiative_results) via the refresh_election_results stored procedure.

Flow:
  1. Call CALL refresh_election_results() — ensures the views are current.
  2. Query mv_candidate_results and mv_initiative_results for this election.

Why materialized views?
  For a completed election the vote counts never change. Pre-computing them
  means repeated result page loads hit the cached view rows instead of
  re-aggregating the full vote tables every time.
"""

from app.repositories import election_repository, vote_repository, society_repository


def get_results(db, election_id, session_user):
    role = session_user["role"]

    if role == "member":
        raise PermissionError("Members cannot view election results.")

    election = election_repository.get_election_by_id(db, election_id)
    if not election:
        raise LookupError("Election not found.")

    if election["status"] not in ("active", "completed"):
        raise ValueError("Results are only available once an election is active or completed.")

    if role == "officer":
        if election["society_id"] != session_user["society_id"]:
            raise PermissionError("Not authorized to view this election.")
        if election["status"] != "completed":
            raise PermissionError("Results are only available after the election is completed.")
    elif role == "employee":
        assigned = society_repository.get_assigned_society_ids(db, session_user["user_id"])
        if election["society_id"] not in assigned:
            raise PermissionError("Not authorized to view this election.")

    # Refresh materialized views via stored procedure, then read from them
    vote_repository.refresh_election_results(db)

    raw_offices     = vote_repository.get_candidate_results_from_view(db, election_id)
    raw_initiatives = vote_repository.get_initiative_results_from_view(db, election_id)

    # Group candidates under their office
    offices = {}
    for row in raw_offices:
        oid = row["office_id"]
        if oid not in offices:
            offices[oid] = {
                "office_id":    oid,
                "office_title": row["office_title"],
                "candidates":   [],
            }
        offices[oid]["candidates"].append({
            "candidate_id":   row["candidate_id"],
            "candidate_name": row["candidate_name"],
            "vote_count":     row["vote_count"],
        })

    # Group options under their initiative
    initiatives = {}
    for row in raw_initiatives:
        iid = row["initiative_id"]
        if iid not in initiatives:
            initiatives[iid] = {
                "initiative_id":    iid,
                "initiative_title": row["initiative_title"],
                "options":          [],
            }
        initiatives[iid]["options"].append({
            "option_id":    row["option_id"],
            "option_label": row["option_label"],
            "vote_count":   row["vote_count"],
        })

    return {
        "election_id":   election_id,
        "election_name": election["name"],
        "status":        election["status"],
        "offices":       list(offices.values()),
        "initiatives":   list(initiatives.values()),
    }
