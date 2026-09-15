"""
Data Access Layer — VoteRepository

Responsibility: Recording votes and querying vote tallies.

Loose coupling: This module does NOT enforce the one-vote-per-user
rule or check election status — those are business rules enforced
in voting_service.py. This module only inserts and reads rows.

Transactions: insert_vote, insert_candidate_vote, insert_write_in_vote,
and insert_initiative_vote are intentionally NOT committed here.
The business layer (voting_service.py) owns the transaction boundary
and calls db.commit() only after ALL inserts succeed, ensuring
atomicity across multiple tables.
"""


def has_user_voted(db, user_id, election_id):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM vote
            WHERE user_id = %s AND election_id = %s
            """,
            (user_id, election_id)
        )
        return cur.fetchone() is not None


def insert_vote(db, user_id, election_id):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO vote (user_id, election_id, submitted_at)
            VALUES (%s, %s, NOW())
            RETURNING vote_id
            """,
            (user_id, election_id)
        )
        return cur.fetchone()


def insert_candidate_vote(db, vote_id, office_id, candidate_id):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO candidate_vote (vote_id, office_id, candidate_id)
            VALUES (%s, %s, %s)
            """,
            (vote_id, office_id, candidate_id)
        )


def insert_write_in_vote(db, vote_id, office_id, write_in_name):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO candidate_vote (vote_id, office_id, write_in_name)
            VALUES (%s, %s, %s)
            """,
            (vote_id, office_id, write_in_name)
        )


def insert_initiative_vote(db, vote_id, initiative_id, option_id):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO initiative_vote (vote_id, initiative_id, option_id)
            VALUES (%s, %s, %s)
            """,
            (vote_id, initiative_id, option_id)
        )


def get_member_vote_status(db, election_id):
    """
    Returns every eligible voter for an election with a flag
    indicating whether they have voted yet.
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT u.user_id,
                   u.first_name || ' ' || u.last_name AS member_name,
                   u.email,
                   CASE WHEN v.user_id IS NOT NULL THEN true ELSE false END AS has_voted
            FROM election e
            JOIN "user" u
                ON u.society_id = e.society_id
               AND u.role IN ('member', 'officer')
               AND u.status = 'active'
            LEFT JOIN vote v
                ON v.election_id = e.election_id
               AND v.user_id = u.user_id
            WHERE e.election_id = %s
            ORDER BY has_voted DESC, u.last_name
            """,
            (election_id,)
        )
        return cur.fetchall()


def get_participation(db, society_id):
    """
    For each active election in the given society, return total eligible
    voters (active members + officers) and how many have voted so far.
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT e.election_id, e.name,
                   e.start_date, e.end_date,
                   COUNT(DISTINCT u.user_id)  AS total_eligible,
                   COUNT(DISTINCT v.user_id)  AS voted_count
            FROM election e
            JOIN "user" u
                ON u.society_id = e.society_id
               AND u.role IN ('member', 'officer')
               AND u.status = 'active'
            LEFT JOIN vote v
                ON v.election_id = e.election_id
            WHERE e.society_id = %s
              AND e.status = 'active'
            GROUP BY e.election_id, e.name, e.start_date, e.end_date
            ORDER BY e.start_date
            """,
            (society_id,)
        )
        return cur.fetchall()


def get_participation_for_societies(db, society_ids):
    """Same as get_participation but for a list of society IDs (used by employees)."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT e.election_id, e.name,
                   e.start_date, e.end_date,
                   COUNT(DISTINCT u.user_id)  AS total_eligible,
                   COUNT(DISTINCT v.user_id)  AS voted_count
            FROM election e
            JOIN "user" u
                ON u.society_id = e.society_id
               AND u.role IN ('member', 'officer')
               AND u.status = 'active'
            LEFT JOIN vote v
                ON v.election_id = e.election_id
            WHERE e.society_id = ANY(%s)
              AND e.status = 'active'
            GROUP BY e.election_id, e.name, e.start_date, e.end_date
            ORDER BY e.start_date
            """,
            (society_ids,)
        )
        return cur.fetchall()


def refresh_election_results(db):
    """
    Calls the stored procedure that refreshes both materialized views.
    Run this after votes are submitted or when an election is completed.
    """
    with db.cursor() as cur:
        cur.execute("CALL refresh_election_results()")


def get_candidate_results_from_view(db, election_id):
    """Read pre-computed candidate tallies from the materialized view."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT office_id, office_title, office_order,
                   candidate_id, candidate_name, candidate_order, vote_count
            FROM mv_candidate_results
            WHERE election_id = %s
            ORDER BY office_order, candidate_order
            """,
            (election_id,)
        )
        return cur.fetchall()


def get_initiative_results_from_view(db, election_id):
    """Read pre-computed initiative tallies from the materialized view."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT initiative_id, initiative_title, initiative_order,
                   option_id, option_label, option_order, vote_count
            FROM mv_initiative_results
            WHERE election_id = %s
            ORDER BY initiative_order, option_order
            """,
            (election_id,)
        )
        return cur.fetchall()


def get_office_results(db, election_id):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT o.office_id, o.title,
                   c.name,
                   COUNT(cv.candidate_vote_id) AS votes
            FROM office o
            JOIN candidate c ON c.office_id = o.office_id
            LEFT JOIN candidate_vote cv ON cv.candidate_id = c.candidate_id
            WHERE o.election_id = %s
            GROUP BY o.office_id, o.title, o.display_order, c.candidate_id, c.name, c.display_order
            ORDER BY o.display_order, c.display_order
            """,
            (election_id,)
        )
        return cur.fetchall()


def get_initiative_results(db, election_id):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT i.initiative_id, i.title,
                   io.option_id, io.label,
                   COUNT(iv.initiative_vote_id) AS votes
            FROM initiative i
            JOIN initiative_option io ON io.initiative_id = i.initiative_id
            LEFT JOIN initiative_vote iv ON iv.option_id = io.option_id
            WHERE i.election_id = %s
            GROUP BY i.initiative_id, i.title, i.display_order,
                     io.option_id, io.label, io.display_order
            ORDER BY i.display_order, io.display_order
            """,
            (election_id,)
        )
        return cur.fetchall()
