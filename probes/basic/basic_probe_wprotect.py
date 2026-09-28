#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""wprotect-acceptance -- a disk WRITE error reaches BASIC (D-WPROTECT, D-SAVEOPEN).

Until 2026-09-28 zerobas reported NO disk write error at all: disk/driver.asm's
fdc_write_phys tested the DSKIO code with `cp 0`, which clears the carry, so a
write-protected disk answered OK where the CF-3300 raises 68. Two more layers sat
behind it -- SAVE ,A reported through load_error, and a SAVE with a file open
never even reached the drive (chan_gate's flush overwrote fopen_cross's verb
selector) and answered OK. The investigation is scratchpad/errkeep2_probe.py
(its runs 1-6) and scratchpad/wptrace_probe.py; this is its gate, self-contained
in probes/ so the battery's fingerprint covers it.

Each case boots once on the National CF-3300 and on zerobas's DISK build, each
with a PRIVATE copy of the fixture image -- read-only on the host (the emulator
mounts it write-protected) except `sv_openrw`, which must be writable -- trapped
by ON ERROR, and the two readings must agree:

  wp_ctl    SAVE, nothing open                          68
  wp_save   HI.TXT open FOR INPUT; SAVE                 68 (the code survives the open file)
  wp_asave  the same, SAVE ,A                           68
  wp_bsave  the same, BSAVE                             68
  wp_copy   HI.TXT open; COPY it                        64 (open file, before any write)
  wp_name   HI.TXT open; NAME it                        64
  wp_out    MAXFILES=2; HI.TXT open; OPEN FOR OUTPUT    68
  sv_openrw HI.TXT open; SAVE; read the file back       255 (it WAS written)

Exit 0 = all agree; 1 = any disagreement or a missing reading.
Knife (2026-09-28): the old `cp 0` restored -> 5 of 8 FAIL
(scratchpad/wprotect_knife.out).

    python3 -u probes/basic/basic_probe_wprotect.py [case ...]
"""
import os
import re
import shutil
import stat
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl  # noqa: E402

REF, ZB = "National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"
FIXTURE = os.path.join(REPO, "disk", "test720.dsk")
TAIL = ['90 PRINT"[";ERR;ERL;"]":END', "RUN"]
OPN = '20 OPEN "HI.TXT" FOR INPUT AS #1'


def prog(*body, pre=()):
    return ["NEW"] + list(pre) + ["10 ON ERROR GOTO 90"] + list(body) + TAIL


CASES = {
    "wp_ctl": prog('30 SAVE "X.BAS":PRINT"[OK]":END'),
    "wp_save": prog(OPN, '30 SAVE "X.BAS":PRINT"[OK]":END'),
    "wp_asave": prog(OPN, '30 SAVE "X.BAS",A:PRINT"[OK]":END'),
    "wp_bsave": prog(OPN, '30 BSAVE "X.BIN",&HC000,&HC010:PRINT"[OK]":END'),
    "wp_copy": prog(OPN, '30 COPY "HI.TXT" TO "HJ.TXT":PRINT"[OK]":END'),
    "wp_name": prog(OPN, '30 NAME "HI.TXT" AS "HJ.TXT":PRINT"[OK]":END'),
    "wp_out": prog(OPN, '30 OPEN "Y.TXT" FOR OUTPUT AS #2:PRINT"[OK]":END',
                   pre=("5 MAXFILES=2",)),
    "sv_openrw": prog(OPN, '30 SAVE "Y.BAS"',
                      '40 CLOSE:OPEN "Y.BAS" FOR INPUT AS #1:A$=INPUT$(1,#1):PRINT"[";ASC(A$);"]":END'),
}
WRITABLE = {"sv_openrw"}


def image(writable):
    fh = tempfile.NamedTemporaryFile(suffix=".dsk", delete=False)
    fh.close()
    shutil.copy(FIXTURE, fh.name)
    if not writable:
        os.chmod(fh.name, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
    return fh.name


def main():
    only = sys.argv[1:] or list(CASES)
    got = {}
    for m in (REF, ZB):
        cf = m == REF
        for k in only:
            raw = omsx_repl.run_cases(m, [("direct", CASES[k])], batch=False,
                                      reset=("", "SCREEN 0", "CLS") if cf else ("CLS",),
                                      boot=14.0 if cf else 8.0, capture="screen",
                                      diska=image(k in WRITABLE), step=8.0,
                                      cap_gap=20.0)[0] or ""
            r = re.findall(r"\[[^\]\"]*\]", raw)
            got[(m, k)] = " ".join(r[-1].split()) if r else "NO READING"
    print(f"{'case':9} {'CF-3300':>16} {'zerobas':>16}")
    bad = 0
    for k in only:
        a, b = got[(REF, k)], got[(ZB, k)]
        print(f"{'  ' if a == b else '✗ '}{k:9} {a:>16} {b:>16}")
        bad += a != b or "NO READING" in (a, b)
    print(f"WPROTECT: {'PASS' if not bad else f'FAIL ({bad} of {len(only)})'}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
