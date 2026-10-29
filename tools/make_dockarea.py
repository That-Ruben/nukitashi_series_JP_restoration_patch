"""Hover-menu hit masks (both games).

The auto-hide menu uses two invisible layers whose hit area is their image
(alpha >= 128): dockarea (mw/dockarea64, 1600x64 at y=836) opens the menu,
dockarea2 (mw/base, 1080x32 at x=360 y=868) is where the close timer counts
the cursor as "still on the menu". The right-side Save/Load column
(x=1520, y=541-858) is in neither, so the menu closed under the cursor.
These L-shaped masks keep the stock bottom strips and add that column.
patch_tbl.py points both tbl entries at them (x/y/w/h below).
"""
import os
from PIL import Image

AN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  "analysis")
OUT = os.path.join(AN, "dockarea")

TOP = 541          # top of the right column (N2 bt_save; N1 starts at 546)
COL_X = 1520       # left edge of the right column
SCREEN_W, SCREEN_H = 1600, 900

# name: (x, y, bottom strip height, bottom strip x-start)
MASKS = {
    "dockarea_l": (0, TOP, 64, 0),        # opener: stock 64px strip + column
    "dockarea2_l": (360, TOP, 32, 360),   # keep-open: stock 32px strip + column
}


def make(x, y, strip_h, strip_x):
    w, h = SCREEN_W - x, SCREEN_H - y
    im = Image.new("RGBA", (w, h), (255, 255, 255, 0))
    im.paste((255, 255, 255, 255), (strip_x - x, h - strip_h, w, h))
    im.paste((255, 255, 255, 255), (COL_X - x, 0, w, h))
    return im


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, args in MASKS.items():
        im = make(*args)
        im.save(os.path.join(OUT, f"{name}.png"), optimize=True)
        print(f"wrote {name}.png {im.size} at x={args[0]} y={args[1]}")
