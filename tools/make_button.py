"""Generate pc/<lang>/config1/bt_language_ja.png for Nukitashi.

Template: the game's own bt_language_cn.png (143x156, three 52px rows:
white/black normal, cyan/white selected, cyan/white hover). The cn glyphs
are erased from the central text area and 日本語 is rendered in the game's
own Source Han Sans Medium, size-tuned so the ink height matches the cn
glyphs (22px, ink center y ~23.5 per row).

Usage: python make_button.py  -> analysis/bt_language_ja.png
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfs import PfsArchive

AN = os.path.join(ROOT, "analysis")
TEXT = "日本語"
ROW_H = 52
TEXT_AREA = (6, 4, 137, 48)   # per-row central area (glyphs live here)


def get_font():
    dest = os.path.join(AN, "fonts")
    path = os.path.join(dest, "sourcehansans-medium.otf")
    if not os.path.exists(path):
        os.makedirs(dest, exist_ok=True)
        a = PfsArchive(os.path.join(ROOT, "NUKITASHI", "NUKITASHI.pfs"))
        e = next(e for e in a.entries
                 if e.name.lower().endswith("sourcehansans-medium.otf"))
        with open(path, "wb") as f:
            f.write(a.read(e))
        a.close()
    return path


def ink_bbox(font, text):
    im = Image.new("L", (400, 120), 0)
    d = ImageDraw.Draw(im)
    d.text((20, 20), text, font=font, fill=255)
    return im.getbbox()


def main():
    fpath = get_font()
    # tune size for 22px ink height
    size, best = None, None
    for s in range(20, 34):
        f = ImageFont.truetype(fpath, s)
        b = ink_bbox(f, TEXT)
        h = b[3] - b[1]
        if best is None or abs(h - 22) < best[0]:
            best = (abs(h - 22), s, h)
    size = best[1]
    font = ImageFont.truetype(fpath, size)
    print(f"font size {size} (ink height {best[2]})")

    im = Image.open(os.path.join(AN, "btn", "bt_language_cn.png")).convert("RGBA")
    px = im.load()
    d = ImageDraw.Draw(im)
    for row in range(3):
        y0 = row * ROW_H
        bg = px[10, y0 + 26]
        d.rectangle([TEXT_AREA[0], y0 + TEXT_AREA[1],
                     TEXT_AREA[2], y0 + TEXT_AREA[3]], fill=bg)
        color = (0, 0, 0, 255) if row == 0 else (255, 255, 255, 255)
        # ink-align: center x=71.5, ink center y = y0+23.5
        b = ink_bbox(font, TEXT)
        tw, th = b[2] - b[0], b[3] - b[1]
        # ink_bbox coords are relative to a draw at (20,20): the pen position
        # that puts ink-left at X is X - (b[0]-20), same for Y
        d.text((71.5 - tw / 2 - (b[0] - 20), y0 + 23.5 - th / 2 - (b[1] - 20)),
               TEXT, font=font, fill=color)
    out = os.path.join(AN, "bt_language_ja.png")
    im.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
