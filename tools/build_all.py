"""One-command DIY build for the Nukitashi 1 JP-restoration patch.

Usage:
  python tools/build_all.py <WESTERN_GAME_DIR> <JP_GAME_DIR> [NIP_PFS_069]

Produces dist/NUKITASHI.pfs.080 (official-English variant) and, if the
NIP archive is given (or found next to the game dir), dist/NUKITASHI.pfs.081
(Improvement-Patch-English variant). Deterministic: identical inputs give
byte-identical patches.

Steps: extract JP scripts + EN system/art sources -> inject ja text
(label-matched) -> generate button/keyboard art -> patch engine files ->
assemble archives.
"""
import glob
import os
import re
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
AN = os.path.join(ROOT, "analysis")
sys.path.insert(0, TOOLS)
from pfs import PfsArchive


def run(script, *args):
    subprocess.run([sys.executable, os.path.join(TOOLS, script), *args],
                   check=True)


def game_archives(game_dir, base):
    return [p for p in sorted(glob.glob(os.path.join(game_dir, base + "*")))
            if not re.search(r"\.pfs\.08\d$", p)]


def extract(archives, match, outroot, flatten_to=None):
    """Extract effective (last-wins, case-insensitive) files matching
    `match(lowname)`; flatten_to puts all files in one dir by basename."""
    best = {}
    for p in archives:
        a = PfsArchive(p)
        for e in a.entries:
            low = e.name.lower()
            if match(low):
                best[low] = (p, e.name)
        a.close()
    n = 0
    for low, (arc, name) in sorted(best.items()):
        a = PfsArchive(arc)
        data = a.read(name)
        a.close()
        if flatten_to:
            dest = os.path.join(outroot, flatten_to, low.split("\\")[-1])
        else:
            dest = os.path.join(outroot, low.replace("\\", os.sep))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        n += 1
    return n


def main(west, jp, nip=None):
    west_arcs = game_archives(west, "NUKITASHI.pfs")
    jp_arcs = game_archives(jp, "NUKITASHI.pfs")
    assert west_arcs and jp_arcs, "game archives not found"

    print("== extract JP scripts ==")
    n = extract(jp_arcs, lambda l: l.startswith("script\\") and l.endswith(".ast"),
                os.path.join(AN, "extracted_jp"), flatten_to="script")
    print(f"  {n} scripts")

    print("== extract EN system files ==")
    n = extract(west_arcs, lambda l: l.startswith("system\\"),
                os.path.join(AN, "extracted_en_sys"))
    print(f"  {n} files")

    print("== extract art sources ==")
    n = extract(west_arcs,
                lambda l: l.startswith("pc\\en\\config1\\bt_language"),
                AN, flatten_to="btn")
    n += extract(west_arcs,
                 lambda l: l.startswith("pc\\en\\mw\\bt_"),
                 AN, flatten_to="mwbtn")
    os.makedirs(os.path.join(AN, "kb"), exist_ok=True)
    kbsrc = os.path.join(AN, "kb", "setting__keyboard_en.png")
    for p in west_arcs:
        a = PfsArchive(p)
        for e in a.entries:
            if e.name.lower() == "pc\\en\\config5\\setting__keyboard.png":
                with open(kbsrc, "wb") as f:
                    f.write(a.read(e))
        a.close()
    assert os.path.exists(kbsrc)
    print(f"  {n} buttons + keyboard")

    print("== inject ja (official) ==")
    run("inject_ja.py", west, os.path.join(AN, "extracted_jp", "script"),
        os.path.join(AN, "ja_inject", "script"))

    print("== art ==")
    run("make_button.py")
    run("make_langbtn.py")
    run("edit_keyboard.py")

    print("== ja asset restore ==")
    run("ja_assets.py", jp, "--restore")

    print("== engine patches ==")
    run("patch_system.py")
    for lang in ("en", "cn", "tw", "ja"):
        run("patch_tbl.py",
            os.path.join(AN, "extracted_en_sys", "system", "table",
                         f"list_windows_{lang}.tbl"),
            os.path.join(AN, "patched_tbl", f"list_windows_{lang}.tbl"))

    print("== build .080 ==")
    run("build_patch.py", os.path.join(AN, "ja_inject", "script"),
        os.path.join(ROOT, "dist", "NUKITASHI.pfs.080"))

    if nip is None:
        cand = glob.glob(os.path.join(os.path.dirname(west.rstrip("\\/")),
                                      "*", "NUKITASHI.pfs.069"))
        nip = cand[0] if cand else None
    if nip and os.path.exists(nip):
        print("== inject ja (NIP) + build .081 ==")
        run("inject_ja.py", west, os.path.join(AN, "extracted_jp", "script"),
            os.path.join(AN, "ja_inject_nip", "script"), nip)
        run("build_patch.py", os.path.join(AN, "ja_inject_nip", "script"),
            os.path.join(ROOT, "dist", "NUKITASHI.pfs.081"))
    else:
        print("== NIP archive not found; skipping .081 ==")

    print("done.")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
