#!/usr/bin/env python3
r"""D-DEVBARE K-DB1 — put the `FOR OUTPUT` requirement back.

One cut, and the prediction is exact: the four rows that a bare device OPEN
makes possible must redden, and NOTHING else may. `w.forout` keeps its FOR
clause, so it cannot move; `w.crtlen` is refused by the terminator check rather
than by this branch; `w.crtin`/`w.lptin` are already refused.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard

TMP, SRC = "/tmp/zerobas", "basic/files.asm"
ROW = re.compile(r"^w\.")
CUT = ("                jr      nz,oodv_as          ; no FOR clause -> OUTPUT (measured)",
       "                jr      nz,oo_fail_syn      ; K-DB1 CUT (restored on exit)")
EXPECT = {"w.crtbare", "w.crtwrite", "w.crtclose", "w.lptbare"}


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def read_rows(path):
    rows = {}
    if not os.path.exists(path):
        return rows
    for line in open(path, errors="replace"):
        p = line.split()
        if len(p) >= 2 and ROW.match(p[0]):
            rows[p[0]] = " ".join(p[1:]).replace(" SAME", "").replace(" DIFF", "").strip()
    return rows


def main():
    base = read_rows(f"{TMP}/devbare_zb_base.out")
    if not base:
        print(f"NO BASELINE: ZEROBAS_REFCACHE=0 python3 scratchpad/devbare_probe.py zb "
              f"> {TMP}/devbare_zb_base.out")
        return 2
    print(f"baseline: {len(base)} row(s)\n")
    orig = open(SRC).read()
    if orig.count(CUT[0]) != 1:
        print("KNIFE BROKEN: the retarget is not unique in " + SRC)
        return 1
    restore = lambda: open(SRC, "w").write(orig)
    atexit.register(restore)
    fails = []
    try:
        open(SRC, "w").write(orig.replace(*CUT))
        before = knife_guard.hashes()
        print("K-DB1: planted, rebuilding...")
        moved, after, rc = knife_guard.build(f"{TMP}/db1_build.out", before)
        print(knife_guard.report("K-DB1", moved, before, after))
        if rc or not moved:
            print("K-DB1: BUILD FAILED or ROM unchanged")
            return 1
        sh("ZEROBAS_REFCACHE=0 python3 scratchpad/devbare_probe.py zb",
           f"{TMP}/db1.out")
    finally:
        restore(); atexit.unregister(restore)
    cut = read_rows(f"{TMP}/db1.out")
    if not cut:
        print("  🔴 NO ROWS READ BACK — not 'reddened nothing'")
        fails.append("readback")
    else:
        moved_rows = sorted(r for r in base if base[r] != cut.get(r))
        ok = set(moved_rows) == EXPECT
        print(f"  moved {len(moved_rows)}: {' '.join(moved_rows) or '(none)'}"
              f"\n  want  {len(EXPECT)}: {' '.join(sorted(EXPECT))}"
              f"   {'OK' if ok else '🔴 MISMATCH'}")
        if not ok:
            fails.append("K-DB1")
    sh("make repack-machine", f"{TMP}/db1_restore.out")
    print("=" * 68)
    print("VERDICT:", "arm live" if not fails else f"🔴 {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
