#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""closefail-acceptance -- a Disk BASIC channel's FAILURE and edge faces, against the CF-3300 (D-COPYSLOW step 1,
2026-11-28): a CLOSE that fails, a full record whose write fails, APPEND to an exact multiple of 256 B.

Measured on the National CF-3300 (scratchpad/AE_bfiles_u2.out): a failing CLOSE of an OUTPUT channel leaves it OPEN
in RANDOM mode -- the channel block's +0 mode goes 02 -> 04 -- so the SECOND CLOSE is a random-mode close, the
directory entry only. On a FULL disk that succeeds (the channel is freed: D-DISKFULL's face); on a WRITE-PROTECTED
disk it fails again. zerobas's old DOUT_DEAD bit freed the channel silently on BOTH (the wp row was red before).
Two cases, each on both machines, from MSX-DOS's `BASIC`:
    wp     OPEN / PRINT# on a writable disk, the disk swapped (openMSX `diska`) for a READ-ONLY copy -- openMSX mounts
           it write-protected -- then CLOSE, CLOSE
    full   every free cluster marked used, OPEN / PRINT# / CLOSE / CLOSE / OPEN / CLOSE
    rfail  a full disk: a PRINT# that FILLS a record (its write fails "Disk full"; the CF DROPS the record), then
           one more PRINT# (Ok on the CF -- zerobas used to retry and fail again: DOUT_RFULL), CLOSE / CLOSE
    inlf   INPUT # after an LF in its lead-in (INPUT$ took "AB" CR first, or controls without): the CF skips the LF
           but no blank after it -- LF "12" reads 12, LF " 12" / LF ",12" read 0 (2026-11-28, AE_bfiles_inlf.out)
    inra   the one-byte read-ahead: block +3 (the byte fetched, $00 none) and +6 (the last fetched index) after every
           step, across a record boundary; a NUL that EOF() read ahead is LOST, as on the CF-3300 (65, EOF 0, 66, 67)
    inbl   blanks only, and the end met after skipping: an EMPTY item, not "Input past end"; a blank after an LF stays
           unread (B1 " " CR LF " ": 0 and EOF 0; B2 " " CR LF: 0 and EOF -1)
    app256 APPEND to a host-injected file of EXACTLY 256 B, PRINT #1,"X": the CF-3300 OVERWRITES the last record
           from its start -- a 256 B file, "X" CR LF ^Z over its first four bytes (Joost 2026-11-28: "Copy the CF
           exactly"); the file's size and sha1 are compared too
Compared per case: the message after each typed line, and channel #1's block +0 after each CLOSE (BASIC's own data at
$DD6E with MAXFILES=1 -- a work-area read, not code). Exit 0 when both cases agree, 1 on a divergence, 2 when the
CF-3300 itself did not answer.
"""
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "disk"))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import disk_probe_dossession as D                   # noqa: E402
import disk_probe_diskfull                          # noqa: E402
import omsx_preflight                               # noqa: E402
import probe_tmp                                    # noqa: E402

SRC = os.path.expanduser("~/Documents/msx/msx/disks/test.dsk")
OURS = os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")
CASES = {
    "wp": [("mf", "MAXFILES=1"), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'), ("p1", 'PRINT #1,"B"'),
           ("c1", "CLOSE"), ("c2", "CLOSE")],
    "full": [("mf", "MAXFILES=1"), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'), ("p1", 'PRINT #1,"HELLO"'),
             ("c1", "CLOSE"), ("c2", "CLOSE"), ("o2", 'OPEN "F1.TXT" FOR OUTPUT AS #1'), ("c3", "CLOSE")],
    "rfail": [("cs", "CLEAR 1000"), ("mf", "MAXFILES=1"), ("o1", 'OPEN "F1.TXT" FOR OUTPUT AS #1'),
              ("pf", 'PRINT #1,STRING$(254,"A")'), ("p2", 'PRINT #1,"B"'), ("c1", "CLOSE"), ("c2", "CLOSE")],
    "app256": [("oa", 'OPEN "F.TXT" FOR APPEND AS #1'), ("lc", "PRINT LOC(1);LOF(1)"), ("px", 'PRINT #1,"X"'),
               ("c1", "CLOSE")],
    # an LF met in INPUT #'s lead-in: skipped, blank-skipping off after it (each file read by its own line)
    "inlf": [("cs", "CLEAR 500")] + [
        ("t" + nm, f'OPEN "{nm}.TXT" FOR INPUT AS #1:' + (f"A$=INPUT$({n},#1):" if n else "")
         + f'INPUT #1,X:INPUT #1,Y:PRINT "{nm}";X;Y:CLOSE') for nm, (_b, n) in
        {"P1": (0, 3), "P2": (0, 3), "P3": (0, 3), "P4": (0, 3), "Q1": (0, 1), "Q2": (0, 0), "Q3": (0, 4),
         "Q4": (0, 1), "Q5": (0, 2)}.items()],
    # the CF-3300's one-byte read-ahead: block +3 / +6 after every step, across a record boundary (R.TXT, 363 B) and
    # with a NUL read ahead by EOF() and then lost (N.TXT "A" 00 "B" "C")
    "inra": [("cs", "CLEAR 1000"), ("oi", 'OPEN "R.TXT" FOR INPUT AS #1'), ("r255", "A$=INPUT$(255,#1)"),
             ("r1", "A$=INPUT$(1,#1):PRINT ASC(A$)"), ("r1b", "A$=INPUT$(1,#1):PRINT ASC(A$)"), ("eof", "PRINT EOF(1)"),
             ("r8", "A$=INPUT$(8,#1):PRINT ASC(RIGHT$(A$,1))"), ("cl", "CLOSE"),
             ("on", 'OPEN "N.TXT" FOR INPUT AS #1'), ("na", "A$=INPUT$(1,#1):PRINT ASC(A$)"), ("ne", "PRINT EOF(1)"),
             ("nb", "A$=INPUT$(1,#1):PRINT ASC(A$)"), ("nc", "A$=INPUT$(1,#1):PRINT ASC(A$)"), ("cn", "CLOSE")],
    # blanks only / the end after skipping (tests/test_seqin.py used to pin "the end" for these -- never measured)
    "inbl": [("cs", "CLEAR 500")] + [("t" + nm, f'OPEN "{nm}.TXT" FOR INPUT AS #1:INPUT #1,X:PRINT "{nm}";X;EOF(1):CLOSE')
                                     for nm in ("B1", "B2", "B3", "B4")],
}
INBL = {"B1": b" \r\n ", "B2": b" \r\n", "B3": b"\r\n \r\n", "B4": b"\n 5\r\n"}
INLF = {"P1": b"AB\r\n12\r\n9\r\n", "P2": b"AB\r\n 12 \r\n9\r\n", "P3": b"AB\r\n,12\r\n9\r\n",
        "P4": b"AB\r\n\r\n12\r\n9\r\n", "Q1": b"A 9\r\n7\r\n", "Q2": b" 12 \r\n7\r\n",
        "Q3": b"AB\r\n 12\r\n7\r\n", "Q4": b"A,9\r\n7\r\n", "Q5": b"AB 9\r\n7\r\n"}


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
BLK0 = 0xDD6E   # channel #1's block +0 at MAXFILES=1, the same address on both (measured)


def run(machine, case):
    steps = CASES[case]
    D.SESSION = [("boot", None, 14), ("date", "", 5), ("basic", "BASIC", 8)] + [(t, x, 30) for t, x in steps]
    dsk = probe_tmp.tmp(f"closefail_{case}_{machine}.dsk")
    shutil.copyfile(SRC, dsk)
    if case in ("full", "rfail"):
        disk_probe_diskfull.full_disk(dsk)
    if case == "app256":
        inject(dsk, "F       TXT", b"A" * 254 + b"\r\n")
    if case == "inlf":
        for nm, body in INLF.items():
            inject(dsk, f"{nm:8s}TXT", body)
    if case == "inbl":
        for nm, body in INBL.items():
            inject(dsk, f"{nm:8s}TXT", body)
    if case == "inra":
        inject(dsk, "R       TXT", b"012345678\r\n" * 33)
        inject(dsk, "N       TXT", b"A\x00BC\r\n")
    ro = probe_tmp.tmp(f"closefail_{case}_{machine}_ro.dsk")
    if os.path.exists(ro):
        os.chmod(ro, 0o644)
    shutil.copyfile(SRC, ro)
    os.chmod(ro, 0o444)
    out = probe_tmp.tmp(f"closefail_{case}_{machine}.txt")
    if os.path.exists(out):
        os.remove(out)
    tcl = D.tcl(out)
    a = "  close $f }"
    assert tcl.count(a) == 1
    hook = f"  puts $f \"B0 $tag [rd {BLK0}] [rd {BLK0 + 3}] [rd {BLK0 + 6}]\"\n"
    if case == "wp":
        hook += f"  if {{$tag eq \"p1\"}} {{diska {{{ro}}}}}\n"
    tcl = tcl.replace(a, hook + a)
    tcl = tcl.replace("$::tries > 240", "$::tries > 12000")
    b = "{boot datecmd basic basicmem}"
    assert tcl.count(b) == 1
    tcl = tcl.replace(b, "{boot datecmd basic basicmem " + " ".join(t for t, _ in steps) + "}")
    sf = probe_tmp.tmp(f"closefail_{case}_{machine}.tcl")
    open(sf, "w").write(tcl)
    subprocess.run(omsx_preflight.guarded(["openmsx", "-machine", machine, "-diska", dsk, "-command",
                   "set renderer none; set sound_driver null", "-script", sf]),
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1800)
    if not os.path.exists(out):
        return None
    lines = open(out).read().splitlines()
    b0 = {ln.split()[1]: int(ln.split()[2]) for ln in lines if ln.startswith("B0 ")}
    b36 = {ln.split()[1]: (int(ln.split()[3]), int(ln.split()[4])) for ln in lines if ln.startswith("B0 ")}
    if not any(ln.startswith(steps[-1][0] + " ") for ln in lines):
        return None
    # each step's message is read from ITS OWN snapshot (a long session scrolls: reading every step from the last
    # screen lost the first ones -- the inlf case, 2026-11-28)
    msgs = []
    for t, x in steps:
        snap = next((ln for ln in lines if ln.startswith(t + " ")), None)
        msgs.append(step_msg(snap, x) if snap else "<no snapshot>")
    res = {"msgs": msgs, "b0": [b0.get(t) for t, _ in steps if t.startswith("c") and t != "cs"]}
    if case == "inra":   # the read-ahead's two header bytes after every step
        res["b3b6"] = [b36.get(t) for t, _ in steps if t != "cs"]   # from the first OPEN: before it the block is
                                                                       # unwritten RAM (the CF's 02 C0, ours FF FF --
                                                                       # D-FCBSHAPE's header, not the read-ahead)
    if case == "app256":
        res["file"] = [e for e in D.disk_listing(bytearray(open(dsk, "rb").read())) if e.startswith("F.TXT")]
    return res


def step_msg(snap, x):
    """The message after the typed line x on one snapshot."""
    p = snap.split()
    w = int(p[1][2:])
    raw = bytes.fromhex(p[3])
    rows = [raw[k * w:(k + 1) * w].decode("latin1").rstrip() for k in range(24)]
    # the typed line's LAST occurrence on its own snapshot (repeated CLOSE lines: the latest is this step's), matched
    # with SPACES REMOVED, each kept character remembering its row -- a long line WRAPS, and the CF-3300's BASIC screen
    # here is SCREEN 1 at WIDTH 29 inside 32-column rows, so padding the rows does not rejoin it (2026-11-28); the
    # message is the first non-blank row after the row the line ends on
    chars = [(c, ri) for ri, r in enumerate(rows) for c in r if c != " "]
    flat = "".join(c for c, _ in chars)
    xs = x.replace(" ", "")
    i = flat.rfind(xs)
    if i < 0:
        return "<line not seen>"
    nxt = chars[i + len(xs) - 1][1] + 1
    msg = next((r.strip() for r in rows[nxt:] if r.strip()), "")
    return "ok" if msg in ("Ok", "ZB") else msg


def main():
    bad = blind = 0
    for case in CASES:
        ref, ours = run("National_CF-3300", case), run(OURS, case)
        if ref is None:
            print(f"  NO-REFERENCE {case}")
            blind += 1
            continue
        same = ours == ref
        print(f"  {'ok  ' if same else 'DIFF'} {case:5s} CF {ref}\n{'':13s}ZB {ours}")
        bad += not same
    print(f"{len(CASES)} cases, {bad} diverge, {blind} without a reference")
    return 2 if blind else 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
