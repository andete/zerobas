#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Knives for playqueue-acceptance (D-PLAYQUEUE). Each cut is byte-neutral and must
turn both zerobas rows red. The ROMs are hashed around every cut, an unbuilt cut
is refused, and build() lets the clock tick (make's 1-second mtimes).

  K-A  sub/playparse.asm a window writes from the GET pointer (`ld a,(iy+QD_PUT)`
       -> `ld a,(iy+QD_GET)` in pt_window): what is queued is overwritten -- replace
  K-S  basic/playsvc.asm an end marker never waits (`ld (iy+QD_PUTBAK),a` ->
       three `nop`s): no sync
  K-F  sub/playparse.asm a full ring does not end the window (`jr c,pk_full` ->
       `jr c,$+2`): PLAY never waits, the ring overruns
  K-Z  sub/playparse.asm a rest queues 2 of its 3 bytes (its duration high
       byte's `ld a,h / call pt_put` -> four `nop`s). (The first K-Z declared a
       note 6 B to pt_pkt and MISSED: that moves only the window's bookkeeping,
       never what reaches the ring, which is what QUETAB's put pointer shows.)
"""
import hashlib, os, subprocess, sys, time
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(REPO)
KNIVES_ALL = [
    ("K-A", "sub/playparse.asm", "playqueue",
     "                ld      a,(iy+QD_PUT)\n                ld      (ix+VCX_WPUT),a\n",
     "                ld      a,(iy+QD_GET)\n                ld      (ix+VCX_WPUT),a\n"),
    ("K-S", "basic/playsvc.asm", "playqueue",
     "                ld      (iy+QD_PUTBAK),a    ; waiting\n",
     "                nop\n                nop\n                nop                 ; waiting\n"),
    ("K-F", "sub/playparse.asm", "playqueue",
     "                jr      c,pk_full\n",
     "                jr      c,$+2\n"),
    ("K-Z", "sub/playparse.asm", "playqueue",
     "                ld      a,l\n                call    pt_put\n                ld      a,h\n                call    pt_put\n                jp      pt_ch_loop\n",
     "                ld      a,l\n                call    pt_put\n                nop\n                nop\n                nop\n                nop\n                jp      pt_ch_loop\n"),
]
KNIVES = [k for k in KNIVES_ALL if not sys.argv[1:] or k[0] in sys.argv[1:]]
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
    ok = set(red) == set(ZB)          # two programs: a machine can be red twice
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
