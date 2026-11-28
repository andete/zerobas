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
MFCTRL = os.environ.get("MFCTRL") == "1"
MFIN = os.environ.get("MFIN") == "1"
PROLOGUE = ""
if MFCTRL:   # CTRL held at boot (the CF's one-drive, HIMEM $E48D boot): where do the FCB slots go?
    MF15 = True
    SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "disk", "test720.dsk")
    PROLOGUE = "keymatrixdown 6 0x02\nafter time 6 { keymatrixup 6 0x02 }\n"   # as probes/disk/disk_probe_bootkeys.py
    STEPS = [("dt", ""), ("mf", "MAXFILES=2"), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'),
             ("o2", 'OPEN "F2.TXT" FOR OUTPUT AS #2'), ("cl", "CLOSE")]
if MFIN:     # an INPUT row's state: the record's unread count (DIN_LEFT) and a CR handed over alone (DIN_CRPEND)
    MF15 = True
    STEPS = [("mk", 'OPEN "T.TXT" FOR OUTPUT AS #1:PRINT #1,"AB":PRINT #1,"CD":CLOSE'),
             ("oi", 'OPEN "T.TXT" FOR INPUT AS #1'), ("r1", 'A$=INPUT$(1,#1):PRINT ASC(A$)'),
             ("r2", 'A$=INPUT$(2,#1):PRINT ASC(A$);ASC(MID$(A$,2))'), ("r3", 'A$=INPUT$(1,#1):PRINT ASC(A$)'),
             ("r4", 'INPUT #1,B$:PRINT B$'), ("cl", "CLOSE")]
MFDFULL = os.environ.get("MFDFULL") == "1"
if MFDFULL:  # a FULL disk (D-DISKFULL's face: the 2nd CLOSE frees silently) -- a flag, or only the order of the work?
    MFFLAG = True
    MF15 = True
    STEPS = [("mf", "MAXFILES=1"), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'), ("p1", 'PRINT #1,"HELLO"'),
             ("c1", "CLOSE"), ("c2", "CLOSE"), ("o1b", 'OPEN "F1.TXT" FOR OUTPUT AS #1'), ("c3", "CLOSE")]
if os.environ.get("MFRFAIL") == "1":   # a FULL record whose write FAILS (full disk), then one more PRINT#: where is
    MFDFULL = True                      # "retry that record" kept on the CF (zerobas: DOUT_RFULL)? header values per step
    MFFLAG = True
    MF15 = True
    STEPS = [("cs", "CLEAR 1000"), ("mf", "MAXFILES=1"), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'),
             ("pf", 'PRINT #1,STRING$(254,"A")'), ("p2", 'PRINT #1,"B"'), ("c1", "CLOSE"), ("c2", "CLOSE")]
MFAPP = os.environ.get("MFAPP") == "1"
if MFAPP:    # APPEND to a file of EXACTLY 256 B (host-injected: BASIC's CLOSE adds a Ctrl-Z): LOC / LOF after the OPEN,
    MFFLAG = True   # then one PRINT# -- what zerobas's DOUT_RFULL-on-APPEND ("rewrite the reloaded full record") must keep
    MF15 = True
    STEPS = [("oa", 'OPEN "F.TXT" FOR APPEND AS #1'), ("lc", "PRINT LOC(1);LOF(1)"), ("px", 'PRINT #1,"X"'),
             ("cl", "CLOSE")]


def inject(path, name11, data):
    """Write a file into a FAT12 image from the host: the first free root entry, the first free clusters, both FATs."""
    import struct
    img = bytearray(open(path, "rb").read())
    bps, spc, res, nf, nroot, tot, _m, spf = struct.unpack_from("<HBHBHHBH", img, 11)
    root = (res + nf * spf) * bps
    data0 = root + nroot * 32
    ncl = (tot - data0 // bps) // spc + 2

    def get(c):
        v = struct.unpack_from("<H", img, res * bps + c * 3 // 2)[0]
        return v >> 4 if c & 1 else v & 0xFFF

    def put(c, val):
        for k in range(nf):
            o = (res + k * spf) * bps + c * 3 // 2
            v = struct.unpack_from("<H", img, o)[0]
            v = (v & 0x000F) | (val << 4) if c & 1 else (v & 0xF000) | val
            struct.pack_into("<H", img, o, v)
    need = max(1, -(-len(data) // (spc * bps)))
    free = [c for c in range(2, ncl) if get(c) == 0][:need]
    for i, c in enumerate(free):
        put(c, free[i + 1] if i + 1 < len(free) else 0xFFF)
        o = data0 + (c - 2) * spc * bps
        chunk = data[i * spc * bps:(i + 1) * spc * bps]
        img[o:o + len(chunk)] = chunk
    for i in range(nroot):
        o = root + 32 * i
        if img[o] in (0, 0xE5):
            e = bytearray(32)
            e[0:11] = name11.encode("latin1")
            struct.pack_into("<HI", e, 26, free[0], len(data))
            img[o:o + 32] = e
            break
    open(path, "wb").write(img)


if os.environ.get("MFIN2") == "1":   # what the CF keeps in an INPUT channel's block +3 / +6 across a RECORD BOUNDARY
    MFFLAG = True                    # (+6 wraps to 0 both when a record is fresh and when it is spent): header values
    MF15 = True
    STEPS = [("cs", "CLEAR 1000"),
             ("mk", 'OPEN "T.TXT" FOR OUTPUT AS #1:FOR I=1 TO 33:PRINT #1,"012345678":NEXT:CLOSE'),
             ("oi", 'OPEN "T.TXT" FOR INPUT AS #1'), ("r255", "A$=INPUT$(255,#1)"),
             ("r1", 'A$=INPUT$(1,#1):PRINT ASC(A$)'), ("r1b", 'A$=INPUT$(1,#1):PRINT ASC(A$)'),
             ("eof", "PRINT EOF(1)"), ("r7", 'A$=INPUT$(8,#1):PRINT ASC(RIGHT$(A$,1))'),
             ("r1c", 'A$=INPUT$(1,#1):PRINT ASC(A$)'), ("cl", "CLOSE")]
MFAPP2 = os.environ.get("MFAPP2") == "1"
if MFAPP2:   # Joost "Measure first": WHICH files does the CF's APPEND overwrite? host files of a 256 multiple with and
    MFFLAG = True   # without a final Ctrl-Z, and one BASIC writes itself (253 A + CR LF + its CLOSE's Ctrl-Z = 256 B)
    MF15 = True
    STEPS = [("cs", "CLEAR 1000"), ("mb", 'OPEN "B256.TXT" FOR OUTPUT AS #1:PRINT #1,STRING$(253,"A"):CLOSE')]
    for nm in ("A256", "Z256", "A512", "Z512", "B256"):
        STEPS += [("a" + nm, f'OPEN "{nm}.TXT" FOR APPEND AS #1:PRINT #1,"X":CLOSE')]
MFIN3 = os.environ.get("MFIN3") == "1"
if MFIN3:    # a held $00 vs "nothing held" in +3, and the CR-then-LF case (D-INPLF): host file "A" 00 "B" CR LF "12" CR LF
    MFFLAG = True
    MF15 = True
    STEPS = [("oi", 'OPEN "N.TXT" FOR INPUT AS #1'), ("ra", "A$=INPUT$(1,#1):PRINT ASC(A$)"),
             ("rn", "A$=INPUT$(1,#1):PRINT ASC(A$)"), ("rb", "A$=INPUT$(1,#1):PRINT ASC(A$)"),
             ("rc", "A$=INPUT$(1,#1):PRINT ASC(A$)"), ("ix", "INPUT #1,X:PRINT X"), ("iy", "INPUT #1,Y:PRINT Y"),
             ("ef", "PRINT EOF(1)"), ("cl", "CLOSE")]
MFIN4 = os.environ.get("MFIN4") == "1"
if MFIN4:    # is the LF HELD (+3) after a multi-byte INPUT$ ends on a CR, and NOT after INPUT$(1) takes it? file "AB" CR LF "12" CR LF
    MFFLAG = True
    MF15 = True
    STEPS = [("om", 'OPEN "N.TXT" FOR INPUT AS #1'), ("r3", "A$=INPUT$(3,#1):PRINT LEN(A$)"),
             ("im", "INPUT #1,X:PRINT X"), ("cm", "CLOSE"),
             ("os", 'OPEN "N.TXT" FOR INPUT AS #1'), ("s1", "A$=INPUT$(1,#1)"), ("s2", "A$=INPUT$(1,#1)"),
             ("s3", "A$=INPUT$(1,#1):PRINT ASC(A$)"), ("is", "INPUT #1,X:PRINT X"), ("cs", "CLOSE")]
MFIN5 = os.environ.get("MFIN5") == "1"
INF5 = {"P1": b"AB\r\n12\r\n", "P2": b"AB\r\n 12 \r\n", "P3": b"AB\r\n,12\r\n", "P4": b"AB\r\n\r\n12\r\n"}
if MFIN5:    # D-INPLF's rule, re-measured: after INPUT$ took a CR, what INPUT # reads depends on what FOLLOWS the LF?
    MF15 = True
    STEPS = [("cs", "CLEAR 500")]
    for nm in INF5:
        STEPS += [("t" + nm, f'OPEN "{nm}.TXT" FOR INPUT AS #1:A$=INPUT$(3,#1):INPUT #1,X:INPUT #1,Y:'
                             f'PRINT "{nm}";X;Y:CLOSE')]
MFIN6 = os.environ.get("MFIN6") == "1"
# (file, INPUT$ count before the two INPUT # items) -- is blank-skipping off only after INPUT$ took a CR, or after ANY INPUT$?
INF6 = {"Q1": (b"A 9\r\n7\r\n", 1), "Q2": (b" 12 \r\n7\r\n", 0), "Q3": (b"AB\r\n 12\r\n7\r\n", 4),
        "Q4": (b"A,9\r\n7\r\n", 1), "Q5": (b"AB 9\r\n7\r\n", 2)}
if MFIN6:
    MF15 = True
    STEPS = [("cs", "CLEAR 500")]
    for nm, (_b, n) in INF6.items():
        pre = f"A$=INPUT$({n},#1):" if n else ""
        STEPS += [("t" + nm, f'OPEN "{nm}.TXT" FOR INPUT AS #1:{pre}INPUT #1,X:INPUT #1,Y:PRINT "{nm}";X;Y:CLOSE')]
MFBL = os.environ.get("MFBL") == "1"
INFB = {"B1": b" \r\n ", "B2": b" \r\n", "B3": b"\r\n \r\n", "B4": b"\n 5\r\n"}
if MFBL:     # blanks only (tests/test_seqin.py pins "the end before any byte" for " " CR LF " "): the CF's reading
    MF15 = True
    STEPS = [("cs", "CLEAR 500")] + [("t" + nm, f'OPEN "{nm}.TXT" FOR INPUT AS #1:INPUT #1,X:PRINT "{nm}";X;EOF(1):CLOSE')
                                     for nm in INFB]
MFIN7 = os.environ.get("MFIN7") == "1"
if MFIN7:    # is +3 = $00 the CF's "nothing held"? EOF() fetches a NUL into +3, then INPUT$(1): the NUL, or the byte after it?
    MFFLAG = True
    MF15 = True
    STEPS = [("oi", 'OPEN "N.TXT" FOR INPUT AS #1'), ("ra", "A$=INPUT$(1,#1):PRINT ASC(A$)"),
             ("ef", "PRINT EOF(1)"), ("rn", "A$=INPUT$(1,#1):PRINT ASC(A$)"), ("rb", "A$=INPUT$(1,#1):PRINT ASC(A$)"),
             ("cl", "CLOSE")]
MFFCB = os.environ.get("MFFCB") == "1"
if MFFCB:    # slice 5: an OUTPUT channel's FCB +25..+35 VALUES (work-area RAM) on both -- the CF's slot 1 $DEB5, zerobas's
    MF15 = True   # DSK_ENGTAB row 1 $E4BF -- after OPEN, 300 B, 1.3 KB of PRINT#, and CLOSE: same field meanings?
    STEPS = [("mf", "MAXFILES=1"), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'),
             ("p3", 'FOR I=1 TO 30:PRINT #1,"012345678":NEXT'), ("p13", 'FOR I=1 TO 100:PRINT #1,"012345678":NEXT'),
             ("cl", "CLOSE")]
MFTAB = os.environ.get("MFTAB") == "1"
if MFTAB:    # FILTAB ($F860): does the CF fill MS-BASIC's per-channel pointer table with each block's address? (work-area)
    MF15 = True
    STEPS = [("mf", "MAXFILES=2"), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'), ("o2", 'OPEN "F2.TXT" FOR OUTPUT AS #2'),
             ("cl", "CLOSE")]
if os.environ.get("MFCRT") == "1":   # a NON-disk device at #7: is the number limit the disk's or BASIC's?
    MF15 = True
    STEPS = [("mf", "MAXFILES=15"), ("o7", 'OPEN "CRT:" FOR OUTPUT AS #7'), ("p7", 'PRINT #7,"YY"'),
             ("cl", "CLOSE")]
D.SESSION = ([("boot", None, 14)] if MFCTRL else [("boot", None, 14), ("date", "", 5), ("basic", "BASIC", 8)]) + [(t, x, 30 if os.environ.get("MFHI") == "1" or os.environ.get("MFCRT") == "1" or os.environ.get("MFSLOT") == "1" or os.environ.get("MFWR") == "1" or MFFLAG or MFCTRL or MFIN else 15 if MF15 else 8) for t, x in STEPS]
order = (["boot"] if MFCTRL else ["basic"]) + [t for t, _ in STEPS]
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
CMD = CMD.replace("BYTELO", "0xDC00" if (MFFLAG or MFIN) else "0xDE77")
if MFCTRL:   # the slots might sit anywhere in the claim: bytes up to TXTMAX, not just to $DF93
    CMD = CMD.replace("$a <= 0xDF93", "$a <= 0xE7AD")
for m in machines:
    td = tempfile.mkdtemp()
    dsk = os.path.join(td, "d.dsk")
    subprocess.run(["cp", SRC, dsk], check=True)
    if MFAPP:
        inject(dsk, "F       TXT", b"A" * 254 + b"\r\n")
    if MFIN3:
        inject(dsk, "N       TXT", b"A\x00B\r\n12\r\n")
    if MFIN4:
        inject(dsk, "N       TXT", b"AB\r\n12\r\n")
    if MFIN7:
        inject(dsk, "N       TXT", b"A\x00BC\r\n")
    if MFBL:
        for nm, body in INFB.items():
            inject(dsk, f"{nm:8s}TXT", body)
    if MFIN6:
        for nm, (body, _n) in INF6.items():
            inject(dsk, f"{nm:8s}TXT", body)
    if MFIN5:
        for nm, body in INF5.items():
            inject(dsk, f"{nm:8s}TXT", body + b"9\r\n")
    if MFAPP2:
        inject(dsk, "A256    TXT", b"A" * 254 + b"\r\n")
        inject(dsk, "Z256    TXT", b"A" * 253 + b"\r\n\x1a")
        inject(dsk, "A512    TXT", b"A" * 510 + b"\r\n")
        inject(dsk, "Z512    TXT", b"A" * 509 + b"\r\n\x1a")
    if MFDFULL:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "probes", "disk"))
        import disk_probe_diskfull   # noqa: E402  full_disk(): every free cluster marked used, every FAT copy
        disk_probe_diskfull.full_disk(dsk)
    out = os.path.join(td, "o.txt")
    fl = os.path.join(td, "cells.txt")
    tcl = D.tcl(out)
    tcl = tcl.replace("set throttle off", "set throttle off\n" + PROLOGUE + "set ::counting 0\n"
                      f"set ::fl [open {{{fl}}} w]\n" + CMD, 1)
    a = "  close $f }"
    assert tcl.count(a) == 1
    if MFTAB:
        tcl_tab = ("  set ft [rd16 0xF860]; set tv {}; for {set i 0} {$i < 4} {incr i} {lappend tv [format %04X [rd16 "
                   "[expr {$ft + 2*$i}]]]}; puts $::fl \"TAB $tag [format %04X $ft] MEMSIZ [format %04X [rd16 0xF672]] "
                   "$tv\"\n")
    else:
        tcl_tab = ""
    if MFFCB:
        base = 0xDEB5 if "CF-3300" in m else 0xE4BF
        tcl_fcb = ("  set fv {}; for {set i 25} {$i < 36} {incr i} {lappend fv [rd [expr {%d + $i}]]}; "
                   "puts $::fl \"FCB $tag $fv\"\n" % base)
    else:
        tcl_fcb = ""
    # MFFLAG / MFDFULL: channel #1's block HEADER VALUES ($DD6E-$DD76 at MAXFILES=1: BASIC's data, a work-area read,
    # not code) after every step -- where the CF keeps a failed CLOSE's state
    hook = ("  set hv {}; for {set i 0} {$i < 9} {incr i} {lappend hv [rd [expr {0xDD6E + $i}]]}; puts $::fl \"HDR $tag $hv\"\n"
            if MFFLAG else "")
    hook += tcl_fcb + tcl_tab
    hook += "  puts $::fl \"HIMEM $tag [rd16 0xFC4A]\"\n  if {$tag eq \"" + order[0] + "\"} {set ::counting 1}\n"
    for k, v in zip(order, order[1:]):
        hook += f"  if {{$tag eq \"{k}\"}} {{set ::step {v}}}\n"
    hook += f"  if {{$tag eq \"{order[-1]}\"}} {{set ::counting 0; puts $::fl \"CELLS $::cells\"; flush $::fl}}\n"
    if MFFLAG:
        ro = os.path.join(td, "ro.dsk")
        subprocess.run(["cp", SRC, ro], check=True)
        os.chmod(ro, 0o444)   # openMSX mounts a read-only image write-protected (probes/disk/build_bdosxe_disk.py)
        if not (MFFULL or MFDFULL or MFAPP or MFAPP2 or MFIN3 or MFIN4 or MFIN7 or os.environ.get("MFIN2") == "1"):
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
    if MFAPP2:
        for e in D.disk_listing(bytearray(open(dsk, "rb").read())):
            if e[:4] in ("A256", "Z256", "A512", "Z512", "B256"):
                print("   after: " + e)
    if MFAPP:
        print("   F.TXT after: " + " | ".join(e for e in D.disk_listing(bytearray(open(dsk, "rb").read()))
                                          if e.startswith("F.TXT")))
    for ln in lines:
        if ln.startswith("TAB "):
            print("   FILTAB after " + " ".join(ln.split()[1:]))
        if ln.startswith("FCB "):
            print(f"   FCB +25..+35 after {ln.split()[1]:4s}: " + " ".join(f"{int(x):02X}" for x in ln.split()[2:]))
    for ln in lines:
        if ln.startswith("HDR "):
            print(f"   block header +0..+8 after {ln.split()[1]:4s}: " + " ".join(f"{int(x):02X}" for x in ln.split()[2:]))
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
