"""
Outbox relay — publishes committed events from the database to Kafka.

Run as its own process:
    python -m workers.outbox_relay

The web application never talks to Kafka. It records events in the
`event_outbox` table inside the same transaction as the vote, and this process
moves them to the broker. That separation means a broker outage delays event
delivery but never rejects a vote; when Kafka returns, the backlog drains.

Delivery is at-least-once. Rows are marked published only after the broker
acknowledges them, so a crash in between causes a republish rather than a loss.
Consumers must therefore be idempotent.
"""
import json
import logging
import os
import signal
import time
from datetime import datetime, timedelta, timezone
from functools import partial

import psycopg
from confluent_kafka import Producer
from dotenv import load_dotenv
from psycopg.rows import dict_row

from app.repositories import outbox_repository

load_dotenv()

BATCH_SIZE = int(os.getenv("RELAY_BATCH_SIZE", "500"))
IDLE_SLEEP_SECONDS = float(os.getenv("RELAY_IDLE_SLEEP", "1.0"))
RETENTION_HOURS = int(os.getenv("RELAY_RETENTION_HOURS", "24"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [relay] %(message)s",
)
log = logging.getLogger(__name__)

_running = True


def _stop(signum, _frame):
    global _running
    log.info("received signal %s, finishing current batch then exiting", signum)
    _running = False


def connect_db():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "american_dream"),
        user=os.getenv("DB_USER", "appuser"),
        password=os.getenv("DB_PASSWORD", ""),
        row_factory=dict_row,
    )


def build_producer():
    return Producer({
        "bootstrap.servers": os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        # Wait for all in-sync replicas before considering a write successful.
        # Combined with marking the outbox row only after the ack, this is what
        # makes "published" mean the broker actually has the event.
        "acks": "all",
        "enable.idempotence": True,
        "retries": 10,
        "client.id": "election-outbox-relay",
    })


def publish_batch(producer, rows):
    """Publish rows and return the ids the broker acknowledged."""
    delivered = set()
    failed = {}

    # The Python client's delivery callback receives only (err, msg), so the
    # event id is bound per message rather than carried on the message itself.
    def on_delivery(event_id, err, _msg):
        if err is None:
            delivered.add(event_id)
        else:
            failed[event_id] = str(err)

    for row in rows:
        # psycopg returns JSONB as a dict; Kafka needs bytes.
        payload = row["payload"]
        value = payload if isinstance(payload, (str, bytes)) else json.dumps(payload)
        producer.produce(
            topic=row["topic"],
            key=(row["event_key"] or "").encode(),
            value=value.encode() if isinstance(value, str) else value,
            on_delivery=partial(on_delivery, row["event_id"]),
        )

    producer.flush(30)

    if failed:
        log.error("%d events failed to publish, will retry: %s",
                  len(failed), list(failed.items())[:3])
    return delivered


def run():
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    producer = build_producer()
    conn = connect_db()
    log.info("relay started (batch=%d, idle_sleep=%.1fs)", BATCH_SIZE, IDLE_SLEEP_SECONDS)

    published_total = 0
    last_cleanup = time.monotonic()

    while _running:
        try:
            # conn.transaction(), not `with conn:` — in psycopg3 the connection
            # context manager closes the connection on exit, which would end the
            # relay after a single batch.
            with conn.transaction():
                rows = outbox_repository.claim_unpublished(conn, BATCH_SIZE)
                if rows:
                    delivered = publish_batch(producer, rows)
                    outbox_repository.mark_published(conn, delivered)
                    published_total += len(delivered)
                    if delivered:
                        log.info("published %d events (total %d)",
                                 len(delivered), published_total)
            # Committed here. Rows that failed to publish still have
            # published_at NULL and are retried on the next pass.

            if not rows:
                time.sleep(IDLE_SLEEP_SECONDS)

            if time.monotonic() - last_cleanup > 3600:
                with conn.transaction():
                    cutoff = datetime.now(timezone.utc) - timedelta(hours=RETENTION_HOURS)
                    removed = outbox_repository.delete_published_before(conn, cutoff)
                    if removed:
                        log.info("pruned %d published events older than %dh",
                                 removed, RETENTION_HOURS)
                last_cleanup = time.monotonic()

        except psycopg.OperationalError as exc:
            log.warning("database connection lost (%s), reconnecting in 5s", exc)
            time.sleep(5)
            try:
                conn.close()
            except Exception:
                pass
            conn = connect_db()

    producer.flush(10)
    conn.close()
    log.info("relay stopped after publishing %d events", published_total)


if __name__ == "__main__":
    run()
