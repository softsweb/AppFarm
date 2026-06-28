import time

import requests

from . import config

# Reddit ideas via pullpush.io (public, no auth, works from datacenter IPs).
# Reddit's own .json 403s VPSs and creating a Reddit API app is gated, so this
# public mirror is the zero-config source.
PULLPUSH = "https://api.pullpush.io/reddit/search/submission/"


def harvest():
    headers = {"User-Agent": config.REDDIT_USER_AGENT}
    after = int(time.time()) - config.IDEA_MAX_AGE_DAYS * 86400
    out = []
    for sub in config.SUBREDDITS:
        try:
            r = requests.get(
                PULLPUSH,
                params={
                    "subreddit": sub,
                    "sort_type": "score",
                    "sort": "desc",
                    "size": config.PULLPUSH_SIZE,
                    "after": after,
                },
                headers=headers,
                timeout=25,
            )
            if r.status_code != 200:
                continue
            for d in r.json().get("data", []):
                if d.get("over_18") or d.get("stickied"):
                    continue
                title = d.get("title", "") or ""
                body = d.get("selftext", "") or ""
                if body in ("[removed]", "[deleted]"):
                    body = ""
                url = d.get("full_link") or ("https://reddit.com" + (d.get("permalink") or ""))
                out.append(
                    {
                        "title": title,
                        "idea": (title + "\n\n" + body).strip(),
                        "source_url": url,
                        "up": d.get("score", 0),
                        "comments": d.get("num_comments", 0),
                    }
                )
        except Exception:
            continue
    return out
