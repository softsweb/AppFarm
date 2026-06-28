import hashlib
import re

from . import db
from .harvester import harvest

# Words that signal a small, buildable web tool
BUILDABLE = (
    "app", "tool", "website", "web app", "tracker", "generator", "converter",
    "calculator", "dashboard", "reminder", "planner", "list", "manager",
    "timer", "note", "budget", "log", "journal", "organizer", "checklist",
)
# Phrases that signal "someone is asking for a buildable thing"
REQUEST_PHRASES = (
    "is there an app", "is there a tool", "looking for an app", "looking for a tool",
    "app that", "tool that", "website that", "need an app", "need a tool",
    "wish there was", "anyone made", "does anyone know of", "build me",
    "someone make", "i want an app", "i want a tool", "an app to", "a tool to",
    "an app for", "a tool for", "an app where", "a website to",
)
# Words that signal "too hard for a single self-hosted web app in one shot"
HARD = (
    "blockchain", "hardware", "mobile app", "ios", "android", "native",
    "machine learning", "gpu", "real-time video", "desktop app", "browser extension",
)


# Things that can't be a small self-hosted web app - never pick these
EXCLUDE = (
    "programming language", "imessage", "browser extension", "kernel", "compiler",
    "operating system", "physical product", "hardware", "chrome extension",
)


def key(c):
    return hashlib.sha1(c["source_url"].encode()).hexdigest()


_STOP = {"the", "a", "an", "to", "of", "and", "or", "for", "in", "on", "it", "is",
         "app", "that", "you", "your", "this", "with", "be", "as", "i", "if"}


def _words(text):
    """Normalized significant-word set for similarity comparison."""
    toks = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in toks if len(w) > 2 and w not in _STOP}


def _too_similar(idea, existing_word_sets):
    """True if idea overlaps heavily with an idea we have already used.
    Catches the same request crossposted to several subreddits."""
    a = _words(idea)
    if not a:
        return False
    for b in existing_word_sets:
        if not b:
            continue
        inter = len(a & b)
        union = len(a | b) or 1
        if inter / union >= 0.6:
            return True
    return False


# Self-promo / "look what I built" markers - these are not requests, push them down
BRAG = (
    "i built", "i made", "i've built", "i have built", "i created", "my saas",
    "my app", "mrr", "launched", "i actually did it", "what i learned", "revenue",
    "subscribers", "i sold", "acquired", "side project", "just shipped",
    "monthly traffic", "feedback on my", "roast my", "show off",
)

# Ideas that depend on external data/services we can't use (self-hosted, no APIs)
NEEDS_EXTERNAL = (
    "song", "music", "spotify", "playlist", "movie", "netflix", "stream",
    "video", "youtube", "photo", "camera", "picture", "notification", "news",
    "weather", "stock", "crypto", "maps", "gps", "location", "translate",
    " ai ", "gpt", "llm", "real-time", "realtime", "sms", "scrape", "live tv",
)


def score(c):
    t = c["idea"].lower()
    demand = min(c.get("up", 0), 500) / 500.0 + min(c.get("comments", 0), 200) / 200.0  # 0..2
    build = sum(1.0 for w in BUILDABLE if w in t)
    build += sum(1.5 for p in REQUEST_PHRASES if p in t)
    build -= sum(1.0 for w in HARD if w in t)
    build -= sum(2.0 for p in BRAG if p in t)
    build -= sum(1.5 for w in NEEDS_EXTERNAL if w in t)
    length = 0.5 if 40 < len(c["idea"]) < 1500 else 0.0
    c["_build"] = build
    return round(0.5 * demand + build + length, 3)


def pick():
    # Ideas we have already used (live/soon/archived) - skip anything that is
    # essentially the same request, even if it was crossposted elsewhere.
    used = [_words(a["idea"]) for a in db.list_all()]
    candidates = []
    for c in harvest():
        if not c["idea"] or db.is_seen(key(c)):
            continue
        if any(x in c["idea"].lower() for x in EXCLUDE):
            continue
        if _too_similar(c["idea"], used):
            continue
        c["score"] = score(c)
        candidates.append(c)
    # Strongly prefer items that actually look like a buildable app/request.
    strong = [c for c in candidates if c.get("_build", 0) >= 1.0]
    pool = strong if strong else candidates
    pool.sort(key=lambda x: x["score"], reverse=True)
    if not pool:
        return None
    # Let Claude choose the best, genuinely-useful idea from the shortlist.
    from . import builder
    shortlist = pool[:20]
    return builder.llm_select(shortlist) or shortlist[0]
