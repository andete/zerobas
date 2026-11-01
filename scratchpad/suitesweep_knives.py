#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-SUITESWEEP step 2a: can each never-red suite catch a knife in its OWN subject?

scratchpad/suite_census.py listed the gate suites that have never gone red in any
recorded run. Never red can mean "blind" or "guards something nobody broke", and
only a planted fault tells them apart. For each candidate: ONE same-length
instruction change in the code the suite is NAMED for (designed by a read-only
study on 2026-11-01, every anchor unique in its file), rebuild, hash EVERY built
ROM (a plant that moved nothing is refused, not read), run ONLY that suite,
restore. Step 2b -- which OTHER suites catch the same knife (redundancy) -- needs
whole batteries and runs later, only for the suites that pass here.

    python3 -u scratchpad/suitesweep_knives.py [SUITE ...]
"""
import glob
import hashlib
import os
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# suite, file, unique anchor (a substring of one line), replacement for it
KNIVES = [
    ("ctrlkeys-acceptance", "cbios-repack/ctrl-keys.patch",
     "+                and     $1F", "+                and     $3F"),
    ("math-acceptance", "basic/expr.asm",
     "jr      z,evmc_int_pack     ; positive: truncate == floor already",
     "jr      nz,evmc_int_pack    ; positive: truncate == floor already"),
    ("ifsem-acceptance", "basic/interp.asm",
     "inc     b                   ; a nested IF claims the next ELSE",
     "nop                         ; a nested IF claims the next ELSE"),
    ("width-acceptance", "sub2/scrstmt.asm",
     "ld      a,40                ; (no flags -- the `dec a` Z survives)",
     "ld      a,41                ; (no flags -- the `dec a` Z survives)"),
    ("lineerr-acceptance", "basic/graphics.asm",
     "jp      z,loc_missing       ; end of line / next statement -> ERR 24",
     "jp      z,elg_syntax        ; end of line / next statement -> ERR 24"),
    ("arrdim-acceptance", "sub/arrays.asm",
     "jp      c,aal_soor          ; D-ARR-B site B -- see aal_soor",
     "jp      c,aal_oom           ; D-ARR-B site B -- see aal_soor"),
    ("nodisk-acceptance", "basic/files.asm",
     "jp      gb_illegal          ; Illegal function call -- TRAPPABLE,",
     "jp      loc_missing         ; Illegal function call -- TRAPPABLE,"),
    ("dout-acceptance", "disk/kernel.asm",
     "ld      a, $1A              ; CP/M text EOF, as the CF-3300's CLOSE",
     "ld      a, $1B              ; CP/M text EOF, as the CF-3300's CLOSE"),
    ("intarg-acceptance", "basic/interp.asm",
     "and     $C0                 ; 0..16383 iff $0000..$3FFF",
     "and     $80                 ; 0..16383 iff $0000..$3FFF"),
    ("pulong-acceptance", "basic/pu-render.inc", "cp      25", "cp      26"),
    ("catterm-acceptance", "basic/str-engine.asm",
     "ld      a,10                ; type mismatch, unless the operand's",
     "ld      a,11                ; type mismatch, unless the operand's"),
    ("basicint-acceptance", "basic/field.asm",
     "call    relink              ; the game's own loader set the links",
     "ld      de,relink           ; the game's own loader set the links"),
    ("inputary-acceptance", "basic/input.asm",
     "jp      z,tgt_store_num     ; an int16 in DE",
     "jp      nz,tgt_store_num    ; an int16 in DE"),
    ("string-acceptance", "sub/strheap.asm",
     "ld      a,1                 ; rhslen > lhslen -> lhs < rhs",
     "ld      a,4                 ; rhslen > lhslen -> lhs < rhs"),
    ("binfre-acceptance", "sub/strheap.asm", "ld      c,16", "ld      c,15"),
    ("biosregs-acceptance", "cbios-repack/bios-regs.patch",
     "+                sub     e", "+                cp      e"),
    ("instr128-acceptance", "sub/strheap.asm",
     "inc     a                   ; A = max_start (recomputed)",
     "dec     a                   ; A = max_start (recomputed)"),
    ("loaddi-acceptance", "disk/kernel.asm",
     "ei                          ; D-LOADDI: the hook arrives through",
     "di                          ; D-LOADDI: the hook arrives through"),
    ("caswbrk-acceptance", "tape/tape.asm",
     "call    cas_stop_w      ; until the key is up; CF = failed",
     "ld      de,cas_stop_w   ; until the key is up; CF = failed"),
    ("sound-acceptance", "basic/sound.asm",
     "cp      14                  ; registers 0..13 are the writable PSG set;",
     "cp      15                  ; registers 0..13 are the writable PSG set;"),
]


def sh(cmd):
    return subprocess.run(cmd, shell=True, cwd=REPO, capture_output=True, text=True)


def roms():
    h = hashlib.sha256()
    for f in sorted(glob.glob(os.path.join(REPO, "build", "*.rom"))):
        h.update(open(f, "rb").read())
    return h.hexdigest()[:12]


def main():
    only = sys.argv[1:]
    for suite, path, old, new in KNIVES:
        full = os.path.join(REPO, path)
        if os.path.exists(full) and open(full).read().count(old) != 1:
            sys.exit(f"{suite}: anchor not unique in {path}")
    b = sh("make repack-machine")
    if b.returncode:
        sys.exit("the BASE tree does not build")
    base = roms()
    print("base roms", base, flush=True)
    for suite, path, old, new in KNIVES:
        if only and suite not in only:
            continue
        full = os.path.join(REPO, path)
        keep = open(full).read()
        open(full, "w").write(keep.replace(old, new))
        try:
            b = sh("make repack-machine")
            h = roms() if b.returncode == 0 else "BUILD-FAILED"
            if h == "BUILD-FAILED" or h == base:
                why = "the build FAILED" if h == "BUILD-FAILED" else "no ROM moved (inert plant)"
                print(f"{suite:24s} NO READING: {why}", flush=True)
                if b.returncode:
                    print("   " + (b.stdout + b.stderr).strip().splitlines()[-1][:150], flush=True)
                continue
            g = sh(f"make {suite}")
            verdict = "CAUGHT (red)" if g.returncode else "MISSED (green)"
            tail = (g.stdout + g.stderr).strip().splitlines()[-1:] or [""]
            print(f"{suite:24s} roms {h}  {verdict}   last line: {tail[0][:110]}", flush=True)
        finally:
            open(full, "w").write(keep)
    sh("make repack-machine")
    print("restored roms", roms(), "(base", base + ")", flush=True)


if __name__ == "__main__":
    main()
