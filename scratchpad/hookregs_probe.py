#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""S10.B design input: the REGISTER CONTRACT at the CF-3300's channel hook cells
during `OPEN"HK.TXT"FOR OUTPUT AS#1 : PRINT#1,"AB" : CLOSE#1`.

D-CHANHOOK (spec §6.6bb) counted which claimed cells the channel verbs enter
($FE85 per byte out, $FE5D/$FE58/$FEB2/$FEB7 around OPEN/CLOSE, $FE4E per
statement). S10.B has disk.rom claim $FE85 for PRINT#, and software that hooks
it expects the standard convention -- so what do the registers hold on entry?
A breakpoint at each cell logs AF/BC/DE/HL/IX/IY/SP and the stack's top word:
registers only, no bytes of any reference code (the cells are executed, not
read). The program runs once, typed as one line, after a SCREEN 0 reset.
"""
import os, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

CELLS = [0xFE4E, 0xFE58, 0xFE5D, 0xFE62, 0xFE85, 0xFEB2, 0xFEB7]
LINE = 'OPEN"HK.TXT"FOR OUTPUT AS#1:PRINT#1,"AB":CLOSE#1'


def main():
    rows = {}
    for tag, machine in (("CF-3300", "National_CF-3300"),
                         ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
        dsk = probe_tmp.tmp(f"hookregs_{tag}.dsk")
        shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
        out = probe_tmp.tmp(f"hookregs_{tag}.log")
        conds = "".join(
            f"debug set_condition {{[reg PC] == 0x{c:04X} && $::armed}} {{ hk 0x{c:04X} }}; " for c in CELLS)
        pro = (f"set ::armed 0; set ::hf [open {{{out}}} w]; "
               "proc rw {a} { return [format %02X%02X [debug read memory [expr {($a+1) & 0xFFFF}]] [debug read memory $a]] }; "
               "proc hk {c} { set sp [reg SP]; set bc [reg BC]; "
               "set stk [list [rw $sp] [rw [expr {$sp+2}]] [rw [expr {$sp+4}]] [rw [expr {$sp+6}]]]; "
               "puts $::hf \"[format %04X $c] AF=[format %04X [reg AF]] BC=[format %04X $bc] "
               "DE=[format %04X [reg DE]] HL=[format %04X [reg HL]] IX=[format %04X [reg IX]] "
               "IY=[format %04X [reg IY]] SP=[format %04X $sp] stk=[join $stk ,] "
               "(BC-1)=[format %02X [debug read memory [expr {$bc-1}]]] (BC)=[format %02X [debug read memory $bc]]\"; "
               "flush $::hf }; "
               + conds + "after time 16 { set ::armed 1 }")
        omsx_repl.run_cases(machine, [("direct", [LINE])], batch=False, reset=("", "SCREEN 0"),
                            boot=14.0, step=6.0, diska=dsk, prologue=(pro,))
        rows[tag] = [ln.rstrip() for ln in open(out)] if os.path.exists(out) else []
        print(f"== {tag}: {len(rows[tag])} hook entries during the line")
        for ln in rows[tag][:40]:
            print("  " + ln)
    return 0


if __name__ == "__main__":
    sys.exit(main())
