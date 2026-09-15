"""
Data Access Layer — OfficeRepository

Raw SQL for offices. No business rules.
"""


def delete_offices_for_election(db, election_id):
    """Cascade deletes candidates too via FK ON DELETE CASCADE."""
    with db.cursor() as cur:
        cur.execute(
            "DELETE FROM office WHERE election_id = %s",
            (election_id,)
        )


def insert_office(db, election_id, title, votes_allowed, allow_write_in, display_order):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO office
                (election_id, title, votes_allowed, allow_write_in, display_order)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING office_id
            """,
            (election_id, title, votes_allowed, allow_write_in, display_order)
        )
        return cur.fetchone()["office_id"]


def get_offices_for_election(db, election_id):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT office_id, title, votes_allowed, allow_write_in, display_order
            FROM office
            WHERE election_id = %s
            ORDER BY display_order
            """,
            (election_id,)
        )
        return cur.fetchall()


def get_offices_with_candidates(db, election_id):
    """
    Single JOIN query replacing the N+1 pattern of fetching candidates
    per office. Returns offices with candidates already nested.
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT o.office_id, o.title, o.votes_allowed,
                   o.allow_write_in, o.display_order,
                   c.candidate_id, c.name AS candidate_name,
                   c.title_position, c.biography, c.photo_url,
                   c.display_order AS candidate_order
            FROM office o
            LEFT JOIN candidate c ON c.office_id = o.office_id
            WHERE o.election_id = %s
            ORDER BY o.display_order, c.display_order
            """,
            (election_id,)
        )
        rows = cur.fetchall()

    # Group candidates under their office in Python — no extra queries
    offices = {}
    for row in rows:
        oid = row["office_id"]
        if oid not in offices:
            offices[oid] = {
                "office_id": oid,
                "title": row["title"],
                "votes_allowed": row["votes_allowed"],
                "allow_write_in": row["allow_write_in"],
                "display_order": row["display_order"],
                "candidates": [],
            }
        if row["candidate_id"] is not None:
            offices[oid]["candidates"].append({
                "candidate_id": row["candidate_id"],
                "name": row["candidate_name"],
                "title_position": row["title_position"],
                "biography": row["biography"],
                "photo_url": row["photo_url"],
                "display_order": row["candidate_order"],
            })

    return list(offices.values())
