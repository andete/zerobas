#!/usr/bin/env python3
r"""D-PUEXP knife -- `^^^^`.

Thirteen of seventeen exponent rows were green on the first build and the four
that were not came from TWO defects, both of which have an arm here so they
cannot come back quietly:

  K-PX1  make the exponent path unreachable
  K-PX2  let the four carets take no width
  K-PX3  drop the point's own column from n
  K-PX4  never write a leading column      <- the pu_sign_tenant defect
  K-PX5  do not force a zero value's exponent to 0
  K-PX6  let a rounding carry not bump the exponent

🎯 K-PX4 IS A REGRESSION ARM FOR A SHIPPED-IN-DRAFT BUG. Writing a SPACE for a
positive value looks harmless and is not: the fixed-point path writes no sign at
all, and pu_sign_tenant PREPENDS its `+` rather than overwriting a blank, so
`+##.##^^^^` overflowed its own field and `**` stopped filling. Its must-hold
list carries `e.negtight`, where the leading character is real.

The other defect -- computing n BEFORE `call flt_fmt` and reading C after, when
BC does not survive the call -- has no arm because it is a reordering rather than
a substitution. It is worth naming anyway: one of its two wrong answers was a
plausible 0, which let `e.round` pass on the same format string that `e.big` and
`e.small` failed on.
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
    "K-PX1": (P, "                jp      m,pnt_exp",
              "                                    ; KNIFE: exponent unreachable",
              {"e.basic", "e.wide", "e.big", "e.zero", "e.comma"},
              {"e.car3", "d.basic", "m.basic"}),
    "K-PX2": (R, "                ld      a,b\n                add     a,4\n                ld      b,a                 ; and they occupy four columns",
              "                ld      a,b\n                ld      b,a                 ; KNIFE: carets take no width",
              {"e.basic", "e.wide"}, {"d.basic", "c.hash"}),
    "K-PX3": (P, "                dec     a                   ; ...and the point's own column",
              "                                            ; KNIFE: point column uncounted",
              {"e.basic", "e.wide", "e.comma"}, {"e.nodot", "d.basic"}),
    "K-PX4": (P, "                ld      a,c\n                or      a\n                jr      nz,pnt_x_sgnd\n                ld      a,'0'",
              "                jr      pnt_x_sgnd          ; KNIFE: no leading column",
              {"e.big", "e.small"},
              {"e.basic", "e.wide", "e.negtight", "d.basic"}),
    "K-PX5": (P, "                ld      a,c                 ; a ZERO value: force the exponent to",
              "                ld      a,b                 ; KNIFE: zero not forced",
              {"e.zero"}, {"e.basic", "e.big", "d.basic"}),
    "K-PX6": (P, "                ld      a,(PU_COMMAS)       ; which the EXPONENT absorbs rather\n                inc     a                   ; than the field (row e.round)",
              "                ld      a,(PU_COMMAS)       ; KNIFE: exponent not bumped",
              {"e.round"}, {"e.basic", "e.big", "e.zero"}),
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
    sh("make repack-machine", "/tmp/zerobas/px_build_base.out")
    base_hash = rom_hash()
    sh("caffeinate -i -s python3 scratchpad/pufloat_probe.py vg8020,cf3300,zb",
       "/tmp/zerobas/px_base.out")
    base = rows("/tmp/zerobas/px_base.out")
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
            rc = sh("make repack-machine", f"/tmp/zerobas/px_{lab}_build.out")
            h = rom_hash()
            if rc != 0 or h == base_hash:
                print(f"{lab}: INERT -- rc={rc} roms={h}; DISCARDED, not green")
                fails += 1
                continue
            sh("caffeinate -i -s python3 scratchpad/pufloat_probe.py vg8020,cf3300,zb",
               f"/tmp/zerobas/px_{lab}.out")
            got = rows(f"/tmp/zerobas/px_{lab}.out")
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
    sh("make repack-machine", "/tmp/zerobas/px_restore.out")
    print(f"\nrestored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}\n"
          f"{len(ARMS) - fails}/{len(ARMS)} arms PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
