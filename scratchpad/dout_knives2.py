#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""S10.B increment 2 knives (APPEND on disk.rom's writer): each cut must move
EXACTLY its own rows of probes/disk/disk_probe_dout.py, and no other.

  K-AP1  disk.rom hk_fapp no longer steps back onto a trailing Ctrl-Z, so the
         old Ctrl-Z stays inside the file -> app6, app256, append DIVERGE
  K-AP2  basic/expr.asm LOC's DOUT_MODE arm cut (LOC reads LOF again)
         -> app6, app256 DIVERGE (on OUTPUT LOF = LOC, so no other row sees it)

🔴 RESTORE ON EVERY EXIT (D-KNIFEGUARD): originals held in memory, put back by
try/finally AND atexit; knife_guard proves each cut reached the installed ROM.
"""
import atexit, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import knife_guard                  # D-KNIFEROM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
KNIVES = {
    "K-AP1": ("disk/kernel.asm",
              """                cp      $1A
                jr      nz, hfa_pos
                dec     bc                  ; a Ctrl-Z: the next byte goes ON it
""",
              """                cp      $1A
                jr      hfa_pos             ; K-AP1 CUT (restored on exit)
                dec     bc
""",
              {"app6", "app256", "append"}),
    "K-AP2": ("basic/expr.asm",
              """                cp      DOUT_MODE
                jr      nz,ev_ff_lof_checked ; sequential/device: LOC == LOF
""",
              """                cp      DOUT_MODE
                jr      ev_ff_lof_checked   ; K-AP2 CUT (restored on exit)
""",
              {"app6", "app256"}),
}
TMP = "/tmp/zerobas"
PROBE = "ZEROBAS_BASIC_MACHINE=C-BIOS_MSX1_EU_REPACK_DISK python3 -u probes/disk/disk_probe_dout.py"


def sh(cmd, log):
    with open(log, "w") as fh:
        return subprocess.call(cmd, shell=True, stdout=fh, stderr=subprocess.STDOUT)


def diverging(log):
    return {m.group(1) for m in re.finditer(r"^DIVERGES (\S+)", open(log, errors="replace").read(), re.M)}


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
    sh("make repack-machine", f"{TMP}/apknife_restore.out")
    print(f"\n{'ALL KNIVES BITE, EACH ON ITS OWN ROWS' if not fails else 'FAILED: ' + ', '.join(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
