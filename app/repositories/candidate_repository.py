"""
Data Access Layer — CandidateRepository

Raw SQL for candidates. No business rules.
"""


def insert_candidate(db, office_id, name, title_position, biography, photo_url, display_order):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO candidate
                (office_id, name, title_position, biography, photo_url, display_order)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING candidate_id
            """,
            (office_id, name, title_position, biography, photo_url, display_order)
        )
        return cur.fetchone()["candidate_id"]


def get_candidates_for_office(db, office_id):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT candidate_id, name, title_position, biography, photo_url, display_order
            FROM candidate
            WHERE office_id = %s
            ORDER BY display_order
            """,
            (office_id,)
        )
        return cur.fetchall()
