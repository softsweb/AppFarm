import os
import sqlite3
import time

from . import config


def conn():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS apps(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE,
                name TEXT,
                idea TEXT,
                source_url TEXT,
                score REAL,
                status TEXT,
                monetization TEXT,
                pitch TEXT,
                visits INTEGER DEFAULT 0,
                created_at REAL,
                built_at REAL,
                archived_at REAL,
                last_checked REAL
            )"""
        )
        c.execute("CREATE TABLE IF NOT EXISTS seen(key TEXT PRIMARY KEY, ts REAL)")
        # Migrate older DBs that predate the monetization column.
        cols = {r["name"] for r in c.execute("PRAGMA table_info(apps)").fetchall()}
        if "monetization" not in cols:
            c.execute("ALTER TABLE apps ADD COLUMN monetization TEXT")
        if "pitch" not in cols:
            c.execute("ALTER TABLE apps ADD COLUMN pitch TEXT")


def add_app(slug, name, idea, source_url, score, status, monetization="", pitch=""):
    with conn() as c:
        c.execute(
            """INSERT INTO apps(slug, name, idea, source_url, score, status,
                                monetization, pitch, created_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (slug, name, idea, source_url, score, status, monetization, pitch,
             time.time()),
        )


def get_by_slug(slug):
    with conn() as c:
        r = c.execute("SELECT * FROM apps WHERE slug=?", (slug,)).fetchone()
        return dict(r) if r else None


def get_soon():
    with conn() as c:
        r = c.execute(
            "SELECT * FROM apps WHERE status='soon' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return dict(r) if r else None


def list_live():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM apps WHERE status='live'").fetchall()]


def list_all():
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM apps ORDER BY created_at DESC").fetchall()]


def set_status(slug, status, built_at=None, archived_at=None):
    with conn() as c:
        if built_at is not None:
            c.execute("UPDATE apps SET status=?, built_at=? WHERE slug=?", (status, built_at, slug))
        elif archived_at is not None:
            c.execute(
                "UPDATE apps SET status=?, archived_at=? WHERE slug=?", (status, archived_at, slug)
            )
        else:
            c.execute("UPDATE apps SET status=? WHERE slug=?", (status, slug))


def update_visits(slug, n):
    with conn() as c:
        c.execute(
            "UPDATE apps SET visits=?, last_checked=? WHERE slug=?", (n, time.time(), slug)
        )


def mark_seen(key):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO seen(key, ts) VALUES(?,?)", (key, time.time()))


def is_seen(key):
    with conn() as c:
        return c.execute("SELECT 1 FROM seen WHERE key=?", (key,)).fetchone() is not None
