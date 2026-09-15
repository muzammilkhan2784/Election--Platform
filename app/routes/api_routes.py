"""
REST Layer — API Routes

Responsibility: HTTP interface only.
  - Parses incoming JSON
  - Owns the transaction boundary using psycopg3's `with db:` context manager
    (commits on success, rolls back automatically on any exception)
  - Calls the appropriate business-layer service
  - Maps Python exceptions to HTTP status codes
  - Returns JSON responses

Loose coupling: Zero business logic or SQL lives here.
Swapping Flask for another framework only requires changes in this file.

Layer flow (one-way, top to bottom):
  REST layer  →  Business layer (services/)  →  Data layer (repositories/)  →  PostgreSQL
"""

from flask import Blueprint, request, session, jsonify
from app.db import get_db
from app.services import (
    auth_service, election_service, voting_service,
    results_service, ballot_service, user_service
)

api_bp = Blueprint("api", __name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_login():
    if "user_id" not in session:
        return jsonify({"message": "Not authenticated."}), 401
    return None


def _session_user():
    return {
        "user_id": session["user_id"],
        "society_id": session.get("society_id"),
        "role": session["role"],
        "email": session.get("email", ""),
        "first_name": session["first_name"],
        "last_name": session["last_name"],
    }


def _serialize_election(e):
    return {
        "election_id": e["election_id"],
        "name": e["name"],
        "status": e["status"],
        "society_name": e.get("society_name"),
        "start_date": str(e["start_date"]) if e.get("start_date") else None,
        "end_date": str(e["end_date"]) if e.get("end_date") else None,
    }


# ── Auth ──────────────────────────────────────────────────────────────────────

@api_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    db = get_db()
    try:
        user = auth_service.login(db, email, password)
    except ValueError as e:
        return jsonify({"message": str(e)}), 400
    except PermissionError as e:
        return jsonify({"message": str(e)}), 401

    from app.repositories import user_repository
    with db:
        user_repository.update_last_login(db, user["user_id"])

    session.clear()
    session["user_id"] = user["user_id"]
    session["society_id"] = user["society_id"]
    session["role"] = user["role"]
    session["email"] = user["email"]
    session["first_name"] = user["first_name"]
    session["last_name"] = user["last_name"]

    return jsonify({"userId": user["user_id"], "role": user["role"]}), 200


@api_bp.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out."}), 200


# ── Current user ──────────────────────────────────────────────────────────────

@api_bp.route("/me")
def me():
    err = _require_login()
    if err:
        return err
    return jsonify(_session_user()), 200


@api_bp.route("/me", methods=["PUT"])
def update_me():
    """Any logged-in user can update their own first/last name."""
    err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    updates = {}
    if "first_name" in data:
        updates["first_name"] = data["first_name"].strip()
    if "last_name" in data:
        updates["last_name"] = data["last_name"].strip()

    if not updates:
        return jsonify({"message": "Nothing to update."}), 400

    from app.repositories import user_repository
    db = get_db()
    with db:
        user = user_repository.update_user(db, session["user_id"], updates)
    if not user:
        return jsonify({"message": "User not found."}), 404

    session["first_name"] = user["first_name"]
    session["last_name"] = user["last_name"]
    return jsonify(dict(user)), 200


@api_bp.route("/me/password", methods=["PUT"])
def change_password():
    """Any logged-in user can change their own password."""
    err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    current = data.get("current_password", "")
    new_pw  = data.get("new_password", "")

    if not current or not new_pw:
        return jsonify({"message": "Current and new password are required."}), 400
    if len(new_pw) < 8:
        return jsonify({"message": "New password must be at least 8 characters."}), 400

    import bcrypt
    from app.repositories import user_repository
    db = get_db()
    row = user_repository.get_user_by_id(db, session["user_id"])
    # get_user_by_id doesn't return password_hash — fetch it separately
    with db.cursor() as cur:
        cur.execute('SELECT password_hash FROM "user" WHERE user_id = %s', (session["user_id"],))
        pw_row = cur.fetchone()

    if not pw_row or not bcrypt.checkpw(current.encode(), pw_row["password_hash"].encode()):
        return jsonify({"message": "Current password is incorrect."}), 400

    new_hash = bcrypt.hashpw(new_pw.encode(), bcrypt.gensalt(10)).decode()
    with db:
        with db.cursor() as cur:
            cur.execute(
                'UPDATE "user" SET password_hash = %s, updated_at = NOW() WHERE user_id = %s',
                (new_hash, session["user_id"])
            )

    return jsonify({"message": "Password updated."}), 200


# ── Societies ─────────────────────────────────────────────────────────────────

@api_bp.route("/societies")
def list_societies():
    err = _require_login()
    if err:
        return err

    from app.repositories import society_repository
    su = _session_user()
    db = get_db()

    if su["role"] == "admin":
        societies = society_repository.list_societies(db)
    elif su["role"] == "employee":
        ids = society_repository.get_assigned_society_ids(db, su["user_id"])
        societies = society_repository.list_societies(db, society_ids=ids)
    else:
        return jsonify({"message": "Not authorized."}), 403

    return jsonify([dict(s) for s in societies]), 200


# ── Elections ─────────────────────────────────────────────────────────────────

@api_bp.route("/elections")
def list_elections():
    err = _require_login()
    if err:
        return err

    db = get_db()
    elections = election_service.get_elections_for_user(db, _session_user())
    return jsonify([_serialize_election(e) for e in elections]), 200


@api_bp.route("/elections", methods=["POST"])
def create_election():
    """Employee/admin creates a new election in draft state."""
    err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    db = get_db()
    try:
        with db:
            election = ballot_service.create_election(db, _session_user(), data)
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 400

    return jsonify(election), 201


@api_bp.route("/elections/<int:election_id>")
def get_election(election_id):
    err = _require_login()
    if err:
        return err

    db = get_db()
    try:
        data = election_service.get_election_with_ballot(db, election_id, _session_user())
    except LookupError as e:
        return jsonify({"message": str(e)}), 404
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403

    e = data["election"]
    e["start_date"] = str(e["start_date"]) if e.get("start_date") else None
    e["end_date"] = str(e["end_date"]) if e.get("end_date") else None

    return jsonify(data), 200


@api_bp.route("/elections/<int:election_id>/ballot", methods=["PUT"])
def save_ballot(election_id):
    """
    Replace the entire ballot for a draft election.
    Transaction owned here: `with db:` commits all inserts atomically
    or rolls back everything if any insert fails.
    """
    err = _require_login()
    if err:
        return err

    ballot_data = request.get_json(silent=True) or {}
    db = get_db()
    try:
        with db:
            ballot_service.save_ballot(db, election_id, _session_user(), ballot_data)
    except LookupError as e:
        return jsonify({"message": str(e)}), 404
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"message": "Ballot saved."}), 200


@api_bp.route("/elections/<int:election_id>/publish", methods=["POST"])
def publish_election(election_id):
    """Transition election from draft → active."""
    err = _require_login()
    if err:
        return err

    db = get_db()
    try:
        with db:
            ballot_service.publish_election(db, election_id, _session_user())
    except LookupError as e:
        return jsonify({"message": str(e)}), 404
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 409

    return jsonify({"message": "Election is now active."}), 200


@api_bp.route("/elections/<int:election_id>/members")
def get_member_vote_status(election_id):
    """Officer/employee/admin: who has voted and who hasn't for a specific election."""
    err = _require_login()
    if err:
        return err
    su = _session_user()
    if su["role"] not in ("officer", "employee", "admin"):
        return jsonify({"message": "Not authorized."}), 403

    from app.repositories import vote_repository
    db = get_db()
    rows = vote_repository.get_member_vote_status(db, election_id)
    return jsonify([
        {
            "user_id":     r["user_id"],
            "member_name": r["member_name"],
            "email":       r["email"],
            "has_voted":   r["has_voted"],
        }
        for r in rows
    ]), 200


@api_bp.route("/elections/participation")
def get_participation():
    """Officer sees turnout stats for all active elections in their society."""
    err = _require_login()
    if err:
        return err

    su = _session_user()
    if su["role"] not in ("officer", "employee", "admin"):
        return jsonify({"message": "Officers, employees, and admins only."}), 403

    from app.repositories import vote_repository, user_repository
    db = get_db()

    if su["role"] == "employee":
        society_ids = user_repository.get_assigned_society_ids(db, su["user_id"])
        if not society_ids:
            return jsonify({"message": "You are not assigned to a society."}), 400
        rows = vote_repository.get_participation_for_societies(db, society_ids)
    else:
        if not su["society_id"]:
            return jsonify({"message": "You are not assigned to a society."}), 400
        rows = vote_repository.get_participation(db, su["society_id"])
    return jsonify([
        {
            "election_id":     r["election_id"],
            "name":            r["name"],
            "start_date":      str(r["start_date"]) if r["start_date"] else None,
            "end_date":        str(r["end_date"]) if r["end_date"] else None,
            "total_eligible":  r["total_eligible"],
            "voted_count":     r["voted_count"],
        }
        for r in rows
    ]), 200


@api_bp.route("/elections/pending")
def get_pending_tasks():
    """Employee sees draft elections in their assigned societies."""
    err = _require_login()
    if err:
        return err
    su = _session_user()
    if su["role"] != "employee":
        return jsonify({"message": "Employees only."}), 403

    from app.repositories import user_repository
    db = get_db()
    society_ids = user_repository.get_assigned_society_ids(db, su["user_id"])
    if not society_ids:
        return jsonify([]), 200

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT e.election_id, e.name, e.status, e.start_date, e.end_date,
                   s.name AS society_name
            FROM election e
            JOIN society s ON s.society_id = e.society_id
            WHERE e.society_id = ANY(%s) AND e.status = 'draft'
            ORDER BY e.created_at DESC
            """,
            (society_ids,)
        )
        rows = cur.fetchall()

    return jsonify([
        {
            "election_id":   r["election_id"],
            "name":          r["name"],
            "status":        r["status"],
            "start_date":    str(r["start_date"]) if r["start_date"] else None,
            "end_date":      str(r["end_date"]) if r["end_date"] else None,
            "society_name":  r["society_name"],
        }
        for r in rows
    ]), 200


@api_bp.route("/elections/<int:election_id>/voted")
def check_voted(election_id):
    err = _require_login()
    if err:
        return err
    db = get_db()
    from app.repositories import vote_repository
    voted = vote_repository.has_user_voted(db, session["user_id"], election_id)
    return jsonify({"voted": voted}), 200


@api_bp.route("/elections/<int:election_id>/vote", methods=["POST"])
def submit_vote(election_id):
    """
    Submit a vote. Transaction owned here: all inserts commit together
    or roll back together if anything fails.
    """
    err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    db = get_db()
    try:
        with db:
            voting_service.submit_vote(db, election_id, _session_user(), data)
    except LookupError as e:
        return jsonify({"message": str(e)}), 404
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 409

    return jsonify({"message": "Vote submitted successfully."}), 200


@api_bp.route("/elections/<int:election_id>/results")
def get_results(election_id):
    err = _require_login()
    if err:
        return err

    db = get_db()
    try:
        data = results_service.get_results(db, election_id, _session_user())
    except LookupError as e:
        return jsonify({"message": str(e)}), 404
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 409

    return jsonify(data), 200


# ── Admin Reports ─────────────────────────────────────────────────────────────

@api_bp.route("/reports")
def get_reports():
    err = _require_login()
    if err:
        return err
    if _session_user()["role"] != "admin":
        return jsonify({"message": "Admins only."}), 403

    from app.repositories import audit_repository
    db = get_db()
    society_stats = audit_repository.get_society_stats(db)
    system_stats  = audit_repository.get_system_stats(db)

    return jsonify({
        "society_stats": [
            {
                "society_id":          r["society_id"],
                "name":                r["name"],
                "total_elections":     r["total_elections"],
                "active_elections":    r["active_elections"],
                "completed_elections": r["completed_elections"],
                "member_count":        r["member_count"],
                "avg_turnout":         float(r["avg_turnout"]),
            }
            for r in society_stats
        ],
        "system_stats": {
            "active_elections":    system_stats["active_elections"],
            "draft_elections":     system_stats["draft_elections"],
            "completed_elections": system_stats["completed_elections"],
            "total_users":         system_stats["total_users"],
            "active_users":        system_stats["active_users"],
            "members":             system_stats["members"],
            "officers":            system_stats["officers"],
            "employees":           system_stats["employees"],
            "admins":              system_stats["admins"],
            "recent_logins":       system_stats["recent_logins"],
        },
    }), 200


# ── Audit Logs ────────────────────────────────────────────────────────────────

@api_bp.route("/audit")
def get_audit_logs():
    err = _require_login()
    if err:
        return err
    if _session_user()["role"] != "admin":
        return jsonify({"message": "Admins only."}), 403

    from app.repositories import audit_repository
    db = get_db()
    ballot_events = audit_repository.list_ballot_audit_events(db)
    vote_events   = audit_repository.list_vote_activity(db)

    return jsonify({
        "ballot_events": [
            {
                "audit_id":       r["audit_id"],
                "action":         r["action"],
                "details":        r["details"],
                "edited_at":      str(r["edited_at"]),
                "election_name":  r["election_name"],
                "user_name":      r["user_name"],
                "user_email":     r["user_email"],
            }
            for r in ballot_events
        ],
        "vote_events": [
            {
                "submitted_at":   str(r["submitted_at"]),
                "election_name":  r["election_name"],
                "user_name":      r["user_name"],
                "user_email":     r["user_email"],
            }
            for r in vote_events
        ],
    }), 200


# ── Admin — Society management ────────────────────────────────────────────────

@api_bp.route("/societies", methods=["POST"])
def create_society():
    err = _require_login()
    if err:
        return err
    if _session_user()["role"] != "admin":
        return jsonify({"message": "Admins only."}), 403

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    description = (data.get("description") or "").strip()
    if not name:
        return jsonify({"message": "Society name is required."}), 400

    from app.repositories import society_repository
    db = get_db()
    with db:
        society = society_repository.insert_society(db, name, description)
    return jsonify(dict(society)), 201


@api_bp.route("/societies/assignments")
def list_assignments():
    err = _require_login()
    if err:
        return err
    if _session_user()["role"] != "admin":
        return jsonify({"message": "Admins only."}), 403

    from app.repositories import society_repository
    db = get_db()
    return jsonify([dict(a) for a in society_repository.list_assignments(db)]), 200


@api_bp.route("/users/<int:user_id>/societies", methods=["POST"])
def assign_society(user_id):
    err = _require_login()
    if err:
        return err
    if _session_user()["role"] != "admin":
        return jsonify({"message": "Admins only."}), 403

    data = request.get_json(silent=True) or {}
    society_id = data.get("society_id")
    if not society_id:
        return jsonify({"message": "society_id is required."}), 400

    from app.repositories import society_repository
    db = get_db()
    with db:
        society_repository.assign_employee(db, user_id, society_id)
    return jsonify({"message": "Assigned."}), 200


@api_bp.route("/users/<int:user_id>/societies/<int:society_id>", methods=["DELETE"])
def unassign_society(user_id, society_id):
    err = _require_login()
    if err:
        return err
    if _session_user()["role"] != "admin":
        return jsonify({"message": "Admins only."}), 403

    from app.repositories import society_repository
    db = get_db()
    with db:
        society_repository.unassign_employee(db, user_id, society_id)
    return jsonify({"message": "Unassigned."}), 200


# ── Admin — User management ───────────────────────────────────────────────────

@api_bp.route("/users")
def list_users():
    err = _require_login()
    if err:
        return err

    db = get_db()
    try:
        users = user_service.list_users(db, _session_user())
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403

    return jsonify(users), 200


@api_bp.route("/users", methods=["POST"])
def create_user():
    err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    db = get_db()
    try:
        with db:
            user = user_service.create_user(db, _session_user(), data)
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except ValueError as e:
        return jsonify({"message": str(e)}), 400

    return jsonify(user), 201


@api_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    err = _require_login()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    db = get_db()
    try:
        with db:
            user = user_service.update_user(db, _session_user(), user_id, data)
    except PermissionError as e:
        return jsonify({"message": str(e)}), 403
    except LookupError as e:
        return jsonify({"message": str(e)}), 404
    except ValueError as e:
        return jsonify({"message": str(e)}), 400

    return jsonify(user), 200
