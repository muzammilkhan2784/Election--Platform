"""
Data Access Layer — InitiativeRepository

Raw SQL for initiatives and options. No business rules.
"""


def delete_initiatives_for_election(db, election_id):
    """Cascade deletes options and votes via FK ON DELETE CASCADE."""
    with db.cursor() as cur:
        cur.execute(
            "DELETE FROM initiative WHERE election_id = %s",
            (election_id,)
        )


def insert_initiative(db, election_id, title, description, display_order):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO initiative (election_id, title, description, display_order)
            VALUES (%s, %s, %s, %s)
            RETURNING initiative_id
            """,
            (election_id, title, description, display_order)
        )
        return cur.fetchone()["initiative_id"]


def insert_option(db, initiative_id, label, display_order):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO initiative_option (initiative_id, label, display_order)
            VALUES (%s, %s, %s)
            """,
            (initiative_id, label, display_order)
        )


def get_initiatives_with_options(db, election_id):
    """
    Single JOIN query replacing the N+1 pattern of fetching options
    per initiative. Returns initiatives with options already nested.
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT i.initiative_id, i.title, i.description, i.display_order,
                   io.option_id, io.label, io.display_order AS option_order
            FROM initiative i
            LEFT JOIN initiative_option io ON io.initiative_id = i.initiative_id
            WHERE i.election_id = %s
            ORDER BY i.display_order, io.display_order
            """,
            (election_id,)
        )
        rows = cur.fetchall()

    initiatives = {}
    for row in rows:
        iid = row["initiative_id"]
        if iid not in initiatives:
            initiatives[iid] = {
                "initiative_id": iid,
                "title": row["title"],
                "description": row["description"],
                "display_order": row["display_order"],
                "options": [],
            }
        if row["option_id"] is not None:
            initiatives[iid]["options"].append({
                "option_id": row["option_id"],
                "label": row["label"],
                "display_order": row["option_order"],
            })

    return list(initiatives.values())


def get_initiatives_for_election(db, election_id):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT initiative_id, title, description, display_order
            FROM initiative
            WHERE election_id = %s
            ORDER BY display_order
            """,
            (election_id,)
        )
        return cur.fetchall()


def get_options_for_initiative(db, initiative_id):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT option_id, label, display_order
            FROM initiative_option
            WHERE initiative_id = %s
            ORDER BY display_order
            """,
            (initiative_id,)
        )
        return cur.fetchall()
