#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""nobasic-acceptance / nobasic-all-acceptance: zerobas's disk ROM on C-BIOS hosts with NO BASIC (C-BIOS integration
step 3; D-DISKMSX2HOST, 2026-11-27: one ROM for every C-BIOS config family).

    disk_probe_nobasichosts.py [VARIANT ...]      (default: all 12 -- tools/install_cbios_msx2.NOBASIC)

Installs CBIOS2_CUR_<VARIANT>_NOBASIC_DISK for each variant from tools/cbios-nobasic.pin (C-BIOS's ROMs by SHA-1, this
tree's build/disk.rom in the subslot the config leaves free -- the installer prints which), then per variant runs:
  * disk_probe_dossession -- the typed MSX-DOS session against the CF-3300 (21 rows + the disk image);
  * disk_probe_nobasicreach -- no disk-ROM path enters zerobas's main ROM, every run witnessed booting our ROM and
    reaching its BDOS (the variant's disk subslot).
Exit: 0 every variant green; 2 if any is an INSTRUMENT FAULT (the install refused, a reach run without witnesses, no
subslot reported); else 1. Never green on a variant that did not run.

Before D-DISKMSX2HOST the ROM assumed MSX1's layout (RAM in subslot 0, itself in 1): MSX2 restarted, MSX2+ never
reached our BDOS (scratchpad/AE_msx2host1.out); after it, 12 of 12 (scratchpad/AE_msx2host2.out).
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "tools"))
ALL = ["MSX1_EU", "MSX1", "MSX1_JP", "MSX1_BR", "MSX2", "MSX2_EU", "MSX2_JP", "MSX2_BR",
       "MSX2P", "MSX2P_EU", "MSX2P_JP", "MSX2P_BR"]


def done(p):
    return p.returncode, p.stdout + p.stderr


# every spawn below is a LIST LITERAL with no `-machine` (tools/check_probe_preflight.py): the sub-probes guard
# their own openMSX launches
KW = dict(cwd=REPO, capture_output=True, text=True, timeout=1800)


def main():
    vs = sys.argv[1:] or ALL
    bad_v = [v for v in vs if v not in ALL]
    if bad_v:
        print(f"nobasichosts: unknown variant(s) {bad_v}")
        return 2
    rc, out = done(subprocess.run(["python3", "tools/install_cbios_msx2.py", "--pinned", "--variants", ",".join(vs)],
                                  env=dict(os.environ), **KW))
    print(out.strip())
    if rc:
        print("nobasichosts: INSTRUMENT FAULT -- the pinned install refused")
        return 2
    sub = dict(re.findall(r"installed: CBIOS2_CUR_(\S+)_NOBASIC_DISK\s+\(disk in (3-\d)", out))
    red, fault = [], []
    for v in vs:
        if v not in sub:
            print(f"=== {v}: no subslot reported by the installer")
            fault.append(v)
            continue
        m = f"CBIOS2_CUR_{v}_NOBASIC_DISK"
        env = dict(os.environ, DOSSESSION_ZB_MACHINE=m, NOBASICREACH_MACHINE=m, NOBASICREACH_SLOT=sub[v])
        r1, o1 = done(subprocess.run(["python3", "-u", "probes/disk/disk_probe_dossession.py"], env=env, **KW))
        r2, o2 = done(subprocess.run(["python3", "-u", "probes/disk/disk_probe_nobasicreach.py"], env=env, **KW))
        s1 = next((ln for ln in reversed(o1.splitlines()) if ln.startswith(("PASS", "FAIL", "INSTRUMENT"))), "<none>")
        s2 = next((ln for ln in reversed(o2.splitlines()) if ln.startswith("nobasicreach:")), "<none>")
        print(f"=== {v} (disk {sub[v]}): session rc={r1} {s1}\n{'':20s}reach rc={r2} {s2}", flush=True)
        if r1 or r2:
            print("\n".join("    | " + ln for ln in (o1 if r1 else o2).splitlines()[:60]))
        (fault if 2 in (r1, r2) else red if (r1 or r2) else []).append(v)
    print(f"nobasichosts: {len(vs) - len(red) - len(fault)}/{len(vs)} green"
          + (f"; RED {red}" if red else "") + (f"; INSTRUMENT FAULT {fault}" if fault else ""))
    return 2 if fault else 1 if red else 0


if __name__ == "__main__":
    sys.exit(main())
