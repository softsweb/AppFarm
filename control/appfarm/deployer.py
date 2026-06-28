import docker

from . import config


def _client():
    return docker.from_env()


def build_and_run(slug, build_dir):
    cli = _client()
    tag = f"appfarm-app-{slug}:latest"
    cli.images.build(path=build_dir, tag=tag, rm=True)

    name = f"appfarm-app-{slug}"
    try:
        old = cli.containers.get(name)
        old.remove(force=True)
    except docker.errors.NotFound:
        pass

    host = f"{slug}.{config.DOMAIN}"
    entry = "websecure" if config.ENABLE_TLS else "web"
    labels = {
        "traefik.enable": "true",
        f"traefik.http.routers.{slug}.rule": f"Host(`{host}`)",
        f"traefik.http.routers.{slug}.entrypoints": entry,
        f"traefik.http.services.{slug}.loadbalancer.server.port": str(config.APP_PORT),
    }
    if config.ENABLE_TLS:
        labels[f"traefik.http.routers.{slug}.tls.certresolver"] = config.CERT_RESOLVER

    cli.containers.run(
        tag,
        name=name,
        detach=True,
        network=config.DOCKER_NETWORK,
        labels=labels,
        restart_policy={"Name": "unless-stopped"},
        volumes={f"appfarm-app-{slug}-data": {"bind": "/data", "mode": "rw"}},
    )
    return host


def stop(slug):
    cli = _client()
    try:
        c = cli.containers.get(f"appfarm-app-{slug}")
        c.remove(force=True)
    except docker.errors.NotFound:
        pass


def destroy(slug):
    """Remove the app's container, image, and data volume entirely."""
    cli = _client()
    try:
        cli.containers.get(f"appfarm-app-{slug}").remove(force=True)
    except docker.errors.NotFound:
        pass
    except Exception:
        pass
    try:
        cli.images.remove(f"appfarm-app-{slug}:latest", force=True)
    except Exception:
        pass
    try:
        cli.volumes.get(f"appfarm-app-{slug}-data").remove(force=True)
    except Exception:
        pass
