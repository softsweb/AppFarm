from apscheduler.schedulers.background import BackgroundScheduler

from . import config, pipeline, pruner


def start():
    s = BackgroundScheduler(daemon=True)
    if config.BUILDS_ENABLED:
        s.add_job(pipeline.run_cycle, "cron", hour=config.BUILD_HOUR, minute=0,
                  id="cycle", replace_existing=True)
    s.add_job(pruner.prune, "interval", hours=6, id="prune", replace_existing=True)
    s.start()
    return s
