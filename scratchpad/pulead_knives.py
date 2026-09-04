#!/usr/bin/env python3
r"""D-PULEAD knife -- `.##`, a numeric field with NO integer column.

  K-PL1  do not start a field on a leading `.`
  K-PL2  do not mark the field as having no integer column
  K-PL3  keep flt_fmt's lone `0` instead of dropping it
  K-PL4  widen the places mask back to $7F

🎯 K-PL4 GUARDS A CONSEQUENCE, NOT A FEATURE. Claiming PU_DEC bit6 for this
slice made every existing `and $7F` on that cell wrong -- three of them, across
two files -- because places would then read as 64 + places. Nothing about the
`.##` rows says "check the mask"; this arm is here because the change that
enabled them silently moved a boundary somewhere else.

K-PL2 and K-PL3 separate two things that look like one: whether the format HAS an
integer column, and whether flt_fmt happened to produce a digit for it. `.##`
with .5 has neither; `.##` with 0 has the second but not the first, and that is
the row (`d.leadzer`) that tells them apart.
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
    "K-PL1": (R, "                cp      '#'\n                jp      z,ptf_num\n                ; --- D-PULEAD",
              "                cp      '#'\n                jp      z,ptf_num\n                jr      ptf_notdot          ; KNIFE: no leading-dot field\n                ; --- D-PULEAD",
              {"d.lead", "d.leadone", "d.leadzer"},
              {"d.leadzero", "d.basic", "c.hash"}),
    "K-PL2": (R, "                or      $40                 ; D-PULEAD: no integer column at all",
              "                or      $00                 ; KNIFE: column not marked",
              {"d.lead", "d.leadzer"},
              {"d.leadzero", "d.basic", "d.leadover"}),
    # 🔴 THIS ARM READ FAIL ON ITS FIRST RUN AND THE CODE WAS FINE. Inverting
    # `jr z` to `jr nz` does not "keep the lone zero" -- it drops every NON-zero
    # digit, so d.leadover lost its `1` and the must-hold list fired correctly.
    # Suppressing a branch means REMOVING it, not reversing it.
    "K-PL3": (P, "                cp      '0'\n                jr      z,pnt_dropz",
              "                cp      '0'                 ; KNIFE: lone 0 kept",
              {"d.leadzer"},
              {"d.leadover", "d.leadzero", "d.basic"}),
    "K-PL4": (P, "                and     $3F",
              "                and     $7F                 ; KNIFE: bit6 leaks into places",
              {"d.lead", "d.leadzer"},
              {"d.basic", "d.wide", "c.hash"}),
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
    sh("make repack-machine", "/tmp/zerobas/pl_build_base.out")
    base_hash = rom_hash()
    sh("caffeinate -i -s python3 probes/basic/basic_probe_pusing.py vg8020,cf3300,zb",
       "/tmp/zerobas/pl_base.out")
    base = rows("/tmp/zerobas/pl_base.out")
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
            rc = sh("make repack-machine", f"/tmp/zerobas/pl_{lab}_build.out")
            h = rom_hash()
            if rc != 0 or h == base_hash:
                print(f"{lab}: INERT -- rc={rc} roms={h}; DISCARDED, not green")
                fails += 1
                continue
            sh("caffeinate -i -s python3 probes/basic/basic_probe_pusing.py vg8020,cf3300,zb",
               f"/tmp/zerobas/pl_{lab}.out")
            got = rows(f"/tmp/zerobas/pl_{lab}.out")
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
    sh("make repack-machine", "/tmp/zerobas/pl_restore.out")
    print(f"\nrestored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}\n"
          f"{len(ARMS) - fails}/{len(ARMS)} arms PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
