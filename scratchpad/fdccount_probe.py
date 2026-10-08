#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-BLKIOPERCALL step 2, MEASURE FIRST: how many FDC sector commands does a
32 KB WRBLK write (128 calls of 256 B, disk_probe_wrblk_alt.py's --wseek
phase, PHASE byte 7 -> 8) issue on the CF-3300, and on ours?

The WD2793 is memory-mapped in the disk ROM's slot (openMSX's machine config,
`<WD2793 id="Memory Mapped FDC">`); its command register is $7FB8 on BOTH machines (National's mapping; the first
cut watched Philips' $7FF8 and counted NOTHING on either side -- found by
watching $7F80..$7FFF: commands land at $7FB8, data at $7FBB). A write
watchpoint there records each command's TYPE -- read sector $80..$9F, write
sector $A0..$BF -- binned by the exerciser's PHASE byte ($C000, its own data
in page-3 RAM). Clean room: an I/O register write and work-area RAM, both on
the permitted side; nothing of the ROM is read. A write to $7FB8 while page 1
is RAM would also fire, so only the two sector-command ranges are counted,
and a phase with ZERO write commands is an instrument suspect.

    python3 -u scratchpad/fdccount_probe.py [ours] [cf]
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
import probe_tmp                                    # noqa: E402
import disk_probe_wrblk_alt as A                    # noqa: E402
RT = A.RT


def count(machine, tag):
    dsk = probe_tmp.tmp(f"fdccount_{tag}.dsk")
    A.build(RT.DEFAULT_DOS, dsk, A.assemble(), False, True)
    out = probe_tmp.tmp(f"fdccount_{tag}.txt")
    if os.path.exists(out):
        os.remove(out)
    tcl = (f"set fc_f [open {{{out}}} w]\n"
           "array set ::fc {}\n"
           "debug set_watchpoint write_mem 0x7FB8 {} { set v $::wp_last_value; "
           "if {$v >= 0x80 && $v < 0xC0} { set k \"[debug read memory 0xC000],"
           "[expr {$v < 0xA0 ? {R} : {W}}]\"; "
           "if {[info exists ::fc($k)]} { incr ::fc($k) } else { set ::fc($k) 1 } } }\n"
           "proc fc_dump {} { foreach k [lsort [array names ::fc]] "
           "{ puts $::fc_f \"$k $::fc($k)\" }; flush $::fc_f }\n"
           "after time 595 fc_dump\n")
    A.run_once(machine, dsk, 14, 600, 900, None, extra_tcl=tcl)
    got = open(out).read().split() if os.path.exists(out) else []
    rows = dict(zip(got[0::2], got[1::2]))
    print(f"{tag}: " + " ".join(f"ph{k}={v}" for k, v in sorted(rows.items())), flush=True)
    return rows


which = sys.argv[1:] or ["ours", "cf"]
if "ours" in which:
    count(RT.OUR_MACHINE, "ours")
if "cf" in which:
    count(RT.REF_MACHINE, "cf")
