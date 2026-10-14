NUKITASHI 1 & 2 - Japanese Language Restoration Patch
======================================================
v1.3 - by That-Ruben

Makes NUKITASHI and NUKITASHI 2 readable in Japanese, English, or both
at once. The western (Shiravune) releases already contain the Japanese
UI and fonts, but the Japanese text itself was replaced with a
placeholder and the language option was hidden. This patch restores the
text from the Japanese release and re-enables the option.

Requires the free 18+ patch from Shiravune (the base Steam release does
not contain the full game files).

Features
--------
- Japanese added as a 4th language: Config > Common > LANGUAGE
- Instant JP/EN toggle in-game: press L, or click the JP button in the
  popup menu (the button stays lit while Japanese is active)
- Dual language display: press K, or click the & button in the popup
  menu, to also show the other language in a smaller font above the
  text. Off by default.
- Voice playback is no longer interrupted by the backlog, the config /
  save / load screens, or quicksaves - only a new voice line stops it
- The popup menu closes 3 seconds after the mouse leaves it instead
  of 5 (I would have liked to make it 1, but the side menu in this
  game is actually broken, like it doesn't detect your mouse and
  closes while you hover over it)
- Restored several authentic Japanese UI graphics that the localization
  had replaced with English versions

Note: if L / K do nothing right after loading an old save (from before
you installed the patch), open the backlog once - the keys work from
then on, permanently. Saves made after that are fine.

Note (NUKITASHI 2): There's some cut content in both the japanese and western release. 
It's not accessible in any version of the game, but I'll be releasing a patch for that soon.
Some of it needs to be translated first.

Install (NUKITASHI 1)
---------------------
Copy ONE file into the game folder (next to NUKITASHI.exe):

  NUKITASHI.pfs.080  - the standard version.

  NUKITASHI.pfs.081  - if you have the fan-made "Nukitashi Improvement
                       Patch" (NUKITASHI.pfs.069) installed, use this
                       one instead. It keeps that patch's English
                       script.

Install (NUKITASHI 2)
---------------------
Copy ONE file into the game folder (next to NUKITASHI2.exe):

  root.pfs.080  - the standard version.

  root.pfs.081  - if you have the fan-made "Nukitashi 2 Improvement
                 Patch" (root.pfs.069) installed, use this one instead.
                 It keeps that patch's English script.

Uninstall: delete the file(s) again.

Note before uninstalling: if the dual language display is enabled,
disable it and save again before removing the patch. The Artemis engine
bakes the message-window layer tree into the save file and restores it
verbatim on load, so if you saved with dual language enabled, it will
still be there even if you uninstalled the patch. (To fix such a save
afterwards: reinstall the patch, load the save, advance one line, save
again.)

IMPORTANT - about other patches
-------------------------------
Because of how the Artemis engine loads patch archives, the last archive
overrides whole files, including all languages at once. That is why two
builds exist: each carries the English text of its base game.

- Installing .080 alone on top of the Improvement Patch will revert your
  English text to the official translation (use .081 instead).
- If you use some other script patch that this mod doesn't know about,
  it will be overridden the same way. Reach out (see below) and a
  compatible build can be made.

Version history
---------------
v1.3 (2026-10-15) - fixed some compatibility issues
v1.2 (2026-08-18) - NUKITASHI 2: fixed DLC script error from v1.1
v1.1 (2026-08-06) - fixed some stray placeholder text
v1   (2026-07-20) - first release

Credits
-------
Patch by That-Ruben.
The Nukitashi Improvement Patches, whose English script is included in
the .081 builds, are by Y0mi916:
  NUKITASHI 1: https://vndb.org/r109660
  NUKITASHI 2: https://vndb.org/r119008

Issues / contact
----------------
Bug reports and compatibility requests:
https://github.com/That-Ruben/nukitashi_series_JP_restoration_patch
https://that-ruben.vercel.app/nukitashi
