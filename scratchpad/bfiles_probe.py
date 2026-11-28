#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""D-COPYSLOW Q7 + Q8 (Joost 2026-11-28 "Measure Disk BASIC first"). Q7: where does the reference keep Disk BASIC
CHANNEL state? Disk BASIC (via `BASIC` at A>): MAXFILES=2, OPEN for output, PRINT# ~720 B, CLOSE, OPEN for input,
INPUT#, CLOSE. Every RAM write in $C000-$F37F is counted per 16 B block and per step -- ADDRESSES ONLY, no byte, no
PC (clean room) -- and HIMEM ($FC4A, a work-area cell) is read at each step's end. Q8 falls out of the same counts:
any write to $DE77-$DF93 or to drive B's image span ($DF94-$E593) with B: never used.
Every step waits 8 s before the still-screen test (the CF-3300's silent disk work fooled a 3 s one, 2026-11-28).
    python3 -u scratchpad/bfiles_probe.py [MACHINE ...]
"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "disk"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "lib"))
import disk_probe_dossession as D  # noqa: E402
import omsx_preflight  # noqa: E402

machines = sys.argv[1:] or ["National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"]
SRC = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
STEPS = [("mf", "MAXFILES=2"), ("op", 'OPEN "F.TXT" FOR OUTPUT AS #1'),
         ("pr", 'FOR I=1 TO 60:PRINT #1,"0123456789":NEXT'), ("cl", "CLOSE #1"),
         ("oi", 'OPEN "F.TXT" FOR INPUT AS #2'), ("ip", "INPUT #2,A$:PRINT A$"), ("cl2", "CLOSE")]
# MF15=1 (D-COPYSLOW U1 / U2, Joost "Full redesign, staged"): 15 channels open at once, and per-BYTE counts in the
# CF-3300's $DE77-$DF93 (the per-channel stride) and $E580-$E59F (its cells just under A's image)
MF15 = os.environ.get("MF15") == "1"
if MF15:
    # each loop prints I first, so a refusal names its channel (the CF-3300 said "Bad file number" mid-loop and a
    # line typed while it was busy arrived garbled, 2026-11-28 -- waits raised to 15 s)
    STEPS = [("mf", "MAXFILES=15"),
             ("op", 'FOR I=1 TO 15:PRINT I;:OPEN "F"+CHR$(64+I)+".TXT" FOR OUTPUT AS #I:NEXT'),
             ("pr", 'FOR I=1 TO 15:PRINT #I,"X":NEXT'), ("cl", "CLOSE")]
if os.environ.get("MFSTEP") == "1":   # one channel per step: the stride; then #15 with six open (count or number?)
    MF15 = True
    STEPS = [("mf", "MAXFILES=15")] + [(f"o{n}", f'OPEN "F{n}.TXT" FOR OUTPUT AS #{n}') for n in range(1, 7)] + [
        ("o15", 'OPEN "FF.TXT" FOR OUTPUT AS #15'), ("cl", "CLOSE"), ("o15b", 'OPEN "FF.TXT" FOR OUTPUT AS #15'),
        ("cl2", "CLOSE")]
if os.environ.get("MFHI") == "1":   # #15 with NOTHING else open: a refusal is about the NUMBER, success about the COUNT
    MF15 = True
    STEPS = [("mf", "MAXFILES=15"), ("o15", 'OPEN "FF.TXT" FOR OUTPUT AS #15'), ("p15", 'PRINT #15,"X"'),
             ("cl", "CLOSE"), ("o7", 'OPEN "F7.TXT" FOR OUTPUT AS #7'), ("cl2", "CLOSE")]
if os.environ.get("MFSLOT") == "1":   # #3 first, then #1: is FCB slot n tied to file number n, or first-free?
    MF15 = True
    STEPS = [("mf", "MAXFILES=6"), ("o3", 'OPEN "F3.TXT" FOR OUTPUT AS #3'), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'),
             ("cl", "CLOSE")]
if os.environ.get("MFWR") == "1":   # which FCB bytes move while a file is WRITTEN (1.3 KB: past one 1 KB cluster)
    MF15 = True
    STEPS = [("mf", "MAXFILES=1"), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'),
             ("p1", 'FOR I=1 TO 130:PRINT #1,"012345678":NEXT'), ("cl", "CLOSE")]
MFFLAG = os.environ.get("MFFLAG") == "1"
if MFFLAG:   # the flags byte's two states: a FULL record not yet written (254 chars + CR LF = 256), then one more
    #          PRINT#; then the disk swapped for a READ-ONLY copy and CLOSE (fails), then CLOSE again
    MF15 = True
    STEPS = [("mf", "MAXFILES=1"), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'), ("pf", 'PRINT #1,STRING$(254,"A")'),
             ("p2", 'PRINT #1,"B"'), ("c1", "CLOSE"), ("c2", "CLOSE")]
MFFULL = os.environ.get("MFFULL") == "1"
if MFFULL:   # the FULL-record state alone (MFFLAG's STRING$(254) was "Out of string space" on both: CLEAR first)
    MFFLAG = True
    MF15 = True   # per-byte counts (forgotten on the first run: it fell back to 16 B blocks, 2026-11-28)
    STEPS = [("cs", "CLEAR 1000"), ("mf", "MAXFILES=1"), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'),
             ("pf", 'PRINT #1,STRING$(254,"A")'), ("p2", 'PRINT #1,"B"'), ("c1", "CLOSE")]
if os.environ.get("MFCRT") == "1":   # a NON-disk device at #7: is the number limit the disk's or BASIC's?
    MF15 = True
    STEPS = [("mf", "MAXFILES=15"), ("o7", 'OPEN "CRT:" FOR OUTPUT AS #7'), ("p7", 'PRINT #7,"YY"'),
             ("cl", "CLOSE")]
D.SESSION = [("boot", None, 14), ("date", "", 5), ("basic", "BASIC", 8)] + [(t, x, 30 if os.environ.get("MFHI") == "1" or os.environ.get("MFCRT") == "1" or os.environ.get("MFSLOT") == "1" or os.environ.get("MFWR") == "1" or MFFLAG else 15 if MF15 else 8) for t, x in STEPS]
order = ["basic"] + [t for t, _ in STEPS]
SPANS = [(0xDE77, 0xDF93, "below B's image"), (0xDF94, 0xE593, "B's FAT image"), (0xE595, 0xEB94, "A's FAT image"),
         (0xEB95, 0xED94, "dir buf"), (0xED95, 0xEF94, "data buf"), (0xEF95, 0xF194, "mount buf"),
         (0xF195, 0xF1C8, "DPB + after"), (0xF1C9, 0xF37F, "fixed area")]
CMD = ("set ::step basic; set ::cells [dict create]\n"
       "debug set_watchpoint write_mem {0xC000 0xF37F} {$::counting} { dict incr ::cells "
       "\"$::step:[expr {$::wp_last_address >> 4}]\" }\n")
if MF15:   # exact bytes in the two spans of interest, 16 B blocks elsewhere (keys: B<addr> for a byte, <blk> for a block)
    CMD = ("set ::step basic; set ::cells [dict create]\n"
           "debug set_watchpoint write_mem {0xC000 0xF37F} {$::counting} { set a $::wp_last_address; "
           "if {($a >= BYTELO && $a <= 0xDF93) || ($a >= 0xE580 && $a <= 0xE59F)} "
           "{ dict incr ::cells \"$::step:B$a\" } else { dict incr ::cells \"$::step:[expr {$a >> 4}]\" } }\n")
CMD = CMD.replace("BYTELO", "0xDC00" if MFFLAG else "0xDE77")
for m in machines:
    td = tempfile.mkdtemp()
    dsk = os.path.join(td, "d.dsk")
    subprocess.run(["cp", SRC, dsk], check=True)
    out = os.path.join(td, "o.txt")
    fl = os.path.join(td, "cells.txt")
    tcl = D.tcl(out)
    tcl = tcl.replace("set throttle off", "set throttle off\nset ::counting 0\n"
                      f"set ::fl [open {{{fl}}} w]\n" + CMD, 1)
    a = "  close $f }"
    assert tcl.count(a) == 1
    hook = "  puts $::fl \"HIMEM $tag [rd16 0xFC4A]\"\n  if {$tag eq \"basic\"} {set ::counting 1}\n"
    for k, v in zip(order, order[1:]):
        hook += f"  if {{$tag eq \"{k}\"}} {{set ::step {v}}}\n"
    hook += f"  if {{$tag eq \"{order[-1]}\"}} {{set ::counting 0; puts $::fl \"CELLS $::cells\"; flush $::fl}}\n"
    if MFFLAG:
        ro = os.path.join(td, "ro.dsk")
        subprocess.run(["cp", SRC, ro], check=True)
        os.chmod(ro, 0o444)   # openMSX mounts a read-only image write-protected (probes/disk/build_bdosxe_disk.py)
        if not MFFULL:
            hook += f"  if {{$tag eq \"p2\"}} {{diska {{{ro}}}}}\n"
    tcl = tcl.replace(a, hook + a)
    tcl = tcl.replace("$::tries > 240", "$::tries > 12000")
    b = "{boot datecmd basic basicmem}"
    assert tcl.count(b) == 1
    tcl = tcl.replace(b, "{boot datecmd basic basicmem " + " ".join(t for t, _ in STEPS) + "}")
    sf = os.path.join(td, "s.tcl")
    open(sf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", m, "-diska", dsk, "-command",
                   "set renderer none; set sound_driver null", "-script", sf]),
                   stdout=open(os.path.join(td, "err.txt"), "w"), stderr=subprocess.STDOUT, timeout=2400)
    lines = open(fl).read().splitlines()
    print(f"== {m}   (log {td})")
    print("   HIMEM after each step: " + "  ".join(f"{ln.split()[1]}=${int(ln.split()[2]):04X}"
                                                   for ln in lines if ln.startswith("HIMEM")))
    cl = next((ln for ln in lines if ln.startswith("CELLS ")), "CELLS").split()[1:]
    if not cl:
        print("   NO WRITES RECORDED -- instrument failed, not a finding")
    per, byte = {}, {}
    for i in range(0, len(cl) - 1, 2):
        step, blk = cl[i].split(":")
        if blk.startswith("B"):
            byte.setdefault(step, {})[int(blk[1:])] = int(cl[i + 1])
            continue
        per.setdefault(step, {})[int(blk) * 16] = int(cl[i + 1])
    for step in order[1:]:
        if step in byte:
            bb_ = byte[step]
            runs_, st_, pv_ = [], None, None
            for a_ in sorted(bb_):
                if st_ is None or a_ != pv_ + 1:
                    if st_ is not None:
                        runs_.append((st_, pv_))
                    st_ = a_
                pv_ = a_
            runs_.append((st_, pv_))
            print(f"   {step:4s} bytes written in {'$DC00' if MFFLAG else '$DE77'}-$DF93 / $E580-$E59F: " +
                  " ".join(f"${lo:04X}-${hi:04X}" if hi > lo else f"${lo:04X}" for lo, hi in runs_))
    for step in order[1:]:
        blks = per.get(step, {})
        runs, st, prev, tot = [], None, None, 0
        for a in sorted(blks):
            if st is None or a != prev + 16:
                if st is not None:
                    runs.append((st, prev + 15, tot))
                st, tot = a, 0
            prev = a
            tot += blks[a]
        if st is not None:
            runs.append((st, prev + 15, tot))
        print(f"   {step:4s} " + "  ".join(f"${lo:04X}-${hi:04X}:{n}" for lo, hi, n in runs))
    allb = {}
    for step in per:
        for a, n in per[step].items():
            allb[a] = allb.get(a, 0) + n
    print("   by CF span (all steps): " + "  ".join(
        f"{name}={sum(n for a, n in allb.items() if lo <= a + 15 and a <= hi)}" for lo, hi, name in SPANS))
    snaps = {ln.split()[0]: ln for ln in open(out).read().splitlines()}
    if order[-1] in snaps:
        p = snaps[order[-1]].split()
        wd = int(p[1][2:])
        bb = bytes.fromhex(p[3])
        rows = [bb[k * wd:(k + 1) * wd].decode("latin1").rstrip() for k in range(24)]
        print("   final screen: " + " / ".join(r.strip() for r in rows if r.strip())[-300:])
