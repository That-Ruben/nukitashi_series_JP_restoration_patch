# NUKITASHI Series Japanese Language Restoration

Restores the **Japanese text option** in the western (Shiravune) releases of
*NUKITASHI* and *NUKITASHI 2* (Artemis engine, developed by Qruppo).

The western releases still ship the entire Japanese UI and fonts, but the
Japanese dialogue itself was replaced with a placeholder and the language
option was hidden. This project restores it:

- **Japanese as a 4th language** in Config → Common → LANGUAGE
- **Instant JP⇄EN toggle** with the **L** key, or the JP button in the
  popup menu (stays lit while Japanese is active)
- **Dual-language display** with the **K** key, or the **&** button — shows
  the other language in a smaller font above the text. Off by default.
- Voice playback survives the backlog, config/save/load screens, and
  quicksaves — only a new voice line interrupts it
- The popup menu closes 3 seconds after the mouse leaves it, not 5
- Restored several authentic Japanese UI graphics the localization had
  replaced with English versions
- The new hotkeys are documented on the Config → KEYBOARD screen

## Installing the patch

Grab the [released zip](https://catbox.moe/c/anetpf), then copy **one** file
into the relevant game folder:

**NUKITASHI 1** — next to `NUKITASHI.exe`:
- `NUKITASHI.pfs.080` — the standard version.
- `NUKITASHI.pfs.081` — if you have the fan-made "Nukitashi Improvement
  Patch" (`NUKITASHI.pfs.069`) installed, use this instead. It keeps that
  patch's English script.

**NUKITASHI 2** — next to `NUKITASHI2.exe`:
- `root.pfs.080` — the standard version.
- `root.pfs.081` — if you have the fan-made "Nukitashi 2 Improvement Patch"
  (`root.pfs.069`) installed, use this instead.

Requires the free 18+ patch from Shiravune (the base Steam release doesn't
contain the full game files). Uninstall: delete the file(s) again.

**Why two builds per game?** The Artemis engine overrides *whole files*, and
script files carry every language's text together — so any patch
necessarily ships an English text base along with the Japanese. `.080`
carries the official English, `.081` carries the Improvement Patch's
English. If you use another script patch this project doesn't know about,
open an issue — a compatible build is easy to make.

### Known gap (NUKITASHI 2)

A handful of short bonus scenes bundled with the Append DLC still show
English text in Japanese mode — about 200 lines across 5 script files
(`root.pfs.010`, `script\11_zz06.ast`, `11_zz08.ast`, `11_zz09.ast`,
`11_zz10.ast`, `11_zz11.ast`). No Japanese source for this content could be
found anywhere in the available game files. If you know where this text
comes from, please open an issue.

## This repository

**No game data is distributed here** — only the toolchain and documentation
to build the patch from game copies you own.

### Building it yourself

```
python tools/build_all.py <WESTERN_GAME_DIR> <JP_GAME_DIR> [NIP_PFS_069]
python tools/build_all2.py <WESTERN_GAME_DIR> <JP_GAME_DIR> [NIP2_PFS]
```

Outputs `dist/NUKITASHI.pfs.080`/`.081` and `dist/root.pfs.080`/`.081`
respectively. Both builds are deterministic — identical inputs produce
byte-identical patches.

### How it works (short version)

- `pfs.py` — reader/writer for Artemis pf8 archives
- `inject_ja.py` / `inject_ja2.py` — label-matched splice of the Japanese
  `ja` subtree from the JP release into each western placeholder text
  block. NUKITASHI 2's DLC append scripts (`08_hw06`, `12_in01`-`08`) use
  an older label scheme with no shared key against the western build, so
  those are instead aligned positionally and verified per block by
  matching voice-file ID and speaker name before injection
- `patch_tbl.py` / `patch_system.py` — add the 日本語 config button, the
  L/K hotkey bindings and toggle functions, the dual-language display
  fixes, and the voice-keep behavior to the engine's Lua/tbl data
- `ja_assets.py` / `ja_assets2.py` — restore `pc/ja/` UI images the
  localization replaced with English ones (detected by hash comparison
  against the JP release)
- `edit_keyboard.py` / `make_button.py` / `make_langbtn.py` — generate the
  language config button and popup-menu mini-buttons, and add the hotkey
  legend to the keyboard help screen

## Version history

- **v1.1** (2026-08-06) - fixed some stray placeholder text
- **v1**   (2026-07-20) — first release, both games.

## Credits

Patch by **That-Ruben**. Tools are MIT-licensed (see LICENSE).

The Nukitashi Improvement Patches, whose English script is included in the
`.081` builds, are by **Y0mi916**:
- NUKITASHI 1: https://vndb.org/r109660
- NUKITASHI 2: https://vndb.org/r119008
