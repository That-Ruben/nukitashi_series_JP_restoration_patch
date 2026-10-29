"""One-command DIY build for the Nukitashi 2 JP-restoration patch.

Usage:
  python tools/build_all2.py <WESTERN_GAME_DIR> <JP_GAME_DIR> [NIP2_PFS]

Produces dist/root.pfs.080 (official-English variant) and, if the NIP2
archive is given (or found next to the game dir), dist/root.pfs.081
(Improvement-Patch-English variant). Deterministic: identical inputs give
byte-identical patches.

The art generators (make_button/make_langbtn/edit_keyboard) read the N1
extraction dirs; every N2 art source is byte-identical to N1's, so this
script seeds those dirs from N2's own archives when absent and asserts
equality when present — an N2-only user needs no N1 files.
"""
import glob
import hashlib
import os
import re
import shutil
import subprocess
import sys

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)
AN = os.path.join(ROOT, "analysis")
sys.path.insert(0, TOOLS)
from pfs import PfsArchive

FONTS = ("sourcehansans-medium.otf", "sourcehansans-bold.otf",
         "rounded-x-mgenplus-1p-bold.ttf")


def run(script, *args):
    subprocess.run([sys.executable, os.path.join(TOOLS, script), *args],
                   check=True)


def game_archives(game_dir, base):
    return [p for p in sorted(glob.glob(os.path.join(game_dir, base + "*")))
            if not re.search(r"\.pfs\.(08\d|069)$", p)]


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


def seed(src, dst):
    """Copy src -> dst if absent; if present, assert byte equality (the
    generators consume dst — a silent divergence would ship stale art)."""
    if not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
        return
    h = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
    assert h(src) == h(dst), f"N2 art source diverged from N1: {dst}"


def main(west, jp, nip=None):
    west_arcs = game_archives(west, "root.pfs")
    jp_arcs = game_archives(jp, "NUKITASHI2.pfs")
    assert west_arcs and jp_arcs, "game archives not found"

    print("== extract JP scripts ==")
    n = extract(jp_arcs, lambda l: l.startswith("script\\") and l.endswith(".ast"),
                os.path.join(AN, "extracted_jp2"), flatten_to="script")
    print(f"  {n} scripts")

    print("== extract EN system files ==")
    n = extract(west_arcs, lambda l: l.startswith("system\\"),
                os.path.join(AN, "extracted_en2_sys"))
    print(f"  {n} files")

    print("== extract art sources ==")
    n = extract(west_arcs,
                lambda l: l.startswith("pc\\en\\config1\\bt_language"),
                AN, flatten_to="btn2")
    n += extract(west_arcs,
                 lambda l: l.startswith("pc\\en\\mw\\bt_"),
                 AN, flatten_to="mwbtn2")
    n += extract(west_arcs,
                 lambda l: l in ["font\\" + f for f in FONTS]
                 or l in ["font\\hp\\" + f for f in FONTS],
                 AN, flatten_to="fonts_n2")
    kbsrc = os.path.join(AN, "kb2", "setting__keyboard_en.png")
    os.makedirs(os.path.dirname(kbsrc), exist_ok=True)
    for p in west_arcs:
        a = PfsArchive(p)
        for e in a.entries:
            if e.name.lower() == "pc\\en\\config5\\setting__keyboard.png":
                with open(kbsrc, "wb") as f:
                    f.write(a.read(e))
        a.close()
    assert os.path.exists(kbsrc)
    print(f"  {n} buttons/fonts + keyboard")

    print("== seed shared generator inputs (byte-identical to N1) ==")
    for lang in ("en", "cn", "tw"):
        seed(os.path.join(AN, "btn2", f"bt_language_{lang}.png"),
             os.path.join(AN, "btn", f"bt_language_{lang}.png"))
    seed(kbsrc, os.path.join(AN, "kb", "setting__keyboard_en.png"))
    for f in FONTS:
        seed(os.path.join(AN, "fonts_n2", f), os.path.join(AN, "fonts", f))

    print("== inject ja (official) ==")
    run("inject_ja2.py", west, os.path.join(AN, "extracted_jp2", "script"),
        os.path.join(AN, "ja_inject2", "script"))

    print("== art ==")
    run("make_button.py")
    run("make_langbtn.py")
    run("edit_keyboard.py")
    extract(west_arcs, lambda l: l in ("pc\\en\\config3\\sound_bg.png",
                                       "pc\\ja\\config3\\sound_bg.png"),
            os.path.join(AN, "snd_src"))
    run("make_bgmduck.py", os.path.join(AN, "snd_src"),
        os.path.join(AN, "kb_edit"))

    print("== ja asset restore ==")
    run("ja_assets2.py", jp, west, "--restore")

    print("== ja append route-select art ==")
    run("make_route_append.py", jp)

    print("== hover-menu masks ==")
    run("make_dockarea.py")

    print("== engine patches ==")
    run("patch_system.py",
        os.path.join(AN, "extracted_en2_sys", "system"),
        os.path.join(AN, "patched_sys2"))
    for lang in ("en", "cn", "tw", "ja"):
        run("patch_tbl.py",
            os.path.join(AN, "extracted_en2_sys", "system", "table",
                         f"list_windows_{lang}.tbl"),
            os.path.join(AN, "patched_tbl2", f"list_windows_{lang}.tbl"))

    print("== build .080 ==")
    run("build_patch2.py", os.path.join(AN, "ja_inject2", "script"),
        os.path.join(ROOT, "dist", "root.pfs.080"))

    if nip is None:
        cand = glob.glob(os.path.join(os.path.dirname(west.rstrip("\\/")),
                                      "*", "root.pfs.069"))
        nip = cand[0] if cand else None
    if nip and os.path.exists(nip):
        print("== inject ja (NIP2) + build .081 ==")
        run("inject_ja2.py", west, os.path.join(AN, "extracted_jp2", "script"),
            os.path.join(AN, "ja_inject2_nip", "script"), nip)
        run("build_patch2.py", os.path.join(AN, "ja_inject2_nip", "script"),
            os.path.join(ROOT, "dist", "root.pfs.081"))
    else:
        print("== NIP2 archive not found; skipping .081 ==")

    print("done.")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
