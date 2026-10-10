#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-READERL knives: each cut must move EXACTLY its predicted rows of
probes/basic/basic_probe_readerl.py, judged on the zerobas column against the
uncut build's.

  K-RE1  exr_syn's ERRLIN store cut         -> trapped untrap listdot direct directdot
  K-RE2  ex_read's DATALINE restore cut     -> after
  K-RE3  the abort's ERRLIN read -> 65535   -> untrap listdot direct directdot reraise
  K-RE4  the tenant's RDV_LINE store cut    -> all but reraise

🔴 RESTORE ON EVERY EXIT: originals in memory, put back by try/finally AND
atexit; knife_guard proves the cut reached the installed ROM. A run with rows
missing refuses (D-KNIFEROWS).
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ALL = {"trapped", "untrap", "listdot", "direct", "directdot", "after", "reraise"}
KNIVES = {
    "K-RE1": ("basic/program.asm",
              "                ld      (ERRLIN),de\n                ld      (DOT),de\n",
              "                nop                         ; K-RE1 CUT\n                nop\n                nop\n                nop\n                ld      (DOT),de\n",
              {"trapped", "untrap", "listdot", "direct", "directdot"}),
    "K-RE2": ("basic/program.asm",
              "                ld      (DATALINE),hl       ; HL stays the item's line for exr_syn\n",
              "                nop                         ; K-RE2 CUT\n                nop\n                nop\n",
              {"after"}),
    "K-RE3": ("basic/arrays.asm",
              "                ld      de,(ERRLIN)\n",
              "                ld      de,$FFFF            ; K-RE3 CUT\n                nop\n",
              {"untrap", "listdot", "direct", "directdot", "reraise"}),
    "K-RE4": ("basic/readdata-body.inc",
              "                ld      (RDV_LINE),hl\n",
              "                nop                         ; K-RE4 CUT\n                nop\n                nop\n",
              ALL - {"reraise"}),
}
TMP = "/tmp/zerobas"
PROBE = "python3 -u probes/basic/basic_probe_readerl.py"


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def zb(log):
    return {m.group(1): m.group(2) for m in
            re.finditer(r"^ROW (\w+) VG=\[.*?\] ZB=\[(.*?)\] ", open(log, errors="replace").read(), re.M)}


def main():
    os.makedirs(TMP, exist_ok=True)
    sh("make repack-machine", f"{TMP}/reknife_base_build.out")
    sh(PROBE, f"{TMP}/reknife_base.out")
    base = zb(f"{TMP}/reknife_base.out")
    if set(base) != ALL:
        print(f"BASELINE BROKEN: rows {sorted(base)}")
        return 2
    fails = []
    for k, (src, old, new, want) in KNIVES.items():
        orig = open(src).read()
        if orig.count(old) != 1:
            print(f"KNIFE BROKEN: {k} anchor count {orig.count(old)} in {src}")
            return 2
        restore = lambda o=orig, f=src: open(f, "w").write(o)
        atexit.register(restore)
        try:
            open(src, "w").write(orig.replace(old, new))
            before = knife_guard.hashes()
            moved, after, rc = knife_guard.build(f"{TMP}/{k}_build.out", before)
            print(knife_guard.report(k, moved, before, after))
            if rc:
                print(f"{k}: BUILD FAILED with the cut in -- {TMP}/{k}_build.out")
                return 2
            if not moved:
                print(f"{k}: refusing to score an INERT cut")
                return 2
            sh(PROBE, f"{TMP}/{k}_probe.out")
        finally:
            restore()
            atexit.unregister(restore)
        cut = zb(f"{TMP}/{k}_probe.out")
        if set(cut) != ALL:
            print(f"{k}: KNIFE RUN INCOMPLETE -- rows {sorted(ALL - set(cut))} never printed; "
                  f"refusing to score them as unmoved ({TMP}/{k}_probe.out)")
            return 2
        got = {r for r, v in cut.items() if v != base.get(r)}
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'}  {k}: moved {sorted(got)} (want exactly {sorted(want)})")
        if not ok:
            fails.append(k)
    sh("make repack-machine", f"{TMP}/reknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
