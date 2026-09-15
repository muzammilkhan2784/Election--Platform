"""
Data Access Layer — ElectionRepository

Responsibility: Raw database reads and writes for elections.

Loose coupling: No business rules here. Filtering by role, checking
access rights, and deciding which elections a user may see is entirely
the responsibility of the business layer (election_service.py).
This module only runs the SQL it is told to run.
"""


def list_elections(db, society_id=None, society_ids=None):
    with db.cursor() as cur:
        if society_id is not None:
            cur.execute(
                """
                SELECT e.election_id, e.name, e.status,
                       e.start_date, e.end_date, s.name AS society_name
                FROM election e
                JOIN society s ON s.society_id = e.society_id
                WHERE e.society_id = %s
                ORDER BY e.start_date DESC
                """,
                (society_id,)
            )
        elif society_ids is not None:
            cur.execute(
                """
                SELECT e.election_id, e.name, e.status,
                       e.start_date, e.end_date, s.name AS society_name
                FROM election e
                JOIN society s ON s.society_id = e.society_id
                WHERE e.society_id = ANY(%s)
                ORDER BY e.start_date DESC
                """,
                (society_ids,)
            )
        else:
            cur.execute(
                """
                SELECT e.election_id, e.name, e.status,
                       e.start_date, e.end_date, s.name AS society_name
                FROM election e
                JOIN society s ON s.society_id = e.society_id
                ORDER BY e.start_date DESC
                """
            )
        return cur.fetchall()


def get_election_by_id(db, election_id):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT e.election_id, e.society_id, e.name, e.status,
                   e.start_date, e.end_date, e.description, e.instructions,
                   s.name AS society_name
            FROM election e
            JOIN society s ON s.society_id = e.society_id
            WHERE e.election_id = %s
            """,
            (election_id,)
        )
        return cur.fetchone()


def get_election_for_update(db, election_id):
    """
    SELECT FOR UPDATE — locks the election row for the duration of the
    current transaction. Prevents two employees from saving the ballot
    concurrently and overwriting each other's changes.
    Must be called inside a transaction (i.e. inside `with db:`).
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT election_id, society_id, status
            FROM election
            WHERE election_id = %s
            FOR UPDATE
            """,
            (election_id,)
        )
        return cur.fetchone()


def insert_election(db, society_id, created_by, name, start_date, end_date,
                    description=None, instructions=None):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO election
                (society_id, created_by, name, start_date, end_date,
                 description, instructions, status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'draft', NOW(), NOW())
            RETURNING election_id, society_id, name, status,
                      start_date, end_date, description, instructions
            """,
            (society_id, created_by, name, start_date, end_date,
             description, instructions)
        )
        return cur.fetchone()


def update_election_status(db, election_id, status):
    with db.cursor() as cur:
        cur.execute(
            """
            UPDATE election SET status = %s, updated_at = NOW()
            WHERE election_id = %s
            RETURNING election_id, status
            """,
            (status, election_id)
        )
        return cur.fetchone()
