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

SUPERSEDED 2026-08-01: cadence is back to 1 post/day and destination URLs
are built by direct_link() below -- pins link straight to the Etsy listing,
never to the github.io redirect. The `tracking_url` field still present in
the shard files is DEAD DATA; do not read it. The paragraph below describes
the 3-slot design that is no longer in use, kept for context only.

UPDATED 2026-07-19 (scaling 1 post/day -> 3 posts/day): added a "slot"
concept (0, 1, 2 -- one per scheduled trigger/time-of-day) so a single
calendar date can drive 3 distinct posts instead of 1, guaranteed distinct
from each other (see build_weighted_list's global-index math below). Each of
the 3 scheduled triggers passes its own fixed --slot; slot is NOT auto-picked
by time-of-day, it's just an integer baked into each trigger's prompt.

Usage:
    python3 pick_daily_pin.py                        # today (UTC date), pool fetched from GitHub raw
    python3 pick_daily_pin.py 2026-08-01              # a specific date
    python3 pick_daily_pin.py --local /path/to/repo   # read shards from a local clone instead of network

    --slot is still accepted but 2026-08-01 set POSTS_PER_DAY back to 1, so
    slot 0 is the only valid value; anything else exits with an error.

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
      "source_url": "https://www.etsy.com/listing/4511280044/multi-park-...?utm_source=pinterest&...",
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
NUM_SHARDS = 13  # bumped 2026-08-01: shard 12 added for the Christmas POD push (4 SKUs x 2 variants)

# 2026-08-02: 1 -> 2 posts/day.
#
# The 2026-08-01 note below said volume was not the lever, citing impressions
# falling 252 -> 138 when cadence went 1 -> 3/day. That reading was confounded
# and is now retired: every pin in that window pointed at the github.io
# redirect, so the account was posting MORE pins that all carried the defect
# that was suppressing them. It measured the redirect, not the cadence.
#
# 2/day is chosen off the rotation maths, not off that number. Pool = 241 pin
# files over 53 listings; weighted list is 122 slots after the Christmas
# re-weight below. At 2/day the full cycle is 61 days and no listing repeats
# inside ~20 slots. At 3-4/day the same-listing gap drops under 10 days, which
# is where Pinterest's freshness signal starts working against us. 2/day is
# the most volume the existing creative supports without repeating itself.
POSTS_PER_DAY = 2

# Cadence changed mid-rotation, so the post counter cannot simply be
# day_index * POSTS_PER_DAY -- that would jump the walk backwards and re-serve
# pins posted in the last week. Instead the counter is continuous across the
# switch: every day before CADENCE_SWITCH contributed exactly 1 post, every day
# from it contributes POSTS_PER_DAY.
CADENCE_SWITCH = date(2026, 8, 3)


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

    Bug 3 (fixed 2026-08-02, when the Christmas SKUs were weighted up for the
    September window): the "successive passes" scheme only spreads evenly while
    the weights are roughly flat. Pass N contains only the listings with
    weight >= N, so raising four listings from 3 to 6 made passes 4, 5 and 6
    contain nothing but those four -- twelve consecutive Christmas slots at the
    tail of the cycle, each listing recurring every 4 slots. Exactly the
    clustering bug 1 was about, reintroduced through the weight field.

    Fix: the order is now produced by SMOOTH WEIGHTED ROUND-ROBIN (the credit
    scheme nginx uses for upstream balancing) instead of by passes. Every
    listing accumulates its weight each step; the highest running credit takes
    the slot and pays back the total weight. A listing of weight w therefore
    lands almost exactly every total/w slots regardless of what the other
    weights are, so the weight field is safe to use as a seasonality dial --
    which is what it is now being used for.

    An earlier attempt placed each occurrence at fraction (k + phase) / w and
    sorted. Rejected: equal spacing in FRACTION is not equal spacing in INDEX
    once the fractions bunch up, and the simulation showed the Christmas
    listings still recurring every 9 slots. The credit scheme spaces by index
    directly. Verified by simulation: minimum same-listing gap 20 slots
    (10 days at 2/day), minimum same-image gap 40 slots (20 days), and no
    calendar day serves one listing twice.
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

    active = [b for b in order if weight_of[b] > 0]  # weight 0 == benched
    total = sum(weight_of[b] for b in active)
    rank = {b: i for i, b in enumerate(order)}

    slots = [None] * total
    # Heaviest listings claim their ideal positions first, so the seasonal
    # dial (weight) gets the cleanest spacing; lighter listings fill the gaps.
    for base in sorted(active, key=lambda b: (-weight_of[b], rank[b])):
        w = weight_of[base]
        for k in range(w):
            ideal = int((k + 0.5) * total / w)
            j = ideal
            while slots[j % total] is not None:
                j += 1
            slots[j % total] = base
    listing_seq = slots

    occurrence_count = {base: 0 for base in order}
    wl = []
    for base in listing_seq:
        variants = groups[base]
        wl.append(variants[occurrence_count[base] % len(variants)])
        occurrence_count[base] += 1
    return wl


def direct_link(pin):
    """
    Builds the pin's destination URL: the Etsy listing itself, plus UTM params.

    2026-08-01. Replaces the `tracking_url` GitHub Pages redirect that every
    pin pointed at from 2026-07-07 onward. That redirect was built to fix
    Etsy's "How shoppers found you -> Social media: 0" and is the most likely
    reason that number stayed 0: Pinterest's own policy names redirects as a
    spam signal, and crawling the bounce page instead of the listing stripped
    the Etsy product metadata that turns a pin into a rich Product Pin.

    Confirmed on this account the same day: all six pins on the Disney board
    that still point at a bare etsy.com/listing URL render as full Product
    Pins (Etsy verified badge + live price); every pin pointing at the
    github.io redirect renders as a plain pin. Zero exceptions in the sample.

    Attribution now comes from these UTM params plus Etsy's own traffic-source
    report. We lose per-pin beacon counts and gain Product Pins.

    Raises if the listing URL is not an etsy.com URL -- a wrong link is far
    worse than a skipped post, so fail loudly rather than post something odd.
    """
    listing_url = (pin.get("listing_url") or "").strip()
    if not listing_url.startswith("https://www.etsy.com/listing/"):
        raise SystemExit(
            f"refusing to build a destination URL for {pin.get('file')!r}: "
            f"listing_url is {listing_url!r}, not an etsy.com listing"
        )
    if "?" in listing_url:
        raise SystemExit(
            f"listing_url for {pin.get('file')!r} already carries a query string "
            f"({listing_url!r}); refusing to append UTM params blindly"
        )

    stem = pin["file"].rsplit(".", 1)[0]
    # listing_url is either .../listing/<id> or .../listing/<id>/<slug>.
    # Campaign groups by product, so prefer the human-readable slug and fall
    # back to the numeric id when the shard entry doesn't carry one.
    tail = listing_url[len("https://www.etsy.com/listing/"):].split("/")
    campaign = tail[1] if len(tail) > 1 and tail[1] else tail[0]

    return (
        f"{listing_url}"
        f"?utm_source=pinterest"
        f"&utm_medium=pin"
        f"&utm_campaign={campaign}"
        f"&utm_content={stem}"
    )


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
    max_slot = POSTS_PER_DAY if target_date >= CADENCE_SWITCH else 1
    if not (0 <= slot < max_slot):
        raise SystemExit(
            f"slot must be 0..{max_slot - 1} for {target_date} "
            f"(cadence switched to {POSTS_PER_DAY}/day on {CADENCE_SWITCH}), got {slot}"
        )

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
    if target_date < CADENCE_SWITCH:
        # historical 1/day era -- one post per day, slot 0 only
        global_index = day_index
    else:
        posts_before_switch = (CADENCE_SWITCH - ROTATION_EPOCH).days
        days_since_switch = (target_date - CADENCE_SWITCH).days
        global_index = posts_before_switch + days_since_switch * POSTS_PER_DAY + slot
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
        "source_url": direct_link(pin),
        "description": pin.get("bonus", ""),
        "listing_url": pin.get("listing_url", ""),
        "weight": pin.get("weight", 1),
    }
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
