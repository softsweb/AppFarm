import time

import requests

from . import config, db, deployer


def refresh_visits():
    for a in db.list_live():
        try:
            r = requests.get(
                f"http://appfarm-app-{a['slug']}:{config.APP_PORT}/stats", timeout=5
            )
            db.update_visits(a["slug"], int(r.json().get("visits", a["visits"])))
        except Exception:
            continue


def prune():
    refresh_visits()
    now = time.time()

    # 1. Lifetime + performance filter
    for a in db.list_live():
        born = a["built_at"] or a["created_at"] or now
        age_days = (now - born) / 86400.0
        if age_days >= config.APP_LIFETIME_DAYS and a["visits"] < config.MIN_VISITS_TO_SURVIVE:
            deployer.stop(a["slug"])
            db.set_status(a["slug"], "archived", archived_at=now)

    # 2. Hard cap on live apps - archive the weakest, oldest first
    live = db.list_live()
    if len(live) > config.MAX_LIVE_APPS:
        live.sort(key=lambda a: (a["visits"], a["built_at"] or a["created_at"] or 0))
        for a in live[: len(live) - config.MAX_LIVE_APPS]:
            deployer.stop(a["slug"])
            db.set_status(a["slug"], "archived", archived_at=now)
