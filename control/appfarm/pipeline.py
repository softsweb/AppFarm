import re
import time

from slugify import slugify

from . import builder, db, deployer, scorer


def _slug_and_name(title, idea):
    brand = builder.pick_brand_name(idea)
    if brand:
        slug = re.sub(r"[^a-z0-9]", "", brand.lower())[:14] or "app"
        name = brand[:1].upper() + brand[1:]
    else:
        slug = slugify(title)[:20].strip("-") or "app"
        name = title[:40].strip() or "Untitled app"
    if db.get_by_slug(slug):
        slug = f"{slug}-{str(int(time.time()))[-3:]}"
    return slug, name


def pick_and_store_soon():
    """Choose the next idea, give it a brand name, store it as the SOON app."""
    c = scorer.pick()
    if not c:
        return None
    slug, name = _slug_and_name(c["title"], c["idea"])
    pitch = builder.write_pitch(name, c["idea"])
    db.add_app(slug=slug, name=name, idea=c["idea"], source_url=c["source_url"],
               score=c["score"], status="soon", monetization=c.get("monetization", ""),
               pitch=pitch)
    db.mark_seen(scorer.key(c))
    return slug


def build_app(slug):
    a = db.get_by_slug(slug)
    if not a:
        raise ValueError(f"no app with slug {slug}")
    dest = builder.prepare(slug, a["name"], a["idea"])
    builder.build_code(dest)
    host = deployer.build_and_run(slug, dest)
    db.set_status(slug, "live", built_at=time.time())
    return host


def run_cycle():
    """Daily job: build the pending SOON app, then pick tomorrow's SOON."""
    soon = db.get_soon()
    if soon:
        build_app(soon["slug"])
    pick_and_store_soon()


def build_now():
    """Pick one idea and build + deploy it immediately (manual/testing)."""
    slug = pick_and_store_soon()
    if not slug:
        return None
    return build_app(slug)
