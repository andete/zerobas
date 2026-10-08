#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-CASBIN knives: each cut must move EXACTLY its own rows of
probes/basic/basic_probe_casbin.py (bnn bty bbare bnodev lbin cbin).

  K-BN1  cas_skip_data's binary arm cut (a $D0 file stops the search) -> bnn, bnodev, lbin, cbin
  K-BN2  BLOAD's `set 6` cut (BLOAD then wants an ASCII file)           -> bnn, bty, bbare, bnodev
  K-BN3  isd_tape's `dec hl` cut (the diskless name read from char 2)   -> bnodev

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
KNIVES = {
    "K-BN1": ("basic/casmatch-body.inc",
              "                jr      z,csd_bin           ; D-CASBIN: a BSAVE file, stepped over\n",
              "                nop                         ; K-BN1 CUT (restored on exit)\n"
              "                nop\n",
              {"bnn", "bnodev", "lbin", "cbin"}),
    "K-BN2": ("basic/bload-body.inc",
              "                set     6,(hl)              ; BLOAD wants $D0\n",
              "                nop                         ; K-BN2 CUT (restored on exit)\n"
              "                nop\n",
              {"bnn", "bty", "bbare", "bnodev"}),
    "K-BN3": ("basic/bload-body.inc",
              "                dec     hl                  ; D-CASBIN: back to the name's FIRST char --\n",
              "                nop                         ; K-BN3 CUT (restored on exit)\n",
              {"bnodev"}),
}
TMP = "/tmp/zerobas"
PROBE = "python3 -u probes/basic/basic_probe_casbin.py"


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
    sh("make repack-machine", f"{TMP}/bnknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
