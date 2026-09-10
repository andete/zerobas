#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""M-PSETPLOT — make an off-screen PSET *plot*, which is the arm M-PLOTCLIP proved is needed.

M-PLOTCLIP (2026-09-10) cut the TENANT's clip (`gfx_plot_cur`'s three bare
`ret`s) and the four pixel clip rows did NOT move -- refuting my own prediction
and locating their decision elsewhere. `basic/graphics.asm` says where, in the
comment above the branch: this `jp nc` "IS WHAT MAKES GFX_OP=1'S ALIASED
MARSHALLING SAFE" -- the tenant's op-1 arm reads `GXPOS`/`GYPOS` LOW BYTE and
"0..255 guaranteed in-range", and THIS branch is that guarantee.

\U0001f3af SO PSET AND LINE CLIP IN DIFFERENT PLACES, and that is the whole
reason 35 arms never moved these rows: PSET is refused in the RESIDENT, before
the tenant is ever called, while LINE/CIRCLE/DRAW are clipped inside it. A cut at
one site cannot move rows that belong to the other.

Removing the branch lets an off-screen coordinate through to a tenant that
assumes it is in range -- so it plots at the LOW BYTE, which is exactly the
address these rows read:

    clip_noop_x300   PSET(300,100)  reads (44,100)    300 & 255 = 44
    clip_noop_xneg   PSET(-1,0)     reads (248,0)      -1 & 255 = 255? -> 248 band
    clip_noop_y192   PSET(0,192)    reads the sprite-attribute area it would land in

\U0001f3af THE PREDICTION, AND ITS ASYMMETRY IS THE EVIDENCE:

    clip_noop_x300, clip_noop_xneg, clip_noop_y192   MOVE  -- PSET rows, this site
    clip_alloff                                      HOLDS -- LINE(300,300)-(400,400),
        a TENANT-path row; M-PLOTCLIP already failed to move it, so if it holds
        here too its decision is at a THIRD site (a whole-segment line clipper)
    off_ok, clip_offscr_ok, clip_neg_ok, empty, bare_b, offscreen   HOLD
        -- error-code-only, and removing a guard raises nothing
    pset_offscr_ok                                   HOLDS -- it asserts NO ERROR,
        and an off-screen PSET that plots still raises nothing

⚠️ THE BRANCH IS LOAD-BEARING FOR AN INVARIANT, NOT JUST FOR A PIXEL. Its own
comment warns "DO NOT MOVE THE TENANT CALL ABOVE THIS TEST" because the work-area
cells stop being the plot target without it. That is precisely why it is worth a
knife: an invariant one instruction wide should have a row that notices when it
goes.
"""
import hashlib
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "lib"))
import probe_tmp                                                  # noqa: E402,F401

SRC = os.path.join(ROOT, "basic", "graphics.asm")
ROMS = ("build/zerobas-main-eu.rom", "build/sub.rom")
PROBE = "probes/basic/basic_probe_graphics.py"
FIND = ("                jp      nc,exec_stmt        "
        "; off-screen -> no plot (work area already moved)\n")
REPL = "                ; MUTANT: the off-screen guard removed\n"
WANT_MOVED = {"clip_noop_x300", "clip_noop_xneg", "clip_noop_y192"}
WANT_HELD = {"clip_alloff", "off_ok", "clip_offscr_ok", "clip_neg_ok",
             "empty", "bare_b", "offscreen", "pset_offscr_ok"}


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
    out = {}
    for ln in open(path, errors="replace"):
        m = re.match(r"\s+(PASS|FAIL)\s+(\S+)", ln)
        if m:
            out[m.group(2)] = m.group(1)
    return out


def main() -> int:
    sh("make repack-machine", probe_tmp.tmp("pp_base_build.out"))
    base_hash = rom_hash()
    sh(f"caffeinate -i -s python3 {PROBE}", probe_tmp.tmp("pp_base.out"))
    base = verdicts(probe_tmp.tmp("pp_base.out"))
    if len(base) < 50:
        print(f"\U0001f534 BASE TABLE HAS ONLY {len(base)} ROW(S) -- refusing.")
        return 2
    missing = sorted((WANT_MOVED | WANT_HELD) - set(base))
    if missing:
        print(f"\U0001f534 THE PREDICTION NAMES ROWS THIS RUN DOES NOT HAVE: "
              f"{missing}")
        return 2
    print(f"base ROMs {base_hash}   {len(base)} rows read")

    orig = open(SRC, errors="replace").read()
    if orig.count(FIND) != 1:
        print(f"\U0001f534 PLANT SITE NOT UNIQUE ({orig.count(FIND)} hit(s))")
        return 2
    try:
        open(SRC, "w").write(orig.replace(FIND, REPL, 1))
        rc = sh("make repack-machine", probe_tmp.tmp("pp_arm_build.out"))
        h = rom_hash()
        if rc != 0 or h == base_hash:
            print(f"M-PSETPLOT: INERT -- rc={rc} roms={h}; DISCARDED")
            return 2
        sh(f"caffeinate -i -s python3 {PROBE}", probe_tmp.tmp("pp_arm.out"))
        got = verdicts(probe_tmp.tmp("pp_arm.out"))
        moved = {k for k in base if got.get(k) != base[k]}
    finally:
        open(SRC, "w").write(orig)
        sh("make repack-machine", probe_tmp.tmp("pp_restore.out"))

    hit, held = moved & WANT_MOVED, WANT_HELD - moved
    other = sorted(moved - WANT_MOVED)
    print(f"M-PSETPLOT: roms={h}   {len(moved)} row(s) moved in total")
    print(f"  predicted-to-MOVE that moved : {sorted(hit)}  ({len(hit)}/{len(WANT_MOVED)})")
    print(f"  predicted-to-HOLD that held  : {sorted(held)}  ({len(held)}/{len(WANT_HELD)})")
    print(f"  other rows moved             : {len(other)}  {other[:12]}")
    ok = hit == WANT_MOVED and held == WANT_HELD
    print(f"\n{'\U0001f7e2 EXACT' if ok else '\U0001f534 NOT EXACT'}")
    print(f"restored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
