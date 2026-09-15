# American Dream Election System

A multi-tenant web platform that runs elections for professional societies (IEEE, ACM, and others), built with Flask and PostgreSQL. Each society is an isolated tenant: its members, elections, ballots, and results are never visible to another society.

Runs locally via Docker Compose.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3 / Flask |
| Database | PostgreSQL 16 (psycopg3) |
| Frontend | Vanilla JS + Tailwind CSS |
| Auth | Flask sessions + bcrypt |
| Local infrastructure | Docker Compose |
| Server | Gunicorn (production) |

---

## Architecture

Strict 3-layer separation:

```
HTTP Request
    ↓
app/routes/api_routes.py      ← REST layer: HTTP in/out, owns transactions (with db:)
    ↓
app/services/                 ← Business layer: role checks, validation, state rules
    ↓
app/repositories/             ← Data layer: raw parameterized SQL only
    ↓
PostgreSQL
```

**Transaction boundaries** are owned exclusively by the route layer using psycopg3's `with db:` context manager, which auto-commits on success and rolls back on any exception. Services never call `commit()` or `rollback()` — they let exceptions propagate so the route's context manager can roll back the whole request.

**N+1 queries** are eliminated via JOIN queries in the repository layer. Candidates are fetched with their offices in a single query; options are fetched with their initiatives in a single query. Grouping happens in Python.

---

## Advanced Database Features

| Feature | Where |
|---|---|
| Materialized views | `mv_candidate_results`, `mv_initiative_results` — pre-computed vote tallies |
| Stored procedure | `refresh_election_results()` — refreshes both materialized views atomically |
| SELECT FOR UPDATE | `get_election_for_update()` in `election_repository.py` — prevents concurrent ballot edits |
| Bulk loading | `COPY`-based import of the 1.9M-row historical dataset |
| Parameterized queries | All SQL uses `%s` placeholders throughout repositories |

---

## Project Structure

```
election-system/
├── app/
│   ├── __init__.py              # App factory, blueprint registration, static file serving
│   ├── config.py                # Config from .env
│   ├── db.py                    # psycopg3 connection with dict_row
│   ├── routes/
│   │   └── api_routes.py        # All REST endpoints
│   ├── services/
│   │   ├── auth_service.py      # Login, password verification
│   │   ├── ballot_service.py    # Election creation, ballot save/publish
│   │   ├── voting_service.py    # Vote submission (role + society + duplicate checks)
│   │   ├── election_service.py  # Role-based election listing + ballot fetch
│   │   ├── results_service.py   # Results access with role restrictions
│   │   ├── society_service.py   # Society management
│   │   └── user_service.py      # Admin user management
│   └── repositories/
│       ├── election_repository.py
│       ├── office_repository.py
│       ├── initiative_repository.py
│       ├── candidate_repository.py
│       ├── vote_repository.py
│       ├── society_repository.py
│       ├── audit_repository.py
│       └── user_repository.py
├── frontend/                    # Served directly by Flask (send_from_directory)
│   ├── login.html
│   ├── dashboard.html / dashboard.js
│   ├── ballot.html / ballot.js
│   ├── ballot-editor.html / ballot-editor.js
│   ├── results.html / results.js
│   ├── participation.html / participation.js
│   ├── pending-tasks.html / pending-tasks.js
│   ├── admin.html / admin.js
│   ├── settings.html / settings.js
│   └── components.js            # Shared navbar, footer, alerts
├── data/                        # Raw source dataset (pipe-separated)
│   ├── societies.txt
│   ├── members.psv
│   ├── dirty.psv
│   ├── elections.psv
│   ├── candidates.psv
│   └── votes.psv
├── database/
│   ├── schema.sql               # Schema (tables, constraints, indexes)
│   ├── materialized_view.sql    # Materialized views + stored procedure
│   ├── import_election_data.py  # Bulk loader for the historical dataset
│   ├── migrations/              # Migration scripts
│   └── seed.py                  # Demo accounts + one active election
├── tests/
│   └── test_*.py                # 29 unit tests (service layer)
├── docker-compose.yml           # Local PostgreSQL
├── run.py                       # Start the app for development
├── server.py                    # Start the app in production (via Gunicorn)
├── requirements.txt
├── requirements-dev.txt
└── .env                         # Not committed — see setup below
```

---

## Roles & Access

| Role | Access |
|---|---|
| `member` | Vote on active elections in their society; view results of completed elections |
| `officer` | Vote + view voter participation (who voted/who hasn't) + view completed election results |
| `employee` | Assigned to societies; build & publish ballots, view results, view participation, manage pending tasks |
| `admin` | Everything + manage users, societies, employee assignments, audit logs, and reports |

---

## Election States

```
draft → active → completed
```

- **draft**: ballot can be edited by employees/admins
- **active**: members/officers can vote; ballot is locked; each user can only vote once
- **completed**: voting closed; results visible to employees, admins, and officers

---

## API Endpoints

| Method | Path | Access | Description |
|---|---|---|---|
| POST | `/api/auth/login` | Public | Login |
| POST | `/api/auth/logout` | Auth | Logout |
| GET | `/api/me` | Auth | Current user info |
| PUT | `/api/me` | Auth | Update own name |
| PUT | `/api/me/password` | Auth | Change own password |
| GET | `/api/elections` | Auth | List elections (role-filtered) |
| POST | `/api/elections` | Employee/Admin | Create election |
| GET | `/api/elections/<id>` | Auth | Get election + full ballot |
| PUT | `/api/elections/<id>/ballot` | Employee/Admin | Save ballot (draft only) |
| POST | `/api/elections/<id>/publish` | Employee/Admin | Publish election |
| GET | `/api/elections/<id>/voted` | Auth | Check if current user has voted |
| POST | `/api/elections/<id>/vote` | Member/Officer | Submit vote |
| GET | `/api/elections/<id>/results` | Employee/Admin/Officer | View results |
| GET | `/api/elections/participation` | Officer/Employee/Admin | Turnout stats + member roster for active elections |
| GET | `/api/elections/pending` | Employee | Draft elections in assigned societies needing a ballot |
| GET | `/api/elections/<id>/members` | Officer/Employee/Admin | Per-election member voted/not-voted roster |
| GET | `/api/societies` | Admin/Employee | List societies |
| POST | `/api/societies` | Admin | Create society |
| GET | `/api/societies/assignments` | Admin | List employee–society assignments |
| GET | `/api/users` | Admin | List all users |
| POST | `/api/users` | Admin | Create user |
| PUT | `/api/users/<id>` | Admin | Update user (status, role, etc.) |
| POST | `/api/users/<id>/societies` | Admin | Assign employee to society |
| DELETE | `/api/users/<id>/societies/<sid>` | Admin | Remove employee from society |
| GET | `/api/audit` | Admin | Ballot edit events + vote activity log |
| GET | `/api/reports` | Admin | System-wide stats + per-society stats |

---

## Setup

### 1. Install

```bash
git clone <repo-url>
cd election-system
python -m venv venv
source venv/Scripts/activate      # Windows; use venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
```

### 2. Configure environment

Create a `.env` file in the project root (never commit this). Docker Compose and the
Flask app both read it, so the credentials stay in one place:

```
DB_HOST=localhost
DB_PORT=5433
DB_NAME=american_dream
DB_USER=appuser
DB_PASSWORD=devpassword
SECRET_KEY=<random string>
FLASK_ENV=development
```

Generate a secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

> **Port note:** `5433` is used instead of the default `5432` to avoid colliding
> with any PostgreSQL already installed on the host machine. Change it if `5433`
> is taken.

### 3. Start PostgreSQL

```bash
docker compose up -d
```

### 4. Create the schema

```bash
docker compose exec -T postgres psql -U appuser -d american_dream < database/schema.sql
docker compose exec -T postgres psql -U appuser -d american_dream < database/materialized_view.sql
```

### 5. Load data

Demo accounts plus one active election to vote in:

```bash
python database/seed.py
```

Optionally, load the full historical dataset (20,000 members, 2,000 elections,
500,000 ballots, 1.36M individual selections) from the files in `data/`:

```bash
python database/import_election_data.py --reset
python database/seed.py
```

`--reset` truncates all data tables first, since the source files carry explicit
primary keys. Run `seed.py` afterwards to re-create the demo accounts. The import
takes roughly 90 seconds and uses `COPY` rather than row-by-row inserts.

### 6. Run

```bash
# Development — what you use locally
python run.py
```

The app is served at `http://localhost:3000`.

For production, `server.py` is the entry point, run behind Gunicorn:

```bash
gunicorn -w 2 -b 0.0.0.0:3000 server:application
```

Gunicorn is Linux/macOS only, so on Windows use `run.py` locally and Gunicorn
when deploying to a server.

---

## Demo Accounts

Created by `seed.py`. All passwords: `password123`

| Email | Name | Role | Society |
|---|---|---|---|
| `admin@example.com` | Admin User | admin | — |
| `employee@example.com` | Emma Ployee | employee | IEEE + ACM |
| `officer@example.com` | Oliver Ficer | officer | IEEE |
| `member@example.com` | Mary Member | member | IEEE |
| `member2@example.com` | Mark Two | member | ACM |

Accounts from the bulk import also use `password123`, with emails formed as
`<username><member_id>@example.com`.

---

## Historical Dataset

The pipe-separated files in `data/` hold a historical dataset spanning elections
from 2000 to 2025:

| File | Contents |
|---|---|
| `societies.txt` | 80 professional societies |
| `members.psv` | 20,000 members |
| `dirty.psv` | 300 member corrections requiring cleanup |
| `elections.psv` | 2,000 elections |
| `candidates.psv` | 4,966 offices and 12,451 candidates |
| `votes.psv` | 1,395,092 ballot selections |

`import_election_data.py` handles three quirks in this data:

- **`dirty.psv`** carries duplicate rows, society IDs written as `.10` instead of `10`,
  blank roles, and mixed line endings. These are de-duplicated, repaired, and defaulted.
- **Undervotes** — 39,454 rows record a member skipping an office, with no candidate
  selected. The `chk_candidate_or_writein` constraint has no representation for
  "abstained", so these are reported but not stored; the ballot still records that the
  member participated.
- **Multi-seat offices** — 614 offices allow 2 votes, so one member legitimately appears
  twice for the same office. The importer preserves these and validates that no ballot
  exceeds its office's `votes_allowed`.

Elections are imported as `completed` and attributed to a `system@americandream.local`
account, since the source data has no creator column and `election.created_by` is `NOT NULL`.

---

## Running Tests

```bash
python -m pytest tests/ -v
```

29 unit tests covering the service layer:

| File | Tests | Covers |
|---|---|---|
| `test_auth_service.py` | 7 | Login and password verification |
| `test_election_service.py` | 10 | Role-based election listing and ballot access |
| `test_voting_service.py` | 12 | Vote submission rules and transaction contract |

Repositories and the remaining services (`ballot`, `results`, `society`, `user`) are
not yet covered.
