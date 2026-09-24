#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-ADDR29 S1: is zerobas's FOUTBUF the SAME variable as the published FBUFFR?

An equate move (spec-basic-addr29.md route E) is only legitimate when the
CONTENT matches: after a number is formatted, a program that PEEKs FBUFFR
($F7C5) must read on zerobas what it reads on the VG-8020. This snapshots
FBUFFR on the reference and FOUTBUF on zerobas at the moment the program writes
its end mark, for a few formatting operations, and prints both as ASCII + hex.

Clean room: RAM contents at a program-written mark; no ROM byte is read.
"""
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_DISK"
FBUFFR, FOUTBUF, WIDTH = 0xF7C5, 0xF024, 24
MARK = 0xE000
CASES = ['A$=STR$(123.5)', 'A$=STR$(-7)', 'A$=STR$(1E+20)', 'A#=1/3:A$=STR$(A#)',
         'PRINT 42', 'PRINT 3.25']

TCL = r'''
array set ::snap {}
debug set_watchpoint write_mem @MARK@ {} {
    set b [debug read_block memory @BASE@ @W@]
    binary scan $b H* hx
    set ::snap($::wp_last_value) $hx
}
proc __dump {} {
    set f [open {@OUT@} w]
    foreach k [array names ::snap] { puts $f "S $k $::snap($k)" }
    close $f
    after time 1 __dump
}
after time 1 __dump
'''


def run(machine, base):
    import omsx_repl
    fd, out = tempfile.mkstemp(prefix="fbuffr-")
    os.close(fd)
    t = TCL
    for k, v in (("@MARK@", str(MARK)), ("@BASE@", str(base)), ("@W@", str(WIDTH)),
                 ("@OUT@", out)):
        t = t.replace(k, v)
    specs = [("direct", ["NEW", f"10 {op}:POKE&H{MARK:04X},{i + 1}", "RUN"])
             for i, op in enumerate(CASES)]
    omsx_repl.run_cases(machine, specs, batch=True, reset=("CLS",), boot=8.0,
                        capture="screen", prologue=(t,))
    got = {}
    for ln in open(out):
        p = ln.split()
        if len(p) == 3 and p[0] == "S":
            got[int(p[1])] = bytes.fromhex(p[2])
    os.unlink(out)
    return got


def show(b):
    return "".join(chr(c) if 32 <= c < 127 else "." for c in b) + "  " + b.hex(" ")


def main():
    # since D-ADDR29 S1 zerobas's FOUTBUF IS FBUFFR+1, so both sides are read at
    # the published address (FOUTBUF-1 == FBUFFR here; `$F024` before S1)
    ref, zb = run(REF, FBUFFR), run(ZB, FBUFFR if "--before" not in sys.argv else FOUTBUF)
    # other code writes $E000 too (ref 0/255, zb 15/240) -- only 1..N are ours
    want = set(range(1, len(CASES) + 1))
    if not want <= set(ref) or not want <= set(zb):
        print(f"REFUSE: snapshots ref {sorted(ref)} zb {sorted(zb)}")
        return 2
    for i, op in enumerate(CASES):
        r, z = ref[i + 1], zb[i + 1]
        print(f"{op}\n  ref FBUFFR : {show(r)}\n  zb FBUFFR : {show(z)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
