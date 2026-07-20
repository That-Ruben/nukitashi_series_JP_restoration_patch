"""Audit western pc/ja UI assets against the authentic JP release (N2).

Same hash rule as N1's ja_assets.py: a western ja asset is 'anglicized'
when its bytes equal the western en/cn/tw asset at the same path while the
JP release has a different file there. Report only — restoration is a
reviewed, explicit step (HENPRI lesson: byte-equality across languages can
be by design for functional art).

Usage: python ja_assets2.py [JP_GAME_DIR] [--restore]
  (restore writes analysis/ja_restore2)
"""
import glob
import hashlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfs import PfsArchive

WEST = os.path.join(ROOT, "NUKITASHI 2")
_dirs = [a for a in sys.argv[1:] if a != "--restore"]
JP = _dirs[0] if _dirs else r"O:\Games\nukitashigames\remastered2"

# The JP release kept the ORIGINAL UI tree (pc/ja/adv, flat config/,
# scenario/) while the western remaster rebuilt it (config1-5, blog bt_*,
# scenario1) — only 54 paths are shared, so most anglicized files have no
# same-layout JP source and are left alone (the remaster's ja art simply
# never existed in Japanese).
#
# Not restored (reviewed 2026-07-20):
# - mw/choice.png: plain orange bar, no language content; JP copy is 1px
#   narrower (769 vs 770) — same clip-mismatch risk as in N1.
# - save/bt_data.png, bt_delete.png, new.png: JP slot art is 2-4px smaller
#   AND has the "save here" hover with "No data" still visible underneath
#   that looked broken in N1 (Ruben tested); western versions behave.
EXCLUDES = {
    "pc\\ja\\mw\\choice.png",
    "pc\\ja\\save\\bt_data.png",
    "pc\\ja\\save\\bt_delete.png",
    "pc\\ja\\save\\new.png",
}


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
    west_ja = effective(os.path.join(WEST, "root.pfs*"), "pc\\ja\\")
    jp_ja = effective(os.path.join(JP, "NUKITASHI2.pfs*"), "pc\\ja\\")
    west_other = {l: effective(os.path.join(WEST, "root.pfs*"),
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
        outroot = os.path.join(ROOT, "analysis", "ja_restore2")
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
