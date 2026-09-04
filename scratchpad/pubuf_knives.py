#!/usr/bin/env python3
r"""D-PUBUF knife -- PRINT USING's numeric render buffer.

`NUMBUF` is EIGHT bytes at $E0C0, shared with print.asm / list.asm /
str-engine.asm. PRINT USING has been rendering into it, and D-PUCOMMA made
`12,345,678` -- eleven bytes with its terminator -- which runs into VALTYP and
STRPTR. Those are rewritten by the next evaluation, so it stayed invisible.

🎯 IT IS NOT INVISIBLE AT FOURTEEN. `USING"##.##^^^^";1.5E+10` renders
`15000000000.00` -- FIFTEEN bytes -- which reaches PRDEST ($E0CB), the cell
PRINT reads to choose its sink. The row printed NOTHING AT ALL, and an empty
column reads like a row with nothing to say rather than the defect itself.

  K-PB1  point the render buffer back at NUMBUF
         -> e.huge goes SILENT again; the short-field rows must not move.
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
S = "basic/sysvars.inc"
ARMS = {
    "K-PB1": (S, "PU_NUM          equ     DETOKBUF + 256      ; PRINT USING numeric render buffer,",
              "PU_NUM          equ     $E0C0               ; KNIFE: back onto the 8-byte NUMBUF",
              {"e.huge"},
              {"d.basic", "c.hash", "m.small", "d.wide", "a.dot"}),
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
    sh("make repack-machine", "/tmp/zerobas/pb_build_base.out")
    base_hash = rom_hash()
    sh("caffeinate -i -s python3 probes/basic/basic_probe_pusing.py vg8020,cf3300,zb",
       "/tmp/zerobas/pb_base.out")
    base = rows("/tmp/zerobas/pb_base.out")
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
            rc = sh("make repack-machine", f"/tmp/zerobas/pb_{lab}_build.out")
            h = rom_hash()
            if rc != 0 or h == base_hash:
                print(f"{lab}: INERT -- rc={rc} roms={h}; DISCARDED, not green")
                fails += 1
                continue
            sh("caffeinate -i -s python3 probes/basic/basic_probe_pusing.py vg8020,cf3300,zb",
               f"/tmp/zerobas/pb_{lab}.out")
            got = rows(f"/tmp/zerobas/pb_{lab}.out")
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
    sh("make repack-machine", "/tmp/zerobas/pb_restore.out")
    print(f"\nrestored {rom_hash()} (base {base_hash}) "
          f"{'OK' if rom_hash() == base_hash else '*** MISMATCH ***'}\n"
          f"{len(ARMS) - fails}/{len(ARMS)} arms PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
