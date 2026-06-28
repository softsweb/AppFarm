import os

import requests
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import config, db

BASE = os.path.dirname(__file__)
app = FastAPI(title="AppFarm")
templates = Jinja2Templates(directory=os.path.join(BASE, "templates"))
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")

scheme = "https" if config.ENABLE_TLS else "http"


def _live_visits(slug, fallback):
    """Poll the app's own /stats so the dashboard shows real-time counts."""
    try:
        r = requests.get(f"http://appfarm-app-{slug}:{config.APP_PORT}/stats", timeout=2)
        n = int(r.json().get("visits", fallback))
        if n != fallback:
            db.update_visits(slug, n)
        return n
    except Exception:
        return fallback


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    apps = db.list_live()
    for a in apps:
        a["visits"] = _live_visits(a["slug"], a["visits"])
        a["winner"] = a["visits"] >= config.WINNER_VISITS
        a["url"] = f"{scheme}://{a['slug']}.{config.DOMAIN}"
    # Default order is newest first; the dashboard dropdown re-sorts client-side.
    apps.sort(key=lambda a: a.get("created_at") or 0, reverse=True)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "apps": apps,
            "soon": db.get_soon(),
            "domain": config.DOMAIN,
            "threshold": config.WINNER_VISITS,
        },
    )


@app.get("/healthz")
def healthz():
    return {"ok": True}
