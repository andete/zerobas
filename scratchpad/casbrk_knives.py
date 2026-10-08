#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASBRK knives: each cut must move EXACTLY its own rows of
probes/basic/basic_probe_casbrk.py (dload / pload / pcload / prun / popen / pmerge).

  K-CB1  LOAD/CLOAD/RUN's header-search carry back to dpl_err   -> dload, pload, pcload, prun
  K-CB2  OPEN FOR INPUT's header-search carry back to load_error -> popen
  K-CB3  MERGE's header-search carry back to mc_ioerr            -> pmerge

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
KNIVES = {
    "K-CB1": ("basic/cload.asm",
              "                jp      c,dpl_dio           ; tape error / Ctrl-STOP abort: 19 (D-CASBRK)\n",
              "                jp      c,dpl_err           ; K-CB1 CUT (restored on exit)\n",
              {"dload", "pload", "pcload", "prun"}),
    "K-CB2": ("basic/files.asm",
              "                jp      c,dpl_dio           ; D-CASBRK: an I/O error / Ctrl-STOP is 19, raised\n",
              "                jp      c,oocas_ioerr       ; K-CB2 CUT (restored on exit)\n",
              {"popen"}),
    "K-CB3": ("basic/files.asm",
              "                jp      c,dpl_dio           ; D-CASBRK: 19, raised. mc_ioerr's disk_error\n",
              "                jp      c,mc_ioerr          ; K-CB3 CUT (restored on exit)\n",
              {"pmerge"}),
}
TMP = "/tmp/zerobas"
PROBE = "python3 -u probes/basic/basic_probe_casbrk.py"


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def diverging(log):
    return {m.group(1) for m in re.finditer(r"^DIVERGES (\w+)", open(log, errors="replace").read(), re.M)}


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
    sh("make repack-machine", f"{TMP}/cbknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
