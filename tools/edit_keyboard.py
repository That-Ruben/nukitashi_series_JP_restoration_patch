"""Add L / K hotkey legend rows to the EN keyboard-help screen.

pc/en/config5/setting__keyboard.png (1205x684): three legend columns; the
right column ends with 'Rotate down Wheel' and its separator at y~597,
leaving free space below — two single-line rows fit there.

Style matched from the art itself: separator rows are copied pixel-for-
pixel from an existing one; key names orange bold, descriptions dark with
【ADV】 tags (game's own fonts). EN image only for now (Ruben's call).

Usage: python edit_keyboard.py -> analysis/kb_edit/pc/en/config5/...
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfs import PfsArchive

AN = os.path.join(ROOT, "analysis")
SRC = os.path.join(AN, "kb", "setting__keyboard_en.png")

KEY_X, DESC_X = 820, 934
# home-row keycaps (borders detected at y=205): K=(500,545), L=(555,600);
# bound-key letters (like A/S) are ink-aligned at cap_left+4, ink top y=189
KEYCAPS = {"K": 500, "L": 555}
CAP_INK_Y = 189
SEP_X0, SEP_X1 = 795, 1180
SEP_SRC_Y = 597          # existing separator under 'Rotate down Wheel'
ROWS = [                 # (text top y, key, description)
    (608, "L", "【ADV】 Switch language (JP/EN)"),
    (641, "K", "【ADV】 Toggle dual language display"),
]
SEP_YS = [630, 663]


def get_font(name):
    dest = os.path.join(AN, "fonts", name)
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        a = PfsArchive(os.path.join(ROOT, "NUKITASHI", "NUKITASHI.pfs"))
        e = next(e for e in a.entries if e.name.lower().endswith(name))
        with open(dest, "wb") as f:
            f.write(a.read(e))
        a.close()
    return dest


def sample_colors(im):
    px = im.load()
    # orange from 'Rotate down Wheel' glyphs (~y=568), dark from its desc
    best_o, best_d = None, None
    for y in range(560, 580):
        for x in range(820, 930):
            r, g, b, a = px[x, y]
            if a > 200 and r > 180 and g < 140 and b < 110:
                best_o = (r, g, b, 255)
    for y in range(520, 545):
        for x in range(945, 1100):
            r, g, b, a = px[x, y]
            if a > 200 and r < 110 and g < 110 and b < 110:
                best_d = (r, g, b, 255)
    return best_o or (237, 90, 40, 255), best_d or (60, 60, 60, 255)


def main():
    im = Image.open(SRC).convert("RGBA")
    orange, dark = sample_colors(im)
    print("colors:", orange, dark)

    sep = im.crop((SEP_X0, SEP_SRC_Y - 1, SEP_X1, SEP_SRC_Y + 2))
    for y in SEP_YS:
        im.paste(sep, (SEP_X0, y - 1))

    fkey = ImageFont.truetype(get_font("sourcehansans-bold.otf"), 15)
    fdesc = ImageFont.truetype(get_font("sourcehansans-medium.otf"), 14)
    d = ImageDraw.Draw(im)
    for y, key, desc in ROWS:
        d.text((KEY_X, y), key, font=fkey, fill=orange)
        d.text((DESC_X, y), desc, font=fdesc, fill=dark)

    # orange letters on the K/L keycaps (ink-aligned like the A/S keys)
    for ch, cap_x in KEYCAPS.items():
        probe = Image.new("L", (60, 60), 0)
        ImageDraw.Draw(probe).text((10, 10), ch, font=fkey, fill=255)
        b = probe.getbbox()
        d.text((cap_x + 4 - (b[0] - 10), CAP_INK_Y - (b[1] - 10)),
               ch, font=fkey, fill=orange)

    # discreet credit, bottom-right corner
    fcred = ImageFont.truetype(get_font("sourcehansans-medium.otf"), 11)
    credit = "JP patch by That-Ruben"
    cb = d.textbbox((0, 0), credit, font=fcred)
    d.text((1198 - (cb[2] - cb[0]), 682 - (cb[3] - cb[1]) - 2),
           credit, font=fcred, fill=(150, 150, 150, 255))

    out = os.path.join(AN, "kb_edit", "pc", "en", "config5",
                       "setting__keyboard.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.save(out)
    print("wrote", out)


if __name__ == "__main__":
    main()
