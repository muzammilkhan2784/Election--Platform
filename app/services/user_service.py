"""
Business Layer — UserService

Responsibility: User management rules (admin only).

Rules enforced here:
  - Only admins can create or update users
  - Email must be unique (DB constraint, caught and re-raised)
  - Role must be a valid value
"""

import bcrypt
from app.repositories import user_repository

VALID_ROLES = {"member", "officer", "employee", "admin"}


def create_user(db, session_user, data):
    if session_user["role"] != "admin":
        raise PermissionError("Only admins can create users.")

    email = data.get("email", "").strip()
    password = data.get("password", "")
    role = data.get("role", "")
    first_name = data.get("first_name", "").strip()
    last_name = data.get("last_name", "").strip()
    society_id = data.get("society_id")

    if not email or not password:
        raise ValueError("Email and password are required.")
    if role not in VALID_ROLES:
        raise ValueError(f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(10)).decode()

    try:
        user = user_repository.insert_user(
            db, society_id, email, password_hash, first_name, last_name, role
        )
    except Exception as e:
        if "unique" in str(e).lower():
            raise ValueError("A user with this email already exists.")
        raise

    return dict(user)


def update_user(db, session_user, user_id, data):
    if session_user["role"] != "admin":
        raise PermissionError("Only admins can update users.")

    allowed_fields = {"first_name", "last_name", "role", "status", "society_id"}
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if "role" in updates and updates["role"] not in VALID_ROLES:
        raise ValueError(f"Invalid role. Must be one of: {', '.join(VALID_ROLES)}")

    if not updates:
        raise ValueError("No valid fields provided to update.")

    user = user_repository.update_user(db, user_id, updates)
    if not user:
        raise LookupError("User not found.")

    return dict(user)


DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def list_users(db, session_user, search=None, role=None, limit=50, offset=0):
    if session_user["role"] != "admin":
        raise PermissionError("Only admins can list all users.")

    # Clamp rather than reject: a caller asking for 10,000 rows gets a sane
    # page instead of an error, and the endpoint cannot be used to pull the
    # whole roster in one request. Absent means "default"; a supplied number is
    # clamped, so limit=0 is treated as a too-small page rather than falling
    # back to the default.
    limit = DEFAULT_PAGE_SIZE if limit in (None, "") else int(limit)
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    offset = 0 if offset in (None, "") else max(0, int(offset))

    rows, total = user_repository.list_users(
        db, search=(search or "").strip() or None, role=role or None,
        limit=limit, offset=offset,
    )
    return {
        "users": [dict(u) for u in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def list_employees(db, session_user):
    if session_user["role"] != "admin":
        raise PermissionError("Only admins can list employees.")
    return [dict(u) for u in user_repository.list_employees(db)]
