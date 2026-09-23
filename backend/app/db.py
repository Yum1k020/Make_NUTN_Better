"""SQLite storage and explicitly synthetic reference data for the local baseline."""

import sqlite3
from pathlib import Path

import click
from flask import current_app, g

DEMO_USER_ID = "user-demo-001"


def get_db():
    if "db" not in g:
        db = sqlite3.connect(current_app.config["DATABASE"])
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        g.db = db
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    Path(current_app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    db = get_db()
    with db:
        for statement in (
            "CREATE TABLE IF NOT EXISTS departments (id TEXT PRIMARY KEY)",
            "CREATE TABLE IF NOT EXISTS admission_years (year INTEGER PRIMARY KEY)",
            "CREATE TABLE IF NOT EXISTS semesters (id TEXT PRIMARY KEY)",
            """CREATE TABLE IF NOT EXISTS rule_sets (
                id TEXT PRIMARY KEY,
                department_id TEXT NOT NULL REFERENCES departments(id),
                admission_year INTEGER NOT NULL REFERENCES admission_years(year),
                UNIQUE (department_id, admission_year))""",
            """CREATE TABLE IF NOT EXISTS user_profiles (
                user_id TEXT PRIMARY KEY,
                department_id TEXT REFERENCES departments(id),
                admission_year INTEGER REFERENCES admission_years(year),
                rule_set_id TEXT REFERENCES rule_sets(id),
                current_semester_id TEXT REFERENCES semesters(id))""",
        ):
            db.execute(statement)
        db.executemany("INSERT OR IGNORE INTO departments VALUES (?)",
                       [("dept-csie",), ("dept-demo",)])
        db.executemany("INSERT OR IGNORE INTO admission_years VALUES (?)", [(114,), (115,)])
        db.executemany("INSERT OR IGNORE INTO semesters VALUES (?)",
                       [("semester-115-1",), ("semester-115-2",)])
        db.execute("INSERT OR IGNORE INTO rule_sets VALUES (?, ?, ?)",
                   ("rules-csie-115-v1", "dept-csie", 115))
        db.execute("INSERT OR IGNORE INTO user_profiles (user_id) VALUES (?)", (DEMO_USER_ID,))


def init_app(app):
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """Create baseline tables and seed missing test data without resetting profiles."""
        init_db()
        click.echo("Initialized SQLite baseline (existing profiles preserved).")
