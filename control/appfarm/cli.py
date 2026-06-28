import sys

from . import db, pipeline, pruner


def serve():
    db.init()
    from .scheduler import start
    start()
    import uvicorn
    from .dashboard import app
    uvicorn.run(app, host="0.0.0.0", port=8000)


def main():
    db.init()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "serve"
    if cmd == "serve":
        serve()
    elif cmd == "build-now":
        print(pipeline.build_now() or "no candidate found")
    elif cmd == "run-cycle":
        pipeline.run_cycle()
        print("cycle done")
    elif cmd == "pick-soon":
        print(pipeline.pick_and_store_soon() or "no candidate found")
    elif cmd == "prune":
        pruner.prune()
        print("prune done")
    elif cmd == "reset":
        from . import deployer
        for a in db.list_all():
            deployer.destroy(a["slug"])
        import os
        from . import config
        try:
            os.remove(config.DB_PATH)
        except FileNotFoundError:
            pass
        db.init()
        print("reset done - all apps removed, database cleared")
    elif cmd == "init":
        print("db ready")
    else:
        print(f"unknown command: {cmd}")
        print("commands: serve | build-now | run-cycle | pick-soon | prune | reset | init")


if __name__ == "__main__":
    main()
