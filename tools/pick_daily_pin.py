#!/usr/bin/env python3
"""
Deterministic, stateless daily pin picker for the MidwestMade4U Pinterest
auto-poster (built 2026-07-19 to actually wire up the rotation system that
had been sitting unused since it was first built).

No persistent "posted" ledger is needed for pin SELECTION -- the pin for any
given calendar date is a pure function of that date, so the same day always
picks the same pin (safe to re-run), and every pin in the pool gets used
(proportional to its weight) before any repeat. This was the design intent
documented in generate_variants.py's _rotation_comment; this script is the
first actual implementation of it.

Usage:
    python3 pick_daily_pin.py                  # today (UTC date), pool fetched from GitHub raw
    python3 pick_daily_pin.py 2026-08-01        # a specific date (for testing/backfill)
    python3 pick_daily_pin.py --local /path/to/repo  # read shards from a local clone instead of network

Prints one JSON object to stdout with everything the caller needs to place
the Pinterest post:
    {
      "date": "2026-07-19",
      "day_index": 200,
      "selection_index": 45,
      "pin_index": 12,
      "file": "pin_003_disneyland_day_v3.jpg",
      "title": "...",
      "board_id": "...",
      "image_url": "https://raw.githubusercontent.com/.../pin_003_disneyland_day_v3.jpg",
      "source_url": "https://midwestmade4u-prog.github.io/.../r/pin_003_disneyland_day_v3.html",
      "description": "..."
    }

Weighting is read directly from each pin's own "weight" field in the shard
files (source of truth) -- NOT from pinterest_static_meta.json's
weighted_list, which is a derived convenience copy only. If the two ever
disagree, the per-pin weight field wins.

A pin entry may optionally carry its own absolute "image_url" (e.g. an
already-live i.pinimg.com URL for a pin that was posted manually before
being folded into rotation) -- if present it's used as-is instead of the
default REPO_RAW_BASE + file construction. Added 2026-07-19 when the 12 new
holiday/back-to-school SKUs were folded in: their v1 image is the already-
live Canva export on Pinterest's own CDN, so there was no need to re-host it
in this repo (only the freshly generated v2-v5 variants live here).
"""
import json
import sys
import os
import urllib.request
from datetime import date, timezone, datetime

REPO_RAW_BASE = "https://raw.githubusercontent.com/midwestmade4u-prog/midwestmade4u-pins/main/"
ROTATION_EPOCH = date(2026, 1, 1)
NUM_SHARDS = 12  # bumped 2026-07-19: shards 10-11 added for the 12 new holiday/back-to-school SKUs


def fetch_json(url):
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_json(path):
    with open(path) as f:
        return json.load(f)


def build_pool(local_dir=None):
    pool = []
    for i in range(NUM_SHARDS):
        fname = f"pinterest_shard_{i:02d}.json"
        if local_dir:
            shard = load_json(os.path.join(local_dir, fname))
        else:
            shard = fetch_json(REPO_RAW_BASE + fname)
        pool.extend(shard)
    return pool


def build_weighted_list(pool):
    """
    Builds the day-by-day rotation order as successive full PASSES over the
    pool rather than grouping each pin's repeats together.

    IMPORTANT: grouping repeats together (e.g. [.., 100,100,100, 101,101,101, ..],
    which is how the original hand-maintained weighted_list was built) makes a
    stateless day-index walk land on the EXACT SAME image on 3 consecutive
    calendar days for every weight-3 pin -- directly defeating the whole point
    of the 5-variant fresh-pin system, which exists specifically to avoid
    Pinterest's same-image-repost penalty. Caught by testing this script
    against consecutive dates before it ever went live.

    Instead: pass 1 = every pin once (in pool order), pass 2 = every pin with
    weight >= 2 once, pass 3 = every pin with weight >= 3 once, etc. Within a
    single pass every pin index is distinct (no adjacent repeats), and a given
    weight-3 pin's three occurrences land ~70 days apart (min gap = len(pool
    restricted to weight>=2), comfortably beyond any realistic repost window.
    """
    max_weight = max((p.get("weight", 1) for p in pool), default=1)
    wl = []
    for occurrence in range(1, max_weight + 1):
        wl.extend(idx for idx, p in enumerate(pool) if p.get("weight", 1) >= occurrence)
    return wl


def main():
    args = sys.argv[1:]
    local_dir = None
    target_date = None
    i = 0
    while i < len(args):
        if args[i] == "--local":
            local_dir = args[i + 1]
            i += 2
        else:
            target_date = date.fromisoformat(args[i])
            i += 1

    if target_date is None:
        target_date = datetime.now(timezone.utc).date()

    pool = build_pool(local_dir)
    weighted_list = build_weighted_list(pool)

    day_index = (target_date - ROTATION_EPOCH).days
    if day_index < 0:
        raise SystemExit(f"target date {target_date} is before rotation epoch {ROTATION_EPOCH}")

    selection_index = day_index % len(weighted_list)
    pin_index = weighted_list[selection_index]
    pin = pool[pin_index]

    out = {
        "date": target_date.isoformat(),
        "day_index": day_index,
        "selection_index": selection_index,
        "pin_index": pin_index,
        "pool_size": len(pool),
        "weighted_list_len": len(weighted_list),
        "file": pin["file"],
        "title": pin.get("title", "MidwestMade4U Printable"),
        "board_id": pin["board_id"],
        "image_url": pin.get("image_url") or (REPO_RAW_BASE + pin["file"]),
        "source_url": pin.get("tracking_url", pin.get("listing_url", "")),
        "description": pin.get("bonus", ""),
        "listing_url": pin.get("listing_url", ""),
        "weight": pin.get("weight", 1),
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
