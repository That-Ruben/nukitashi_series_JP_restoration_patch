"""Nukitashi engine patches (port of the HENPRI language mod):

  analysis/patched_sys/list_windows.tbl
     - advkey: L (76) -> LANG -> lang_toggle_jaen, K (75) -> SUBV ->
       sublang_toggle, in both duplicate advkey blocks (Lua last-wins)
     - movies: ja plays the en movie files (no ja files ship in the west)
  analysis/patched_sys/lang.lua
     - lang_toggle_jaen(): main/sub/ui toggle ja <-> en
     - sublang_toggle(): K key; runtime switch of the engine's dormant
       game_sublangview dual-language display (off by default)
  analysis/patched_sys/message.lua
     - mw_textloop/getTextBlockFloat honor the lang parameter (stock code
       rendered the sub layer in the main language)
     - sub layer bottom-anchored above the main text (stock pushed it
       below) via mw_subposition
  analysis/patched_sys/adv_mw.lua
     - sub layer font assigned unconditionally so K works mid-session
  analysis/patched_sys/vsync.lua
     - hover menu closes 1s after the mouse leaves (stock 5s)
  analysis/patched_sys/se.lua + adv.lua + mw.lua
     - voice playback survives UI screens/quicksave/dialogs (HENPRI
       voice-keep port): the "pause" stop mode skips voice, sesys_resume
       keeps still-playing voice entries, msg_hide no longer stops voice,
       return-to-title stops it explicitly
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# optional argv: [SYS_DIR] [OUT_DIR] — N2 passes extracted_en2_sys/system
# and patched_sys2; every anchor is verified to hold in both games
SYS = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    ROOT, "analysis", "extracted_en_sys", "system")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(
    ROOT, "analysis", "patched_sys")

# sub layer bottom anchor: sub01 font top is 550; the ink bottom is pinned
# to 644 (name row starts at 636/641) — tune in-game like HENPRI
SUB_TARGET, SUB_FONTTOP = 644, 550

TOGGLE_FUNC = (
    "----------------------------------------\r\n"
    "-- 言語トグル ja<->en (language mod)\r\n"
    "-- main/ui を切り替え、subは反対言語に揃える\r\n"
    "function lang_toggle_jaen()\r\n"
    "\tlocal nm = get_language() == \"ja\" and \"en\" or \"ja\"\r\n"
    "\tif not init.lang[nm] then return end\r\n"
    "\tse_ok()\r\n"
    "\tset_language(\"main\", nm)\r\n"
    "\tset_language(\"sub\", nm == \"ja\" and \"en\" or \"ja\")\r\n"
    "\tset_language(\"ui\", nm)\r\n"
    "\tlang_redraw()\r\n"
    "\tmwdock_lang_status()\r\n"
    "\tasyssave()\r\n"
    "end\r\n"
    "----------------------------------------\r\n"
    "-- 二言語表示の切替 Kキー (language mod)\r\n"
    "-- エンジン休眠機能 game_sublangview を実行時に切り替える。\r\n"
    "-- デフォルトはオフ、セッション内のみ有効\r\n"
    "function sublang_toggle()\r\n"
    "\tif init.game_sublangview == \"on\" then\r\n"
    "\t\tinit.game_sublangview = \"off\"\r\n"
    "\t\tinit.game_sublangblog = \"off\"\r\n"
    "\t\tlocal id = mw_getmsgid(\"sub\")\r\n"
    "\t\te:tag{\"chgmsg\", id=(id)}\r\n"
    "\t\te:tag{\"rp\"}\r\n"
    "\t\te:tag{\"/chgmsg\"}\r\n"
    "\telse\r\n"
    "\t\tinit.game_sublangview = \"on\"\r\n"
    "\t\tinit.game_sublangblog = \"on\"\r\n"
    "\t\tlocal ln = get_language()\r\n"
    "\t\tlocal sb = get_language(\"sub\")\r\n"
    "\t\tif not sb or sb == ln then\r\n"
    "\t\t\tset_language(\"sub\", ln == \"ja\" and \"en\" or \"ja\")\r\n"
    "\t\tend\r\n"
    "\tend\r\n"
    "\tse_ok()\r\n"
    "\tlang_redraw()\r\n"
    "\tmwdock_sublang_status()\r\n"
    "end\r\n"
)

SUBPOS_FUNC = (
    "----------------------------------------\r\n"
    "-- sub本文を本文の上に下端固定で配置する (language mod)\r\n"
    "function mw_subposition()\r\n"
    "\tlocal id = mw_getmsgid(\"sub\")\r\n"
    "\te:tag{\"chgmsg\", id=(id)}\r\n"
    "\te:tag{\"var\", system=\"get_message_layer_height\", name=\"t.tmp.subh\"}\r\n"
    "\tlocal h = e:var(\"t.tmp.subh\") or 0\r\n"
    "\te:tag{\"/chgmsg\"}\r\n"
    f"\t-- 下端 = フォントtop({SUB_FONTTOP}) + レイヤtop + h を{SUB_TARGET}に固定\r\n"
    f"\te:tag{{\"lyprop\", id=(id), top=({SUB_TARGET} - {SUB_FONTTOP} - h)}}\r\n"
    "end\r\n"
)


def read(rel):
    with open(os.path.join(SYS, rel), "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(name, t):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8", newline="") as f:
        f.write(t)


def patch_tbl():
    t = read(os.path.join("table", "list_windows.tbl"))
    old_def = 'def={[1]={btn="CLICK",adv="CLICK",ui="CLICK"},'
    n = t.count(old_def)
    assert n == 2, f"expected 2 advkey def blocks, found {n}"
    assert "[76]=" not in t and "[75]=" not in t, "keycode already bound"
    t = t.replace(old_def,
                  'def={[76]={btn="L",adv="LANG"},[75]={btn="K",adv="SUBV"},'
                  '[1]={btn="CLICK",adv="CLICK",ui="CLICK"},')
    old_tbl = 'tbl={CLICK="adv_click",'
    n = t.count(old_tbl)
    assert n == 2, f"expected 2 advkey tbl blocks, found {n}"
    t = t.replace(old_tbl,
                  'tbl={LANG="lang_toggle_jaen",SUBV="sublang_toggle",'
                  'CLICK="adv_click",')
    t, nm = patch_movies(t)
    write("list_windows.tbl", t)
    print(f"patched list_windows.tbl (L+K key bindings x2, "
          f"{nm} ja movies -> en files)")


def patch_movies(t):
    """The western release ships each movie only as _en/_cn/_tw files; the
    ja entry (no suffix) names a file that isn't there (N1) or is missing
    from the table altogether (N2), so in Japanese every opening/ending
    plays as a black screen. Point the ja entry at the en file."""
    eol = "\r\n" if "\r\n" in t else "\n"
    start = t.index(f"{eol}movie={{{eol}") + len(eol)
    end = t.index(f"{eol}}},", start)
    block = t[start:end]
    en = dict(re.findall(r'^(\w+)_en=\{file="(\w+)"', block, flags=re.M))
    assert en, "no _en movie entries found"
    lines = block.split(eol)
    out = []
    for ln in lines:
        m = re.match(r'(\w+)=\{file="\w+"(.*)$', ln)
        if m and m.group(1) in en:          # existing ja entry (N1)
            key = m.group(1)
            ln = f'{key}={{file="{en.pop(key)}"{m.group(2)}'
        m = re.match(r'(\w+)_en=\{file="\w+"(.*)$', ln)
        if m and m.group(1) in en:          # no ja entry (N2): add one
            key = m.group(1)
            out.append(f'{key}={{file="{en.pop(key)}"{m.group(2)}')
        out.append(ln)
    assert not en, f"unhandled movies: {en}"
    n = len(re.findall(r'^(\w+)_en=', block, flags=re.M))
    return t[:start] + eol.join(out) + t[end:], n


def patch_lang_lua():
    t = read(os.path.join("msg", "lang.lua"))
    assert "lang_toggle_jaen" not in t
    write("lang.lua", t + TOGGLE_FUNC)
    print("patched lang.lua (+lang_toggle_jaen, +sublang_toggle)")


def patch_message_lua():
    t = read(os.path.join("msg", "message.lua"))

    old = "\tlocal v = getTextBlockFloat(p.text)"
    assert t.count(old) == 1
    t = t.replace(old, "\tlocal v = getTextBlockFloat(p.text, nil, p.lang)")

    old = ("function getTextBlockFloat(p, mode)\r\n"
           "\tlocal r  = nil\r\n"
           "\tlocal z  = p.float or {}\r\n"
           "\tlocal ln = get_language()")
    assert t.count(old) == 1, "getTextBlockFloat anchor not found"
    t = t.replace(old, (
        "function getTextBlockFloat(p, mode, lang)\r\n"
        "\tlocal r  = nil\r\n"
        "\tlocal z  = p.float or {}\r\n"
        "\tlocal ln = lang and p[lang] and lang or get_language()"))

    old = '\t\testag{"lyprop", id=(id), top=(r)}'
    assert t.count(old) == 1
    t = t.replace(old, '\t\testag{"mw_subposition"}')
    t += SUBPOS_FUNC
    write("message.lua", t)
    print("patched message.lua (sub language + bottom anchor)")


LANGSTATUS_FUNC = (
    "----------------------------------------\r\n"
    "-- JPボタンの点灯状態 (language mod): 日本語中はclip_c(オレンジ)\r\n"
    "function mwdock_lang_status()\r\n"
    "\tif checkBtnExist(\"bt_lang\") then\r\n"
    "\t\tbtn_clip(\"bt_lang\", get_language() == \"ja\" and \"clip_c\" or \"clip\")\r\n"
    "\tend\r\n"
    "end\r\n"
    "----------------------------------------\r\n"
    "-- IIボタンの点灯状態 (language mod): 二言語表示中はclip_c(オレンジ)\r\n"
    "function mwdock_sublang_status()\r\n"
    "\tif checkBtnExist(\"bt_sublang\") then\r\n"
    "\t\tbtn_clip(\"bt_sublang\", init.game_sublangview == \"on\" and \"clip_c\" or \"clip\")\r\n"
    "\tend\r\n"
    "end\r\n"
)


def patch_adv_mw_lua():
    t = read(os.path.join("extend", "adv_mw.lua"))
    old = ("\tlocal tb = { adv=1, name=1 }\r\n"
           '\tif init.game_sublangview == "on" then tb.sub = 1 end\t-- sub')
    assert t.count(old) == 1, "adv_mw font anchor not found"
    t = t.replace(old, "\tlocal tb = { adv=1, name=1, sub=1 }"
                       "\t-- sub font always set (language mod)")
    old = "\t\tmwdock_mute_status1()\r\n"
    assert t.count(old) == 2, "mute_status anchors not found"
    t = t.replace(old, old + "\t\tmwdock_lang_status()\t-- JPボタン (language mod)\r\n"
                            "\t\tmwdock_sublang_status()\t-- IIボタン (language mod)\r\n")
    t += LANGSTATUS_FUNC
    write("adv_mw.lua", t)
    print("patched adv_mw.lua (sub font + JP button status)")


def patch_vsync_lua():
    t = read(os.path.join("adv", "vsync.lua"))
    # 1000 was too aggressive: the right-side button column sits OUTSIDE the
    # engine's dockarea hover region (dev oversight the 5s delay papered
    # over), so the timer runs even with the mouse on Save/Load. 3s keeps
    # those usable; the lock button covers anyone who wants it pinned.
    old = "\t\t\tif (advtime - oldtime) > 5000 then"
    assert t.count(old) == 1, "vsync dock-close anchor not found"
    t = t.replace(old, "\t\t\tif (advtime - oldtime) > 3000 then"
                       "\t-- 5000->3000 (language mod)")
    write("vsync.lua", t)
    print("patched vsync.lua (menu close delay 5000 -> 3000 ms)")


def patch_voicekeep():
    se = read(os.path.join("media", "se.lua"))
    old = "\t\tpause = function(id, v)\r\n\t\t\tlocal md = v.mode\r\n"
    assert se.count(old) == 1
    se = se.replace(old, old + '\t\t\tif md == "voice" then return end'
                          "\t-- ボイスは止めない (language mod)\r\n")
    old = ("\t\tif lp == 1 then\r\n"
           "\t\t\tsesys_play(v.mode, v.file, { ch=(v.ch), id=(v.id), "
           "vol=(v.vol), pan=(v.pan), loop=(lp), cat=(v.cat) })\r\n"
           "\t\tend\r\n")
    assert se.count(old) == 1
    se = se.replace(old, old.replace(
        "\t\tend\r\n",
        "\t\telseif v.mode == \"voice\" then\r\n"
        "\t\t\tscr.sesys.buff[i] = v\t-- 再生継続中 (language mod)\r\n"
        "\t\tend\r\n"))
    write("se.lua", se)

    mw = read(os.path.join("msg", "mw.lua"))
    old = "\tnotify(nil, true)\r\n\tsesys_stop(\"voice\")\t\t-- voice停止\r\n"
    assert mw.count(old) == 1
    mw = mw.replace(old, "\tnotify(nil, true)\r\n"
                    "\t-- sesys_stop(\"voice\")\t\t-- voice停止 (language mod)\r\n")
    write("mw.lua", mw)

    adv = read(os.path.join("adv", "adv.lua"))
    old = ("\tif getTitle() and not getExtra(true) then\r\n"
           "\t\tReturnStack()\t\t\t-- 空のスタックを削除\r\n"
           "\t\tsesys_stop(\"pause\")\t\t-- SE一時停止\r\n")
    assert adv.count(old) == 1
    adv = adv.replace(old, old + "\t\tsesys_stop(\"voice\")\t\t-- (language mod)\r\n")
    write("adv.lua", adv)
    print("patched se.lua/mw.lua/adv.lua (voice keep)")


if __name__ == "__main__":
    patch_tbl()
    patch_lang_lua()
    patch_message_lua()
    patch_adv_mw_lua()
    patch_vsync_lua()
    patch_voicekeep()
