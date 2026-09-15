from flask import g, current_app
import psycopg
from psycopg.rows import dict_row


def get_db():
    if "db" not in g:
        g.db = psycopg.connect(
            host=current_app.config["DB_HOST"],
            port=current_app.config["DB_PORT"],
            dbname=current_app.config["DB_NAME"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASSWORD"],
            row_factory=dict_row
        )
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()