# Pin Rotation & Video Pipeline Tools

## `pick_daily_pin.py` (added 2026-07-19 -- the actual live scheduler logic)
Deterministic, stateless picker: for any calendar date, always returns the same one pin (safe to
re-run/re-fire without a posted-ledger). Fetches the 10 shards + `pinterest_static_meta.json` from
`raw.githubusercontent.com` (public, no auth needed) unless `--local <dir>` is passed. Prints a JSON
object with everything needed to place the Pinterest post (title, board_id, image_url, source_url,
description).

```
python3 pick_daily_pin.py                  # today (UTC date)
python3 pick_daily_pin.py 2026-08-01        # a specific date (testing/backfill)
python3 pick_daily_pin.py --local .         # read shards from a local clone instead of the network
```

This is what the recurring Claude Code Remote scheduled task (`create_trigger`, daily cron) actually
calls each day. Selection weight comes from each pin's own `"weight"` field in the shard files (1 or
3) -- `pinterest_static_meta.json`'s `weighted_list` is a derived cache for debugging only; regenerate
it via `build_weighted_list()` in this script any time a pin's weight changes, never hand-edit it.
Two bugs were found and fixed here on 2026-07-19, before this was ever wired to anything live: (1) the
hand-maintained `weighted_list` had silently dropped the 3x boost for 4 listings (a drift bug, invisible
because nothing had ever executed it), and (2) grouping a weight-3 pin's repeats together in the array
(the original construction) makes a stateless day-index walk post the *identical image* on 3 consecutive
days -- exactly what the 5-variant system exists to prevent. Fixed by building the rotation order as
successive passes over the pool instead of grouped repeats (see docstring in the script).

# Video Pin Pipeline Tools

Built Jul 3 2026 to convert static Pinterest pin images into short (~9s) video pins.

## Requirements
- `ffmpeg` + `ffprobe` on PATH
- Python 3 with `Pillow` and `numpy` (`pip3 install Pillow numpy --break-system-packages`)
- Font: `/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf` (adjust `FONT` variable in scripts if unavailable -- any bold sans-serif works)

## Scripts

### `make_video_pin_v2.sh` (current, use this one)
```
./make_video_pin_v2.sh <input.jpg> "<hook text>" "<CTA text>" <output.mp4>
```
Builds a 3-shot "editor cut" video from a single static pin image: headline zoom-in, middle-content zoom-out, price/CTA footer (padded not stretched, to avoid text distortion on thin crops). Shots are chosen automatically by `pick_shots.py` (content-density analysis -- finds the row band with the most text/graphics per section rather than a fixed fraction, so it never lands on blank whitespace). Crossfades between shots, adds a synthesized royalty-free ambient audio bed (layered sine tones -- no external audio file needed), and burns in hook (top) + CTA (bottom) text overlays for the full duration.

CTA text should NOT say "link in bio" -- Pinterest pins are natively clickable, unlike Instagram/TikTok. Use something like "Tap to get..." instead.

### `pick_shots.py <image.jpg>`
Standalone shot-picker, called automatically by `make_video_pin_v2.sh`. Analyzes row/column pixel standard-deviation to find the densest (most text-like) band within each third of the image, converts to composite-canvas fractions, and also samples the footer band's own background color for padding (rather than guessing a fixed color). Prints `y1 y2 y3 shot_height footer_height footer_bg_color` for the shell script to consume.

### `patch_price.py <input.jpg> <output.jpg>`
Surgical digit-patch tool: erases a specific glyph region and redraws a replacement character in a matching font/size/color. Was used to fix a stale "$4.99" -> "$8.99" across all 20 original pin images (same shared template, identical pixel position on every image -- see erase-box/ink-target constants at the top of the file). Reusable for any future single-character price/text fix on this template; would need re-measuring bbox coordinates if the template or image dimensions change.

### `make_video_pin.sh` (v1, superseded -- kept for reference only)
Original single continuous Ken Burns zoom approach. Rejected: "one picture turned into a short video that zooms a little. not good." Left here only as a reference for what NOT to do; use v2.

## Known limitations / next steps
- Only tested on the MidwestMade4U 1000x1500 pin template. Different aspect ratios or templates will need `pick_shots.py`'s density thresholds re-validated.
- No video posting logic here -- that's handled separately via Buffer (`buffer_add_to_queue` Zapier action), not included in this repo.

## Folding in the 12 new holiday/back-to-school SKUs (2026-07-19)

Matt published 12 new Etsy listings + Pinterest pins on 2026-07-18 (9 holiday-themed,
3 back-to-school-themed -- see `claude/project_pin_overhaul_jul18.md` for the source
table of listing IDs / pin URLs / boards). This is how they were folded into the same
rotation system the 34 Disney listings already use, once the scheduler itself was
proven working (see the "Bugs found/fixed" section above).

**`generate_variants_holiday_school.py`** -- a category-aware fork of
`generate_variants.py`. The original's 4 templates (`v2`-`v5`) hard-code Disney-specific
hook copy ("Still scrambling before every Disney trip?", "MidwestMade4U • Disney
Printables", etc.), since it was only ever written for the 34 Disney planners. This
fork keeps the exact same layout/visual logic (fonts, colors, pill facts, footer bars)
but swaps in category-appropriate hook text via a `CATEGORY_COPY` dict keyed by
`"holiday"` / `"school"`. Only `v2`-`v5` are generated by this script -- `v1` is each
listing's already-live, Canva-designed pin image (posted manually 2026-07-18), which
is NOT re-hosted in this repo; see below.

**`build_new12_shard.py`** -- one-off builder that took the 12 SKUs' data (title,
description/bonus text, price, board_id, category, listing_id, and each pin's live
`i.pinimg.com` image URL -- fetched fresh via the Pinterest API since none of this was
sitting in any file) and produced: (1) `r/{stem}.html` redirect pages for all 60 files
(12 listings x 5 variants) via the same OG/Product-markup + click-tracking-beacon
template `generate_redirects.py` uses, and (2) two new shard files,
`pinterest_shard_10.json` (30 entries) and `pinterest_shard_11.json` (30 entries),
using the exact same pin-entry schema as `pinterest_shard_00-09.json`. Every one of the
60 new entries carries `"weight": 3` -- these are the newest listings in the pool, so
they get the same 3x rotation boost listings 21-34 already have.

**`pick_daily_pin.py` change:** a pin entry may now optionally carry its own absolute
`"image_url"` field. If present, `pick_daily_pin.py` uses it as-is instead of
constructing `REPO_RAW_BASE + file`. This is how the 12 new listings' `v1` variant
avoids needing its image downloaded and re-committed to this repo at all -- it just
points straight at the image's permanent `i.pinimg.com` CDN URL from the original
Pinterest post. (`v2`-`v5` don't have this problem since they're generated fresh by
`generate_variants_holiday_school.py` and committed normally.) `NUM_SHARDS` was bumped
from 10 to 12 to match.

**Bonus/description text provenance:** the `"bonus"` field for these 12 listings is a
condensed version of each pin's own live Pinterest description (fetched via the API,
not invented) -- e.g. "Master checklist, gift list & budget tracker, 25-day countdown
calendar, and card & menu planner" for the Christmas Planner Bundle. `is_bundle` is
derived from whether "Bundle" appears in the pin's own title (2 of the 12 do:
christmas-planner-bundle and complete-holiday-command-center) rather than the old
`price != "$8.99"` heuristic, which doesn't apply -- these 12 are priced $2.50-$7.00,
a completely different scale from the original 34's flat $8.99 (+$14.99 bundle) tier.

After this change: pool size 170 -> 230, `weighted_list` length 310 -> 490 (regenerated
via `build_weighted_list()`, not hand-edited). Re-ran the same adjacent-day-repeat
simulation used to catch Bug 2 originally, across 600 simulated days on the new 230-pin
pool: zero adjacent-day repeats, minimum 130-day gap between any repeat of the same
file, and all 60 new files confirmed present in one full rotation cycle.
