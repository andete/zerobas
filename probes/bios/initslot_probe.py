#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""initslot-acceptance (D-INITSLOT): the BIOS's cartridge search keeps the slot ID across
a cartridge's INIT call, so a cartridge whose INIT RETURNS does not stop the search.

Cartridge A (slot 1) writes $5A to $E001 in INIT and returns; cartridge B (slot 2)
writes $A5 to $E000. Each machine boots with both; a write watchpoint on each cell,
fired with the PC in that cartridge's own slot, records that its INIT ran -- the cells
themselves can be overwritten later by BASIC's own RAM set-up. PASS = both INITs ran on
the VG-8020, the NMS 8250 and both zerobas machines. Stock C-BIOS (0.29/0.30: the
`push af` after the VDP wait saved the VDP status, not the slot ID) is printed as the
negative control: it runs slot 1's INIT only.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "lib"))
import omsx_preflight  # noqa: E402

OMSX = shutil.which("openmsx") or "/Applications/openMSX.app/Contents/MacOS/openmsx"
MUST = ["Philips_VG_8020", "Philips_NMS_8250", "C-BIOS_MSX1_EU_REPACK_NODISK",
        "C-BIOS_MSX1_EU_REPACK_DISK"]
CONTROL = "C-BIOS_MSX1_EU"


def run(machine, a_rom, b_rom, td):
    out = os.path.join(td, f"{machine}.txt")
    tcl = os.path.join(td, f"{machine}.tcl")
    open(tcl, "w").write(
        "set ::log {}\n"
        # a write counts only from the CARTRIDGE's own slot: on the references BASIC's
        # page-1 ROM writes these cells too (a page-1 PC alone passed them vacuously)
        "debug set_watchpoint write_mem 0xE000 {[pc_in_slot 2]} { lappend ::log B }\n"
        "debug set_watchpoint write_mem 0xE001 {[pc_in_slot 1]} { lappend ::log A }\n"
        f"after time 12 {{ set f [open {{{out}}} w]; puts $f $::log; close $f; exit }}\n")
    subprocess.run(omsx_preflight.guarded([OMSX, "-machine", machine, "-cart", a_rom, "-cartb", b_rom,
                   "-command", "set renderer none; set sound_driver null; set throttle off",
                   "-script", tcl]), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
    return open(out).read().split() if os.path.exists(out) else None


def main() -> int:
    td = tempfile.mkdtemp(prefix="initslot_")
    try:
        roms = {}
        for x in ("a", "b"):
            roms[x] = os.path.join(td, f"{x}.rom")
            subprocess.run(["pasmo", "--bin", os.path.join(HERE, "initslot", f"{x}.asm"), roms[x]],
                           check=True, capture_output=True)
        ok = True
        for m in MUST + [CONTROL]:
            log = run(m, roms["a"], roms["b"], td)
            both = log is not None and "A" in log and "B" in log
            if m == CONTROL:
                print(f"  control {m:30s} INITs run: {log}  (stock C-BIOS: slot 2 is skipped)")
                continue
            ok &= both
            print(f"  {'PASS' if both else 'FAIL'}  {m:30s} INITs run: {log}")
        print(f"===== initslot-acceptance: {'PASS' if ok else 'FAIL'} =====")
        return 0 if ok else 1
    finally:
        shutil.rmtree(td, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
