import os


def _int(name, default):
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return int(default)


DOMAIN = os.getenv("DOMAIN", "localhost")
CLAUDE_OAUTH_TOKEN = os.getenv("CLAUDE_CODE_OAUTH_TOKEN", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "").strip()

# Reddit ideas come from the public pullpush.io API (no Reddit app / credentials
# needed; it works from datacenter IPs unlike Reddit's own endpoint).
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "AppFarm/1.0 (self-hosted)").strip()
PULLPUSH_SIZE = _int("PULLPUSH_SIZE", 60)
# Only consider ideas posted within this many days (keeps picks reasonably fresh).
IDEA_MAX_AGE_DAYS = _int("IDEA_MAX_AGE_DAYS", 730)

APP_LIFETIME_DAYS = _int("APP_LIFETIME_DAYS", 30)
MIN_VISITS_TO_SURVIVE = _int("MIN_VISITS_TO_SURVIVE", 50)
# Visits needed to earn the 👑 winner badge on the dashboard.
WINNER_VISITS = _int("WINNER_VISITS", 100)
MAX_LIVE_APPS = _int("MAX_LIVE_APPS", 40)

# Request-focused subs (people asking for apps), not builder/self-promo subs.
DEFAULT_SUBREDDITS = ["SomebodyMakeThis", "AppIdeas", "Lightbulb", "DoesThisExist"]
EXTRA_SUBREDDITS = [s.strip() for s in os.getenv("EXTRA_SUBREDDITS", "").split(",") if s.strip()]
SUBREDDITS = DEFAULT_SUBREDDITS + EXTRA_SUBREDDITS

DATA_DIR = os.getenv("APPFARM_DATA_DIR", "/data")
APPS_DIR = os.path.join(DATA_DIR, "apps")
DB_PATH = os.path.join(DATA_DIR, "appfarm.db")
TEMPLATE_DIR = os.getenv("APP_TEMPLATE_DIR", "/app-template")

DOCKER_NETWORK = os.getenv("DOCKER_NETWORK", "appfarm_web")
APP_PORT = 8000

FAKE_BUILD = os.getenv("APPFARM_FAKE_BUILD", "0") == "1"
ENABLE_TLS = os.getenv("APPFARM_ENABLE_TLS", "1") == "1"
CERT_RESOLVER = os.getenv("TRAEFIK_CERT_RESOLVER", "le")
BUILD_TIMEOUT = _int("APPFARM_BUILD_TIMEOUT", 1800)

BUILD_HOUR = _int("APPFARM_BUILD_HOUR", 8)

# Set to 0 to pause the daily build cycle (no new app is generated). The
# dashboard keeps serving the apps that already exist. Pruning still runs.
BUILDS_ENABLED = os.getenv("APPFARM_BUILDS_ENABLED", "1") == "1"
