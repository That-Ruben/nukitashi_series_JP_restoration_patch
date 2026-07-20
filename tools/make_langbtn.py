"""Generate the hover-menu "JP" mini-button sprite (mw/bt_lang.png).

Matches the row's sprite convention (sampled from bt_mute): 4 stacked
state cells, 36x29 at 31px pitch — white (normal), orange 255,79,20
(hover), orange (on: stays lit while the game is in Japanese), gray
127,127,127 (disabled) — each glyph with the row's dark contour.

Usage: python make_langbtn.py  -> analysis/bt_lang.png
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfs import PfsArchive

AN = os.path.join(ROOT, "analysis")
CELL_W, CELL_H, PITCH = 36, 29, 31
TEXT = "JP"
STATES = [((255, 255, 255, 255), (35, 24, 21, 255)),
          ((255, 79, 20, 255), (35, 24, 21, 255)),
          ((255, 79, 20, 255), (35, 24, 21, 255)),
          ((127, 127, 127, 255), (17, 11, 10, 255))]


def get_font():
    dest = os.path.join(AN, "fonts", "rounded-x-mgenplus-1p-bold.ttf")
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        a = PfsArchive(os.path.join(ROOT, "NUKITASHI", "NUKITASHI.pfs"))
        e = next(e for e in a.entries
                 if e.name.lower().endswith("rounded-x-mgenplus-1p-bold.ttf"))
        with open(dest, "wb") as f:
            f.write(a.read(e))
        a.close()
    return dest


def sprite(text, font, out_name):
    im = Image.new("RGBA", (CELL_W, PITCH * 3 + CELL_H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    probe = Image.new("L", (100, 60), 0)
    ImageDraw.Draw(probe).text((10, 10), text, font=font, fill=255)
    b = probe.getbbox()
    tw, th = b[2] - b[0], b[3] - b[1]
    for i, (fill, contour) in enumerate(STATES):
        y0 = i * PITCH
        x = CELL_W / 2 - tw / 2 - (b[0] - 10)
        y = y0 + CELL_H / 2 - th / 2 - (b[1] - 10) - 1   # optical align (Ruben)
        d.text((x, y), text, font=font, fill=fill,
               stroke_width=2, stroke_fill=contour)
    out = os.path.join(AN, out_name)
    im.save(out)
    print("wrote", out)


def main():
    sprite(TEXT, ImageFont.truetype(get_font(), 22), "bt_lang.png")
    # dual-language toggle: "&" as in EN&JP (II looked like a pause button
    # next to the auto/play icons — Ruben)
    sprite("&", ImageFont.truetype(get_font(), 24), "bt_sublang.png")


if __name__ == "__main__":
    main()
