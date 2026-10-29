#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""nodev-acceptance (D-NODEV): with no disk, a name with a `:` anywhere is 56.

Found by the program ladder's L4_errors: `OPEN "NUL:" FOR INPUT` on zerobas's
diskless target waited ~4.5 s for a tape header and gave ERR 19, where the
VG-8020 (no disk) raises 56 at once. The diskless rule recognised only a
drive's second-character colon, so `"NUL:"`, `"AB:"`, `":X"`, `"FOO:BAR"`
went to the cassette (FOR OUTPUT even opened it).

One program, scratchpad/nodev_open.bas: eleven names OPENed FOR OUTPUT (no
tape wait on either machine), each ERR printed. The printer log must equal
the VG-8020's on the DISKLESS target. The DISK target is not run: it is a disk
machine (`X:` is 62 Bad drive name there, `FOO` 70 Disk offline with no disk
in the drive), whose reference is the CF-3300, not the diskless VG-8020.

Clean-room: typed keys and a tape in; the printer port out.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "programs"))
import run_programs                                  # noqa: E402

PROG = "scratchpad/nodev_open.bas"


def main():
    text = open(os.path.join(REPO, PROG)).read()
    ref = run_programs.run(run_programs.REF, "nodev", text)
    print(f"{run_programs.REF:30} {ref[0]}  {ref[1].strip()!r}")
    bad = 0
    for m in ["C-BIOS_MSX1_EU_REPACK_NODISK"]:
        zb = run_programs.run(m, "nodev", text)
        ok = zb[1] == ref[1] and ref[1].count("[") == 11
        bad += not ok
        print(f"{m:30} {zb[0]}  {'SAME' if ok else 'DIVERGES'}")
        if not ok:
            print(f"      zb: {zb[1].strip()!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: a device-like name is `Bad file name` "
          f"without a disk, as on the VG-8020")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
