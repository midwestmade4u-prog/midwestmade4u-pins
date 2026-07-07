#!/usr/bin/env python3
"""
Generates GH-Pages redirect pages (r/{stem}.html) + a tracking_url/_listing_slug
field per pin, from the current pins JSON. Re-run any time a pin is added.

UPDATED 2026-07-07: adds Open Graph Product markup (og:type=product,
product:price:amount/currency, og:availability) to every redirect page.
Pinterest retired the manual "apply for Rich Pins" step -- it's now fully
automatic based on OG/Product metadata on whatever page the pin actually
links to. Since pins now link through this redirect (not straight to Etsy,
per the Phase 1a attribution fix), the redirect page itself needs valid
Product markup or Rich Pins won't populate. Metadata mirrors the real
listing (title/price) so nothing here is misleading -- the redirect still
forwards instantly to the real Etsy listing (meta refresh, content="0").
"""
import json, sys, os
from urllib.parse import urlparse

GH_PAGES_BASE = "https://midwestmade4u-prog.github.io/midwestmade4u-pins"


def listing_slug(url):
    path = urlparse(url).path.strip("/")
    parts = path.split("/")
    if len(parts) >= 3:
        return parts[2]
    elif len(parts) >= 2:
        return parts[1]
    return "unknown"


def clean_title(title):
    return title.split("|")[0].strip()


def main():
    infile = sys.argv[1] if len(sys.argv) > 1 else "pinterest_zapier_pins_v4.json"
    outfile = sys.argv[2] if len(sys.argv) > 2 else "pinterest_zapier_pins_v4.json"

    with open(infile) as f:
        data = json.load(f)

    os.makedirs("r", exist_ok=True)
    repo_raw_base = data.get("repo_raw_base", "")

    for p in data["pins"]:
        stem = p["file"].rsplit(".", 1)[0]
        dest = p.get("listing_url") or data.get("shop_url")
        slug = listing_slug(dest) if p.get("listing_url") else "shop"
        utm_dest = f"{dest}?utm_source=pinterest&utm_medium=pin&utm_campaign={slug}&utm_content={stem}"
        p["tracking_url"] = f"{GH_PAGES_BASE}/r/{stem}.html"
        p["_listing_slug"] = slug

        title = clean_title(p.get("title", "MidwestMade4U Printable"))
        price = p.get("price", "$8.99").replace("$", "")
        image_url = repo_raw_base + p["file"] if repo_raw_base else ""
        page_url = f"{GH_PAGES_BASE}/r/{stem}.html"
        description = p.get("bonus", "Instant download Disney printable planner.")

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
        with open(f"r/{stem}.html", "w") as fh:
            fh.write(html)

    with open(outfile, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Generated {len(data['pins'])} redirect pages -> r/  and wrote {outfile}")


if __name__ == "__main__":
    main()
