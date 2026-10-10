# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-FDCDI / the write cache, the SEQUENCE (2026-10-10): which sectors does each
FDC command touch, on both machines? fdcdi_count.py counted them (CF-3300 16 READ
+ 16 WRITE, zerobas 28 + 36 + 64 seeks); this logs each command with the WD2793's
track ($7FB9) and sector ($7FBA) registers and the drive/side latch ($7FBC), so
the extra commands can be named (data, FAT copy 1 / 2, directory).

(The counter's own header follows.) How many FDC sector commands does the
type-ahead workload -- 200 x PRINT#1 of 19 chars + CLOSE, 4200 B -- issue on the
CF-3300 and on zerobas DISK? Interrupt sampling on zerobas
(scratchpad/fdcdi_iff.out) put nearly all its masked time inside the FDC's DRQ
waits, i.e. per sector command; so the command COUNT is the lever to compare.

A write watchpoint on the WD2793 command register ($7FB8, memory-mapped on both
machines -- scratchpad/fdccount_probe.py) records each command byte while the
program's own marker (POKE &HD000) reads 1. Clean-room: an I/O register write
and work-area RAM; no ROM byte is read.
"""
import collections, os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                    # noqa: E402
import probe_tmp                                    # noqa: E402
import shutil                                       # noqa: E402

LINES = ['OPEN "X" FOR OUTPUT AS 1',
         'POKE &HD000,1:FOR I=1 TO 200:PRINT#1,"ABCDEFGHIJKLMNOPQRS":NEXT:CLOSE#1:POKE &HD000,2',
         'PRINT "[DONE]"']


def kind(b):
    return ("READ" if (b & 0xE0) == 0x80 else "WRITE" if (b & 0xE0) == 0xA0 else
            "force-int" if (b & 0xF0) == 0xD0 else "restore/seek" if (b >> 5) == 0 else "other")


for side, m in (("CF-3300", "National_CF-3300"), ("zerobas", "C-BIOS_MSX1_EU_REPACK_DISK")):
    log = probe_tmp.tmp(f"fdcseq_{m}.txt")
    if os.path.exists(log):
        os.unlink(log)
    dsk = probe_tmp.tmp(f"fdcseq_{m}.dsk")
    shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
    pro = (f"set __cf [open {{{log}}} w]",
           "proc __fdc {} { if {[debug read memory 0xD000] == 1} "
           "{ puts $::__cf [format {%02X:%d:%d:%02X} $::wp_last_value "
           "[debug read memory 0x7FB9] [debug read memory 0x7FBA] [debug read memory 0x7FBC]]; flush $::__cf } }",
           "debug set_watchpoint write_mem 0x7FB8 {} { __fdc }")
    scr = omsx_repl.run_cases(m, [("direct", LINES)], batch=False, diska=dsk, boot=14.0,
                              reset=("", "SCREEN 0:WIDTH 40", "POKE &HD000,0"), step=4.0,
                              run_gap=40.0, prologue=pro)[0]
    v = open(log).read().split() if os.path.exists(log) else []
    c = collections.Counter(kind(int(x.split(":")[0], 16)) for x in v)
    done = "[DONE]" in (scr or "")
    print(f"{side:8s} commands={len(v)} {dict(c)} finished={done}", flush=True)
    seq = []
    for x in v:
        b, trk, sec, lat = x.split(":")
        k = kind(int(b, 16))
        if k in ("READ", "WRITE"):
            seq.append(f"{k[0]}{trk}/{sec}/{lat}")
        elif k == "restore/seek":
            seq.append("s")
    print("  " + " ".join(seq), flush=True)
