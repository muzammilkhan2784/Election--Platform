"""
Load test for the voting path.

    python scripts/load_test.py --voters 200 --concurrency 20

Creates disposable member accounts in the active election's society, has them
all vote as fast as the given concurrency allows, and reports throughput and
latency percentiles.

The point of the exercise is the comparison it enables: every vote emits one
event, but the results consumer collapses them into at most one materialized
view refresh per interval. Compare the refresh count this prints against
`votes x refresh_ms`, which is what refreshing inline on each vote would cost.
"""
import argparse
import http.cookiejar
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

BASE_URL = os.getenv("LOAD_TEST_URL", "http://localhost:3000")
PASSWORD = "password123"


def connect_db():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "american_dream"),
        user=os.getenv("DB_USER", "appuser"),
        password=os.getenv("DB_PASSWORD", ""),
        row_factory=dict_row,
    )


def setup_voters(conn, count):
    """Create `count` members in the active election's society; return ids and ballot."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT election_id, society_id FROM election
            WHERE status = 'active' ORDER BY election_id LIMIT 1
        """)
        election = cur.fetchone()
        if not election:
            sys.exit("No active election found. Run database/seed.py first.")

        cur.execute("""SELECT password_hash FROM "user" WHERE email = 'member@example.com'""")
        row = cur.fetchone()
        if not row:
            sys.exit("Demo accounts missing. Run database/seed.py first.")

        emails = [f"loadtest-{i}@example.com" for i in range(count)]
        cur.executemany("""
            INSERT INTO "user" (society_id, email, password_hash, first_name, last_name, role, status)
            VALUES (%s, %s, %s, 'Load', 'Test', 'member', 'active')
            ON CONFLICT (email) DO NOTHING
        """, [(election["society_id"], e, row["password_hash"]) for e in emails])

        # Clear previous ballots so the test is repeatable (one vote per user
        # per election is enforced by a unique constraint).
        cur.execute("""
            DELETE FROM vote WHERE election_id = %s AND user_id IN (
                SELECT user_id FROM "user" WHERE email LIKE 'loadtest-%%@example.com')
        """, (election["election_id"],))

        cur.execute("""
            SELECT o.office_id, MIN(c.candidate_id) AS candidate_id
            FROM office o JOIN candidate c ON c.office_id = o.office_id
            WHERE o.election_id = %s
            GROUP BY o.office_id ORDER BY o.office_id LIMIT 1
        """, (election["election_id"],))
        office = cur.fetchone()
        if not office:
            sys.exit("Active election has no ballot to vote on.")

    conn.commit()
    return election["election_id"], emails, office


def cast_vote(email, election_id, office):
    """Log in and submit one ballot. Returns elapsed seconds, or None on failure."""
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
    )

    def post(path, body):
        req = urllib.request.Request(
            f"{BASE_URL}{path}",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        return opener.open(req, timeout=30)

    try:
        post("/api/auth/login", {"email": email, "password": PASSWORD})
        started = time.monotonic()
        post(f"/api/elections/{election_id}/vote", {
            "office_votes": [{
                "office_id": office["office_id"],
                "candidate_ids": [office["candidate_id"]],
            }],
            "initiative_votes": [],
        })
        return time.monotonic() - started
    except urllib.error.HTTPError as exc:
        print(f"  {email}: HTTP {exc.code} {exc.read()[:120].decode(errors='replace')}")
        return None
    except Exception as exc:
        print(f"  {email}: {exc}")
        return None


def outbox_counts(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE published_at IS NULL) AS unpublished
            FROM event_outbox
        """)
        return cur.fetchone()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--voters", type=int, default=200)
    ap.add_argument("--concurrency", type=int, default=20)
    args = ap.parse_args()

    conn = connect_db()
    election_id, emails, office = setup_voters(conn, args.voters)
    before = outbox_counts(conn)

    print(f"Voting: {args.voters} ballots on election {election_id}, "
          f"concurrency {args.concurrency}\n")

    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        results = list(pool.map(
            lambda e: cast_vote(e, election_id, office), emails
        ))
    wall = time.monotonic() - started

    latencies = sorted(r for r in results if r is not None)
    failed = len(results) - len(latencies)
    if not latencies:
        sys.exit("Every vote failed.")

    def pct(p):
        return latencies[min(int(len(latencies) * p / 100), len(latencies) - 1)] * 1000

    print(f"\n  votes accepted    {len(latencies)}" + (f"  ({failed} failed)" if failed else ""))
    print(f"  wall time         {wall:.2f}s")
    print(f"  throughput        {len(latencies) / wall:.1f} votes/sec")
    print(f"  latency p50       {statistics.median(latencies) * 1000:.0f}ms")
    print(f"  latency p95       {pct(95):.0f}ms")
    print(f"  latency p99       {pct(99):.0f}ms")
    print(f"  latency max       {latencies[-1] * 1000:.0f}ms")

    after = outbox_counts(conn)
    produced = after["total"] - before["total"]
    print(f"\n  events queued     {produced}")
    print(f"  still unpublished {after['unpublished']} (relay drains these)")
    print("\nCheck how many refreshes those events collapsed into:")
    print("  docker compose logs results-consumer --tail 20")
    conn.close()


if __name__ == "__main__":
    main()
