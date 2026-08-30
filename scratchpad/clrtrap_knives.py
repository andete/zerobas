#!/usr/bin/env python3
r"""D-CLRTRAP — one arm, and it has to read TWO probes.

  K-CT1  cut `clear_vars`'s `call trap_init`. BOTH filed defects must come back,
         and they are different rows in different probes:
           * scratchpad/clrarm_probe.py  `CLEAR, trap still armed`, zb second
             window: 0 -> nonzero (an ARMED trap survives CLEAR).
           * scratchpad/clrtrapstk_probe.py  `CLEAR, still SERVICING`, zb fires:
             1 -> >=2 (a KILLED trap comes back through a stale TRAPSTK record).
         🎯 ONE CUT, TWO INDEPENDENT WITNESSES. Either alone would leave the
         other's mechanism unproved -- the arm-state reset and the service-stack
         reset are the same three bytes but not the same defect.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/vars.asm"
CUT = ("""                call    trap_init""",
       """                                            ; K-CT1 CUT (restored on exit)""")


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


# 🔴 SPLIT ON THE `zb` FIELD, NOT ON A COLUMN INDEX. Both probes left-justify a
# label that contains SPACES, and the two labels have different word counts
# ("CLEAR, trap still armed" is four, "CLEAR, still SERVICING" is three) -- so a
# fixed index reads the side name as a number on one probe and the right cell on
# the other. The first version did exactly that and died on `int('zb')`.
def _after_zb(path, label, n):
    """-> the n-th numeric field after the `zb` side marker on `label`'s row."""
    for line in open(path, errors="replace"):
        if line.startswith(label):
            f = line.split()
            if "zb" in f:
                return int(f[f.index("zb") + n])
    return None


def armed_second_window(path):
    """-> the zb second-window fire count. total @CLEAR 2ndwin -> 3rd after zb."""
    return _after_zb(path, "CLEAR, trap still armed", 3)


def trapstk_fires(path):
    """-> the zb fire count on the `CLEAR, still SERVICING` row."""
    return _after_zb(path, "CLEAR, still SERVICING", 1)


def main():
    orig = open(SRC).read()
    if orig.count(CUT[0]) != 1:
        print("KNIFE BROKEN: `call trap_init` is not unique in " + SRC)
        return 1
    restore = lambda: open(SRC, "w").write(orig)
    atexit.register(restore)
    fails = []
    try:
        open(SRC, "w").write(orig.replace(*CUT))
        before = knife_guard.hashes()
        print("K-CT1: planted, rebuilding...")
        moved, after, rc = knife_guard.build(f"{TMP}/ct1_build.out", before)
        print(knife_guard.report("K-CT1", moved, before, after))
        if rc or not moved:
            print("K-CT1: BUILD FAILED or ROM unchanged")
            return 1
        sh("python3 scratchpad/clrarm_probe.py", f"{TMP}/ct1_arm.out")
        sh("python3 scratchpad/clrtrapstk_probe.py", f"{TMP}/ct1_stk.out")
    finally:
        restore(); atexit.unregister(restore)

    arm = armed_second_window(f"{TMP}/ct1_arm.out")
    stk = trapstk_fires(f"{TMP}/ct1_stk.out")
    if arm is None or stk is None:
        print(f"  🔴 NO READING BACK (arm={arm} stk={stk}) — not 'reddened nothing'")
        fails.append("readback")
    else:
        ok_a, ok_s = arm > 0, stk >= 2
        print(f"  armed-trap 2nd window: {arm}  (want > 0, the ARM state surviving)"
              f"   {'OK' if ok_a else '🔴 MISS'}")
        print(f"  TRAPSTK fires:         {stk}  (want >= 2, the KILLED trap back)"
              f"   {'OK' if ok_s else '🔴 MISS'}")
        if not ok_a:
            fails.append("armed")
        if not ok_s:
            fails.append("trapstk")
    sh("make repack-machine", f"{TMP}/ct1_restore.out")
    print("=" * 68)
    print("VERDICT:", "arm live on both witnesses" if not fails else f"🔴 {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
