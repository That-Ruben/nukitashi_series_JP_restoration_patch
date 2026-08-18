"""Assemble the Nukitashi 2 JP-restoration patch archive (root.pfs.080).

Mirror of build_patch.py with N2's inputs: 295 effective scripts,
patched_sys2/patched_tbl2/ja_restore2, art sources verified byte-identical
to N1's (config buttons, mw icons, keyboard screen), so the generated art
(bt_language_ja, bt_lang, bt_sublang, edited keyboard) is shared.

Usage: python build_patch2.py [SCRIPT_DIR] [OUT_PFS]
  defaults: analysis/ja_inject2/script -> dist/root.pfs.080
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfs import PfsArchive, write_pf8

AN = os.path.join(ROOT, "analysis")


def main(script_dir, out_pfs):
    files = []
    for name in sorted(os.listdir(script_dir)):
        if name.endswith(".ast"):
            with open(os.path.join(script_dir, name), "rb") as f:
                files.append(("script\\" + name, f.read()))
    n_scripts = len(files)
    assert n_scripts == 295, f"expected 295 scripts, got {n_scripts}"

    sysdir = os.path.join(AN, "patched_sys2")
    for rel, arc in (("list_windows.tbl", "system\\table\\list_windows.tbl"),
                     ("lang.lua", "system\\msg\\lang.lua"),
                     ("message.lua", "system\\msg\\message.lua"),
                     ("adv_mw.lua", "system\\extend\\adv_mw.lua"),
                     ("vsync.lua", "system\\adv\\vsync.lua"),
                     ("se.lua", "system\\media\\se.lua"),
                     ("mw.lua", "system\\msg\\mw.lua"),
                     ("adv.lua", "system\\adv\\adv.lua")):
        with open(os.path.join(sysdir, rel), "rb") as f:
            files.append((arc, f.read()))

    tbldir = os.path.join(AN, "patched_tbl2")
    n_tbls = 0
    for lang in ("en", "cn", "tw", "ja"):
        with open(os.path.join(tbldir, f"list_windows_{lang}.tbl"), "rb") as f:
            files.append((f"system\\table\\list_windows_{lang}.tbl", f.read()))
        n_tbls += 1
    assert n_tbls == 4

    with open(os.path.join(AN, "bt_language_ja.png"), "rb") as f:
        bt_ja = f.read()
    for lang in ("ja", "en", "cn", "tw"):
        files.append((f"pc\\{lang}\\config1\\bt_language_ja.png", bt_ja))
    for lang in ("en", "cn", "tw"):
        with open(os.path.join(AN, "btn2", f"bt_language_{lang}.png"), "rb") as f:
            files.append((f"pc\\ja\\config1\\bt_language_{lang}.png", f.read()))

    for sprite in ("bt_lang", "bt_sublang"):
        with open(os.path.join(AN, f"{sprite}.png"), "rb") as f:
            data = f.read()
        for lang in ("ja", "en", "cn", "tw"):
            files.append((f"pc\\{lang}\\mw\\{sprite}.png", data))

    # same five pure-icon sprites as N1: the ja renders have different pixel
    # sizes (bt_mute 36x120 vs en 36x124 etc.) while the tbl clip rects are
    # en-tuned — use the en art for ja too.
    for fn in ("bt_close", "bt_lock", "bt_mute", "bt_repeat", "bt_skip"):
        with open(os.path.join(AN, "mwbtn2", f"{fn}.png"), "rb") as f:
            files.append((f"pc\\ja\\mw\\{fn}.png", f.read()))

    # authentic JP UI assets restored over anglicized western ja files
    restore_root = os.path.join(AN, "ja_restore2")
    if os.path.isdir(restore_root):
        for dirpath, _, names in os.walk(restore_root):
            for fn in sorted(names):
                rel = os.path.relpath(os.path.join(dirpath, fn), restore_root)
                with open(os.path.join(dirpath, fn), "rb") as f:
                    files.append((rel.replace(os.sep, "\\"), f.read()))

    # keyboard-help image (byte-identical screen in both games -> shared)
    kb_root = os.path.join(AN, "kb_edit")
    if os.path.isdir(kb_root):
        for dirpath, _, names in os.walk(kb_root):
            for fn in sorted(names):
                rel = os.path.relpath(os.path.join(dirpath, fn), kb_root)
                with open(os.path.join(dirpath, fn), "rb") as f:
                    files.append((rel.replace(os.sep, "\\"), f.read()))

    # pc/ja/route/append: the western build has no Japanese art for the
    # append route-select screen at all, so New Game was a black screen in
    # Japanese (see make_route_append.py)
    route_root = os.path.join(AN, "ja_route2")
    n_route = 0
    for dirpath, _, names in os.walk(route_root):
        for fn in sorted(names):
            rel = os.path.relpath(os.path.join(dirpath, fn), route_root)
            with open(os.path.join(dirpath, fn), "rb") as f:
                files.append((rel.replace(os.sep, "\\"), f.read()))
            n_route += 1
    assert n_route == 8, f"expected 8 ja route/append sprites, got {n_route}"

    seen = {}
    for name, data in files:
        seen[name] = data
    files = list(seen.items())

    os.makedirs(os.path.dirname(out_pfs), exist_ok=True)
    write_pf8(out_pfs, files)
    size = os.path.getsize(out_pfs)
    print(f"wrote {out_pfs}: {len(files)} files ({n_scripts} scripts), "
          f"{size/1e6:.1f} MB")

    a = PfsArchive(out_pfs)
    assert len(a.entries) == len(files)
    for (name, data), e in zip(files, a.entries):
        assert e.name == name and a.read(e) == data, name
    a.close()
    print("read-back verification OK")


if __name__ == "__main__":
    sdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        AN, "ja_inject2", "script")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
        ROOT, "dist", "root.pfs.080")
    main(sdir, out)
