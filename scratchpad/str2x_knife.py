#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Knives for prstr2x-acceptance (D-PRSTR2X) and keyrepaint-acceptance
(D-KEYREPAINT). Each cut is byte-neutral and must turn both zerobas rows of ITS
gate red. The ROMs are hashed around every cut, an unbuilt cut is refused, and
build() lets the clock tick (make's 1-second mtimes).

  K-R  basic/print.asm exp_num_slhs rewinds to the item's START and runs it
       through `eval` again (`pop de`/`call eval_slhs` -> `pop hl`/`call eval`):
       the old double read, INKEY$ / INPUT$ consume two keys
  K-K  sub/keystr.asm a stored definition never repaints (`ret z` after the
       CNSDFG test -> `ret`): the row keeps the old text
  K-M  sub/keystr.asm the text-mode test never declines (`ret nc` -> `nop`):
       SCREEN 2 paints the row into its pattern table
"""
import hashlib, os, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
KNIVES = [
    ("K-R", "basic/print.asm", "prstr2x",
     "                pop     de                  ; drop the item's START\n"
     "                call    eval_slhs ",
     "                pop     hl                  ; drop the item's START\n"
     "                call    eval      "),
    ("K-K", "sub/keystr.asm", "keyrepaint",
     "                ld      a,(CNSDFG)\n                or      a\n                ret     z\n"
     "                ld      a,(SCRMOD)\n                cp      2\n                ret     nc\n"
     "                jp      ks_paint",
     "                ld      a,(CNSDFG)\n                or      a\n                ret\n"
     "                ld      a,(SCRMOD)\n                cp      2\n                ret     nc\n"
     "                jp      ks_paint"),
    ("K-M", "sub/keystr.asm", "keyrepaint",
     "                cp      2\n                ret     nc\n                jp      ks_paint",
     "                cp      2\n                nop\n                jp      ks_paint"),
]
ZB = ["C-BIOS_MSX1_EU_REPACK_NODISK", "C-BIOS_MSX1_EU_REPACK_DISK"]


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
for name, path, gate, old, new in KNIVES:
    src = open(path).read()
    if src.count(old) != 1:
        sys.exit(f"{name}: anchor found {src.count(old)} times")
    open(path, "w").write(src.replace(old, new))
    try:
        build()
        cut = hashes()
        if cut == base:
            sys.exit(f"{name}: ROMs did not move ({cut}) -- refusing an inert knife")
        r = subprocess.run([sys.executable, "-u", f"probes/basic/basic_probe_{gate}.py"],
                           capture_output=True, text=True)
    finally:
        open(path, "w").write(src)
    red = sorted(ln.split()[0] for ln in r.stdout.splitlines() if "DIVERGES" in ln)
    ok = red == sorted(ZB)
    hit += ok
    print(f"{name} ROMs {base} -> {cut}  red {red}  {'HIT' if ok else 'MISS'}", flush=True)
    for ln in r.stdout.splitlines():
        if ln.startswith("      ref"):
            print("   " + ln.strip())
build()
after = hashes()
print(f"restored ROMs {after} {'== clean' if after == base else '!= CLEAN'}")
print(f"{hit}/{len(KNIVES)} knives HIT")
sys.exit(0 if after == base and hit == len(KNIVES) else 1)
