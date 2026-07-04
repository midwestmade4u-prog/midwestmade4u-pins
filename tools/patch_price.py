#!/usr/bin/env python3
"""
patch_price.py <input.jpg> <output.jpg>
Surgically replaces the leading "4" in the baked-in "$4.99" price text with
an "8" (fixing the stale $4.99 -> $8.99 reprice), on the shared pin template
where the price footer sits at an identical pixel position across all pins
(confirmed on pin_001/006/017: '4' glyph ink bbox = cols 504-521, rows 1441-1462).
"""
import sys
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf"
FONT_SIZE = 28
CREAM = (250, 248, 240)
NAVY = (15, 25, 60)

# erase box: a bit wider/taller than the measured ink bbox (504-521, 1441-1462)
# to fully cover anti-aliased edges of the old "4", without touching the "$"
# (ends ~503) or the "." (starts ~524).
ERASE_BOX = (502, 1436, 524, 1466)  # (left, top, right, bottom)
INK_TARGET = (504, 1441)  # (x, y) top-left of the "8" ink bbox we want


def patch(in_path, out_path):
    im = Image.open(in_path).convert("RGB")
    draw = ImageDraw.Draw(im)

    # 1) erase the old "4"
    draw.rectangle(ERASE_BOX, fill=NAVY)

    # 2) draw new "8" aligned so its ink bbox starts at INK_TARGET
    font = ImageFont.truetype(FONT, FONT_SIZE)
    bbox = draw.textbbox((0, 0), "8", font=font)
    x0 = INK_TARGET[0] - bbox[0]
    y0 = INK_TARGET[1] - bbox[1]
    draw.text((x0, y0), "8", font=font, fill=CREAM)

    im.save(out_path, quality=95)


if __name__ == "__main__":
    patch(sys.argv[1], sys.argv[2])
    print("patched:", sys.argv[2])
