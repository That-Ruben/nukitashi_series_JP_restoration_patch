"""Add the Japanese option to the config-screen language row in
Nukitashi's list_windows_<lang>.tbl files (port of the HENPRI patcher).

- Adds a `lang_ja` toggle button to groups ui_config1_en/_cn/_tw
- Rewrites p2 (mutual-exclusion lists) on all language buttons
- Appends a new group ui_config1_ja (shown while the game runs in
  Japanese), cloned from ui_config1_en with the obj/toggle roles swapped.
- Adds sub01/sub02 font entries for the dual-language display (K key):
  smaller text above the message text, JP-capable font06 for every entry
  since the sub slot always holds ja or en.

- en/ja only: a YES/NO row on the Sound tab for the engine's hidden
  "lower music during voice" flag (conf.fl_bgmvo); label art comes from
  make_bgmduck.py.

Usage: python patch_tbl.py IN_TBL OUT_TBL
"""
import os
import re
import sys

ORDER = ("en", "cn", "tw", "ja")
X = {"en": 605, "cn": 750, "tw": 895, "ja": 1040}
BTNID = {"en": 23, "cn": 24, "tw": 25, "ja": 26}

SUB_ATTRS = ('left=408, top=550, width=950, height=110, align="left", '
             'color="0xffffff", outline=2, outlinecolor="0x000000", '
             'spacetop=0, spacemiddle=-8, spacebottom=-4, kerning=-2, '
             'show="none", indent="indent", hung=1, ruby="font06", '
             'rubysize=13, rubyoutline=1, prohibit=1, layered=1,},')


def sub_block(name, repl=()):
    rows = []
    for lang, size in (("ja", 28), ("en", 27), ("tw", 28), ("cn", 28)):
        attrs = SUB_ATTRS
        for old, new in repl:
            attrs = attrs.replace(old, new)
        rows.append(f'\t\t\t{lang} = {{ face="font06", size={size}, ' + attrs)
    return [f"\t\t{name} = {{"] + rows + ["\t\t},"]


def insert_sub_entries(lines):
    """Insert sub01/sub02 before every adv01/adv02 font entry (the font
    sections appear twice per tbl; Lua last-wins, both get the entries)."""
    eol = "\r\n" if lines[0].endswith("\r\n") else "\n"
    out = []
    n1 = n2 = 0
    for ln in lines:
        if ln.startswith("\t\tadv01 = {"):
            out.extend(s + eol for s in sub_block("sub01"))
            n1 += 1
        elif ln.startswith("\t\tadv02 = {"):
            out.extend(s + eol for s in sub_block(
                "sub02", (("left=408", "left=1200"), ("top=550", "top=2200"),
                          ("width=950", "width=820"))))
            n2 += 1
        out.append(ln)
    assert n1 >= 1, "no adv01 font entry found"
    lines[:] = out
    print(f"  sub01 x{n1}, sub02 x{n2}")


def lang_line(lang, obj):
    others = "|".join("lang_" + o for o in ORDER if o != lang)
    common = (f'\t\tlang_{lang} = {{ name="lang_{lang}", '
              f'file="config1/bt_language_{lang}", id="z.bt.{BTNID[lang]}", '
              f'x={X[lang]}, y=545, w=143, h=51, ')
    mid = (f'def="language", exec="config_toggle", p1="{lang}", '
           f'p2="{others}", p3="{lang}", p4="conf_langchange", '
           f'dir="height", cx="0", ')
    if obj:
        return (common + 'com="obj", ' + mid +
                'cy="52", cw="143", ch="52", clip="0,52,143,51", '
                'clip_d="0,208,143,51", },')
    return (common + 'com="toggle", ' + mid +
            'cy="0", cw="143", ch="52", clip="0,0,143,51", '
            'clip_a="0,52,143,51", clip_c="0,104,143,51", '
            'clip_d="0,156,143,51", },')


BT_LANG = ('\t\tbt_lang = { name="bt_lang", file="mw/bt_lang", '
           'id="mw.bt.dc.16", x=1102, y=865, w=36, h=29, com="btn", '
           'exec="lang_toggle_jaen", dir="height", cx="0", cy="0", '
           'cw="36", ch="31", clip="0,0,36,29", clip_a="0,31,36,29", '
           'clip_c="0,62,36,29", clip_d="0,93,36,29", },')
BT_SUBLANG = ('\t\tbt_sublang = { name="bt_sublang", file="mw/bt_sublang", '
              'id="mw.bt.dc.17", x=1069, y=865, w=36, h=29, com="btn", '
              'exec="sublang_toggle", dir="height", cx="0", cy="0", '
              'cw="36", ch="31", clip="0,0,36,29", clip_a="0,31,36,29", '
              'clip_c="0,62,36,29", clip_d="0,93,36,29", },')


def insert_langbtn(lines):
    """Add the JP and II (dual-language) mini-buttons to the hover menu
    (ui_adv01), after bt_mute."""
    n = 0
    out = []
    for ln in lines:
        out.append(ln)
        if ln.lstrip().startswith('bt_mute = {') and 'mw.bt.dc.2' in ln:
            eol = "\r\n" if ln.endswith("\r\n") else "\n"
            out.append(BT_LANG + eol)
            out.append(BT_SUBLANG + eol)
            n += 1
    assert n == 1, f"expected 1 ui_adv01 bt_mute anchor, found {n}"
    lines[:] = out
    print("  bt_lang + bt_sublang added to ui_adv01")


def find_group(lines, name):
    start = None
    for i, ln in enumerate(lines):
        if re.match(rf"\t{name}\s*=\s*\{{\s*$", ln):
            start = i
        elif start is not None and ln.rstrip("\r\n") == "\t},":
            return start, i
    raise ValueError(f"group {name} not found")


def patch_group(lines, gname, current):
    start, end = find_group(lines, gname)
    body = lines[start:end + 1]
    eol = "\r\n" if body[0].endswith("\r\n") else "\n"
    out = []
    seen = set()
    for ln in body:
        m = re.match(r"\t\tlang_(en|cn|tw|ja) = ", ln)
        if m:
            l = m.group(1)
            seen.add(l)
            out.append(lang_line(l, obj=(l == current)) + eol)
            if l == "tw" and "ja" not in seen and current != "ja":
                out.append(lang_line("ja", obj=False) + eol)
                seen.add("ja")
        else:
            out.append(ln)
    if "ja" not in seen:
        raise ValueError(f"{gname}: no tw line to anchor ja insertion")
    lines[start:end + 1] = out


BGMVO_DY = 62    # row pitch on the Sound tab (sound_bg.png rows every 62px)


def insert_bgmvo_toggle(lines):
    """Sound tab: a YES/NO row below "Click to stop voice" for the engine's
    existing voice-ducking flag conf.fl_bgmvo (music drops to config bgmvo
    while a voice plays; stock game had no control for it). Cloned from the
    voiceskip pair, one row lower; the label is drawn into sound_bg.png by
    make_bgmduck.py."""
    idx = [i for i, ln in enumerate(lines)
           if re.match(r'\t\tvoiceskip[12] = \{ name="voiceskip[12]"', ln)]
    assert len(idx) == 2, f"expected the voiceskip pair, found {len(idx)}"
    new = []
    for n, i in enumerate(idx, 1):
        ln = lines[i]
        other = 3 - n
        ln = ln.replace(f'voiceskip{n} = {{ name="voiceskip{n}"',
                        f'bgmvo{n} = {{ name="bgmvo{n}"')
        ln = ln.replace(f'p2="voiceskip{other}"', f'p2="bgmvo{other}"')
        ln = ln.replace('def="voiceskip"', 'def="fl_bgmvo"')
        ln = re.sub(r'id="z\.bt\.0[12]"', f'id="z.bt.1{n + 1}"', ln)
        y = int(re.search(r' y=(\d+),', ln).group(1))
        ln = ln.replace(f' y={y},', f' y={y + BGMVO_DY},', 1)
        assert "voiceskip" not in ln, ln
        new.append(ln)
    lines[idx[-1] + 1:idx[-1] + 1] = new
    print("  Sound tab: bgmvo YES/NO row")


def fix_select_aread_ja(lines):
    """The ja font for already-chosen choices (select_aread) has left=0
    while the normal one (select) has left=-440, both width=1600 — so
    previously chosen choices were drawn 440px right of their box. The
    western release never displayed ja, so the bad entry went unnoticed."""
    n = 0
    in_aread = False
    for i, ln in enumerate(lines):
        if re.match(r"\t\t\w+ = \{", ln):
            in_aread = ln.startswith("\t\tselect_aread = {")
        elif in_aread and ln.startswith("\t\t\tja = {"):
            old = "left=0, top=8, width=1600,"
            assert old in ln, ln
            lines[i] = ln.replace(old, "left=-440, top=8, width=1600,")
            n += 1
    assert n == 2, f"expected 2 select_aread ja entries, fixed {n}"
    print(f"  ja select_aread position x{n}")


def patch_file(path_in, path_out):
    with open(path_in, "r", encoding="utf-8", newline="") as f:
        lines = f.readlines()
    for l in ("en", "cn", "tw"):
        patch_group(lines, f"ui_config1_{l}", current=l)
    insert_sub_entries(lines)
    insert_langbtn(lines)
    fix_select_aread_ja(lines)
    # labels exist only in the en/ja sound_bg art we generate
    if re.search(r"_(en|ja)\.tbl$", path_in):
        insert_bgmvo_toggle(lines)

    start, end = find_group(lines, "ui_config1_en")
    eol = "\r\n" if lines[start].endswith("\r\n") else "\n"
    ja_group = [f"\tui_config1_ja = {{{eol}"]
    for ln in lines[start + 1:end + 1]:
        m = re.match(r"\t\tlang_(en|cn|tw|ja) = ", ln)
        if m:
            l = m.group(1)
            ja_group.append(lang_line(l, obj=(l == "ja")) + eol)
        else:
            ja_group.append(ln)
    ts, te = find_group(lines, "ui_config1_tw")
    lines[te + 1:te + 1] = ja_group
    os.makedirs(os.path.dirname(os.path.abspath(path_out)), exist_ok=True)
    with open(path_out, "w", encoding="utf-8", newline="") as f:
        f.writelines(lines)
    print(f"patched {path_out}")


if __name__ == "__main__":
    patch_file(sys.argv[1], sys.argv[2])
