"""
Bulk import of the historical election dataset (.psv files) into PostgreSQL.

Usage (from the project root, with the venv active):
    python database/import_election_data.py --reset

    --reset      TRUNCATE all data tables before loading (required for a clean run,
                 since the source files carry explicit primary keys)
    --data-dir   Directory holding the .psv/.txt files (default: data/)

Loads in FK dependency order using COPY, which is ~100x faster than row-by-row
INSERT for the 1.36M candidate_vote rows in this dataset.
"""
import argparse
import csv
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

import bcrypt
import psycopg
from dotenv import load_dotenv

load_dotenv()

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
DEMO_PASSWORD = b"password123"

# Data tables in reverse-dependency order, for TRUNCATE.
DATA_TABLES = [
    "initiative_vote", "initiative_option", "initiative", "candidate_vote", "vote",
    "vote_draft", "ballot_edit_audit", "candidate", "office", "election",
    "session", "employee_society_assignment", '"user"', "society",
]


def connect():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "american_dream"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )


def read_psv(path):
    """Yield dict rows from a pipe-separated file, stripping whitespace and stray CRs."""
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        for row in csv.DictReader(f, delimiter="|"):
            yield {
                k.strip(): (v.strip() if isinstance(v, str) else v)
                for k, v in row.items()
                if k is not None
            }


def parse_societies(path):
    """societies.txt lines look like: '1. American Medical Association (AMA) - Medicine'"""
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            num, _, rest = line.partition(".")
            name, _, description = rest.partition(" - ")
            if not num.isdigit() or not name.strip():
                continue
            out.append((int(num), name.strip(), description.strip() or None))
    return out


def spread_date(start: date, end: date, seed: int) -> date:
    """Deterministically place a ballot somewhere inside the election window."""
    span = (end - start).days
    return start if span <= 0 else start + timedelta(days=seed % (span + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=DATA_DIR)
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()

    d = lambda name: os.path.join(args.data_dir, name)
    for f in ("societies.txt", "members.psv", "dirty.psv", "elections.psv",
              "candidates.psv", "votes.psv"):
        if not os.path.exists(d(f)):
            sys.exit(f"Missing data file: {d(f)}")

    conn = connect()
    conn.autocommit = False
    cur = conn.cursor()

    if args.reset:
        print("Truncating existing data...")
        cur.execute(f"TRUNCATE {', '.join(DATA_TABLES)} RESTART IDENTITY CASCADE")
    else:
        cur.execute('SELECT COUNT(*) FROM "user"')
        if cur.fetchone()[0]:
            sys.exit("Database already has users. Re-run with --reset to reload from scratch.")

    # ── societies ────────────────────────────────────────────────────────────
    societies = parse_societies(d("societies.txt"))
    with cur.copy("COPY society (society_id, name, description) FROM STDIN") as cp:
        for row in societies:
            cp.write_row(row)
    print(f"  societies       {len(societies):>9,}")

    # ── members (clean) ──────────────────────────────────────────────────────
    # One bcrypt hash reused for every demo account: hashing 20k passwords
    # individually would take ~30 minutes and buys nothing for seed data.
    pw_hash = bcrypt.hashpw(DEMO_PASSWORD, bcrypt.gensalt(10)).decode()

    members = {}
    for r in read_psv(d("members.psv")):
        mid = int(r["Member ID"])
        members[mid] = {
            "society_id": int(r["Society ID"]),
            "first_name": r["First Name"],
            "last_name": r["Last Name"],
            "username": r["Username"],
            "role": (r.get("Role") or "member").strip() or "member",
        }

    # ── members (dirty overlay) ──────────────────────────────────────────────
    # dirty.psv is a corrections feed over the same member IDs. Three defects:
    # duplicate rows, society IDs written as '.10', and blank roles.
    seen, dupes, fixed_society, fixed_role, new_members = set(), 0, 0, 0, 0
    for r in read_psv(d("dirty.psv")):
        mid = int(r["MemberID"])
        if mid in seen:
            dupes += 1
            continue
        seen.add(mid)

        raw_society = (r.get("SocietyID") or "").strip()
        if raw_society.startswith("."):
            raw_society = raw_society[1:]
            fixed_society += 1

        role = (r.get("Role") or "").strip()
        if not role:
            role = "member"
            fixed_role += 1

        if mid not in members:
            new_members += 1
        members[mid] = {
            "society_id": int(raw_society),
            "first_name": r["FirstName"],
            "last_name": r["LastName"],
            "username": r["Username"],
            "role": role,
        }

    with cur.copy(
        'COPY "user" (user_id, society_id, email, password_hash, first_name, '
        "last_name, role, status) FROM STDIN"
    ) as cp:
        for mid, m in members.items():
            cp.write_row((
                mid, m["society_id"], f"{m['username']}{mid}@example.com", pw_hash,
                m["first_name"], m["last_name"], m["role"], "active",
            ))
    print(f"  members         {len(members):>9,}   "
          f"(dirty.psv: {dupes} dupes dropped, {fixed_society} society IDs repaired, "
          f"{fixed_role} blank roles defaulted, {new_members} new)")

    # Elections need a creator (created_by is NOT NULL); the source data has no
    # such column, so attribute imported records to a dedicated system account.
    system_user_id = max(members) + 1
    cur.execute(
        'INSERT INTO "user" (user_id, email, password_hash, first_name, last_name, role, status)'
        " VALUES (%s, %s, %s, %s, %s, 'admin', 'active')",
        (system_user_id, "system@americandream.local", pw_hash, "System", "Import"),
    )

    # ── elections ────────────────────────────────────────────────────────────
    elections = {}
    for r in read_psv(d("elections.psv")):
        eid = int(r["Election ID"])
        elections[eid] = (
            date.fromisoformat(r["Start Date"]),
            date.fromisoformat(r["End Date"]),
        )
    with cur.copy(
        "COPY election (election_id, society_id, created_by, name, start_date, "
        "end_date, status) FROM STDIN"
    ) as cp:
        for r in read_psv(d("elections.psv")):
            eid = int(r["Election ID"])
            cp.write_row((
                eid, int(r["Society ID"]), system_user_id, r["Election Title"],
                elections[eid][0], elections[eid][1], "completed",
            ))
    print(f"  elections       {len(elections):>9,}")

    # ── offices + candidates ─────────────────────────────────────────────────
    offices, candidates = {}, []
    office_rank, candidate_rank = defaultdict(int), defaultdict(int)
    for r in read_psv(d("candidates.psv")):
        oid, eid = int(r["Office ID"]), int(r["Election ID"])
        if oid not in offices:
            office_rank[eid] += 1
            offices[oid] = (eid, r["Office Name"], int(r["Allowed Votes"]), office_rank[eid])
        candidate_rank[oid] += 1
        name = " ".join(p for p in (r["Candidate First Name"], r["Candidate Last Name"]) if p)
        candidates.append((
            int(r["Candidate ID"]), oid, name,
            r.get("Candidate Credentials") or None,
            r.get("Candidate Bio") or None,
            candidate_rank[oid],
        ))

    with cur.copy(
        "COPY office (office_id, election_id, title, votes_allowed, allow_write_in, "
        "display_order) FROM STDIN"
    ) as cp:
        for oid, (eid, title, allowed, order) in offices.items():
            cp.write_row((oid, eid, title, allowed, False, order))
    print(f"  offices         {len(offices):>9,}")

    with cur.copy(
        "COPY candidate (candidate_id, office_id, name, title_position, biography, "
        "display_order) FROM STDIN"
    ) as cp:
        for row in candidates:
            cp.write_row(row)
    print(f"  candidates      {len(candidates):>9,}")

    # ── ballots ──────────────────────────────────────────────────────────────
    # Pass 1: every distinct (member, election) pair becomes one vote record.
    ballots = {}
    for r in read_psv(d("votes.psv")):
        key = (int(r["Member ID"]), int(r["Election ID"]))
        if key not in ballots:
            ballots[key] = len(ballots) + 1

    with cur.copy("COPY vote (vote_id, user_id, election_id, submitted_at) FROM STDIN") as cp:
        for (mid, eid), vid in ballots.items():
            start, end = elections[eid]
            cp.write_row((vid, mid, eid, spread_date(start, end, mid * 31 + eid)))
    print(f"  ballots         {len(ballots):>9,}")

    # Pass 2: individual selections. A blank Candidate ID is an undervote — the
    # member skipped that office. The schema's chk_candidate_or_writein constraint
    # has no representation for "abstained", so those rows are counted, not stored;
    # the ballot itself still records that the member participated.
    selections = undervotes = 0
    with cur.copy(
        "COPY candidate_vote (vote_id, office_id, candidate_id) FROM STDIN"
    ) as cp:
        for r in read_psv(d("votes.psv")):
            cid = r["Candidate ID"]
            if not cid:
                undervotes += 1
                continue
            vid = ballots[(int(r["Member ID"]), int(r["Election ID"]))]
            cp.write_row((vid, int(r["Office ID"]), int(cid)))
            selections += 1
    print(f"  selections      {selections:>9,}   ({undervotes:,} undervotes skipped)")

    # ── sequences ────────────────────────────────────────────────────────────
    # COPY bypasses the sequences, so anything inserted afterwards (seed.py, the
    # app itself) would collide with imported IDs unless they are advanced.
    for table, column in [
        ("society", "society_id"), ('"user"', "user_id"), ("election", "election_id"),
        ("office", "office_id"), ("candidate", "candidate_id"), ("vote", "vote_id"),
        ("candidate_vote", "candidate_vote_id"),
    ]:
        cur.execute(
            f"SELECT setval(pg_get_serial_sequence('{table}', '{column}'), "
            f"COALESCE((SELECT MAX({column}) FROM {table}), 1))"
        )

    conn.commit()

    print("Refreshing materialized views...")
    conn.autocommit = True
    cur.execute("CALL refresh_election_results()")

    cur.close()
    conn.close()
    print("Import complete.")


if __name__ == "__main__":
    main()
