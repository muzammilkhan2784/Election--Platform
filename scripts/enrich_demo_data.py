"""
Make the imported dataset usable as a demonstration.

    python scripts/enrich_demo_data.py

The source files describe 20,000 people who are all plain members drawn from a
pool of 177 first names and 256 surnames. That is fine as raw election data but
poor to show or work with: no society has officers or staff, so role-based
screens have nothing to display, and sorting the member list alphabetically
produces screenfuls of the same surname.

This script only touches presentation-level attributes — names, roles, and
the staff accounts that run elections. Votes, ballots and elections are left exactly as
imported, so every tally stays true to the source data.

Re-runnable: it is deterministic (fixed seed) and resets roles before
reassigning, so running it twice produces the same database.
"""
import argparse
import os
import random
import sys

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

SEED = 20260915  # fixed so repeated runs produce identical data

OFFICERS_PER_SOCIETY = 3
EMPLOYEE_COUNT = 18
ADMIN_COUNT = 6
SOCIETIES_PER_EMPLOYEE = (3, 7)

FIRST_NAMES = """
Aaliyah Aarav Abigail Adaora Adrian Ahmed Aisha Alejandro Alice Amara Amelia Amir
Ana Anika Anton Arjun Asha Astrid Aurora Ayaan Beatriz Benedict Bianca Bilal
Camila Carlos Carmen Cassian Catalina Cecilia Chidi Chloe Cian Clara Cormac
Daniela Dario Dashiell Dawit Delphine Diego Dilara Dmitri Eamon Ebele Edith
Eitan Elena Eli Elif Elise Emeka Emiko Enzo Esperanza Esther Ezra Fatima Felix
Fernanda Fiona Florian Freya Gabriel Genevieve Giulia Grace Gunnar Hana Hassan
Hazel Heidi Henrik Hugo Ibrahim Idris Ilana Imani Ines Ingrid Iris Isabela Isaac
Ishaan Ivan Jacinta Jae Javier Jelena Jonas Josefina Juno Kaito Kalinda Kamal
Karim Kassandra Katarina Keiko Kenji Khalid Kiran Klara Lars Laila Leandro Leila
Leo Liang Lidia Linnea Lorenzo Lucia Lukas Mahika Maia Malik Manon Marisol
Mateo Matilda Mei Mikael Milena Mira Mohammed Nadia Nasser Natalia Nikolai Nina
Noor Nuria Odalys Ola Oliver Omar Oona Orla Oscar Priya Quentin Rafael Rania
Raquel Ravi Reza Rhea Rosa Rowan Ruben Sadie Saoirse Sasha Selin Seraphina
Shreya Sienna Sofia Soren Stellan Sunita Svea Tadeo Tamar Tariq Tessa Thandiwe
Theo Tomas Valentina Vera Viktor Wren Xavier Yara Yusuf Zara Zeynep Zola
""".split()

LAST_NAMES = """
Abara Adeyemi Aguilar Ahmadi Akhtar Alcazar Almeida Andersen Andrade Antonov
Arceneaux Arden Ashford Auclair Azevedo Bakshi Balogun Barbosa Bellweather
Benedetti Berhane Bhattacharya Bianchi Blackwood Bocanegra Bonilla Brennan
Cabrera Calderon Callahan Cardoso Carmichael Castellanos Chaudhry Chen Chevalier
Chowdhury Cisneros Clements Colombo Contreras Cortez Dalgaard Damaskinos
Darzi Dasgupta Delacroix Demir Deshmukh Devereaux Dimitrova Dlamini Donnelly
Dubois Dunbar Eriksen Escalante Espinoza Fairbairn Farrow Fennimore Ferreira
Fitzgerald Fontaine Forsythe Gallagher Garrido Ghosh Gilcrest Goncalves
Granados Grimaldi Gustafsson Hadley Halvorsen Hamdan Hargrove Hashimoto
Havilland Hendricks Hernandez Hollingsworth Hussain Ibarra Ishikawa Iyer
Jaworski Jimenez Kaczmarek Kalinowski Kapoor Karlsson Kasprzak Katsaros Kaur
Keating Khoury Kimura Kingsley Kirilenko Kovacs Krishnan Laurent Lefevre
Lindqvist Lombardi Lundgren Macalister Maguire Mahmoud Malinowski Mancini
Mandel Marchetti Mbeki Mendoza Merriweather Mikkelsen Mirembe Mohammadi Montoya
Moreau Mukherjee Nakamura Navarro Ndiaye Nguyen Nikolaidis Nordstrom Novak
Obi Odhiambo Okafor Okonkwo Oliveira Olsen Oyelaran Pagano Palladino Papadakis
Pedersen Pemberton Peralta Petrov Pillai Prescott Quintana Rahimi Ramaswamy
Rasmussen Ravenscroft Rehman Reyes Ricci Rodriguez Rosales Rutherford Saito
Salazar Sandoval Santoro Sarkar Savitsky Schneider Sepulveda Seyfried Shah
Sharma Sinclair Sokolov Soriano Stavros Steinberg Stenhouse Strand Suleiman
Sundqvist Suzuki Tadesse Takahashi Talbot Tanaka Thackeray Thorne Tikhonov
Toussaint Trujillo Uddin Ueda Vaccaro Valdez Vandermeer Varga Vasquez Velasquez
Venkatesan Verhoeven Villalobos Vogel Wainwright Whitfield Wickramasinghe
Winterbourne Wojcik Yamamoto Yildirim Zabala Zamora Zhang Zielinski Zuniga
""".split()


def connect():
    return psycopg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5433"),
        dbname=os.getenv("DB_NAME", "american_dream"),
        user=os.getenv("DB_USER", "appuser"),
        password=os.getenv("DB_PASSWORD", ""),
        row_factory=dict_row,
    )


def diversify_names(conn, rng):
    """
    Widen the name pool so the member list stops repeating.

    The demo accounts from seed.py keep their recognisable names, and the
    system import account is left alone.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT user_id FROM "user"
            WHERE email LIKE '%%@example.com'
              AND email NOT IN ('admin@example.com', 'employee@example.com',
                                'officer@example.com', 'member@example.com',
                                'member2@example.com')
              AND email NOT LIKE 'loadtest-%%'
            ORDER BY user_id
            """
        )
        user_ids = [r["user_id"] for r in cur.fetchall()]

        # Pair names so the same combination is unlikely to repeat.
        combos = [(f, l) for f in FIRST_NAMES for l in LAST_NAMES]
        rng.shuffle(combos)
        if len(combos) < len(user_ids):
            sys.exit("name pool too small for the number of users")

        cur.executemany(
            'UPDATE "user" SET first_name = %s, last_name = %s WHERE user_id = %s',
            [(combos[i][0], combos[i][1], uid) for i, uid in enumerate(user_ids)],
        )
    return len(user_ids), len(FIRST_NAMES), len(LAST_NAMES)


def assign_roles(conn, rng):
    """
    Give each society its own officers, and create staff who run elections
    across several societies — which is what the employee role exists for.
    """
    with conn.cursor() as cur:
        # Reset first so the script is re-runnable.
        cur.execute(
            """UPDATE "user" SET role = 'member'
               WHERE role IN ('officer', 'employee')
                 AND email NOT IN ('employee@example.com', 'officer@example.com')"""
        )
        cur.execute(
            """DELETE FROM employee_society_assignment
               WHERE user_id NOT IN (SELECT user_id FROM "user" WHERE email = 'employee@example.com')"""
        )

        cur.execute("SELECT society_id FROM society ORDER BY society_id")
        societies = [r["society_id"] for r in cur.fetchall()]

        # Officers belong to the society they represent.
        officer_ids = []
        for society_id in societies:
            cur.execute(
                """SELECT user_id FROM "user"
                   WHERE society_id = %s AND role = 'member'
                     AND email NOT LIKE 'loadtest-%%'
                     AND email NOT IN ('member@example.com', 'member2@example.com')
                   ORDER BY user_id LIMIT 40""",
                (society_id,),
            )
            candidates = [r["user_id"] for r in cur.fetchall()]
            if not candidates:
                continue
            picked = rng.sample(candidates, min(OFFICERS_PER_SOCIETY, len(candidates)))
            officer_ids.extend(picked)

        if officer_ids:
            cur.execute(
                '''UPDATE "user" SET role = 'officer' WHERE user_id = ANY(%s)''',
                (officer_ids,),
            )

        # Election staff are not society members: every imported member has
        # already voted, and more importantly an administrator running an
        # election is a different person from a voter in it. So staff are
        # created as their own accounts rather than promoted from the roster.
        cur.execute("""DELETE FROM "user" WHERE email LIKE '%%@staff.americandream.test'""")
        cur.execute("""SELECT password_hash FROM "user" WHERE email = 'member@example.com'""")
        row = cur.fetchone()
        if not row:
            sys.exit("demo accounts missing; run database/seed.py first")
        pw_hash = row["password_hash"]

        used = set()

        def create_staff(role, count):
            """Create `count` staff accounts with distinct names and emails."""
            ids = []
            for _ in range(count):
                while True:
                    first = rng.choice(FIRST_NAMES)
                    last = rng.choice(LAST_NAMES)
                    email = f"{first.lower()}.{last.lower()}@staff.americandream.test"
                    if email not in used:
                        used.add(email)
                        break
                cur.execute(
                    """INSERT INTO "user"
                           (society_id, email, password_hash, first_name, last_name, role, status)
                       VALUES (NULL, %s, %s, %s, %s, %s, 'active')
                       RETURNING user_id""",
                    (email, pw_hash, first, last, role),
                )
                ids.append(cur.fetchone()["user_id"])
            return ids

        employees = create_staff("employee", EMPLOYEE_COUNT)
        # Extra administrators so the admin screens are not a single account.
        admins = create_staff("admin", ADMIN_COUNT)

        assignments = []
        for user_id in employees:
            n = rng.randint(*SOCIETIES_PER_EMPLOYEE)
            for society_id in rng.sample(societies, n):
                assignments.append((user_id, society_id))
        cur.executemany(
            """INSERT INTO employee_society_assignment (user_id, society_id)
               VALUES (%s, %s) ON CONFLICT DO NOTHING""",
            assignments,
        )

    return len(officer_ids), len(employees), len(assignments), len(admins)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-names", action="store_true",
                    help="only reassign roles, leave names as imported")
    args = ap.parse_args()

    rng = random.Random(SEED)
    conn = connect()

    with conn.transaction():
        if not args.skip_names:
            renamed, firsts, lasts = diversify_names(conn, rng)
            print(f"  names       {renamed:>6,} users renamed "
                  f"({firsts} first x {lasts} last names available)")
        officers, employees, assignments, admins = assign_roles(conn, rng)
        print(f"  officers    {officers:>6,} across all societies")
        print(f"  employees   {employees:>6,} with {assignments} society assignments")
        print(f"  admins      {admins:>6,} additional administrator accounts")

    with conn.cursor() as cur:
        cur.execute('SELECT role, COUNT(*) AS n FROM "user" GROUP BY role ORDER BY n DESC')
        print("\nRole distribution:")
        for row in cur.fetchall():
            print(f"  {row['role']:<10} {row['n']:>6,}")

    conn.close()
    print("\nDone. Every vote, ballot and election is unchanged.")


if __name__ == "__main__":
    main()
