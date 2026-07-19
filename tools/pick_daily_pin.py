#!/usr/bin/env python3
"""
Deterministic, stateless daily pin picker for the MidwestMade4U Pinterest
auto-poster (built 2026-07-19 to actually wire up the rotation system that
had been sitting unused since it was first built).

No persistent "posted" ledger is needed for pin SELECTION -- the pin for any
given (calendar date, slot) is a pure function of those two inputs, so the
same date+slot always picks the same pin (safe to re-run), and every pin in
the pool gets used (proportional to its weight) before any repeat. This was
the design intent documented in generate_variants.py's _rotation_comment;
this script is the first actual implementation of it.

UPDATED 2026-07-19 (scaling 1 post/day -> 3 posts/day): added a "slot"
concept (0, 1, 2 -- one per scheduled trigger/time-of-day) so a single
calendar date can drive 3 distinct posts instead of 1, guaranteed distinct
from each other (see build_weighted_list's global-index math below). Each of
the 3 scheduled triggers passes its own fixed --slot; slot is NOT auto-picked
by time-of-day, it's just an integer baked into each trigger's prompt.

Usage:
    python3 pick_daily_pin.py                        # today (UTC date), slot 0, pool fetched from GitHub raw
    python3 pick_daily_pin.py 2026-08-01              # a specific date, slot 0
    python3 pick_daily_pin.py 2026-08-01 --slot 2     # a specific date + slot (0, 1, or 2)
    python3 pick_daily_pin.py --local /path/to/repo   # read shards from a local clone instead of network

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
POSTS_PER_DAY = 3  # bumped 2026-07-19: scaled from 1 to 3 posts/day (see slot math in main())


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
    Builds the rotation order as successive full PASSES over LISTINGS (not
    individual pin files), then assigns each successive occurrence of a
    listing its next variant file (v1, v2, v3, ... cycling back to v1 after
    the last). Returns a list of POOL INDICES, one per rotation "slot".

    IMPORTANT HISTORY -- two bugs already found and fixed here, in order:

    Bug 1 (fixed 2026-07-19, original build): grouping a weighted pin's
    repeats together in the array (e.g. [..,100,100,100,101,101,101,..])
    makes a stateless day-index walk land on the EXACT SAME image on 3
    consecutive calendar days for every weight-3 pin. Fixed by building the
    rotation as successive PASSES over the pool instead.

    Bug 2 (fixed 2026-07-19, when scaling 1 post/day -> 3 posts/day): the
    "successive passes over the pool" fix above was still built at the
    individual-FILE level, and the pool stores a listing's 5 variant files
    consecutively (v1..v5 adjacent). That's harmless walking one step/day,
    but the instant 3 posts/day meant reading 3 CONSECUTIVE pool positions
    per day -- which landed on 3 variants of the SAME listing, not 3
    different products. Caught immediately by testing --slot 0/1/2 for one
    date before wiring up any live triggers (see tools/README.md).

    Fix: pass/repeat weighting now operates on LISTINGS (grouped by each
    pin's "_base_pin", or the file's own stem for v1 entries), not files.
    Within any pass, every entry is a DIFFERENT listing -- so any window of
    consecutive slots up to the number of distinct listings in a pass will
    never repeat a listing. Each time a listing comes up in this listing-
    level sequence, it's assigned its NEXT variant file in v1->v2->v3->v4->
    v5->v1... order, so repeat occurrences of the same listing still use a
    fresh image, preserving the original point of the 5-variant system.
    """
    groups = {}  # base listing key -> list of pool indices, in file (v1..v5) order
    order = []   # base keys in first-seen (pool) order
    for idx, p in enumerate(pool):
        base = p.get("_base_pin") or p["file"].rsplit(".", 1)[0]
        if base not in groups:
            groups[base] = []
            order.append(base)
        groups[base].append(idx)

    weight_of = {base: pool[groups[base][0]].get("weight", 1) for base in order}
    max_weight = max(weight_of.values(), default=1)

    listing_seq = []  # sequence of listing keys, weighted, spread via passes
    for occurrence in range(1, max_weight + 1):
        listing_seq.extend(base for base in order if weight_of[base] >= occurrence)

    occurrence_count = {base: 0 for base in order}
    wl = []
    for base in listing_seq:
        variants = groups[base]
        wl.append(variants[occurrence_count[base] % len(variants)])
        occurrence_count[base] += 1
    return wl


def main():
    args = sys.argv[1:]
    local_dir = None
    target_date = None
    slot = 0
    i = 0
    while i < len(args):
        if args[i] == "--local":
            local_dir = args[i + 1]
            i += 2
        elif args[i] == "--slot":
            slot = int(args[i + 1])
            i += 2
        else:
            target_date = date.fromisoformat(args[i])
            i += 1

    if target_date is None:
        target_date = datetime.now(timezone.utc).date()
    if not (0 <= slot < POSTS_PER_DAY):
        raise SystemExit(f"slot must be 0..{POSTS_PER_DAY - 1}, got {slot}")

    pool = build_pool(local_dir)
    weighted_list = build_weighted_list(pool)

    day_index = (target_date - ROTATION_EPOCH).days
    if day_index < 0:
        raise SystemExit(f"target date {target_date} is before rotation epoch {ROTATION_EPOCH}")

    # Global index walks forward by 1 every single post (not every day), so
    # each day's 3 slots land on 3 CONSECUTIVE weighted_list positions --
    # guaranteed distinct from each other (as long as weighted_list has more
    # than POSTS_PER_DAY entries, true here by a wide margin) -- while still
    # cycling through the whole weighted list in order, same as the 1x/day
    # version did. This is the "days-since-epoch * 3 + slot_offset" scheme
    # originally sketched in generate_variants.py's _rotation_comment, never
    # implemented until now.
    global_index = day_index * POSTS_PER_DAY + slot
    selection_index = global_index % len(weighted_list)
    pin_index = weighted_list[selection_index]
    pin = pool[pin_index]

    out = {
        "date": target_date.isoformat(),
        "slot": slot,
        "day_index": day_index,
        "global_index": global_index,
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
