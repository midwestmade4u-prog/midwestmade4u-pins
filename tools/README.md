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
