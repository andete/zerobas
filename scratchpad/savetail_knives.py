#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-SAVETAIL knives: each cut must move EXACTLY its own rows of
probes/disk/disk_probe_savetail.py.

  K-ST1  basic/save.asm sav_flag_a's first check back to `load_error`
         -> disk_b, cas_b DIVERGE (an option that is not A)
  K-ST2  its second (junk after `,A`) -> disk_a1, cas_a1 DIVERGE

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
KNIVES = {
    "K-ST1": ("basic/save.asm",
              "                jp      nz,stmt_error       ; only ,A is supported: Syntax error\n",
              "                jp      nz,load_error       ; K-ST1 CUT (restored on exit)\n",
              {"disk_b", "cas_b"}),
    "K-ST2": ("basic/save.asm",
              "                jp      nz,stmt_error       ; trailing junk after ,A: likewise\n",
              "                jp      nz,load_error       ; K-ST2 CUT (restored on exit)\n",
              {"disk_a1", "cas_a1"}),
}
TMP = "/tmp/zerobas"
PROBE = "ZEROBAS_BASIC_MACHINE=C-BIOS_MSX1_EU_REPACK_DISK python3 -u probes/disk/disk_probe_savetail.py"


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def diverging(log):
    return {m.group(1) for m in re.finditer(r"^DIFF (\S+)", open(log, errors="replace").read(), re.M)}


def main():
    os.makedirs(TMP, exist_ok=True)
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
        got = diverging(f"{TMP}/{k}_probe.out")
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'}  {k}: diverged {sorted(got)} (want exactly {sorted(want)})")
        if not ok:
            fails.append(k)
    sh("make repack-machine", f"{TMP}/stknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
