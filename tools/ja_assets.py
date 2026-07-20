"""Audit western pc/ja UI assets against the authentic JP release (N1).

A western ja asset is 'anglicized' when its bytes equal the western
en/cn/tw asset at the same path while the JP release has a different file
there. Report only — restoration is a reviewed, explicit step (HENPRI
lesson: byte-equality across languages can be by design for functional
art; blindly restoring the JP file broke backlog portraits there).

Usage: python ja_assets.py [--restore]   (restore writes analysis/ja_restore)
"""
import glob
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfs import PfsArchive

WEST = os.path.join(ROOT, "NUKITASHI")
_dirs = [a for a in sys.argv[1:] if a != "--restore"]
JP = _dirs[0] if _dirs else r"O:\Games\nukitashigames\remastered1"

# Not restored (reviewed 2026-07-20):
# - mw/choice.png: plain orange bar, no language content; JP copy is 1px
#   narrower (769 vs 770) — same clip-mismatch risk as the mw icons.
# - save/bg.png: west is 1610x910 (oversize for pan?) vs JP 1600x900, and
#   west deliberately uses night art to distinguish save from load.
# - save/bg2.png: kept west to stay consistent with bg.png's pairing.
# - save/bt_data.png, bt_delete.png, new.png: JP slot art shows "save
#   here" on hover but the "No data" underneath stays visible — looks
#   broken in-game (Ruben tested); western versions behave better.
# - title/start_*.png: character art, no language content; west copies are
#   a color re-grade of the same-dimension JP art — aesthetic revision,
#   not anglicization (pending Ruben's call).
EXCLUDES = {
    "pc\\ja\\mw\\choice.png",
    "pc\\ja\\save\\bg.png",
    "pc\\ja\\save\\bg2.png",
    "pc\\ja\\save\\bt_data.png",
    "pc\\ja\\save\\bt_delete.png",
    "pc\\ja\\save\\new.png",
} | {f"pc\\ja\\title\\start_{c}.png" for c in
     ("fumino", "hinami", "ikuko", "jun", "misaki", "nanase", "rei", "toka")}


def effective(dirpat, prefix):
    best = {}
    for p in sorted(glob.glob(dirpat)):
        if re.search(r"\.pfs\.08\d$", p):
            continue
        a = PfsArchive(p)
        for e in a.entries:
            low = e.name.lower()
            if low.startswith(prefix):
                best[low] = (p, e.name)
        a.close()
    return best


def read_one(t):
    a = PfsArchive(t[0])
    d = a.read(t[1])
    a.close()
    return d


def main(restore=False):
    west_ja = effective(os.path.join(WEST, "NUKITASHI.pfs*"), "pc\\ja\\")
    jp_ja = effective(os.path.join(JP, "NUKITASHI.pfs*"), "pc\\ja\\")
    west_other = {l: effective(os.path.join(WEST, "NUKITASHI.pfs*"),
                               f"pc\\{l}\\") for l in ("en", "cn", "tw")}

    n = dict(total=len(west_ja), anglicized=0, restorable=0, jp_missing=0,
             distinct_ok=0, jp_same=0)
    restorable = []
    for path, t in sorted(west_ja.items()):
        if path in EXCLUDES:
            n["distinct_ok"] += 1
            continue
        data = read_one(t)
        h = hashlib.md5(data).hexdigest()
        angl = False
        for l in ("en", "cn", "tw"):
            o = west_other[l].get(path.replace("\\ja\\", f"\\{l}\\"))
            if o and hashlib.md5(read_one(o)).hexdigest() == h:
                angl = True
                break
        if not angl:
            n["distinct_ok"] += 1
            continue
        n["anglicized"] += 1
        jp = jp_ja.get(path)
        if jp is None:
            n["jp_missing"] += 1
            print(f"ANGLICIZED, no JP source: {path}")
            continue
        jdata = read_one(jp)
        if hashlib.md5(jdata).hexdigest() == h:
            n["jp_same"] += 1
            continue
        n["restorable"] += 1
        restorable.append((path, jdata))
        print(f"RESTORE: {path}  ({len(data)} -> {len(jdata)} bytes)")

    print("\n== summary ==")
    for k, v in n.items():
        print(f"{k:12} {v}")

    if restore:
        outroot = os.path.join(ROOT, "analysis", "ja_restore")
        import shutil
        if os.path.isdir(outroot):
            shutil.rmtree(outroot)   # no stale files from earlier runs
        for path, jdata in restorable:
            dest = os.path.join(outroot, path.replace("\\", os.sep))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(jdata)
        print(f"wrote {len(restorable)} files under {outroot}")


if __name__ == "__main__":
    main(restore="--restore" in sys.argv)
