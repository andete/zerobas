#!/usr/bin/env python3
"""D-PAINTVRAM knife runner. Predictions: scratchpad/paintvram_knives.md,
written BEFORE any of this ran.

Discipline ([[zerobas-gate-operating-rules]]): `rm -rf build` before EVERY build
(a source write landing in the same mtime tick as the last restore's artifacts
has made `make` skip a knife before), assert the sub.rom hash MOVED on the cut
and RETURNED on the restore, and restore by WRITING THE BYTES, never copy2.

    python3 -u scratchpad/paintvram_knife_run.py [K-PV1 ...]
"""
from __future__ import annotations
import hashlib, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ASM = os.path.join(REPO, "sub", "graphics.asm")
SUBROM = os.path.join(REPO, "build", "sub.rom")
MAINROM = os.path.join(REPO, "build", "zerobas-main-eu.rom")

PAT0 = """                ld      c,0
                call    gfx_wr_raw          ; pattern := $00 (blind: no read)"""
PATFF = """                ld      c,$FF
                call    gfx_wr_raw          ; KNIFED: pattern := $FF"""
COLC = """                ld      a,(GFX_C)
                ld      c,a
                call    gfx_wr_raw          ; colour := C (fg nibble 0)"""
COLB = """                ld      a,(GFX_B)
                ld      c,a
                call    gfx_wr_raw          ; KNIFED: colour := B"""
LEFT = "                sub     (hl)                ; A = D - PXL (D is inside the span)"
LEFTX = "                sub     d                   ; KNIFED: always 0 -> no left partial"
RIGHT = """                ld      a,(GFX_PXR)
                sub     c"""
RIGHTX = """                ld      a,(GFX_PXL)         ; KNIFED: PXL, not PXR
                sub     c"""

KNIVES = {
    "K-PV1": ("gfx_span_bytes: pattern := $FF instead of $00 (SHARED with LINE ,BF)",
              lambda s: s.replace(PAT0, PATFF, 1)),
    "K-PV2": ("gfx_paint_row: left-partial count forced to 0",
              lambda s: s.replace(LEFT, LEFTX, 1)),
    "K-PV3": ("gfx_paint_row: right partial measured from PXL, not PXR",
              lambda s: s.replace(RIGHT, RIGHTX, 1)),
    "K-PV4": ("gfx_span_bytes: fill colour from GFX_B instead of GFX_C",
              lambda s: s.replace(COLC, COLB, 1)),
}


def sh(cmd, log):
    with open(log, "w") as f:
        return subprocess.run(cmd, shell=True, cwd=REPO, stdout=f,
                              stderr=subprocess.STDOUT).returncode


def h(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:8]


def build(tag):
    sh("rm -rf build", f"/tmp/pvk_{tag}_rm.log")
    if sh("make repack-machine", f"/tmp/pvk_{tag}_build.log"):
        return None, None
    return h(SUBROM), h(MAINROM)


def main() -> int:
    want = [k for k in sys.argv[1:] if k in KNIVES] or list(KNIVES)
    orig = open(ASM).read()
    bs, bm = build("base")
    print(f"unknifed  sub.rom={bs}  main={bm}\n")
    fails = 0
    try:
        for name in want:
            desc, patch = KNIVES[name]
            print(f"########## {name} -- {desc}")
            cut = patch(orig)
            if cut == orig:
                print("  🔴 PATCH DID NOT APPLY -- scores nothing"); fails += 1; continue
            open(ASM, "w").write(cut)
            ks, km = build(name)
            if ks is None:
                print(f"  🔴 KNIFED TREE DOES NOT BUILD (/tmp/pvk_{name}_build.log)")
                print("     -- the cut is real but UNSCOREABLE; reported, not hidden")
                fails += 1
                open(ASM, "w").write(orig); build(f"{name}_restore"); continue
            if ks == bs:
                print(f"  🔴 sub.rom HASH UNCHANGED ({ks}) -- THE KNIFE DID NOT TAKE")
                fails += 1
            else:
                print(f"  sub.rom {bs} -> {ks} (cut took); main {bm} -> {km}"
                      f" {'(unmoved, as expected for a sub/ edit)' if km == bm else '🔴 MAIN MOVED'}")
            sh("python3 -u scratchpad/paintvram_rows.py", f"/tmp/pvk_{name}_rows.log")
            sh("python3 -u scratchpad/vram_fidelity.py linebf paint flood",
               f"/tmp/pvk_{name}_fid.log")
            for tag, log in (("rows", f"/tmp/pvk_{name}_rows.log"),
                             ("fidelity", f"/tmp/pvk_{name}_fid.log")):
                print(f"  --- {tag} ---")
                for l in open(log).read().splitlines():
                    if (l.startswith(("  PASS", "  FAIL")) or "IDENTICAL" in l
                            or "DIFFERS" in l or l.startswith("PHASE")):
                        print("  " + l.rstrip())
            print()
    finally:
        open(ASM, "w").write(orig)
        rs, rm = build("restore")
        ok = rs == bs and rm == bm
        print(f"restored sub.rom={rs} main={rm}  "
              f"{'OK' if ok else '🔴 RESTORE DID NOT RETURN THE BASELINE'}")
        fails += not ok
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
