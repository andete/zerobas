#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""M-PLOTCLIP — make the clip STOP CLIPPING, the one arm 35 mutations never tried.

TODO.md's "NINE ACCEPTANCE ROWS STILL NEED A REFUSAL CUT" concluded that six of
them "would need a check SYNTHESISED, not a jump retargeted", and asked -- in its
own words -- "whether an error-code-only acceptance row is the right shape before
writing six of them". This arm is cheaper than answering that by writing six.

\U0001f534 THE NEVER-REDDENED LIST NAMES TEN CLIP ROWS, NOT SIX.
`scratchpad/gate_blindness.json` records 35 arms and 35 rows none of them ever
moved. Among them are the six error-code rows AND FOUR PIXEL ROWS:
`clip_noop_x300`, `clip_noop_xneg`, `clip_noop_y192` (phase A) and `clip_alloff`
(phase C). Those four read the PIXEL PLANE and assert that an off-screen plot
changes nothing -- so "the readout is too narrow" cannot be why they are quiet.

\U0001f3af THE REAL REASON IS THAT NOTHING EVER CUT THE ROUTINE THEY ARE ABOUT.
LINE/CIRCLE/DRAW clip at `gfx_plot_cur`'s three bare `ret`s (sub/graphics.asm),
and of the 35 arms the only one that touches that routine is `M-YBOUND`, which
NARROWS the on-screen bound (`cp 192` -> `cp 191`). Narrowing keeps off-screen
plots clipped, so a row asserting "off-screen draws nothing" correctly does not
move. `M-CLAMPX`/`M-CLAMPY` sound like the site and are not -- they cut
`gfx_clamp_coords`, a different routine.

So this arm removes the clip instead of moving it: the three conditional `ret`s
become `nop`s, and an off-screen coordinate is plotted (wrapped) rather than
dropped.

\U0001f3af THE PREDICTION IS ASYMMETRIC, WHICH IS WHAT MAKES IT EVIDENCE:

    clip_noop_x300, clip_noop_xneg, clip_noop_y192, clip_alloff   MOVE
        -- they assert an off-screen plot changes no pixel, and now it does.
    off_ok, clip_offscr_ok, clip_neg_ok, empty, bare_b, offscreen  HOLD
        -- they read only the ERROR CODE, and removing a clip raises nothing.

If the four pixel rows move, they are proven non-vacuous for free and the item's
list shrinks from nine to six without a single synthesised check. If they do NOT
move, the blindness is deeper than the readout and that is worth more than six
checks would have been.
"""
import hashlib
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                                                  # noqa: E402,F401

SRC = os.path.join(ROOT, "sub", "graphics.asm")
ROMS = ("build/zerobas-main-eu.rom", "build/sub.rom")
PROBE = "probes/basic/basic_probe_graphics.py"

# The three bare `ret`s ARE the clip. Each carries its own comment, which is what
# makes the anchor unique -- `ret nz` alone occurs many times in this file.
PLANTS = [
    ("                ret     nz                  ; x high byte != 0 -> x<0 or x>255 -> clip (skip)\n",
     "                nop                         ; MUTANT: x clip removed\n"),
    ("                ret     nz                  ; y high byte != 0 -> clip\n",
     "                nop                         ; MUTANT: y-high clip removed\n"),
    ("                ret     nc                  ; y >= 192 -> clip\n",
     "                nop                         ; MUTANT: y>=192 clip removed\n"),
]
WANT_MOVED = {"clip_noop_x300", "clip_noop_xneg", "clip_noop_y192", "clip_alloff"}
WANT_HELD = {"off_ok", "clip_offscr_ok", "clip_neg_ok",
             "empty", "bare_b", "offscreen"}


def sh(cmd, out):
    with open(out, "w") as f:
        return subprocess.call(cmd, shell=True, cwd=ROOT, stdout=f,
                               stderr=subprocess.STDOUT)


def rom_hash():
    h = hashlib.sha1()
    for r in ROMS:
        p = os.path.join(ROOT, r)
        h.update(open(p, "rb").read() if os.path.exists(p) else b"ABSENT")
    return h.hexdigest()[:12]


def verdicts(path):
    """{row label: PASS/FAIL} from the probe's own per-row lines."""
    out = {}
    for ln in open(path, errors="replace"):
        m = re.match(r"\s+(PASS|FAIL)\s+(\S+)", ln)
        if m:
            out[m.group(2)] = m.group(1)
    return out


def main() -> int:
    sh("make repack-machine", probe_tmp.tmp("pc_base_build.out"))
    base_hash = rom_hash()
    sh(f"caffeinate -i -s python3 {PROBE}", probe_tmp.tmp("pc_base.out"))
    base = verdicts(probe_tmp.tmp("pc_base.out"))
    if len(base) < 50:
        print(f"\U0001f534 BASE TABLE HAS ONLY {len(base)} ROW(S) -- the probe did "
              f"not run properly; refusing to score the arm.")
        return 2
    missing = sorted((WANT_MOVED | WANT_HELD) - set(base))
    if missing:
        print(f"\U0001f534 THE PREDICTION NAMES ROWS THIS RUN DOES NOT HAVE: "
              f"{missing}. A prediction about rows that do not exist is not a "
              f"prediction.")
        return 2
    print(f"base ROMs {base_hash}   {len(base)} rows read")

    orig = open(SRC, errors="replace").read()
    txt = orig
    for find, repl in PLANTS:
        if find not in txt:
            print(f"\U0001f534 PLANT SITE NOT FOUND: {find.strip()[:50]!r}")
            return 2
        txt = txt.replace(find, repl, 1)
    try:
        open(SRC, "w").write(txt)
        rc = sh("make repack-machine", probe_tmp.tmp("pc_arm_build.out"))
        h = rom_hash()
        if rc != 0 or h == base_hash:
            print(f"M-PLOTCLIP: INERT -- rc={rc} roms={h}; DISCARDED")
            return 2
        sh(f"caffeinate -i -s python3 {PROBE}", probe_tmp.tmp("pc_arm.out"))
        got = verdicts(probe_tmp.tmp("pc_arm.out"))
        moved = {k for k in base if got.get(k) != base[k]}
    finally:
        open(SRC, "w").write(orig)
        sh("make repack-machine", probe_tmp.tmp("pc_restore.out"))

    hit = moved & WANT_MOVED
    held = WANT_HELD - moved
    print(f"M-PLOTCLIP: roms={h}   {len(moved)} row(s) moved in total")
    print(f"  predicted-to-MOVE that moved : {sorted(hit)}  "
          f"({len(hit)}/{len(WANT_MOVED)})")
    print(f"  predicted-to-HOLD that held  : {sorted(held)}  "
          f"({len(held)}/{len(WANT_HELD)})")
    other = sorted(moved - WANT_MOVED)
    print(f"  other rows moved             : {len(other)}  {other[:12]}")
    ok = hit == WANT_MOVED and held == WANT_HELD
    print(f"\n{'\U0001f7e2 EXACT' if ok else '\U0001f534 NOT EXACT'} — "
          f"the four pixel clip rows {'ARE' if hit == WANT_MOVED else 'are NOT'} "
          f"falsifiable by a cut at the routine they are about, and the six "
          f"error-code rows {'held' if held == WANT_HELD else 'did NOT all hold'}.")
    print(f"restored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
