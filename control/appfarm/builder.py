import os
import re
import shutil
import subprocess

from . import config

PROMPT = """You are building a small, single-purpose, self-hosted web app.

Read SPEC.md for the product NAME and the IDEA. Implement it by editing
main.py, templates/index.html, static/style.css, static/logo.svg and
static/favicon.svg ONLY.

Hard rules:
- Single FastAPI app on port 8000 with the existing Dockerfile unchanged.
- Keep the /healthz and /stats endpoints and the visit-counting middleware
  EXACTLY as they are. Do not remove or rename them.
- STORAGE IS CLIENT-SIDE ONLY. Every piece of user/app data MUST be stored in
  the visitor's own browser with localStorage (JavaScript). Each visitor gets
  their own private data - one person's data must NEVER be visible to another.
  Do NOT persist app data on the server. Do NOT add server-side tables or write
  to the server SQLite file for anything other than the existing visit counter.
  The server only serves the page and static assets; all app logic and state
  live in the browser. No external APIs, no API keys, no paid services, no
  outbound network calls, no auth/login.
- Add any new Python dependency to requirements.txt.
- The app must genuinely work and be useful. No placeholder TODOs, no fake data.

Branding and UI (this matters as much as the feature):
- Use the product NAME from SPEC.md as the page title and brand in the header.
- Design a clean, modern SVG logo in static/logo.svg (this may include the
  wordmark) and a matching ICON-ONLY SVG mark in static/favicon.svg: a single
  square glyph with NO text, transparent background, that reads clearly at 22px.
  The AppFarm dashboard shows static/favicon.svg next to the app name, so it must
  look good tiny and standalone.
- Give THIS app its OWN distinct visual identity. Do NOT default to a dark theme
  every time. Choose the palette, mood and typography that genuinely fit THIS
  product - it might be light, warm, pastel, colorful, editorial, brutalist,
  glassy, etc. Vary it from one app to the next; two AppFarm apps should never
  look like the same template.
- Whatever style you pick, it must look distinctly 2026-modern and premium:
  confident typography, considered spacing, tasteful color, smooth
  micro-interactions. Avoid generic AI-slop styling (no plain Bootstrap look,
  no default Inter-on-white).
- It must be fully responsive and mobile-first - flawless on a phone.
- Any modal, dialog, drawer, popup or overlay MUST be fully hidden when closed
  (no empty box visible on load, nothing peeking on screen) and MUST be reliably
  dismissible by a visible close button, by clicking the backdrop, AND by the
  Escape key. Test the open/close in your head before finishing - a broken,
  half-open or unclosable modal is a failed build.

Text rules:
- NEVER use the em-dash character. Not in the UI, not in copy, not in code
  comments, not anywhere. Use a plain hyphen "-" instead.
"""

NAME_PROMPT = (
    "Invent a short, catchy, brandable product name for this app idea.\n"
    "Rules: ONE word, lowercase, letters only (a-z), 3 to 11 characters, no\n"
    "spaces, no punctuation, no quotes, no explanation. Output ONLY the name.\n\n"
    "Idea:\n"
)

SELECT_PROMPT = (
    "Pick ONE Reddit app request to build as a small self-hosted web app.\n"
    "Requirements for the idea you pick:\n"
    "- Genuinely useful to real people.\n"
    "- Fully buildable as a single web app using ONLY browser-local storage - no\n"
    "  external APIs, no logins, no music/video/photo/AI/maps/payments/live-data.\n"
    "- MUST have a realistic way to make money (subscription, one-time unlock,\n"
    "  pro tier, etc.). If an idea cannot be monetized, DO NOT pick it - an app\n"
    "  with no path to revenue is not worth building.\n"
    "Skip joke or meme ideas.\n"
    "Reply on ONE line in exactly this format:\n"
    "<number> | <one short sentence describing how it would make money>\n"
    "Example: 3 | Freemium - free basic tracking, $4/mo Pro unlocks history + export.\n\n"
    "Ideas:\n"
)


PITCH_PROMPT = (
    "Write a short teaser description for an app, to show on a "
    '"Tomorrow\'s build" card on a product dashboard.\n'
    "Rules:\n"
    "- 1 to 2 sentences, about 25-40 words total, on a single line.\n"
    "- Say what the app does and why someone would want it, in a confident,\n"
    "  modern product voice. Plain and concrete, no hype words.\n"
    "- Write as if it is a real shipping product. Do NOT mention Reddit, that\n"
    "  someone requested it, or that it is AI-built.\n"
    "- NEVER use the em-dash character; use a plain hyphen instead.\n"
    "- Output ONLY the description text, nothing else.\n\n"
    "Product name: {name}\n\nIdea:\n{idea}\n"
)


def write_pitch(name, idea):
    """Ask Claude for a short, polished description for the SOON card.
    Returns clean one-line text, or "" so the dashboard falls back to the idea."""
    if config.FAKE_BUILD or not config.CLAUDE_OAUTH_TOKEN:
        return ""
    try:
        res = subprocess.run(
            ["claude", "-p", PITCH_PROMPT.format(name=name, idea=idea[:800]),
             "--dangerously-skip-permissions"],
            cwd="/tmp",
            env=_claude_env(),
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception:
        return ""
    text = " ".join((res.stdout or "").split()).strip()
    return text.replace("—", "-")[:280]


def _claude_env():
    env = dict(os.environ)
    if config.CLAUDE_OAUTH_TOKEN:
        env["CLAUDE_CODE_OAUTH_TOKEN"] = config.CLAUDE_OAUTH_TOKEN
    # Control runs as root (for the Docker socket); Claude Code needs this to
    # allow --dangerously-skip-permissions as root.
    env["IS_SANDBOX"] = "1"
    return env


def pick_brand_name(idea):
    """Ask Claude for a short brandable name. Returns a lowercase slug or None."""
    if config.FAKE_BUILD or not config.CLAUDE_OAUTH_TOKEN:
        return None
    try:
        res = subprocess.run(
            ["claude", "-p", NAME_PROMPT + idea[:600], "--dangerously-skip-permissions"],
            cwd="/tmp",
            env=_claude_env(),
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception:
        return None
    best = ""
    for line in (res.stdout or "").strip().splitlines():
        s = re.sub(r"[^a-z]", "", line.strip().lower())
        if 3 <= len(s) <= 14:
            best = s
    return best or None


def llm_select(candidates):
    """Let Claude choose the single best, genuinely-useful idea. Returns one of
    the candidates or None."""
    if config.FAKE_BUILD or not config.CLAUDE_OAUTH_TOKEN or not candidates:
        return None
    listing = "\n".join(f"{i + 1}. {c['title'][:120]}" for i, c in enumerate(candidates))
    try:
        res = subprocess.run(
            ["claude", "-p", SELECT_PROMPT + listing, "--dangerously-skip-permissions"],
            cwd="/tmp",
            env=_claude_env(),
            capture_output=True,
            text=True,
            timeout=180,
        )
    except Exception:
        return None
    out = (res.stdout or "").strip()
    m = re.search(r"(\d+)", out)
    if not m:
        return None
    idx = int(m.group(1)) - 1
    if not (0 <= idx < len(candidates)):
        return None
    mon = ""
    if "|" in out:
        mon = out.split("|", 1)[1].strip().splitlines()[0][:300]
    cand = candidates[idx]
    cand["monetization"] = mon
    return cand


def prepare(slug, name, idea):
    dest = os.path.join(config.APPS_DIR, slug)
    if os.path.exists(dest):
        shutil.rmtree(dest)
    shutil.copytree(config.TEMPLATE_DIR, dest)
    with open(os.path.join(dest, "SPEC.md"), "w") as f:
        f.write(f"# Product name: {name}\n\n## Idea\n\n{idea}\n")
    return dest


def _differs(dest, rel):
    """True if a built file no longer matches the pristine template copy."""
    a = os.path.join(dest, rel)
    b = os.path.join(config.TEMPLATE_DIR, rel)
    try:
        with open(a, "rb") as fa, open(b, "rb") as fb:
            return fa.read() != fb.read()
    except OSError:
        return False


def build_code(dest):
    if config.FAKE_BUILD:
        return
    cmd = ["claude", "-p", PROMPT, "--dangerously-skip-permissions"]
    if config.CLAUDE_MODEL:
        cmd += ["--model", config.CLAUDE_MODEL]
    res = subprocess.run(
        cmd, cwd=dest, env=_claude_env(), timeout=config.BUILD_TIMEOUT,
        capture_output=True, text=True,
    )
    # Claude Code sometimes exits non-zero even after successfully writing the
    # app, so we trust the produced files over the exit code. We only fail if
    # Claude clearly did nothing (every file still matches the template).
    built = (
        _differs(dest, "templates/index.html")
        or _differs(dest, "main.py")
        or _differs(dest, "static/style.css")
    )
    if not built:
        tail = (res.stderr or res.stdout or "").strip()[-800:]
        raise RuntimeError(f"claude build did not modify the app (exit {res.returncode}): {tail}")
