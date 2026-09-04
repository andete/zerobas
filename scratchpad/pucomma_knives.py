#!/usr/bin/env python3
r"""D-PUCOMMA knife -- eight comma rows went green on the FIRST build, which is
the pattern that most deserves suspicion.

  K-PC1  skip the comma pass entirely
  K-PC2  consume the `,` WITHOUT widening the field
  K-PC3  group in TWOS instead of threes
  K-PC4  drop bit7 from the routing, so an integer comma field takes pu_fmt_int

🎯 K-PC4 IS THE INTERESTING ONE. Its must-HOLD list is `m.small`, `m.trail` and
`m.dot`: two of those render identically through the plain integer path (no comma
is needed at 3 digits, and a trailing `,` prints none), and `m.dot` is a float so
it routes on bit6 regardless. The arm therefore names exactly which rows are
paying for the renderer -- if the must-holds moved, the routing change would be
doing something broader than the claim.
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
P, R, M = "sub/punum.asm", "basic/pu-render.inc", "basic/printusing.asm"
ARMS = {
    "K-PC1": (P, "                bit     7,a\n                jp      z,pnt_point",
              "                bit     7,a\n                jp      pnt_point           ; KNIFE: no commas",
              {"m.basic", "m.big", "m.dot", "m.neg", "m.pos"},
              {"m.small", "m.trail", "m.lead", "d.basic"}),
    "K-PC3": (P, "                ld      l,3                 ; L = digits left in this group",
              "                ld      l,2                 ; KNIFE: group in twos",
              {"m.basic", "m.big", "m.dot", "m.pos"},
              {"m.small", "m.trail", "d.basic"}),
    "K-PC2": (R, "ptf_num_wide:\n                inc     b                   ; `#` and `,` both take a column",
              "                inc     c\n                jr      ptf_num_lp          ; KNIFE: `,` takes no column\n"
              "ptf_num_wide:\n                inc     b",
              {"m.basic", "m.small"}, {"d.basic", "c.hash"}),
    "K-PC4": (M, "                and     $C0                 ; bit6 `.` or bit7 `,` -- either one",
              "                and     $40                 ; KNIFE: `,` not routed",
              # 🔴 I PREDICTED THIS ARM WRONG. `m.big` (1234567) and `m.pos`
              # (12345678) are past int16, so BASIC holds them as floats and they
              # reach the renderer on bit6's path no matter what bit7 does -- the
              # routing bit only decides for values that really are integers.
              # The two int16 comma rows are the whole must-move set.
              {"m.basic", "m.neg"},
              {"d.basic", "m.dot", "m.small", "m.trail", "m.big", "m.pos"}),
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
    sh("make repack-machine", "/tmp/zerobas/pc_build_base.out")
    base_hash = rom_hash()
    sh("caffeinate -i -s python3 probes/basic/basic_probe_pusing.py vg8020,cf3300,zb",
       "/tmp/zerobas/pc_base.out")
    base = rows("/tmp/zerobas/pc_base.out")
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
            rc = sh("make repack-machine", f"/tmp/zerobas/pc_{lab}_build.out")
            h = rom_hash()
            if rc != 0 or h == base_hash:
                print(f"{lab}: INERT -- rc={rc} roms={h}; DISCARDED, not green")
                fails += 1
                continue
            sh("caffeinate -i -s python3 probes/basic/basic_probe_pusing.py vg8020,cf3300,zb",
               f"/tmp/zerobas/pc_{lab}.out")
            got = rows(f"/tmp/zerobas/pc_{lab}.out")
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
    sh("make repack-machine", "/tmp/zerobas/pc_restore.out")
    print(f"\nrestored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}\n"
          f"{len(ARMS) - fails}/{len(ARMS)} arms PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
