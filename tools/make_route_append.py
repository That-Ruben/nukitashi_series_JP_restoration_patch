"""Build the Japanese art for Nukitashi 2's append route-select screen.

The screen New Game opens is drawn from `ui_route_append` (western
list_windows_*.tbl) whenever the append/DLC content is installed, and every
one of its nine sprites lives under `pc/<ui language>/route/append/`.
Shiravune shipped that folder for en, cn and tw only - `pc/ja/route/append/`
does not exist in the western build at all. With the UI in Japanese the
background and all seven route buttons therefore fail to load and New Game
lands on a black screen (Esc still backs out; the EXIT key is bound).

The Japanese release does have this screen, in `pc/ja/route/` (its .014
append archive overwrites the six-button base screen with the seven-button
one), at the same 1600x900 layout and the same 448x252 button tiles. The
only difference is the state-strip pitch: JP stacks the states 254px apart
(clip rows 0/254/508/762), the western re-export 252px apart (0/252/504/756).
The 2px gutters are fully transparent, so re-tiling is pixel-exact.

Row order matches on both sides: 0 = normal, 1 = hover, 2 = disabled. Only
bt_route06 (Asane) and bt_route07 (Susuko) carry a disabled row, which is
exactly what route_init() greys out before a route is cleared; the western
files pad the other five to the same height with a transparent row, and so
do we.

Usage: python make_route_append.py [JP_GAME_DIR]
  writes analysis/ja_route2/pc/ja/route/append/*.png
"""
import glob
import io
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfs import PfsArchive

JP_DEFAULT = r"O:\Games\nukitashigames\remastered2"
OUT = os.path.join(ROOT, "analysis", "ja_route2", "pc", "ja", "route", "append")

JP_PITCH, WEST_PITCH, TILE_H, TILE_W = 254, 252, 252, 448
WEST_ROWS = 3           # western strip height 756 = 3 * 252
BUTTONS = [f"bt_route{i:02d}" for i in range(1, 8)]


def effective(jp_dir):
    best = {}
    for p in sorted(glob.glob(os.path.join(jp_dir, "NUKITASHI2.pfs*"))):
        a = PfsArchive(p)
        for e in a.entries:
            best[e.name.lower()] = (p, e.name)
        a.close()
    return best


def read(best, name):
    arc, real = best[name]
    a = PfsArchive(arc)
    data = a.read(real)
    a.close()
    return data


def main(jp_dir=JP_DEFAULT):
    best = effective(jp_dir)
    os.makedirs(OUT, exist_ok=True)

    bg = read(best, "pc\\ja\\route\\bg.png")
    im = Image.open(io.BytesIO(bg))
    assert im.size == (1600, 900), f"unexpected JP route bg size {im.size}"
    with open(os.path.join(OUT, "bg.png"), "wb") as f:
        f.write(bg)                      # verbatim, no re-encode
    print(f"  bg.png {im.size} (copied)")

    for name in BUTTONS:
        src = Image.open(io.BytesIO(
            read(best, f"pc\\ja\\route\\{name}.png"))).convert("RGBA")
        assert src.width == TILE_W, f"{name}: width {src.width}"
        assert src.height % JP_PITCH == 0, f"{name}: height {src.height}"
        rows = src.height // JP_PITCH
        assert 0 < rows <= WEST_ROWS, f"{name}: {rows} state rows"

        out = Image.new("RGBA", (TILE_W, WEST_PITCH * WEST_ROWS), (0, 0, 0, 0))
        for k in range(rows):
            tile = src.crop((0, k * JP_PITCH, TILE_W, k * JP_PITCH + TILE_H))
            gutter = src.crop((0, k * JP_PITCH + TILE_H,
                               TILE_W, min((k + 1) * JP_PITCH, src.height)))
            assert not gutter.getbbox() or max(gutter.split()[3]
                                               .getextrema()) == 0, \
                f"{name}: gutter after row {k} is not transparent"
            out.paste(tile, (0, k * WEST_PITCH))
        out.save(os.path.join(OUT, f"{name}.png"))
        print(f"  {name}.png {src.size} -> {out.size} ({rows} state rows)")

    print(f"wrote {len(BUTTONS) + 1} files under {OUT}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else JP_DEFAULT)
