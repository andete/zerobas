#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-DISKMSX2HOST: the no-BASIC MSX-DOS session and the reach proof on every C-BIOS NOBASIC_DISK variant.

Installs all 12 from tools/cbios-nobasic.pin, then per variant runs disk_probe_dossession (zerobas side = the
variant, CF-3300 the reference) and disk_probe_nobasicreach (the variant's disk subslot), one emulator at a time,
and prints one verdict line per variant plus the tail of each run.
    python3 -u scratchpad/msx2host_run.py [VARIANT ...]
"""
import os
import subprocess
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALL = ["MSX1_EU", "MSX1", "MSX1_JP", "MSX1_BR", "MSX2", "MSX2_EU", "MSX2_JP", "MSX2_BR",
       "MSX2P", "MSX2P_EU", "MSX2P_JP", "MSX2P_BR"]


def run(cmd, env):
    t = time.time()
    p = subprocess.run(cmd, cwd=REPO, env=env, capture_output=True, text=True, timeout=1800)
    return p.returncode, (p.stdout + p.stderr), time.time() - t


def main():
    vs = sys.argv[1:] or ALL
    rc, out, _ = run(["python3", "tools/install_cbios_msx2.py", "--pinned", "--variants", ",".join(vs)], dict(os.environ))
    print(out.strip())
    if rc:
        return rc
    rows = []
    for v in vs:
        m = f"CBIOS2_CUR_{v}_NOBASIC_DISK"
        sub = "3-3" if v.startswith("MSX2P") else "3-1"
        env = dict(os.environ, DOSSESSION_ZB_MACHINE=m, NOBASICREACH_MACHINE=m, NOBASICREACH_SLOT=sub)
        r1, o1, t1 = run(["python3", "-u", "probes/disk/disk_probe_dossession.py"], env)
        r2, o2, t2 = run(["python3", "-u", "probes/disk/disk_probe_nobasicreach.py"], env)
        last1 = [ln for ln in o1.splitlines() if ln.strip()][-1:] or ["<no output>"]
        last2 = [ln for ln in o2.splitlines() if ln.startswith("nobasicreach:")][-1:] or ["<no verdict>"]
        rows.append((v, r1, r2))
        print(f"\n=== {v} ({sub})  dossession rc={r1} {t1:.0f}s | reach rc={r2} {t2:.0f}s")
        print("  session: " + last1[0][:200])
        print("  reach:   " + last2[0][:200])
        print("  --- session output ---")
        print("\n".join("    " + ln for ln in o1.splitlines()[-40:]))
        sys.stdout.flush()
    print("\nSUMMARY")
    for v, r1, r2 in rows:
        print(f"  {v:9s} session rc={r1}  reach rc={r2}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
