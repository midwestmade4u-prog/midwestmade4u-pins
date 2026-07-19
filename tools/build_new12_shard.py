#!/usr/bin/env python3
"""
One-off builder for the "fold in the new 12" project (2026-07-19).

Takes /tmp/new12/data.json (12 SKUs: title/bonus/price/is_bundle/board_id/
category/listing_id/image_url) and produces:
  1. r/{stem}.html redirect pages (OG/Product markup + click-tracking
     beacons) for all 60 pin files (v1 + v2-v5 per listing), matching
     generate_redirects.py's format exactly.
  2. A single new shard file (pinterest_shard_10.json, pinterest_shard_11.json)
     with the full pin-entry schema used by pinterest_shard_00-09.json,
     weight=3 for every entry (newest listings get the rotation boost, same
     pattern as listings 21-34).

v1 entries point image_url at the already-live i.pinimg.com CDN url (no
local image file -- see pick_daily_pin.py's optional image_url override).
v2-v5 entries point image_url at REPO_RAW_BASE + file (the freshly
generated local jpg, which this script assumes already exists on disk).
"""
import json, os, html
from urllib.parse import urlparse

GH_PAGES_BASE = "https://midwestmade4u-prog.github.io/midwestmade4u-pins"
REPO_RAW_BASE = "https://raw.githubusercontent.com/midwestmade4u-prog/midwestmade4u-pins/main/"


def clean_title(title):
    return title.split("|")[0].strip()


def build_redirect_html(stem, title, description, price, image_url, utm_dest):
    page_url = f"{GH_PAGES_BASE}/r/{stem}.html"
    title = html.escape(title, quote=True)
    description = html.escape(description, quote=True)
    return f"""<!DOCTYPE html>
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
    "https://abacus.jasoncameron.dev/hit/mm4u-listing/{{slug}}",
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


def main():
    with open("/tmp/new12/data.json") as f:
        data = json.load(f)

    os.makedirs("r", exist_ok=True)
    all_entries = []

    for p in data:
        stem = p["file_stem"]
        slug = p["slug"]
        listing_url = f"https://www.etsy.com/listing/{p['listing_id']}"
        utm_dest = f"{listing_url}?utm_source=pinterest&utm_medium=pin&utm_campaign={slug}&utm_content={stem}"
        title = clean_title(p["title"])
        price_num = p["price"].replace("$", "")

        variants = [("v1", None, p["image_url"])] + [
            (v, stem, f"{REPO_RAW_BASE}{stem}_{v}.jpg") for v in ("v2", "v3", "v4", "v5")
        ]

        for vtag, base_pin, image_url in variants:
            file_name = f"{stem}.jpg" if vtag == "v1" else f"{stem}_{vtag}.jpg"
            file_stem_v = file_name.rsplit(".", 1)[0]
            tracking_url = f"{GH_PAGES_BASE}/r/{file_stem_v}.html"

            html = build_redirect_html(file_stem_v, p["title"], p["bonus"], price_num, image_url, utm_dest)
            html = html.replace("mm4u-listing/{slug}", f"mm4u-listing/{p['listing_id']}")
            with open(f"r/{file_stem_v}.html", "w") as fh:
                fh.write(html)

            entry = {
                "file": file_name,
                "title": p["title"],
                "bonus": p["bonus"],
                "board_id": p["board_id"],
                "price": p["price"],
                "listing_url": listing_url,
                "tracking_url": tracking_url,
                "_listing_slug": p["listing_id"],
                "_variant": vtag,
                "weight": 3,
            }
            if base_pin:
                entry["_base_pin"] = base_pin
            if vtag == "v1":
                entry["image_url"] = p["image_url"]
            all_entries.append(entry)

    print(f"Built {len(all_entries)} pin entries, {len(all_entries)} redirect pages.")

    mid = len(all_entries) // 2
    shard_10 = all_entries[:mid]
    shard_11 = all_entries[mid:]
    with open("pinterest_shard_10.json", "w") as f:
        json.dump(shard_10, f, indent=2)
    with open("pinterest_shard_11.json", "w") as f:
        json.dump(shard_11, f, indent=2)
    print(f"Wrote pinterest_shard_10.json ({len(shard_10)}), pinterest_shard_11.json ({len(shard_11)})")


if __name__ == "__main__":
    main()
