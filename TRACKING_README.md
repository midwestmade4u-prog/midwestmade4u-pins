# MidwestMade4U Pinterest Click Tracker (Phase 1a, added 2026-07-07)

## Why
Etsy's "How shoppers found you" showed **Social media: 0** despite daily Pinterest pinning. Root cause: pins linked directly to plain Etsy URLs, so we had no way to see clicks independent of Etsy/Pinterest's own (unreliable) attribution.

## How it works
Every pin now links to a redirect page hosted here on GitHub Pages instead of the raw Etsy URL:

`https://midwestmade4u-prog.github.io/midwestmade4u-pins/r/{pin_file_stem}.html`

Each redirect page:
1. Fires 3 fire-and-forget beacons to [abacus.jasoncameron.dev](https://abacus.jasoncameron.dev) (free, keyless hit-counter API, no signup/no secrets) — one per-pin, one per-listing, one site-total.
2. Immediately redirects (both a `<meta refresh>` for reliability + a JS `location.replace` for speed) to the real Etsy listing, with UTM params appended: `utm_source=pinterest&utm_medium=pin&utm_campaign={listing_slug}&utm_content={pin_file_stem}`.

## Reading click counts (no auth needed)
- Per pin: `GET https://abacus.jasoncameron.dev/get/mm4u-pin/{pin_file_stem}`
- Per listing: `GET https://abacus.jasoncameron.dev/get/mm4u-listing/{listing_slug}`
- Site total: `GET https://abacus.jasoncameron.dev/get/mm4u-total/clicks`

Each returns `{"value": N}`.

## Config
`pinterest_zapier_pins_v3.json` is now the live config (adds `tracking_url` + `_listing_slug` per pin on top of `_v2`). Scheduled tasks should post using `tracking_url` as the pin's destination link, not `listing_url` directly — the redirect page still sends the visitor to the same listing, just via a hop we can count.

## Adding a new pin to the rotation (updated step)
1. Push the pin image here as before.
2. Add its JSON entry (needs `listing_url`).
3. Run `generate_redirects.py` (in `tools/`) to build its `r/{stem}.html` page + populate `tracking_url`/`_listing_slug`, and re-save as the current `_vN.json`.
4. Push.

## Known limitation
abacus.jasoncameron.dev is a free third-party service with no SLA. If it ever goes down, redirects still work (the fetch calls fail silently, redirect is unaffected) — only click counting would gap. Cross-check against Etsy's own traffic-source snapshot in the Phase 2 weekly digest.
