"""
Data Access Layer — UserRepository

Responsibility: Raw database reads and writes for the 'user' table.

Loose coupling: This module has NO knowledge of HTTP, Flask sessions,
or business rules. It only receives a db connection and plain values,
and returns raw data rows. The business layer (auth_service, etc.)
decides what to DO with those rows.
"""


def get_user_by_email(db, email):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT user_id, society_id, email, password_hash,
                   first_name, last_name, role, status
            FROM "user"
            WHERE email = %s
            """,
            (email,)
        )
        return cur.fetchone()


def get_user_by_id(db, user_id):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT user_id, society_id, email,
                   first_name, last_name, role, status
            FROM "user"
            WHERE user_id = %s
            """,
            (user_id,)
        )
        return cur.fetchone()


def list_users(db):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT u.user_id, u.email, u.first_name, u.last_name,
                   u.role, u.status, u.society_id, s.name AS society_name
            FROM "user" u
            LEFT JOIN society s ON s.society_id = u.society_id
            ORDER BY u.role, u.last_name
            """
        )
        return cur.fetchall()


def insert_user(db, society_id, email, password_hash, first_name, last_name, role):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO "user"
                (society_id, email, password_hash, first_name, last_name,
                 role, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())
            RETURNING user_id, society_id, email, first_name, last_name, role, status
            """,
            (society_id, email, password_hash, first_name, last_name, role)
        )
        return cur.fetchone()


def update_user(db, user_id, updates):
    allowed = {"first_name", "last_name", "role", "status", "society_id"}
    fields = {k: v for k, v in updates.items() if k in allowed}
    if not fields:
        return None
    set_clause = ", ".join(f"{k} = %s" for k in fields)
    values = list(fields.values()) + [user_id]
    with db.cursor() as cur:
        cur.execute(
            f"""
            UPDATE "user"
            SET {set_clause}, updated_at = NOW()
            WHERE user_id = %s
            RETURNING user_id, society_id, email, first_name, last_name, role, status
            """,
            values
        )
        return cur.fetchone()


def update_last_login(db, user_id):
    with db.cursor() as cur:
        cur.execute(
            'UPDATE "user" SET last_login = NOW() WHERE user_id = %s',
            (user_id,)
        )


def get_assigned_society_ids(db, user_id):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT society_id
            FROM employee_society_assignment
            WHERE user_id = %s
            """,
            (user_id,)
        )
        return [r["society_id"] for r in cur.fetchall()]
