"""
Data Layer — EventOutboxRepository

Writes and reads rows of the transactional outbox. Inserts happen inside the
caller's transaction so an event is committed together with the change that
produced it; the relay process claims and marks rows separately.
"""
import json


def insert_event(db, topic, event_key, payload):
    """Queue an event. Must be called inside the transaction being recorded."""
    with db.cursor() as cur:
        cur.execute(
            """
            INSERT INTO event_outbox (topic, event_key, payload)
            VALUES (%s, %s, %s)
            RETURNING event_id
            """,
            (topic, str(event_key) if event_key is not None else None, json.dumps(payload)),
        )
        return cur.fetchone()["event_id"]


def claim_unpublished(db, limit):
    """
    Take the next batch of unpublished events.

    FOR UPDATE SKIP LOCKED lets several relay processes run at once: each locks
    a different set of rows instead of blocking on the same ones, so the relay
    scales horizontally without publishing anything twice.
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT event_id, topic, event_key, payload
            FROM event_outbox
            WHERE published_at IS NULL
            ORDER BY event_id
            LIMIT %s
            FOR UPDATE SKIP LOCKED
            """,
            (limit,),
        )
        return cur.fetchall()


def mark_published(db, event_ids):
    if not event_ids:
        return
    with db.cursor() as cur:
        cur.execute(
            "UPDATE event_outbox SET published_at = NOW() WHERE event_id = ANY(%s)",
            (list(event_ids),),
        )


def pending_stats(db):
    """
    Backlog depth and the age of the oldest unpublished event.

    Depth alone is ambiguous — a large backlog draining quickly is healthy while
    a small one that never empties is not. The age of the oldest row is what
    actually says whether the relay is keeping up.
    """
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT COUNT(*) AS pending,
                   COALESCE(EXTRACT(EPOCH FROM (NOW() - MIN(created_at))), 0) AS oldest_seconds
            FROM event_outbox
            WHERE published_at IS NULL
            """
        )
        return cur.fetchone()


def delete_published_before(db, cutoff):
    """Drop already-published rows older than cutoff so the table stays bounded."""
    with db.cursor() as cur:
        cur.execute(
            "DELETE FROM event_outbox WHERE published_at IS NOT NULL AND published_at < %s",
            (cutoff,),
        )
        return cur.rowcount
