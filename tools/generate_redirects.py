#!/usr/bin/env python3
"""
Generates GH-Pages redirect pages (r/{stem}.html) + a tracking_url/_listing_slug
field per pin, from pinterest_zapier_pins_v2.json (or whatever is the current live
config). Re-run this any time a new pin is added to the rotation.

Click tracking: abacus.jasoncameron.dev (free, keyless hit-counter API).
  - per-pin:    GET /get/mm4u-pin/{stem}
  - per-listing GET /get/mm4u-listing/{slug}
  - site total: GET /get/mm4u-total/clicks

Usage: python3 tools/generate_redirects.py <input.json> <output.json>
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


def main():
    infile = sys.argv[1] if len(sys.argv) > 1 else "pinterest_zapier_pins_v2.json"
    outfile = sys.argv[2] if len(sys.argv) > 2 else "pinterest_zapier_pins_v3.json"

    with open(infile) as f:
        data = json.load(f)

    os.makedirs("r", exist_ok=True)

    for p in data["pins"]:
        stem = p["file"].rsplit(".", 1)[0]
        dest = p.get("listing_url") or data.get("shop_url")
        slug = listing_slug(dest) if p.get("listing_url") else "shop"
        utm_dest = f"{dest}?utm_source=pinterest&utm_medium=pin&utm_campaign={slug}&utm_content={stem}"
        p["tracking_url"] = f"{GH_PAGES_BASE}/r/{stem}.html"
        p["_listing_slug"] = slug

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex">
<meta http-equiv="refresh" content="0;url={utm_dest}">
<title>Redirecting to MidwestMade4U...</title>
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
