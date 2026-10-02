#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-DISKFULL regression trace: with the flush-before-store fat_io_putbyte in
disk.rom, a tokenised SAVE on a WRITE-PROTECTED disk answers OK (wprotect-
acceptance wp_ctl) where it raised 68. OUR disk.rom only (slot 3-1): a
breakpoint per routine of the SAVE engine logs DISKOP_STATUS, DISKOP_ERR and
BDOS_WRBUFLEN (= FWR_BUFLEN in disk.rom). Addresses come from build/disk.sym.
"""
import os, re, shutil, stat, sys, tempfile
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

SYM = {}
for ln in open(os.path.join(REPO, "build", "disk.sym")):
    m = re.match(r"^(\w+)\s+EQU\s+0?([0-9A-F]+)H", ln)
    if m:
        SYM[m.group(1)] = int(m.group(2), 16)
WATCH = ["hk_dpsave", "disk_write_begin", "fat_io_create", "sv_load_error", "disk_putbyte",
         "fat_flush_data_sector", "fat_alloc_cluster", "fac_full", "dc_fail", "fat_io_close",
         "disk_write_end", "sav_fin"]
PROG = ["NEW", "10 ON ERROR GOTO 90", '30 SAVE "X.BAS":PRINT"[OK]":END',
        '90 PRINT"[";ERR;ERL;"]":END', "RUN"]


def main():
    dsk = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False).name
    shutil.copy(os.path.join(REPO, "disk", "test720.dsk"), dsk)
    os.chmod(dsk, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    out = probe_tmp.tmp("dfwp_trace.log")
    rw = "proc rw {a} { return [format %02X%02X [debug read memory [expr {$a+1}]] [debug read memory $a]] }; "
    hk = ("proc hk {n} { global tf; if {![pc_in_slot 3 1]} return; "
          f"puts $tf \"$n ST=[format %02X [debug read memory {SYM['DISKOP_STATUS']}]] "
          f"ERR=[format %02X [debug read memory {SYM['DISKOP_ERR']}]] "
          f"BUFLEN=[rw {SYM['BDOS_WRBUFLEN']}] SP=[format %04X [reg SP]] "
          "stk=[rw [reg SP]]\"; flush $tf }; ")
    MSYM = {}
    for ln in open(os.path.join(REPO, "build", "basic-reloc.sym")):
        m = re.match(r"^(\w+)\s+EQU\s+0?([0-9A-F]+)H", ln)
        if m:
            MSYM[m.group(1)] = int(m.group(2), 16)
    hk0 = hk.replace("proc hk {n}", "proc hk0 {n}").replace("[pc_in_slot 3 1]", "[pc_in_slot 0 0]")
    main_w = ["disk_error", "load_error", "raise_error", "fopen_cross", "cg_back", "chan_restore_st"]
    conds0 = "".join(f"debug set_condition {{[reg PC] == 0x{MSYM[w]:04X}}} {{ hk0 M:{w} }}; " for w in main_w)
    conds = "".join(f"debug set_condition {{[reg PC] == 0x{SYM[w]:04X}}} {{ hk {w} }}; " for w in WATCH)
    pro = f"set tf [open {{{out}}} w]; " + rw + hk + hk0 + conds + conds0
    raw = omsx_repl.run_cases("C-BIOS_MSX1_EU_REPACK_DISK", [("direct", PROG)], batch=False,
                              reset=("CLS",), boot=8.0, step=8.0, cap_gap=20.0,
                              diska=dsk, prologue=(pro,))[0] or ""
    print("screen:", re.sub(r"\s+", " ", raw)[-300:])
    lines = open(out).read().splitlines() if os.path.exists(out) else []
    print(f"{len(lines)} hits")
    prev = None
    for ln in lines[:12] + ["  ..."] + lines[-16:]:
        if ln != prev:
            print("  " + ln)
        prev = ln
    return 0


if __name__ == "__main__":
    sys.exit(main())
