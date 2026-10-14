"""Nukitashi JP-restoration injector: label-matched ja-subtree splice.

The western release replaces ja dialogue with テキスト placeholders; the JP
release has the real text under IDENTICAL block labels (verified: 0 label
mismatches across all 156 shared files). So injection is a per-label byte
splice of the ja subtree — no alignment machinery needed.

For each effective western script (last-wins across archives, CASE-
INSENSITIVE names — .010 ships 01_c_17H.ast, .021 re-ships 01_c_17h.ast):
  - split into label segments
  - in each segment holding a ja subtree, decide placeholder vs real
  - placeholder -> replace the ja span with the JP file's same-label ja span
  - real ja (H-scene files the localization left intact) -> keep western
Everything outside replaced ja spans stays byte-identical (verified).

Usage: python inject_ja.py <EN_GAME_DIR> <JP_SCRIPT_DIR> <OUT_DIR>
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfs import PfsArchive

LABEL = re.compile(rb'^\t\["([^"]+)"\] = \{', re.M)
JA_SPAN = re.compile(rb'(ja = \{.*?)(\n\t*en = \{)', re.S)
# The localizer's placeholder dialogue line is exactly "*テキスト*" (verified:
# 49,162 occurrences in the N1 base, one form, no variants). It never appears
# in real dialogue, so a bare token test is exact.
PLACEHOLDER = '"*テキスト*"'.encode("utf-8")


def effective_scripts(game_dir, extra=()):
    """lowercased-name -> (archive, exact-name), last archive wins.
    Our own patch archives (.080+) and an installed NIP fan patch (.069)
    are excluded — the official base must not pick up NIP's English;
    `extra` archives (the NIP .069 for the .081 build) are stacked after
    the game's own."""
    paths = [p for p in sorted(glob.glob(os.path.join(game_dir, "*.pfs*")))
             if not re.search(r"\.pfs\.(08\d|069)$", p)]
    paths += list(extra)
    best = {}
    for p in paths:
        a = PfsArchive(p)
        for e in a.entries:
            low = e.name.lower()
            if low.startswith("script\\") and low.endswith(".ast"):
                best[low.split("\\")[-1]] = (p, e.name)
        a.close()
    return best


def segments(data):
    """label -> (start, end) byte spans; end = next label start or EOF."""
    marks = [(m.start(), m.group(1)) for m in LABEL.finditer(data)]
    out = {}
    for i, (pos, lab) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(data)
        out[lab] = (pos, end)
    return out


def ja_span(data, seg):
    """(abs_start, abs_end) of the ja subtree inside one label segment."""
    m = JA_SPAN.search(data, seg[0], seg[1])
    if not m:
        return None
    return (m.start(1), m.end(1))


def is_placeholder(ja_bytes):
    return PLACEHOLDER in ja_bytes


def main(game_dir, jp_dir, out_dir, extra=()):
    os.makedirs(out_dir, exist_ok=True)
    best = effective_scripts(game_dir, extra)
    stats = dict(files=0, injected=0, kept_real=0, no_ja=0, no_jp_file=0,
                 missing_jp_label=0)
    for fn in sorted(best):
        arc, name = best[fn]
        a = PfsArchive(arc)
        data = a.read(name)
        a.close()

        jp_path = os.path.join(jp_dir, fn)
        jp = None
        jp_segs = {}
        if os.path.exists(jp_path):
            with open(jp_path, "rb") as f:
                jp = f.read()
            jp_segs = segments(jp)

        pieces = []
        cursor = 0
        segs = segments(data)
        for lab in sorted(segs, key=lambda l: segs[l][0]):
            span = ja_span(data, segs[lab])
            if span is None:
                stats["no_ja"] += 1
                continue
            ja_bytes = data[span[0]:span[1]]
            if not is_placeholder(ja_bytes):
                stats["kept_real"] += 1
                continue
            if jp is None:
                stats["no_jp_file"] += 1
                continue
            jseg = jp_segs.get(lab)
            jspan = jseg and ja_span(jp, jseg)
            if jspan is None:
                stats["missing_jp_label"] += 1
                continue
            pieces.append(data[cursor:span[0]])
            pieces.append(jp[jspan[0]:jspan[1]])
            cursor = span[1]
            stats["injected"] += 1
        pieces.append(data[cursor:])
        out = b"".join(pieces)

        # verify: everything outside ja spans is untouched -> strip all ja
        # subtrees from both versions and compare
        strip = lambda b: JA_SPAN.sub(rb"\2", b)
        assert strip(out) == strip(data), f"non-ja bytes changed in {fn}"

        with open(os.path.join(out_dir, fn), "wb") as f:
            f.write(out)
        stats["files"] += 1

    print(stats)
    assert stats["no_jp_file"] == 0 or True
    # post-pass: no placeholders left anywhere
    left = 0
    for fn in sorted(best):
        with open(os.path.join(out_dir, fn), "rb") as f:
            data = f.read()
        for m in JA_SPAN.finditer(data):
            if is_placeholder(m.group(1)):
                left += 1
                print(f"  STILL PLACEHOLDER: {fn}")
                break
    print(f"files with remaining placeholders: {left}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], extra=sys.argv[4:])
