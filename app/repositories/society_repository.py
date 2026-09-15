"""
Data Access Layer — SocietyRepository

Raw SQL for societies and employee assignments. No business rules.
"""


def list_societies(db, society_ids=None):
    with db.cursor() as cur:
        if society_ids:
            cur.execute(
                """
                SELECT society_id, name, description
                FROM society
                WHERE society_id = ANY(%s)
                ORDER BY name
                """,
                (society_ids,)
            )
        else:
            cur.execute(
                """
                SELECT society_id, name, description
                FROM society
                ORDER BY name
                """
            )
        return cur.fetchall()


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


def insert_society(db, name, description):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO society (name, description, created_at, updated_at)
            VALUES (%s, %s, NOW(), NOW())
            RETURNING society_id, name, description
            """,
            (name, description)
        )
        return cur.fetchone()


def assign_employee(db, user_id, society_id):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO employee_society_assignment (user_id, society_id, assigned_at)
            VALUES (%s, %s, NOW())
            ON CONFLICT DO NOTHING
            """,
            (user_id, society_id)
        )


def unassign_employee(db, user_id, society_id):
    with db.cursor() as cur:
        cur.execute(
            """
            DELETE FROM employee_society_assignment
            WHERE user_id = %s AND society_id = %s
            """,
            (user_id, society_id)
        )


def list_assignments(db):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT esa.user_id, esa.society_id,
                   u.first_name || ' ' || u.last_name AS employee_name,
                   s.name AS society_name
            FROM employee_society_assignment esa
            JOIN "user" u ON u.user_id = esa.user_id
            JOIN society s ON s.society_id = esa.society_id
            ORDER BY s.name, u.last_name
            """
        )
        return cur.fetchall()
