def insert_audit_event(db, election_id, user_id, action, details=None):
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO ballot_edit_audit (election_id, user_id, action, details, edited_at)
            VALUES (%s, %s, %s, %s, NOW())
            """,
            (election_id, user_id, action, details)
        )


def get_society_stats(db):
    """Society-level statistics for admin reports."""
    with db.cursor() as cur:
        cur.execute(
            """
            WITH vote_totals AS (
                SELECT election_id, COUNT(*) AS vote_count
                FROM vote
                GROUP BY election_id
            )
            SELECT
                s.society_id,
                s.name,
                COUNT(DISTINCT e.election_id)
                    AS total_elections,
                COUNT(DISTINCT e.election_id)
                    FILTER (WHERE e.status = 'active')
                    AS active_elections,
                COUNT(DISTINCT e.election_id)
                    FILTER (WHERE e.status = 'completed')
                    AS completed_elections,
                COUNT(DISTINCT u.user_id)
                    FILTER (WHERE u.role IN ('member','officer') AND u.status = 'active')
                    AS member_count,
                COALESCE(
                    ROUND(AVG(vt.vote_count)
                        FILTER (WHERE e.status = 'completed'), 1),
                    0
                ) AS avg_turnout
            FROM society s
            LEFT JOIN election e  ON e.society_id  = s.society_id
            LEFT JOIN "user"   u  ON u.society_id  = s.society_id
            LEFT JOIN vote_totals vt ON vt.election_id = e.election_id
            GROUP BY s.society_id, s.name
            ORDER BY s.name
            """
        )
        return cur.fetchall()


def get_system_stats(db):
    """System-wide statistics for admin reports."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE e.status = 'active')  AS active_elections,
                COUNT(*) FILTER (WHERE e.status = 'draft')   AS draft_elections,
                COUNT(*) FILTER (WHERE e.status = 'completed') AS completed_elections
            FROM election e
            """
        )
        election_stats = cur.fetchone()

        cur.execute(
            """
            SELECT
                COUNT(*) AS total_users,
                COUNT(*) FILTER (WHERE status = 'active')  AS active_users,
                COUNT(*) FILTER (WHERE role = 'member')    AS members,
                COUNT(*) FILTER (WHERE role = 'officer')   AS officers,
                COUNT(*) FILTER (WHERE role = 'employee')  AS employees,
                COUNT(*) FILTER (WHERE role = 'admin')     AS admins,
                COUNT(*) FILTER (WHERE last_login > NOW() - INTERVAL '30 minutes') AS recent_logins
            FROM "user"
            """
        )
        user_stats = cur.fetchone()

        return dict(election_stats) | dict(user_stats)


def list_ballot_audit_events(db):
    """All ballot edit / publish events, newest first."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT bea.audit_id, bea.action, bea.details,
                   bea.edited_at,
                   e.name  AS election_name,
                   u.first_name || ' ' || u.last_name AS user_name,
                   u.email AS user_email
            FROM ballot_edit_audit bea
            JOIN election e ON e.election_id = bea.election_id
            JOIN "user"   u ON u.user_id     = bea.user_id
            ORDER BY bea.edited_at DESC
            LIMIT 200
            """
        )
        return cur.fetchall()


def list_vote_activity(db):
    """Who voted in which election, newest first."""
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT v.submitted_at,
                   e.name  AS election_name,
                   u.first_name || ' ' || u.last_name AS user_name,
                   u.email AS user_email
            FROM vote v
            JOIN election e ON e.election_id = v.election_id
            JOIN "user"   u ON u.user_id     = v.user_id
            ORDER BY v.submitted_at DESC
            LIMIT 200
            """
        )
        return cur.fetchall()
