#!/usr/bin/env python3
"""
One-off script: adds the first 3 POD (print-on-demand) pins to the rotation
system -- Midwest Nice tee/mug/tumbler, the first non-digital-download SKUs
in the rotation. Added 2026-07-27.

Mirrors the manual steps documented in TRACKING_README.md ("Adding a new pin
to the rotation"), but writes redirect pages directly (matching
generate_redirects.py's exact template) instead of round-tripping through
the old flat-file schema that script expects, since the live pool is now
shard-based.

Appends to pinterest_shard_11.json (the most recent "newest listings" shard,
weight 3) rather than creating a new shard file -- avoids needing to bump
NUM_SHARDS in pick_daily_pin.py.
"""
import json
import os
from urllib.parse import urlparse

REPO_ROOT = os.path.expanduser("~/midwestmade4u-pins")
GH_PAGES_BASE = "https://midwestmade4u-prog.github.io/midwestmade4u-pins"
REPO_RAW_BASE = "https://raw.githubusercontent.com/midwestmade4u-prog/midwestmade4u-pins/main/"
BOARD_ID = "1078612248196102948"  # Midwest Life Shirts & Gifts, created 2026-07-27

NEW_PINS = [
    {
        "file": "pin_101_midwest_nice_tee.jpg",
        "title": "Midwest Nice. | Midwest Pride Graphic Tee",
        "bonus": "Bella+Canvas 3001 unisex tee, made to order",
        "board_id": BOARD_ID,
        "price": "$24.99",
        "listing_url": "https://www.etsy.com/listing/4544656960/midwest-nice-shirt-midwest-pride-tee",
        "weight": 3,
    },
    {
        "file": "pin_102_midwest_nice_mug.jpg",
        "title": "Midwest Nice. | Midwest Pride Coffee Mug",
        "bonus": "11oz/15oz ceramic mug, made to order",
        "board_id": BOARD_ID,
        "price": "$16.99",
        "listing_url": "https://www.etsy.com/listing/4544641375/midwest-nice-mug-midwest-pride-coffee",
        "weight": 3,
    },
    {
        "file": "pin_103_midwest_nice_tumbler.jpg",
        "title": "Midwest Nice. | 20oz Stainless Steel Tumbler",
        "bonus": "Insulated travel tumbler, made to order",
        "board_id": BOARD_ID,
        "price": "$35.99",
        "listing_url": "https://www.etsy.com/listing/4544657036/midwest-nice-tumbler-20oz-stainless",
        "weight": 3,
    },
]


def listing_slug(url):
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if len(parts) >= 3:
        return parts[2]
    elif len(parts) >= 2:
        return parts[1]
    return "unknown"


def make_redirect_page(pin):
    stem = pin["file"].rsplit(".", 1)[0]
    dest = pin["listing_url"]
    slug = listing_slug(dest)
    utm_dest = f"{dest}?utm_source=pinterest&utm_medium=pin&utm_campaign={slug}&utm_content={stem}"
    tracking_url = f"{GH_PAGES_BASE}/r/{stem}.html"
    title = pin["title"].split("|")[0].strip()
    price = pin["price"].replace("$", "")
    image_url = REPO_RAW_BASE + pin["file"]
    page_url = f"{GH_PAGES_BASE}/r/{stem}.html"
    description = pin.get("bonus", "Made-to-order MidwestMade4U product.")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0;url={utm_dest}">
<title>{title}</title>

<!-- Open Graph / Pinterest Product Rich Pin markup -->
<meta property="og:type" content="product">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{description}">
<meta property="og:url" content="{page_url}">
<meta property="og:image" content="{image_url}">
<meta property="product:price:amount" content="{price}">
<meta property="product:price:currency" content="USD">
<meta property="og:availability" content="instock">

<script>
(function() {{
  var beacons = [
    "https://abacus.jasoncameron.dev/hit/mm4u-pin/{stem}",
    "https://abacus.jasoncameron.dev/hit/mm4u-listing/{slug}",
    "https://abacus.jasoncameron.dev/hit/mm4u-total/clicks"
  ];
  beacons.forEach(function(u) {{
    try {{ fetch(u, {{mode: "no-cors", keepalive: true}}); }} catch (e) {{}}
  }});
  window.location.replace("{utm_dest}");
}})();
</script>
</head>
<body>
<p>Redirecting to <a href="{utm_dest}">the MidwestMade4U listing</a>&hellip;</p>
</body>
</html>
"""
    with open(os.path.join(REPO_ROOT, "r", f"{stem}.html"), "w") as fh:
        fh.write(html)

    pin["tracking_url"] = tracking_url
    pin["_listing_slug"] = slug
    return pin


def main():
    os.makedirs(os.path.join(REPO_ROOT, "r"), exist_ok=True)

    finished = [make_redirect_page(dict(p)) for p in NEW_PINS]

    shard_path = os.path.join(REPO_ROOT, "pinterest_shard_11.json")
    with open(shard_path) as f:
        shard = json.load(f)
    shard.extend(finished)
    with open(shard_path, "w") as f:
        json.dump(shard, f, indent=2)

    print(f"Added {len(finished)} pins to pinterest_shard_11.json (new length {len(shard)})")
    for p in finished:
        print(" -", p["file"], "->", p["tracking_url"])


if __name__ == "__main__":
    main()
