"""
AppFarm app template.

Claude: implement the idea in SPEC.md by editing the index() route, the HTML in
templates/index.html, and static/style.css. You may add more routes and helper
functions, but DO NOT touch the visit-counting middleware, /stats, or /healthz -
AppFarm relies on them to measure traffic.

Storage is CLIENT-SIDE ONLY: keep all user/app data in the browser with
localStorage so every visitor has their own private state. The server-side
SQLite below exists solely for the unique-visitor counter - do not store app
data in it.
"""
import hashlib
import os
import sqlite3
import time

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE = os.path.dirname(__file__)
DATA_DIR = "/data"
DB_PATH = os.path.join(DATA_DIR, "app.db")
os.makedirs(DATA_DIR, exist_ok=True)


def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def _init():
    with db() as c:
        # One row per unique visitor (hashed IP) - the counter is unique visits.
        c.execute("CREATE TABLE IF NOT EXISTS _visitors(ip_hash TEXT PRIMARY KEY, ts REAL)")


_init()

app = FastAPI()
templates = Jinja2Templates(directory=os.path.join(BASE, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")


# --- AppFarm plumbing: do not modify ---
def _client_ip(request: Request) -> str:
    # Behind Traefik the real client IP is the first hop in X-Forwarded-For.
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


@app.middleware("http")
async def _count_visits(request: Request, call_next):
    if request.method == "GET" and request.url.path == "/":
        try:
            ip = _client_ip(request)
            if ip:
                h = hashlib.sha256(ip.encode()).hexdigest()
                with db() as c:
                    c.execute(
                        "INSERT OR IGNORE INTO _visitors(ip_hash, ts) VALUES (?, ?)",
                        (h, time.time()),
                    )
        except Exception:
            pass
    return await call_next(request)


@app.get("/stats")
def _stats():
    with db() as c:
        n = c.execute("SELECT COUNT(*) FROM _visitors").fetchone()[0]
    return {"visits": n}


@app.get("/healthz")
def _healthz():
    return {"ok": True}
# --- end AppFarm plumbing ---


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
