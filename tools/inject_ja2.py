"""Nukitashi 2 JP-restoration injector: label-matched ja-subtree splice,
plus positional alignment for the DLC append scripts.

Same idea as N1's inject_ja.py, with N2's format traps handled:
  - EN archives are named root.pfs*
  - mixed serializations: EN main scripts are compact (["x"]={ / ja={),
    JP scripts and EN append scripts are pretty (\t["x"] = { / ja = {)
    -> whitespace-flexible regexes; injected ja keeps JP's formatting
       (the engine parses Lua table syntax, whitespace-insensitive)
  - EN merges chapters that JP splits into _1.._N part files
    -> global JP label index across all files; 1,721 labels exist in
       more than one JP file, ALL disambiguated by stem prefix (the JP
       part-file stem starts with the EN file's stem; verified 0 remain
       ambiguous)
  - DLC/append scripts (08_hw06_*, 12_in*) use old block_NNNNN labels on
    the JP side -> no label match. VERIFIED (not assumed) that JP still
    has every block, 1:1, just without the localized ja/en/cn/tw label
    scheme: many are ja-ONLY tables (no en/cn/tw siblings at all), which
    the label-matched pass's ja-then-en regex silently skipped, making
    the JP side look short. A brace-balanced parser + positional pairing
    (verified per-block by identical voice-file tag and identical
    speaker name, in order) resolves ALL of them.
  - 11_zz* is the one real exception: its save-title metadata (still
    literal Japanese, untouched by the placeholder system since it's
    outside the injected span) reads "没シナリオ" ("cut scenario") -
    confirmed cut/unreleased content with no JP release anywhere, not a
    missing-file search failure. Left as English by design.

Usage: python inject_ja2.py <EN_GAME_DIR> <JP_SCRIPT_DIR> <OUT_DIR> [EXTRA_PFS...]
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pfs import PfsArchive

LABEL = re.compile(rb'^\t?(?:\["([^"]+)"\]|(block_\d+)) ?= ?\{', re.M)
JA_SPAN = re.compile(rb'(ja ?= ?\{.*?)(\n\t*en ?= ?\{)', re.S)
JA_OPEN = re.compile(rb'\bja ?= ?\{')
VO = re.compile(rb'\{"vo"[^}]*file="([^"]+)"')
NAME = re.compile(rb'name ?= ?\{"([^"]*)"')
# placeholder dialogue is exactly "*テキスト*" (one form, no variants); a bare
# token test avoids the old CJK-count heuristic, which miscounted long JP
# speaker names inside the ja span and skipped real placeholders (N1 bug).
PLACEHOLDER = '"*テキスト*"'.encode("utf-8")

DLC = re.compile(r'^(08_hw06_|12_in)')      # positionally aligned below
NO_JP_SOURCE = re.compile(r'^11_zz')        # confirmed cut content, left EN


def balanced_end(data, open_brace):
    """Index just past the matching '}' for the '{' at data[open_brace]."""
    depth = 0
    i = open_brace
    while i < len(data):
        c = data[i]
        if c == 0x7b:
            depth += 1
        elif c == 0x7d:
            depth -= 1
            if depth == 0:
                return i + 1
        elif c == 0x22:  # skip "..." strings (braces inside don't count)
            i += 1
            while i < len(data) and data[i] != 0x22:
                if data[i] == 0x5c:
                    i += 1
                i += 1
        elif c == 0x5b and i + 1 < len(data) and data[i + 1] == 0x5b:
            j = data.find(b"]]", i + 2)  # [[ ]] long string
            i = j + 1 if j != -1 else len(data)
        i += 1
    raise ValueError("unbalanced braces")


def numkey(fn):
    m = re.match(r'.+?_(\d+)\.ast$', fn)
    return int(m.group(1)) if m else 0


def effective_scripts(game_dir, extra=()):
    """lowercased-name -> (archive, exact-name), last archive wins.
    Our own patch archives (.080+) are excluded; `extra` archives (e.g. a
    fan patch) are stacked after the game's own."""
    paths = [p for p in sorted(glob.glob(os.path.join(game_dir, "root.pfs*")))
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
    """[(label, start, end)] in file order; end = next label start or EOF."""
    marks = [(m.start(), (m.group(1) or m.group(2)).decode())
             for m in LABEL.finditer(data)]
    out = []
    for i, (pos, lab) in enumerate(marks):
        end = marks[i + 1][0] if i + 1 < len(marks) else len(data)
        out.append((lab, pos, end))
    return out


def ja_span(data, start, end):
    """(abs_start, abs_end) of the ja subtree inside one label segment."""
    m = JA_SPAN.search(data, start, end)
    if not m:
        return None
    return (m.start(1), m.end(1))


def is_placeholder(ja_bytes):
    return PLACEHOLDER in ja_bytes


def span_tail(data, start, end):
    """Everything in a ja span after the ja table's closing brace.

    JA_SPAN runs from `ja` up to the newline before `en`, so it carries the
    field separator: `ja = { ... },`. The JP DLC blocks are lifted with the
    balanced-brace parser instead, which stops at the `}` and drops that
    comma - splicing them in raw produced `}` immediately followed by
    `en={`, which is a Lua syntax error, and the whole script then failed to
    load (v1.1 shipped 5,840 of them across the 12_in*/08_hw06_* append
    scripts: black screen / hang on Susuko's route). Keep the original tail."""
    return data[balanced_end(data, data.index(b"{", start)):end]


def check_ja_separators(data, fn):
    """Every ja span must still end in a field separator before `en`."""
    bad = [m.start(1) for m in JA_SPAN.finditer(data)
           if not m.group(1).rstrip().endswith((b",", b";"))]
    assert not bad, (f"{fn}: {len(bad)} ja spans lost their separator "
                     f"(first at byte {bad[0]}) - the script would not parse")


def build_jp_index(jp_dir):
    """label -> [(stem, ja_bytes)] across all JP scripts."""
    index = {}
    for fn in sorted(os.listdir(jp_dir)):
        if not fn.endswith(".ast"):
            continue
        with open(os.path.join(jp_dir, fn), "rb") as f:
            data = f.read()
        stem = fn[:-4].lower()
        for lab, s, e in segments(data):
            span = ja_span(data, s, e)
            if span:
                index.setdefault(lab, []).append(
                    (stem, data[span[0]:span[1]]))
    return index


GROUP = re.compile(r'^(08_hw06|12_in\d+)(?:_\d+)?\.ast$')


def group_of(fn):
    m = GROUP.match(fn)
    return m.group(1) if m else None


def jp_dlc_blocks(jp_dir, files):
    """Ordered list of every ja-bearing block across `files` (document
    order within each file, files in `files` order), using the balanced
    parser since JP DLC blocks are often ja-only (no en/cn/tw siblings)."""
    out = []
    for fn in files:
        with open(os.path.join(jp_dir, fn), "rb") as f:
            data = f.read()
        for lab, s, e in segments(data):
            m = JA_OPEN.search(data, s, e)
            if not m:
                continue
            end = balanced_end(data, m.end() - 1)
            span = data[m.start():end]
            seg = data[s:e]
            nm = NAME.search(span)
            out.append(dict(fn=fn, lab=lab, bytes=span,
                            vo=tuple(v.decode() for v in VO.findall(seg)),
                            name=nm.group(1).decode("utf-8", "replace")
                            if nm else None))
    return out


def align_dlc(out_dir, jp_dir):
    """Positional pass over the DLC append scripts (08_hw06, 12_in01-08):
    JP ships them with old block_NNNNN labels and no shared key with the
    EN side, but every text block pairs up 1:1 in document order. Each
    pairing is verified (not assumed) by matching voice-file tag and
    speaker name before any text is spliced."""
    groups = sorted({g for fn in os.listdir(out_dir)
                     if (g := group_of(fn))})
    stats = dict(groups=len(groups), checked=0, injected=0, kept_real=0)
    for g in groups:
        efs = sorted((fn for fn in os.listdir(out_dir) if group_of(fn) == g),
                     key=numkey)
        jfs = sorted((fn for fn in os.listdir(jp_dir) if group_of(fn) == g),
                     key=numkey)
        jp_blocks = jp_dlc_blocks(jp_dir, jfs)
        jp_i = 0
        for fn in efs:
            path = os.path.join(out_dir, fn)
            with open(path, "rb") as f:
                data = f.read()
            pieces = []
            cursor = 0
            for lab, s, e in segments(data):
                span = ja_span(data, s, e)
                if span is None:
                    continue
                ja_bytes = data[span[0]:span[1]]
                seg = data[s:e]
                vo = tuple(v.decode() for v in VO.findall(seg))
                nm = NAME.search(ja_bytes)
                name = nm.group(1).decode("utf-8", "replace") if nm else None

                assert jp_i < len(jp_blocks), \
                    f"{g}: ran out of JP blocks at {fn}[{lab}]"
                jb = jp_blocks[jp_i]
                assert vo == jb["vo"], (
                    f"{g}: vo mismatch {fn}[{lab}] EN={vo} "
                    f"JP={jb['vo']} ({jb['fn']}[{jb['lab']}])")
                assert name == jb["name"], (
                    f"{g}: name mismatch {fn}[{lab}] EN={name!r} "
                    f"JP={jb['name']!r} ({jb['fn']}[{jb['lab']}])")
                jp_i += 1
                stats["checked"] += 1

                if is_placeholder(ja_bytes):
                    pieces.append(data[cursor:span[0]])
                    pieces.append(jb["bytes"])
                    pieces.append(span_tail(data, span[0], span[1]))
                    cursor = span[1]
                    stats["injected"] += 1
                else:
                    stats["kept_real"] += 1
            pieces.append(data[cursor:])
            out = b"".join(pieces)

            strip = lambda b: JA_SPAN.sub(rb"\2", b)
            assert strip(out) == strip(data), f"non-ja bytes changed in {fn}"
            check_ja_separators(out, fn)
            with open(path, "wb") as f:
                f.write(out)
        assert jp_i == len(jp_blocks), (
            f"{g}: {len(jp_blocks) - jp_i} JP blocks never consumed")
    print("DLC alignment:", stats)
    return stats


def main(game_dir, jp_dir, out_dir, extra=()):
    os.makedirs(out_dir, exist_ok=True)
    best = effective_scripts(game_dir, extra)
    jp_index = build_jp_index(jp_dir)
    stats = dict(files=0, injected=0, kept_real=0, dlc_deferred=0,
                 no_jp_source=0, unresolved=0)
    for fn in sorted(best):
        arc, name = best[fn]
        a = PfsArchive(arc)
        data = a.read(name)
        a.close()
        stem = fn[:-4]

        pieces = []
        cursor = 0
        for lab, s, e in segments(data):
            span = ja_span(data, s, e)
            if span is None:
                continue
            ja_bytes = data[span[0]:span[1]]
            if not is_placeholder(ja_bytes):
                stats["kept_real"] += 1
                continue
            cands = jp_index.get(lab, [])
            match = [c for c in cands
                     if c[0] == stem or c[0].startswith(stem + "_")]
            if not match:
                match = cands
            if len(match) != 1:
                if DLC.match(fn):
                    stats["dlc_deferred"] += 1
                elif NO_JP_SOURCE.match(fn):
                    stats["no_jp_source"] += 1   # 11_zz cut content, leave EN
                else:
                    stats["unresolved"] += 1
                    print(f"  UNRESOLVED: {fn} [{lab}] "
                          f"({len(match)} candidates)")
                continue
            pieces.append(data[cursor:span[0]])
            pieces.append(match[0][1])
            cursor = span[1]
            stats["injected"] += 1
        pieces.append(data[cursor:])
        out = b"".join(pieces)

        # verify: everything outside replaced ja spans is untouched
        strip = lambda b: JA_SPAN.sub(rb"\2", b)
        assert strip(out) == strip(data), f"non-ja bytes changed in {fn}"
        check_ja_separators(out, fn)

        with open(os.path.join(out_dir, fn), "wb") as f:
            f.write(out)
        stats["files"] += 1

    print(stats)
    assert stats["unresolved"] == 0, "non-DLC placeholders left unresolved"

    # DLC append scripts: positional alignment (verified by vo + name)
    align_dlc(out_dir, jp_dir)

    # final check: placeholders may remain ONLY in the confirmed-cut-content
    # 11_zz files (no JP release exists for them; see module docstring)
    bad = []
    for fn in sorted(best):
        with open(os.path.join(out_dir, fn), "rb") as f:
            data = f.read()
        check_ja_separators(data, fn)
        if any(is_placeholder(m.group(1)) for m in JA_SPAN.finditer(data)):
            if not NO_JP_SOURCE.match(fn):
                bad.append(fn)
    assert not bad, f"placeholders left outside the 11_zz set: {bad}"
    n_zz = sum(1 for fn in best if NO_JP_SOURCE.match(fn))
    print(f"placeholders remain only in the {n_zz} confirmed-cut-content "
          f"11_zz files")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], extra=sys.argv[4:])
