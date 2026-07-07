#!/usr/bin/env python3
"""
Fresh-pin variation factory (Phase 1b).

Generates 4 NEW, structurally distinct pin designs (not color tweaks) per
existing listing -- different layout, different hook framing, different
visual anchor -- on top of the 1 original design already in rotation.
Result: 5 pin variants per listing.

Uses only local fonts (Liberation Sans, already on disk) and JSON metadata
(title/bonus/price) -- no PDF rendering needed.

Usage: python3 tools/generate_variants.py pinterest_zapier_pins_v3.json pinterest_zapier_pins_v4.json
"""
import json, sys
from PIL import Image, ImageDraw, ImageFont

W, H = 1000, 1500

NAVY   = (16, 24, 60)
GOLD   = (208, 175, 59)
GREEN  = (40, 130, 69)
CREAM  = (247, 246, 241)
RED    = (196, 30, 58)
WHITE  = (255, 255, 255)
DARK_TEXT = (35, 38, 48)
CARD_A = (255, 255, 255)
CARD_B = (233, 232, 224)

FONT_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

# Universal, verified-true selling points (Canva bonus page + fillable PDF
# ship on every listing per the standing product spec) -- safe to state on
# every pin, no per-listing fabrication.
UNIVERSAL_FACTS = [
    "Printable + Fillable PDF",
    "Instant Download -- No Waiting",
    "Free Editable Canva Bonus Page",
]


def F(size, bold=True):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def center_text(draw, text, font, y, color, img_w=W):
    bb = draw.textbbox((0, 0), text, font=font)
    x = (img_w - (bb[2] - bb[0])) // 2
    draw.text((x, y), text, font=font, fill=color)
    return bb[3] - bb[1]


def wrap_lines(draw, text, font, max_w):
    words, lines, cur = text.split(), [], []
    for word in words:
        test = " ".join(cur + [word])
        bb = draw.textbbox((0, 0), test, font=font)
        if bb[2] > max_w and cur:
            lines.append(" ".join(cur))
            cur = [word]
        else:
            cur.append(word)
    if cur:
        lines.append(" ".join(cur))
    return lines


def draw_check(draw, x, y, size=22, color=GREEN):
    draw.line([(x, y + size * 0.5), (x + size * 0.35, y + size * 0.85),
               (x + size, y)], fill=color, width=max(3, size // 7), joint="curve")


def clean_title(title):
    return title.split("|")[0].strip()


def short_hook(bonus, price, is_bundle):
    if is_bundle:
        return bonus
    return f"FREE bonus: {bonus}"


def fact_pills(d, y, facts, pill_color, text_color, check_color):
    """Draws a stack of pill-shaped fact rows, returns new y."""
    for f in facts:
        h = 64
        d.rounded_rectangle([(70, y), (W - 70, y + h)], radius=h // 2, fill=pill_color)
        draw_check(d, 100, y + h // 2 - 12, size=24, color=check_color)
        d.text((150, y + h // 2 - 16), f, font=F(27, False), fill=text_color)
        y += h + 18
    return y


# ---------------------------------------------------------------------------
# Template B -- Problem-first
# ---------------------------------------------------------------------------
def template_b(title, bonus, price, is_bundle):
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)

    hook = "Still scrambling before every Disney trip?" if not is_bundle else "Piecing together your Disney plan from 5 different tabs?"
    hook_lines = wrap_lines(d, hook, F(48), W - 140)
    band_h = 140 + len(hook_lines) * 60

    d.rectangle([(0, 0), (W, band_h)], fill=RED)
    d.rectangle([(0, band_h), (W, band_h + 8)], fill=GOLD)

    y = 55
    center_text(d, "MidwestMade4U", F(26, False), y, (255, 214, 214))
    y += 55
    for line in hook_lines:
        h = center_text(d, line, F(48), y, WHITE)
        y += h + 16

    y = band_h + 45
    for line in wrap_lines(d, clean_title(title), F(42), W - 120):
        h = center_text(d, line, F(42), y, NAVY)
        y += h + 10
    y += 24
    d.line([(80, y), (W - 80, y)], fill=GOLD, width=4)
    y += 36

    for line in wrap_lines(d, short_hook(bonus, price, is_bundle), F(28, False), W - 200):
        draw_check(d, 90, y + 4, size=24)
        d.text((130, y), line, font=F(28, False), fill=DARK_TEXT)
        y += 42
    y += 30

    y = fact_pills(d, y, UNIVERSAL_FACTS, WHITE, DARK_TEXT, GREEN)

    foot_h = 130
    d.rectangle([(0, H - foot_h), (W, H)], fill=NAVY)
    center_text(d, f"Instant Download  •  Only {price}", F(32), H - foot_h + 30, GOLD)
    center_text(d, "midwestmade4u.etsy.com", F(22, False), H - foot_h + 78, (170, 190, 225))
    return img


# ---------------------------------------------------------------------------
# Template C -- Stat/number-led
# ---------------------------------------------------------------------------
def template_c(title, bonus, price, is_bundle):
    img = Image.new("RGB", (W, H), GOLD)
    d = ImageDraw.Draw(img)

    top_h = 400
    d.rectangle([(0, 0), (W, top_h)], fill=GOLD)
    y = 45
    center_text(d, "MIDWESTMADE4U DIGITAL DOWNLOAD", F(22), y, NAVY)
    y += 55
    big = price if is_bundle else "FREE BONUS"
    center_text(d, big, F(110), y, NAVY)
    y += 135
    sub = "all-in-one bundle -- instant download" if is_bundle else "included with every order"
    center_text(d, sub, F(26, False), y, (60, 50, 20))

    d.rectangle([(0, top_h), (W, H - 100)], fill=NAVY)
    y = top_h + 55
    for line in wrap_lines(d, clean_title(title), F(44), W - 120):
        h = center_text(d, line, F(44), y, WHITE)
        y += h + 12
    y += 16
    d.line([(200, y), (W - 200, y)], fill=GOLD, width=3)
    y += 34

    for line in wrap_lines(d, bonus, F(26, False), W - 160):
        h = center_text(d, line, F(26, False), y, (210, 220, 240))
        y += h + 10
    y += 26

    y = fact_pills(d, y, UNIVERSAL_FACTS, (26, 36, 78), (220, 228, 245), GOLD)
    y += 10

    d.rounded_rectangle([(60, y), (W - 60, y + 100)], radius=14, fill=GOLD)
    center_text(d, "Tap to Grab Yours", F(32), y + 16, NAVY)
    center_text(d, "Instant Digital Download", F(20, False), y + 60, (60, 50, 20))

    d.rectangle([(0, H - 100), (W, H)], fill=GREEN)
    center_text(d, "midwestmade4u.etsy.com", F(24, False), H - 62, WHITE)
    return img


# ---------------------------------------------------------------------------
# Template D -- Quick-facts grid
# ---------------------------------------------------------------------------
def template_d(title, bonus, price, is_bundle):
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    ttl_lines_probe = wrap_lines(d, clean_title(title), F(44), W - 100)
    head_h = 130 + len(ttl_lines_probe) * 58
    d.rectangle([(0, 0), (W, head_h)], fill=NAVY)
    y = 45
    center_text(d, "MidwestMade4U  •  Disney Printables", F(23, False), y, (170, 190, 225))
    y += 48
    for line in ttl_lines_probe:
        h = center_text(d, line, F(44), y, WHITE)
        y += h + 10

    facts = [
        ("Instant", "Download"),
        ("Print or", "Fill Digitally"),
        ("Editable", "PDF Format"),
        ("Bundle Deal" if is_bundle else "Free Bonus", "Included"),
    ]
    foot_h = 150
    grid_top = head_h + 45
    pad = 22
    cell_w = (W - 60) // 2
    cell_h = 340  # tall cards -- fills the canvas instead of leaving a dead zone
    for i, (top, bot) in enumerate(facts):
        col, row = i % 2, i // 2
        x0 = 30 + col * cell_w
        y0 = grid_top + row * (cell_h + pad)
        fill = CARD_A if (i % 2 == 0) else CARD_B
        d.rounded_rectangle([(x0, y0), (x0 + cell_w - pad, y0 + cell_h)], radius=16, outline=(220, 218, 210), width=2, fill=fill)
        draw_check(d, x0 + 34, y0 + 40, size=30)
        d.text((x0 + 34, y0 + 110), top, font=F(34), fill=NAVY)
        d.text((x0 + 34, y0 + 162), bot, font=F(27, False), fill=DARK_TEXT)

    y = grid_top + 2 * (cell_h + pad) + 36
    d.line([(150, y), (W - 150, y)], fill=GOLD, width=3)
    y += 36
    for line in wrap_lines(d, bonus, F(27, False), W - 140):
        h = center_text(d, line, F(27, False), y, DARK_TEXT)
        y += h + 10
    y += 24
    d.rounded_rectangle([(90, y), (W - 90, y + 76)], radius=38, fill=GREEN)
    center_text(d, "Printable + Fillable PDF Included", F(25), y + 24, WHITE)

    d.rectangle([(0, H - foot_h), (W, H)], fill=RED)
    center_text(d, f"Only {price}  •  Instant Download", F(33), H - foot_h + 36, WHITE)
    center_text(d, "midwestmade4u.etsy.com", F(22, False), H - foot_h + 88, (255, 220, 220))
    return img


# ---------------------------------------------------------------------------
# Template E -- Question hook
# ---------------------------------------------------------------------------
def template_e(title, bonus, price, is_bundle):
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)

    q = "Planning a Disney trip and don't know where to start?" if not is_bundle else "Tired of juggling 4 separate Disney planning docs?"
    q_lines = wrap_lines(d, q, F(40), W - 140)
    band_h = 150 + len(q_lines) * 54
    d.rectangle([(0, 0), (W, band_h)], fill=NAVY)
    d.rectangle([(0, band_h), (W, band_h + 6)], fill=GOLD)

    y = 60
    center_text(d, "MidwestMade4U", F(24, False), y, (170, 190, 225))
    y += 54
    for line in q_lines:
        h = center_text(d, line, F(40), y, WHITE)
        y += h + 14

    y = band_h + 45
    center_text(d, "HERE'S THE FIX:", F(24), y, RED)
    y += 52
    for line in wrap_lines(d, clean_title(title), F(36), W - 140):
        h = center_text(d, line, F(36), y, NAVY)
        y += h + 8
    y += 24
    d.line([(150, y), (W - 150, y)], fill=GOLD, width=3)
    y += 32

    for line in wrap_lines(d, short_hook(bonus, price, is_bundle), F(27, False), W - 180):
        h = center_text(d, line, F(27, False), y, DARK_TEXT)
        y += h + 10
    y += 28

    y = fact_pills(d, y, UNIVERSAL_FACTS, WHITE, DARK_TEXT, RED)

    foot_h = 120
    d.rectangle([(0, H - foot_h), (W, H)], fill=GREEN)
    center_text(d, f"Instant Download  •  Only {price}", F(32), H - foot_h + 28, WHITE)
    center_text(d, "midwestmade4u.etsy.com", F(22, False), H - foot_h + 74, (220, 240, 225))
    return img


TEMPLATES = {"v2": template_b, "v3": template_c, "v4": template_d, "v5": template_e}


def main():
    infile = sys.argv[1] if len(sys.argv) > 1 else "pinterest_zapier_pins_v3.json"
    outfile = sys.argv[2] if len(sys.argv) > 2 else "pinterest_zapier_pins_v4.json"

    with open(infile) as f:
        data = json.load(f)

    orig_pins = data["pins"]
    new_pins = []
    generated = 0

    for p in orig_pins:
        stem = p["file"].rsplit(".", 1)[0]
        title = p["title"]
        bonus = p["bonus"]
        price = p.get("price", "$8.99")
        is_bundle = price != "$8.99"

        v1 = dict(p)
        v1["_variant"] = "v1"
        new_pins.append(v1)

        for vtag, fn in TEMPLATES.items():
            img = fn(title, bonus, price, is_bundle)
            new_file = f"{stem}_{vtag}.jpg"
            img.save(new_file, "JPEG", quality=90)
            generated += 1

            variant = {k: v for k, v in p.items() if k not in ("video_url", "tracking_url", "_listing_slug")}
            variant["file"] = new_file
            variant["_variant"] = vtag
            variant["_base_pin"] = stem
            new_pins.append(variant)

    data["pins"] = new_pins
    data["_comment"] = data.get("_comment", "") + (
        " | UPDATED 2026-07-07 (Phase 1b): fresh-pin variation factory. Every listing now has 5 "
        "structurally distinct designs (v1=original, v2=problem-first, v3=stat-led, v4=quick-facts "
        "grid, v5=question-hook) -- different layout/hook/visual anchor each, not color tweaks. "
        "Retires the small 34-image pool that Pinterest's 2026 fresh-pin bias was suppressing."
    )
    data["_rotation_comment"] = (
        "No persistent 'posted' ledger file -- instead a deterministic GLOBAL sequential walk "
        "(days-since-epoch * 3 + slot_offset, epoch 2026-01-01) indexes into the weighted pin list, "
        "so every one of the ~170 pins gets used before any repeat (~40+ day full cycle at 3 posts/day), "
        "with zero write-back risk from ephemeral scheduled-task runs. Functionally equivalent to a "
        "no-repeat ledger without needing one."
    )

    with open(outfile, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Generated {generated} new pin images. Total pins in {outfile}: {len(new_pins)}")


if __name__ == "__main__":
    main()
