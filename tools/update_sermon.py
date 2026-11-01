#!/usr/bin/env python3
"""Find the church's most recent Sunday livestream on YouTube and write it to
assets/data/latest-sermon.json, which the homepage reads to embed the sermon.

Uses only the standard library, so it runs anywhere Python 3.9+ is installed:

    python3 tools/update_sermon.py

How it picks the video:
  1. If the channel is live right now, use that stream.
  2. Otherwise, the newest past livestream that started on a Sunday (Pacific time).
  3. Otherwise, the newest past livestream of any day.
If YouTube can't be reached, the existing JSON file is left as it is.
"""

import json
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

CHANNEL_ID = "UCCrEXJ6uczDrPUvFZ0FEOCA"
STREAMS_URL = f"https://www.youtube.com/channel/{CHANNEL_ID}/streams"
WATCH_URL = "https://www.youtube.com/watch?v={}"
CHURCH_TZ = ZoneInfo("America/Los_Angeles")
MAX_CANDIDATES = 8
OUT = Path(__file__).resolve().parent.parent / "assets" / "data" / "latest-sermon.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Cookie": "CONSENT=YES+1",
}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.read().decode("utf-8", "replace")


def stream_ids():
    """Video IDs from the channel's Live tab, newest first."""
    html = fetch(STREAMS_URL)
    match = re.search(r"var ytInitialData = (\{.*?\});</script>", html, re.S)
    if not match:
        raise RuntimeError("Couldn't find video data on the channel's Live tab")
    data = json.loads(match.group(1))

    ids = []

    def walk(node):
        if isinstance(node, dict):
            lockup = node.get("lockupViewModel")
            if lockup and lockup.get("contentType") == "LOCKUP_CONTENT_TYPE_VIDEO":
                ids.append(lockup.get("contentId"))
            renderer = node.get("videoRenderer")
            if renderer:
                ids.append(renderer.get("videoId"))
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(data)
    seen = []
    for vid in ids:
        if vid and vid not in seen:
            seen.append(vid)
    return seen


def video_details(video_id):
    html = fetch(WATCH_URL.format(video_id))
    title = re.search(r'<meta name="title" content="([^"]*)"', html)
    start = re.search(r'"liveBroadcastDetails":\{[^}]*?"startTimestamp":"([^"]+)"', html)
    live_now = re.search(r'"liveBroadcastDetails":\{[^}]*?"isLiveNow":(true|false)', html)
    upcoming = '"isUpcoming":true' in html
    return {
        "id": video_id,
        "title": unescape(title.group(1)) if title else "",
        "start": datetime.fromisoformat(start.group(1)) if start else None,
        "live": bool(live_now and live_now.group(1) == "true"),
        "upcoming": upcoming,
    }


def unescape(text):
    import html
    return html.unescape(text)


def pick(videos):
    now = datetime.now(timezone.utc)
    started = [v for v in videos if v["start"] and not v["upcoming"] and v["start"] <= now]
    for v in started:
        if v["live"]:
            return v
    for v in started:
        if v["start"].astimezone(CHURCH_TZ).weekday() == 6:  # Sunday
            return v
    return started[0] if started else None


def main():
    try:
        ids = stream_ids()[:MAX_CANDIDATES]
        videos = []
        for vid in ids:
            try:
                videos.append(video_details(vid))
            except Exception as err:  # one bad video shouldn't stop the rest
                print(f"skip {vid}: {err}", file=sys.stderr)
        chosen = pick(videos)
    except Exception as err:
        print(f"Couldn't reach YouTube, keeping the existing file: {err}", file=sys.stderr)
        return 0

    if not chosen:
        print("No past livestreams found, keeping the existing file", file=sys.stderr)
        return 0

    local = chosen["start"].astimezone(CHURCH_TZ)
    payload = {
        "videoId": chosen["id"],
        "title": chosen["title"],
        "date": local.date().isoformat(),
        "live": chosen["live"],
        "updated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    previous = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
    new = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    # Only rewrite when the sermon changes, so the scheduled job doesn't commit every run
    if previous and json.loads(previous).get("videoId") == payload["videoId"] and json.loads(previous).get("live") == payload["live"]:
        print(f"No change: {payload['title']} ({payload['date']})")
        return 0
    OUT.write_text(new, encoding="utf-8")
    print(f"Updated: {payload['title']} ({payload['date']}){' LIVE' if payload['live'] else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
