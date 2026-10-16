#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-WSZERO S16 knife: the string-heap parameter block on the Z80 stack. Do the
rows see the block's address, its result register, its slot map, the tenant's IY
discipline and the one aliasing reorder? Main-side cuts are size-neutral (the
pins); sub-side cuts stay inside sub page 0's free bytes.

K-WS89 the tenant ALSO copies its 8-byte block to the old SH_* home ($EFCA) at
       entry -> `s16sh` (which sums $EFCA..$EFDB after every op) DIVERGES, alone
K-WS90 sh_go returns A = 0 and Z always (`or a` -> `xor a`): every ERR and CMP's
       bits vanish -> ovcat (ERR 15), ovval / ovread (VAL's codes), ovcmp (the
       relation bits) DIVERGE -- scored as "these four are among the diverging"
K-WS91 VAL's integer result slot moved (SHB_VINT 4 -> 6, over the type) -> VAL /
       READ integers are wrong -> ovval, ovread DIVERGE -- scored as "among"
K-WS92 heap_alloc no longer restores IY on success (its `pop iy` -> `inc sp /
       inc sp`, same size): an op that allocates then writes through a garbage IY
       -> ovgc (heavy allocation) DIVERGES -- scored as "among"
K-WS93 she_snap_slice's reorder undone (the PTR store before the SRC read, which
       shares its slot): RIGHT$ of an ARRAY ELEMENT reads its own result as the
       source -> ovslice DIVERGES -- scored as "among"
"""
import os, subprocess, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scratchpad"))
os.chdir(REPO)
import knife_guard                                 # noqa: E402

TMP = os.path.join(tempfile.gettempdir(), "zerobas", "wszero_s16_knife")
ROWS = ["ctl", "s16sh", "ovcat", "ovslice", "ovgc", "ovcmp", "ovval", "ovread"]
KNIVES = [
    ("K-WS89", "sub/strheap.asm",
     [("                push    hl\n                pop     iy                  ; IY = the parameter block (sh_go's HL),\n",
       "                push    hl\n                ld      de,$EFCA            ; KNIFE: the old home\n"
       "                ld      bc,8\n                ldir\n                pop     hl\n"
       "                push    hl\n                pop     iy                  ; IY = the parameter block (sh_go's HL),\n")],
     ["s16sh"], "exact"),
    ("K-WS90", "basic/str-engine.asm",
     [("                or      a                   ; Z iff ERR = 0, CF = 0\n",
       "                xor     a                   ; KNIFE: A = 0, Z always\n")],
     ["ovcat", "ovval", "ovread", "ovcmp"], "among"),
    ("K-WS91", "sub/strheap.asm",
     [("SHB_VINT        equ     4\n", "SHB_VINT        equ     6\n")],
     ["ovval", "ovread"], "among"),
    ("K-WS92", "sub/strheap.asm",
     [("                inc     sp                  ; deallocate the 4-byte frame\n                pop     iy\n                scf",
       "                inc     sp                  ; deallocate the 4-byte frame\n                inc     sp                  ; KNIFE: IY not restored\n                inc     sp\n                scf")],
     ["ovgc"], "among"),
    ("K-WS93", "sub/strheap.asm",
     [("                ld      c,(iy+SHB_SRC)      ; SRC FIRST: PTR shares its slot (S16)\n"
       "                ld      b,(iy+SHB_SRC+1)\n                call    she_putp\n",
       "                call    she_putp            ; KNIFE: PTR first\n"
       "                ld      c,(iy+SHB_SRC)\n                ld      b,(iy+SHB_SRC+1)\n")],
     ["ovslice"], "among"),
]


def cut(text, edits):
    for old, new in edits:
        if text.count(old) != 1:
            raise SystemExit(f"anchor x{text.count(old)}: {old[:60]!r}")
        text = text.replace(old, new)
    return text


def suite(tag, rows):
    log = f"{TMP}/{tag}.log"
    with open(log, "w") as fh:
        subprocess.call([sys.executable, "-u", "probes/basic/basic_probe_wszero.py", *rows],
                        stdout=fh, stderr=subprocess.STDOUT, timeout=5400)
    return [ln.split()[1] for ln in open(log) if ln.startswith("ROW") and "DIVERGES" in ln]


def main():
    os.makedirs(TMP, exist_ok=True)
    saved = {f: open(f).read() for _t, f, _e, _p, _m in KNIVES}
    for _t, f, edits, _p, _m in KNIVES:
        cut(saved[f], edits)                        # refuses before anything is touched
    only = sys.argv[1:]
    for tag, f, edits, pred, mode in KNIVES:
        if only and tag not in only:
            continue
        before = knife_guard.hashes()
        try:
            open(f, "w").write(cut(saved[f], edits))
            moved, _, brc = knife_guard.build(f"{TMP}/mk_{tag}.log", before)
            pins = subprocess.call(["make", "pin-check"], stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
            if brc or not moved or pins:
                print(f"{tag}: build rc={brc} ROM moved={moved} pin-check rc={pins} -- NOT SCORED",
                      flush=True)
                continue
            subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
            red = suite(tag, ROWS)
            hit = sorted(red) == sorted(pred) if mode == "exact" else set(pred) <= set(red)
            print(f"{tag}: diverging {red}; predicted {'exactly' if mode == 'exact' else 'among them'} "
                  f"{pred} -> {'HIT' if hit else 'MISS'}", flush=True)
        finally:
            for p, t in saved.items():
                open(p, "w").write(t)
    _, _, brc = knife_guard.build(f"{TMP}/mk_restore.log", knife_guard.hashes(), clean=True)
    subprocess.call(["make", "repack-machine"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    red = suite("restore", ROWS)
    print(f"restored: build rc={brc}; {'DIVERGE ' + str(red) if red else 'SAME'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
