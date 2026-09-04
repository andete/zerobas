#!/usr/bin/env python3
r"""D-PUDOT knife -- `.` went green on 11 rows at once, which is exactly what a
single "the format is now WIDER" change would also look like.

  K-PD1  never round        -> d.roundup/d.grow/d.growfrac move; d.basic MUST NOT
  K-PD2  drop the carry's `inc c`  -> only the two GROWTH rows move
  K-PD3  re-plant the REVERTED attempt's bug (no point when places==0)
  K-PD4  skip the leading-zero emit -- asks which form flt_fmt produces
  K-PD5  stop counting the places in the field WIDTH

🎯 K-PD2 IS WHY d.grow AND d.growfrac WERE ADDED. Every other d.* row rounds
without gaining an integer digit, so against the old row set that arm would have
moved nothing and reported "unwitnessed" -- a designed no-op, not a control.

K-PD1's must-hold is `d.basic` (1.5 at 2 places is EXACT: no rounding to remove).
"""
import atexit, hashlib, os, re, signal, subprocess, sys

# ⚠️ A `finally` DOES NOT SURVIVE SIGTERM, AND A PLANT THAT OUTLIVES ITS RUN IS
# INVISIBLE. Two runs of this file were lost to exactly that: one killed by
# `pkill`, one by a 2-minute command timeout. Each left a plant in a tracked
# source file, and the NEXT run then read the planted file as its baseline --
# a knife measuring itself. The tell was two live `KNIFE` markers in the tree,
# not anything either run printed.
#
# So the original goes to a SIDECAR ON DISK before the plant, and is restored
# from there at startup by any later run. The sidecar existing at all is the
# alarm: it means a previous run did not finish.
BAK = ".knifebak"


def _restore_all(verbose=True):
    n = 0
    for f in {a[0] for a in ARMS.values()}:
        if os.path.exists(f + BAK):
            os.replace(f + BAK, f)
            n += 1
            if verbose:
                print(f"🔴 LEFTOVER PLANT in {f} -- restored from sidecar")
    return n

ROMS = ("build/zerobas-main-eu.rom", "build/sub.rom")
P, R = "sub/punum.asm", "basic/pu-render.inc"
ARMS = {
    "K-PD1": (P, "                jr      c,pnt_point         ; below half -> plain truncation",
              "                jr      pnt_point           ; KNIFE: never round",
              {"d.roundup", "d.grow", "d.growfrac"}, {"d.basic", "d.int", "c.over16"}),
    "K-PD2": (P, "                inc     c                   ; one more integer digit",
              "                                            ; KNIFE: growth not counted",
              {"d.grow", "d.growfrac"}, {"d.round", "d.roundup", "d.basic"}),
    "K-PD3": (P, "pnt_point:\n                ld      a,(PU_FLAGS)",
              "pnt_point:\n                ld      a,(PU_DEC)\n                or      a\n"
              "                jr      z,pnt_term          ; KNIFE: the reverted bug\n"
              "                ld      a,(PU_FLAGS)",
              {"d.roundup", "d.grow"}, {"d.basic", "d.growfrac"}),
    "K-PD4": (P, "                jr      nz,pnt_places\n                ld      a,'0'",
              "                jr      pnt_places\n                ld      a,'0'",
              {"d.leadzero"}, {"d.basic", "d.zero"}),
    "K-PD5": (R, "                ld      a,(PU_DEC)\n                add     a,b\n                ld      b,a",
              "                ld      a,(PU_DEC)\n                ld      a,b\n"
              "                ld      b,a                 ; KNIFE: places unwidened",
              {"d.basic", "d.wide"}, {"c.hash", "c.round"}),
    # K-PD6 re-plants the CURSOR REWIND that the first cut of this scanner
    # shipped with: `push bc` to save the width, which saves the scan cursor too.
    # Its must-hold list is the whole point -- eleven `d.*` rows cannot see it.
    "K-PD6": (R, "ptf_dec_done:\n                ld      a,(PU_FLAGS)",
              "ptf_dec_done:\n                ld      a,c\n                push    hl\n"
              "                ld      hl,PU_DEC\n                sub     (hl)\n"
              "                pop     hl\n                ld      c,a         ; KNIFE: rewind\n"
              "                ld      a,(PU_FLAGS)",
              {"n.dot"}, {"d.basic", "d.wide", "d.roundup", "a.dot", "p.dot"}),
}


def sh(cmd, out):
    with open(out, "w") as f:
        return subprocess.call(cmd, shell=True, stdout=f, stderr=subprocess.STDOUT)


def rom_hash():
    h = hashlib.sha1()
    for r in ROMS:
        h.update(open(r, "rb").read() if os.path.exists(r) else b"ABSENT")
    return h.hexdigest()[:12]


def rows(path):
    txt = open(path).read()
    if "references agree on" not in txt:
        return None
    out = {}
    for line in txt.splitlines():
        m = re.match(r"^(\S+)\s+('.*?')\s+('.*?')\s+('.*?')\s", line)
        if m:
            out[m.group(1)] = m.group(4)
    return out or None


def main():
    if _restore_all():
        print("   (a previous run was killed mid-arm; tree repaired, "
              "re-measuring from clean)\n")
    atexit.register(_restore_all, False)
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))
    for r in ROMS:
        if os.path.exists(r):
            os.remove(r)
    sh("make repack-machine", "/tmp/zerobas/pd_build_base.out")
    base_hash = rom_hash()
    sh("caffeinate -i -s python3 probes/basic/basic_probe_pusing.py vg8020,cf3300,zb",
       "/tmp/zerobas/pd_base.out")
    base = rows("/tmp/zerobas/pd_base.out")
    if base is None:
        print("🔴 BASE RUN UNREADABLE -- refusing to run any arm"); return 2
    print(f"base ROMs {base_hash}   {len(base)} rows read\n")
    fails = 0
    for lab, (f, find, repl, want, keep) in ARMS.items():
        orig = open(f).read()
        if find not in orig:
            print(f"{lab}: PLANT SITE NOT FOUND in {f} -- arm skipped, NOT green")
            fails += 1
            continue
        open(f + BAK, "w").write(orig)      # crash-safe: disk, not a local
        open(f, "w").write(orig.replace(find, repl, 1))
        for r in ROMS:
            if os.path.exists(r):
                os.remove(r)
        try:
            rc = sh("make repack-machine", f"/tmp/zerobas/pd_{lab}_build.out")
            h = rom_hash()
            if rc != 0 or h == base_hash:
                print(f"{lab}: INERT -- rc={rc} roms={h}; DISCARDED, not green")
                fails += 1
                continue
            sh("caffeinate -i -s python3 probes/basic/basic_probe_pusing.py vg8020,cf3300,zb",
               f"/tmp/zerobas/pd_{lab}.out")
            got = rows(f"/tmp/zerobas/pd_{lab}.out")
            if got is None:
                print(f"{lab}: roms={h} 🔴 UNREADABLE run -- NOT scored")
                fails += 1
                continue
            moved = {k for k in base if got.get(k) != base[k]}
            ok = want <= moved and not (keep & moved)
            fails += 0 if ok else 1
            print(f"{lab}: roms={h}\n"
                  f"    moved     {sorted(moved) or '<none>'}\n"
                  f"    must-move {sorted(want)} -> {'yes' if want <= moved else 'NO'}\n"
                  f"    must-hold {sorted(keep)} -> "
                  f"{'held' if not (keep & moved) else 'MOVED'}   "
                  f"{'PASS' if ok else 'FAIL'}")
        finally:
            open(f, "w").write(orig)
            if os.path.exists(f + BAK):
                os.remove(f + BAK)
            for r in ROMS:
                if os.path.exists(r):
                    os.remove(r)
    sh("make repack-machine", "/tmp/zerobas/pd_restore.out")
    print(f"\nrestored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}\n"
          f"{len(ARMS) - fails}/{len(ARMS)} arms PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
