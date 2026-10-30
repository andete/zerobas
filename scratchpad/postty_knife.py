#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Knives for D-POSTTY. Each cut is byte-neutral and must turn both zerobas rows
red in its own witness. The ROMs are hashed around every cut, an unbuilt cut is
refused, and build() lets the clock tick (make's 1-second mtimes).

  K-P  basic/expr.asm POS(0) reads the screen cursor again (`ld a,(TTYPOS)` ->
       `ld a,(CSRX)`)                          witness: postty-acceptance
  K-W  sub2/scrstmt.asm WIDTH leaves the print column (`xor a` /
       `ld (TTYPOS),a` -> four `nop`s)        witness: postty-acceptance
  K-O  basic/repl.asm the prompt's new line follows the cursor again
       (`ld a,(TTYPOS)` / `or a` -> `ld a,(CSRX)` / `dec a`, the pre-fix pair;
       swapping only the load made it ALWAYS open a line, which G2's ending
       needs anyway, so it missed)            witness: the ladder's G2_runner
"""
import hashlib, os, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
GATE = [sys.executable, "-u", "probes/basic/basic_probe_postty.py"]
G2 = [sys.executable, "-u", "probes/programs/run_programs.py", "--gaps", "G2_runner"]
KNIVES = [
    ("K-P", "basic/expr.asm", "                ld      a,(TTYPOS)          ; 0-based already\n",
     "                ld      a,(CSRX)            ; 0-based already\n", GATE),
    ("K-W", "sub2/scrstmt.asm",
     "                xor     a                   ; D-POSTTY: and BASIC's print column with it\n"
     "                ld      (TTYPOS),a ",
     "                nop                         ; D-POSTTY: and BASIC's print column with it\n"
     "                nop\n                nop\n                nop        ", GATE),
    ("K-O", "basic/repl.asm",
     "                ld      a,(TTYPOS)          ; D-POSTTY: BASIC's print column decides,\n"
     "                or      a ",
     "                ld      a,(CSRX)            ; D-POSTTY: BASIC's print column decides,\n"
     "                dec     a ", G2),
]
ZB = sorted(["C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK"])


def hashes():
    h = hashlib.sha256()
    for f in sorted(os.listdir("build")):
        if f.endswith(".rom"):
            h.update(open(os.path.join("build", f), "rb").read())
    return h.hexdigest()[:8]


def build():
    r = subprocess.run(["make", "repack-machine"], capture_output=True, text=True)
    if r.returncode:
        sys.exit("build failed:\n" + r.stdout[-2000:] + r.stderr[-2000:])
    time.sleep(1.1)


build()
base = hashes()
hit = 0
for name, path, old, new, cmd in KNIVES:
    src = open(path).read()
    if src.count(old) != 1:
        sys.exit(f"{name}: anchor found {src.count(old)} times")
    open(path, "w").write(src.replace(old, new))
    try:
        build()
        cut = hashes()
        if cut == base:
            sys.exit(f"{name}: ROMs did not move ({cut}) -- refusing an inert knife")
        r = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        open(path, "w").write(src)
    red = sorted(ln.split()[0] for ln in r.stdout.splitlines()
                 if "DIVERGES" in ln or "DIFFERS" in ln)
    ok = red == ZB
    hit += ok
    print(f"{name} ROMs {base} -> {cut}  red {red}  {'HIT' if ok else 'MISS'}", flush=True)
build()
after = hashes()
print(f"restored ROMs {after} {'== clean' if after == base else '!= CLEAN'}")
print(f"{hit}/{len(KNIVES)} knives HIT")
sys.exit(0 if after == base and hit == len(KNIVES) else 1)
