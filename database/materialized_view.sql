-- ─────────────────────────────────────────────────────────────────────────────
-- Materialized Views + Stored Procedure for Election Results
--
-- Why materialized views?
--   Counting votes requires joining 4-5 tables and aggregating thousands of
--   rows. For a completed election those numbers never change, so we can
--   pre-compute and cache the result set. Subsequent reads hit the cached
--   rows directly instead of re-running the aggregation.
--
-- How to apply:
--   Run this file AFTER DDL_FooFighters.sql:
--     psql -U <user> -d <db> -f database/materialized_view.sql
--
--   Then call the stored procedure any time votes are added or when an
--   election is marked completed:
--     CALL refresh_election_results();
-- ─────────────────────────────────────────────────────────────────────────────


-- ── 1. Candidate results ─────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_candidate_results AS
SELECT
    e.election_id,
    o.office_id,
    o.title          AS office_title,
    o.display_order  AS office_order,
    c.candidate_id,
    c.name           AS candidate_name,
    c.display_order  AS candidate_order,
    COUNT(cv.candidate_vote_id) AS vote_count
FROM election e
JOIN office           o  ON o.election_id  = e.election_id
JOIN candidate        c  ON c.office_id    = o.office_id
LEFT JOIN candidate_vote cv ON cv.candidate_id = c.candidate_id
GROUP BY
    e.election_id,
    o.office_id, o.title, o.display_order,
    c.candidate_id, c.name, c.display_order
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_candidate_results_pk
    ON mv_candidate_results (election_id, office_id, candidate_id);


-- ── 2. Initiative results ─────────────────────────────────────────────────────

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_initiative_results AS
SELECT
    e.election_id,
    i.initiative_id,
    i.title          AS initiative_title,
    i.display_order  AS initiative_order,
    io.option_id,
    io.label         AS option_label,
    io.display_order AS option_order,
    COUNT(iv.initiative_vote_id) AS vote_count
FROM election e
JOIN initiative        i  ON i.election_id   = e.election_id
JOIN initiative_option io ON io.initiative_id = i.initiative_id
LEFT JOIN initiative_vote iv ON iv.option_id  = io.option_id
GROUP BY
    e.election_id,
    i.initiative_id, i.title, i.display_order,
    io.option_id, io.label, io.display_order
WITH DATA;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_initiative_results_pk
    ON mv_initiative_results (election_id, initiative_id, option_id);


-- ── 3. Stored procedure — refresh both views atomically ───────────────────────
--
--  Called from Python:  with db.cursor() as cur: cur.execute("CALL refresh_election_results()")
--  Or manually:         CALL refresh_election_results();
--
--  CONCURRENTLY requires the unique indexes above so reads are not blocked
--  while the refresh runs.

CREATE OR REPLACE PROCEDURE refresh_election_results()
LANGUAGE plpgsql
AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_candidate_results;
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_initiative_results;
END;
$$;
