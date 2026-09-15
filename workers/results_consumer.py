"""
Results consumer — keeps the results materialized views current.

Run as its own process:
    python -m workers.results_consumer

Why this exists
---------------
`refresh_election_results()` re-aggregates every candidate_vote row. Measured on
the full dataset (1.36M rows) it takes about 700ms, while submitting a vote takes
about 20ms. Refreshing inside the vote request would therefore make voting ~30x
slower, and `REFRESH MATERIALIZED VIEW CONCURRENTLY` cannot overlap itself, so
concurrent voters would serialise behind each other.

Refreshing per vote does not scale: 100 votes/second would demand 70 seconds of
refresh work per second. This consumer instead collapses any number of vote
events into at most one refresh per REFRESH_INTERVAL_SECONDS, so refresh cost is
a fixed duty cycle (700ms per interval) no matter how fast votes arrive, and
results lag by at most that interval.

Delivery semantics
------------------
The relay is at-least-once, so events can repeat. That is safe here: a refresh
recomputes from the base tables, so applying it twice yields the same result.
Offsets are committed only after a successful refresh, so a crash re-reads the
events rather than silently skipping a refresh.
"""
import json
import logging
import os
import signal
import time

import psycopg
from confluent_kafka import Consumer, KafkaError
from dotenv import load_dotenv

load_dotenv()

TOPIC = os.getenv("VOTE_TOPIC", "election.vote.cast")
GROUP_ID = os.getenv("RESULTS_CONSUMER_GROUP", "results-refresher")
REFRESH_INTERVAL_SECONDS = float(os.getenv("REFRESH_INTERVAL_SECONDS", "5"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [results] %(message)s",
)
log = logging.getLogger(__name__)

_running = True


def _stop(signum, _frame):
    global _running
    log.info("received signal %s, shutting down", signum)
    _running = False


def connect_db():
    conn = psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "american_dream"),
        user=os.getenv("DB_USER", "appuser"),
        password=os.getenv("DB_PASSWORD", ""),
    )
    # REFRESH MATERIALIZED VIEW CONCURRENTLY cannot run inside a transaction block.
    conn.autocommit = True
    return conn


def build_consumer():
    return Consumer({
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        "group.id": GROUP_ID,
        "auto.offset.reset": "earliest",
        # Offsets are committed by hand after a refresh succeeds, so a crash
        # replays the events instead of losing the refresh they should have caused.
        "enable.auto.commit": False,
    })


def refresh(conn):
    started = time.monotonic()
    with conn.cursor() as cur:
        cur.execute("CALL refresh_election_results()")
    return (time.monotonic() - started) * 1000


def run():
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    consumer = build_consumer()
    consumer.subscribe([TOPIC])
    conn = connect_db()
    log.info("consuming %s as group '%s', refreshing at most every %.1fs",
             TOPIC, GROUP_ID, REFRESH_INTERVAL_SECONDS)

    pending = 0
    elections_seen = set()
    last_refresh = 0.0
    refresh_count = 0

    while _running:
        msg = consumer.poll(0.5)

        if msg is not None:
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    log.error("consumer error: %s", msg.error())
            else:
                pending += 1
                try:
                    event = json.loads(msg.value())
                    elections_seen.add(event.get("election_id"))
                except (ValueError, TypeError):
                    log.warning("skipping unparseable message at offset %s", msg.offset())

        due = (time.monotonic() - last_refresh) >= REFRESH_INTERVAL_SECONDS
        if pending and due:
            try:
                elapsed_ms = refresh(conn)
                refresh_count += 1
                log.info(
                    "refreshed in %.0fms — collapsed %d vote events across %d election(s)",
                    elapsed_ms, pending, len(elections_seen),
                )
                consumer.commit(asynchronous=False)
                pending = 0
                elections_seen.clear()
                last_refresh = time.monotonic()
            except psycopg.OperationalError as exc:
                log.warning("database error during refresh (%s), reconnecting", exc)
                try:
                    conn.close()
                except Exception:
                    pass
                time.sleep(5)
                conn = connect_db()

    consumer.close()
    conn.close()
    log.info("stopped after %d refreshes", refresh_count)


if __name__ == "__main__":
    run()
