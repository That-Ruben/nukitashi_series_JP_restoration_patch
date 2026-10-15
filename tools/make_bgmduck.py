"""Add a "lower music during voice" label row to the Sound config tab art.

pc/<lang>/config3/sound_bg.png holds the label column of the Sound tab:
seven rows, 50px tall, every 62px (y=0..418). The image is 482px tall, so
an eighth row fits exactly at y=431. The row is cloned from the "Click to
stop voice" row, its text erased, and the new label drawn in a font matched
to the original artwork (the game doesn't ship the label fonts):

  en: Calibri Regular 28 (the font of the original labels; ink width
      201 px vs the original "Click to stop voice" 203 px)
  ja: Noto Sans JP, weight 400, size 23

The YES/NO buttons for the row are added to the tbl by patch_tbl.py.

Usage: python make_bgmduck.py SRC_ROOT OUT_ROOT
  SRC_ROOT contains pc/{en,ja}/config3/sound_bg.png (extracted by build_all)
"""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = "C:/Windows/Fonts"
LABEL = {"en": "Lower music during voice", "ja": "ボイス再生時にBGMを下げる"}
REF = {"en": "Click to stop voice", "ja": "クリックでボイスを停止"}
ROW_SRC, ROW_DST, ROW_H = 369, 431, 50
CELL_W = 398                         # label cell is x=0..397
CELL_RGBA = (255, 255, 255, 229)
SC = 4                               # supersampling factor


def font(lang):
    if lang == "en":
        f = ImageFont.truetype(os.path.join(FONTS, "calibri.ttf"), 28 * SC)
        assert f.getname() == ("Calibri", "Regular"), f.getname()
        return f
    f = ImageFont.truetype(os.path.join(FONTS, "NotoSansJP-VF.ttf"), 23 * SC)
    f.set_variation_by_axes([400])
    return f


def ink(lang, txt):
    """Coverage mask of txt at 1x, drawn at SC x and downsampled."""
    F = font(lang)
    # en: the original labels set Calibri tighter inside words (stop = 44px
    # vs Calibri's 47) but with wider word gaps
    stroke = 0
    track, space = (-0.6, 1.0) if lang == "en" else (0.0, 0.0)
    im = Image.new("L", (600 * SC, 60 * SC), 0)
    d = ImageDraw.Draw(im)
    x = 10 * SC
    for ch in txt:
        d.text((x, 10 * SC), ch, font=F, fill=255,
               stroke_width=stroke, stroke_fill=255)
        x += F.getlength(ch) + (space if ch == " " else track) * SC
    return im.resize((600, 60), Image.LANCZOS)


def bbox(mask, t=60):
    ys, xs = np.where(np.asarray(mask) > t)
    return xs.min(), ys.min(), xs.max(), ys.max()


def make(lang, src, dst):
    im = Image.open(src).convert("RGBA")
    assert im.height >= ROW_DST + ROW_H, im.size
    a = np.asarray(im)
    # ja has an invisible 1px residue line (alpha <= 3) at y=431
    assert a[ROW_DST:ROW_DST + ROW_H, :, 3].max() <= 3, \
        "target row area is not empty"
    # where the original label's ink starts, so the new text lines up
    cell = a[ROW_SRC:ROW_SRC + ROW_H, :CELL_W].astype(float)
    m = (255 - cell[:, :, :3].mean(2)) * (cell[:, :, 3] / 255)
    ys, xs = np.where(m > 60)
    ox, oy = xs.min(), ys.min()

    row = im.crop((0, ROW_SRC, CELL_W, ROW_SRC + ROW_H))
    ImageDraw.Draw(row).rectangle((ox - 4, 2, CELL_W - 2, ROW_H - 3),
                                  fill=CELL_RGBA)
    rx, ry, _, _ = bbox(ink(lang, REF[lang]))
    g = ink(lang, LABEL[lang])
    black = Image.new("RGBA", g.size, (0, 0, 0, 255))
    black.putalpha(g)
    row.alpha_composite(black, (int(ox - rx), int(oy - ry)))
    gx0, _, gx1, _ = bbox(g)
    assert ox + (gx1 - gx0) < CELL_W - 4, "label too wide for the cell"

    im.paste(row, (0, ROW_DST))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    im.save(dst)
    print(f"wrote {dst}")


def main(src_root, out_root):
    for lang in ("en", "ja"):
        rel = os.path.join("pc", lang, "config3", "sound_bg.png")
        make(lang, os.path.join(src_root, rel), os.path.join(out_root, rel))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
