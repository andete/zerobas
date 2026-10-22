#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DISKRUN triage (the MemMan class): boot ONE image of the disk collection and log
every call a program in RAM makes to the PUBLISHED slot entries -- RDSLT $000C,
WRSLT $0014, CALSLT $001C, ENASLT $0024, CALLF $0030 -- and to EXTBIO $FFCA and the
BDOS door $F37D: registers at the entry, and registers again when it returns to its
caller. Black box: breakpoints at published addresses, registers and RAM stack
words only; no ROM byte is read and the software is never decoded.

Only calls whose RETURN ADDRESS is in $8000..$F37F are logged (a program loaded
into RAM; the ROMs' own internal use of the entries and the hook area stay out).
The image is copied to /tmp; the collection comes from DISKCORPUS_DIR.

    DISKCORPUS_DIR=... python3 -u scratchpad/slotcalls_probe.py IMAGE \
        [--machines ref,zb] [--end 45] [--max 300]
"""
import argparse, os, shutil, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "probes", "lib"))
import omsx_preflight  # noqa: E402
import diskcorpus_run as D  # noqa: E402

ENTRIES = {0x000C: "RDSLT", 0x0014: "WRSLT", 0x001C: "CALSLT", 0x0024: "ENASLT",
           0x0030: "CALLF", 0xFFCA: "EXTBIO", 0xF37D: "BDOS"}


def build_tcl(out, end, cap):
    # one-shot return breakpoints: openMSX's set_bp returns an id; the command is
    # given at creation, so the id is looked up through a global map by address
    regs = ("set r [format \"AF=%04X BC=%04X DE=%04X HL=%04X IX=%04X IY=%04X SP=%04X A8=%02X\" "
            "[reg af] [reg bc] [reg de] [reg hl] [reg ix] [reg iy] [reg sp] [debug read ioports 0xA8]]")
    L = ["set throttle off", "set ::n 0", "array set ::rbp {}",
         "proc __w {a} { expr {[debug read memory [expr {$a & 0xFFFF}]] + 256*[debug read memory [expr {($a+1) & 0xFFFF}]]} }",
         "proc __put {s} {", f"  set f [open {{{out}}} a]; puts $f $s; close $f", "}",
         "proc __ret {addr name} {",
         "  " + regs,
         "  __put [format \"%8.3f   RET %-6s       %s\" [machine_info time] $name $r]",
         "  if {[info exists ::rbp($addr)]} { debug remove_bp $::rbp($addr); unset ::rbp($addr) }",
         "}",
         "proc __ent {name} {",
         "  set ret [__w [reg sp]]",
         "  if {$ret < 0x8000 || $ret >= 0xF380} return",
         f"  if {{[incr ::n] > {cap}}} return",
         "  " + regs,
         "  __put [format \"%8.3f ENTER %-6s %04X %s\" [machine_info time] $name $ret $r]",
         "  if {![info exists ::rbp($ret)]} {",
         "    set ::rbp($ret) [debug set_bp $ret {} [list __ret $ret $name]]",
         "  }",
         "}"]
    for a, n in ENTRIES.items():
        L.append(f"debug set_bp {a:#06x} {{}} {{__ent {n}}}")
    L.append(f"after time {end} {{ exit }}")
    return "\n".join(L) + "\n"


def run(machine, image, end, cap):
    td = tempfile.mkdtemp(prefix="slotc_")
    try:
        dsk = os.path.join(td, "d.dsk")
        shutil.copy(image, dsk)
        out = os.path.join(td, "o.txt")
        s = os.path.join(td, "s.tcl")
        open(s, "w").write(build_tcl(out, end, cap))
        subprocess.run(omsx_preflight.guarded([D.OMSX, "-machine", machine, "-diska", dsk,
                        "-command", "set renderer none; set sound_driver null", "-script", s]),
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=240 + 4 * end)
        return open(out).read().rstrip() if os.path.exists(out) else "<NO OUTPUT>"
    finally:
        shutil.rmtree(td, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--machines", default="ref,zb")
    ap.add_argument("--end", type=float, default=45)
    ap.add_argument("--max", type=int, default=300)
    a = ap.parse_args()
    image = os.path.join(os.environ["DISKCORPUS_DIR"], a.image)
    for m in a.machines.split(","):
        machine = D.REF if m == "ref" else D.ZB
        print(f"### {m} ({machine})")
        print(run(machine, image, a.end, a.max))


if __name__ == "__main__":
    main()
