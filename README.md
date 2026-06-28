# AppFarm 🌾

A self-hosted server that **builds a new app every day, on autopilot, using your own Claude.**

> 📺 **Watch it in action:** https://youtu.be/2hjqmdB7upc
>
> 🖥️ **Need a server to run this on?** Spin one up on **[Hostinger](https://hostinger.com/softsweb)** and use code **`SOFTSWEB10`** for 10% off. Pick their **Ubuntu 24 + Docker** image and AppFarm runs out of the box.

Each day it scans what people are begging for on Reddit (subreddits like
r/SomebodyMakeThis), picks one, gives it a short brand name, has **Claude Code**
build it with a futuristic mobile UI + logo, and deploys it to its own subdomain
(`appname.yourdomain.com`) via Traefik + Docker. Apps that get traffic survive and
earn a 👑. Apps nobody visits get archived automatically.

> Runs entirely on **your own Claude Pro/Max subscription** - no API key, no per-token bill.

---

## What you need

- An always-on VPS running Debian/Ubuntu. Docker can already be installed or not -
  `install.sh` handles both. I run this on **[Hostinger](https://hostinger.com/softsweb)**
  (their "Ubuntu 24 + Docker" image ships Docker pre-installed, so it works out of
  the box) - use code **`SOFTSWEB10`** for 10% off if you grab one.
- A domain, e.g. `abc.com`, with DNS pointing at the server:
  - `A   abc.com        -> SERVER_IP`
  - `A   *.abc.com      -> SERVER_IP`   (wildcard - lets every app get a subdomain)
- A **Claude Pro or Max** subscription.

## Setup (the "regular user" path)

```bash
git clone <this-repo> appfarm && cd appfarm

# 1. Prepare the host. Installs Docker if missing, and applies the one tweak
#    AppFarm needs so Traefik can talk to Docker 29+ (see note below).
#    Safe to run even if your VPS already came with Docker.
sudo ./install.sh

# 2. Get your Claude subscription token (run this on any machine where you can log in):
npx @anthropic-ai/claude-code setup-token
#   -> copy the token it prints

# 3. Configure
cp .env.example .env
nano .env            # set DOMAIN, ACME_EMAIL, paste CLAUDE_CODE_OAUTH_TOKEN

# 4. Launch
docker compose up -d --build
```

> **Don't skip `install.sh` even if Docker is already installed.** Docker Engine
> 29+ rejects Traefik's bundled API client, so without the `DOCKER_MIN_API_VERSION`
> fix the script applies, Traefik can't read container labels and none of your app
> subdomains will route. The script is idempotent - if the fix is already in place
> it does nothing.

Open `https://abc.com` - the dashboard. It lists live apps and the **SOON** card
(tomorrow's pick).

## Where to run it

You just need a cheap always-on VPS. I use **[Hostinger](https://hostinger.com/softsweb)** -
their **Ubuntu 24 + Docker** image comes with Docker pre-installed, so step 1 above
is basically instant. Use code **`SOFTSWEB10`** at checkout for **10% off**:

👉 **https://hostinger.com/softsweb** (code **`SOFTSWEB10`**)

Any provider works, but if this repo saved you time, grabbing your box through that
link is the easiest way to say thanks - it costs you nothing extra and helps keep
projects like this coming.

## Test it without spending credits first

Set `APPFARM_FAKE_BUILD=1` in `.env`, then trigger a build manually:

```bash
docker compose exec control python -m appfarm.cli build-now
```

This runs the full pipeline (harvest → pick → deploy) but ships the bare template
instead of calling Claude. Once the subdomain comes up and shows on the dashboard,
flip `APPFARM_FAKE_BUILD=0` and run `build-now` again for a real Claude build.

## Manual commands

```bash
docker compose exec control python -m appfarm.cli build-now    # pick + build + deploy one app now
docker compose exec control python -m appfarm.cli run-cycle    # promote SOON -> build, then pick next SOON
docker compose exec control python -m appfarm.cli prune        # refresh visits, archive losers
docker compose exec control python -m appfarm.cli pick-soon    # just choose tomorrow's idea
```

## The daily schedule (the "cron")

There is no system crontab. An in-process scheduler (APScheduler) runs inside the
`control` container and drives everything:

- **Once a day at hour `APPFARM_BUILD_HOUR`** (default `8`, in the container's
  timezone = UTC) it runs one cycle: build yesterday's queued **SOON** app, then
  pick and queue tomorrow's SOON idea.
- **Every 6 hours** it prunes - refreshes visit counts and archives apps that
  have aged out or failed to attract traffic.

To build at a different time, set `APPFARM_BUILD_HOUR` in `.env` (0-23) and
`docker compose up -d control`. You can always force a build now with the manual
commands above.

## Configuration (`.env`)

| Variable | Default | What it does |
|---|---|---|
| `DOMAIN` | - | Your root domain; apps deploy to `name.DOMAIN` |
| `ACME_EMAIL` | - | Email for Let's Encrypt TLS |
| `CLAUDE_CODE_OAUTH_TOKEN` | - | Your Claude Pro/Max token from `setup-token` |
| `APPFARM_BUILD_HOUR` | `8` | Hour of day (UTC) the daily build runs |
| `APP_LIFETIME_DAYS` | `30` | Days an app has to prove itself |
| `MIN_VISITS_TO_SURVIVE` | `50` | Below this at end of life → archived |
| `WINNER_VISITS` | `100` | Unique visits needed for the 👑 winner badge |
| `MAX_LIVE_APPS` | `40` | Hard cap on live app containers |
| `EXTRA_SUBREDDITS` | - | Extra idea sources (comma-separated) |
| `APPFARM_FAKE_BUILD` | `0` | `1` = ship the bare template (no Claude credits) |

## How survival works

- Each app gets `APP_LIFETIME_DAYS` to prove itself.
- If by then it has fewer than `MIN_VISITS_TO_SURVIVE` visits → container stopped, marked archived (not deleted).
- Hard cap of `MAX_LIVE_APPS` live containers; when full, the weakest gets archived.
- Apps over `WINNER_VISITS` get a 👑 on the dashboard - those are your winners.

## Visits and data

- **Visits are unique.** Each app counts one visit per unique visitor (hashed IP,
  so it's privacy-friendly and not tied to a person). Reloading 100 times from the
  same IP still counts as 1 - the number reflects how many distinct people showed
  up, which is the only signal that matters.
- **App data lives in the visitor's browser** (localStorage), not on the server.
  Every visitor gets their own private state, so the public demo apps never mix
  one person's data with another's. The server only serves the page and keeps the
  unique-visitor counter.

## The point

AppFarm finds and ships candidates. **Winners are yours to graduate** - take one
with real traffic and turn it into a proper SaaS by hand. AppFarm is the lottery
machine; you cash the ticket.

---

**Ready to run your own?** Get a server on **[Hostinger](https://hostinger.com/softsweb)**
with code **`SOFTSWEB10`** for 10% off, and you're minutes away from your first build.

📺 Watch the full walkthrough: https://youtu.be/2hjqmdB7upc
