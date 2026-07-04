#!/usr/bin/env python3
"""
pick_shots.py <image_path>
Analyzes a pin image row-by-row for "content density" (text/graphics vs blank
background) and picks 3 shot windows (headline third / middle third / footer
third) that land on the densest, most content-full band within each third --
so a video "shot" never lands on blank whitespace.
Prints: y_frac1 y_frac2 y_frac3  (top edge of each shot, as a fraction of image height)
Each shot height is fixed at 0.36 of the image height (caller applies this).
"""
import sys
from PIL import Image
import numpy as np

SHOT_H_FRAC = 0.36

def row_density(im):
    gray = np.array(im.convert("L"), dtype=np.float32)
    # local row "content" score = std deviation of pixel values in that row
    # (blank/flat-color rows have near-zero std; text/graphic rows have high std)
    row_std = gray.std(axis=1)
    # smooth with a small moving average to avoid single-row noise
    k = max(3, im.height // 150)
    kernel = np.ones(k) / k
    smoothed = np.convolve(row_std, kernel, mode="same")
    return smoothed

def best_window(density, height, search_lo, search_hi, win_frac):
    win_h = int(height * win_frac)
    lo_px = int(height * search_lo)
    hi_px = int(height * search_hi) - win_h
    hi_px = max(hi_px, lo_px)
    best_y, best_score = lo_px, -1
    step = max(1, height // 300)
    for y in range(lo_px, hi_px + 1, step):
        score = density[y:y + win_h].sum()
        if score > best_score:
            best_score, best_y = score, y
    return best_y / height

def main():
    path = sys.argv[1]
    im = Image.open(path)
    h = im.height
    density = row_density(im)

    # search ranges per shot keep rough narrative order (top->bottom) while
    # allowing enough slack to dodge blank gaps within each third.
    # Shot 3 is pinned to the bottom-most content band directly rather than
    # density-searched: a density search over a wide lower range keeps
    # re-discovering the (denser) bullet list instead of the actual thin
    # price/CTA footer strip, which these pin templates consistently place
    # right at the bottom edge. Find the lowest contiguous dense band that
    # starts after 0.85 instead.
    FOOTER_H_FRAC = 0.075
    y1 = best_window(density, h, 0.00, 0.42, SHOT_H_FRAC)
    y2 = best_window(density, h, 0.28, 0.72, SHOT_H_FRAC)

    # Footer: center tightly on the single densest row in the bottom search
    # zone (the price/CTA text itself) rather than searching for a whole
    # dense "region" -- a region-walk gets fooled by faint background
    # texture/dots and stops too early, leaving a gap of blank space above
    # the actual text inside the crop. Centering on the peak row guarantees
    # the text sits in the middle of the shot.
    footer_lo = int(h * 0.85)
    footer_density = density[footer_lo:]
    peak_idx = footer_lo + (int(np.argmax(footer_density)) if footer_density.size else 0)
    peak_frac = peak_idx / h
    # bias the window so the text peak sits near the TOP of the crop (just a
    # sliver of headroom above it) rather than centered -- the blank gap on
    # these templates is always ABOVE the footer text, not below it (there's
    # nothing below the price band but the image's own bottom edge), so most
    # of the window should extend *below* the peak, not above it.
    y3 = max(0.0, peak_frac - FOOTER_H_FRAC * 0.12)
    y3 = min(y3, 1.0 - FOOTER_H_FRAC)

    # convert from SOURCE-image fraction to COMPOSITE (1080x1920) fraction --
    # the composite letterboxes the source (scaled to width 1080) vertically
    # centered inside the 1920-tall canvas, so a source y-fraction "f" maps to
    # composite pixel = top_margin + f * scaled_source_height.
    COMP_W, COMP_H = 1080, 1920
    scaled_h = COMP_W * (im.height / im.width)
    top_margin = (COMP_H - scaled_h) / 2
    def to_comp_frac(f):
        return (top_margin + f * scaled_h) / COMP_H

    y1c, y2c, y3c = to_comp_frac(y1), to_comp_frac(y2), to_comp_frac(y3)
    shot_h_comp_frac = (SHOT_H_FRAC * scaled_h) / COMP_H
    footer_h_comp_frac = (FOOTER_H_FRAC * scaled_h) / COMP_H

    # sample the footer's own background color (away from text, near the
    # left edge) so the pad color matches the band instead of guessing navy
    rgb_im = im.convert("RGB")
    sample_x = max(0, int(im.width * 0.04))
    sample_y = min(im.height - 1, peak_idx + int(FOOTER_H_FRAC * h * 0.3))
    r, g, b = rgb_im.getpixel((sample_x, sample_y))
    footer_color = f"0x{r:02x}{g:02x}{b:02x}"

    print(f"{y1c:.4f} {y2c:.4f} {y3c:.4f} {shot_h_comp_frac:.4f} {footer_h_comp_frac:.4f} {footer_color}")

if __name__ == "__main__":
    main()
