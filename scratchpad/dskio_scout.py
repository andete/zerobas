#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
r"""D-DSKIO scout — what DSKI$ / DSKO$ actually do on the CF-3300 and the VG-8020.

Three measurements, all black-box (docs/spec-basic-dskio.md §1-2):
  faces   the string DSKI$ evaluates to, the address in its descriptor, the
          bytes there; DSKO$'s arities; out-of-range sector and drive faces.
  dump    a Tcl write-watchpoint on $FFF0 dumps $8000..$FFFF at three POKEs --
          before any DSKI$, after DSKI$(0,7), after DSKI$(0,0) -- and the
          script searches the dumps for the directory / boot-sector bytes and
          for a pointer cell holding that address. This is how the buffer
          ($EB95) and its pointer ($F351) were found; a BASIC PEEK loop over
          the same band did not finish inside any budget.
  dsko    DSKI$(0,7), POKE the first byte of the buffer, DSKO$ 0,7, FILES; then
          read sector 7 of the private image from the host side.
  vg      the diskless reference: every form is ERR 5 except the statement
          position of DSKI$, which is ERR 2.
"""
from __future__ import annotations
import os, sys, shutil
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)   # chokepoint ROOT rule: never a hardcoded path
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl, probe_sides, probe_tmp                       # noqa: E402
FIXTURE = os.path.join(REPO, "disk", "test720.dsk")

def fence(tag, c):
    k = len(c or "")
    while True:
        i = c.rfind("[" + tag, 0, k)
        if i < 0: return None
        j = c.find("]", i + 1)
        if j > 0 and '";' not in c[i:j]: return " ".join(c[i + len(tag) + 1:j].split())
        k = i

def run(side, cfg, tag, prog, prologue=None, gap=40.0):
    dsk = probe_tmp.tmp(f"dskio_{tag}_{side}.dsk"); shutil.copyfile(FIXTURE, dsk)
    kw = dict(batch=False, boot=cfg["boot"], reset=cfg["reset"], run_gap=gap)
    if side != "vg8020": kw["diska"] = probe_sides.diska(side, dsk)
    if prologue: kw["prologue"] = (prologue,)
    cap = omsx_repl.run_cases(cfg["machine"], [(tag, prog + ["RUN"])], **kw)[0] or ""
    return cap, dsk

FACES = {
 "vp":  ['20 A$=DSKI$(0,0)', '30 P=PEEK(VARPTR(A$)+1)+256*PEEK(VARPTR(A$)+2)', '40 PRINT"[vp";LEN(A$);P;PEEK(P);PEEK(P+1);PEEK(P+2);PEEK(P+3);"]":END'],
 "dir": ['20 A$=DSKI$(0,7)', '30 P=PEEK(VARPTR(A$)+1)+256*PEEK(VARPTR(A$)+2)', '40 PRINT"[dir";P;CHR$(PEEK(P));CHR$(PEEK(P+1));CHR$(PEEK(P+2));CHR$(PEEK(P+3));"]":END'],
 "o2":  ['20 A$=DSKI$(0,0)', '30 DSKO$ 0,0', '40 PRINT"[o2 OK]":END'],
 "o1":  ['30 DSKO$ 0', '40 PRINT"[o1 OK]":END'],
 "bad": ['20 A$=DSKI$(0,9999)', '40 PRINT"[bad OK";LEN(A$);"]":END'],
 "drv": ['20 A$=DSKI$(1,0)', '40 PRINT"[drv OK";LEN(A$);"]":END'],
 "dr3": ['20 A$=DSKI$(3,0)', '40 PRINT"[dr3 OK";LEN(A$);"]":END'],
 "ptr": ['20 A$=DSKI$(0,7)', '30 P=PEEK(&HF351)+256*PEEK(&HF352)', '40 PRINT"[ptr";P;CHR$(PEEK(P));CHR$(PEEK(P+1));CHR$(PEEK(P+2));CHR$(PEEK(P+3));"]":END'],
}
VG = {
 "vi":  ['20 A$=DSKI$(0,0)', '40 PRINT"[vi OK";LEN(A$);"]":END'],
 "vo":  ['20 DSKO$ 0,0', '40 PRINT"[vo OK]":END'],
 "vi1": ['20 A$=DSKI$(0)', '40 PRINT"[vi1 OK";LEN(A$);"]":END'],
 "vo1": ['20 DSKO$ 0', '40 PRINT"[vo1 OK]":END'],
 "vis": ['20 DSKI$ 0,0', '40 PRINT"[vis OK]":END'],
}
def trap(tag, body): return ['10 ON ERROR GOTO 90'] + body + [f'90 PRINT"[{tag} ERR";ERR;"]":END']

def main() -> int:
    cfgs = probe_sides.sides("cf3300", "vg8020")
    cf = cfgs["cf3300"]
    print("=== faces (cf3300)")
    for tag, body in FACES.items():
        cap, _ = run("cf3300", cf, tag, trap(tag, body))
        print(f"  {tag:4} {fence(tag, cap)!r}")
    print("=== dump (cf3300): where does the sector go, and what points at it")
    base = probe_tmp.tmp("dskio_dump")
    prologue = ('set ::n 0\n' 'debug set_watchpoint write_mem 0xFFF0 {} {\n' '  incr ::n\n'
                f'  set f [open "{base}_$::n.bin" w]\n' '  fconfigure $f -translation binary\n'
                '  puts -nonewline $f [debug read_block memory 0x8000 0x8000]\n' '  close $f }\n')
    prog = trap("dd", ['20 POKE &HFFF0,1', '30 A$=DSKI$(0,7)', '40 POKE &HFFF0,2', '50 A$=DSKI$(0,0)', '60 POKE &HFFF0,3', '70 PRINT"[dd OK]":END'])
    cap, _ = run("cf3300", cf, "dd", prog, prologue=prologue)
    print("  face:", fence("dd", cap))
    def find(b, needle):
        out, k = [], 0
        while (i := b.find(needle, k)) >= 0: out.append(f"${0x8000 + i:04X}"); k = i + 1
        return out
    for n, what in ((1, "before any DSKI$"), (2, "after DSKI$(0,7)"), (3, "after DSKI$(0,0)")):
        p = f"{base}_{n}.bin"
        if not os.path.exists(p): print(f"  dump {n}: MISSING"); continue
        d = open(p, "rb").read()
        print(f"  dump {n} ({what}): 'TEST    BIN' at {find(d, b'TEST    BIN')}  'ZEROBAS ' at {find(d, b'ZEROBAS ')}")
        if n == 3:
            for a in find(d, b"ZEROBAS "):
                buf = int(a[1:], 16) - 3
                lo, hi = buf & 0xFF, buf >> 8
                print(f"    buffer ${buf:04X}; pointer cells holding it: {find(d, bytes([lo, hi]))}")
    print("=== dsko (cf3300): write the buffer back")
    prog = trap("do", ['20 A$=DSKI$(0,7)', '30 P=PEEK(&HF351)+256*PEEK(&HF352):POKE P,ASC("X")', '40 DSKO$ 0,7', '50 FILES', '60 PRINT"[do OK]":END'])
    cap, dsk = run("cf3300", cf, "do", prog)
    rows = [cap[k:k + 40].rstrip() for k in range(0, len(cap), 40)]
    print("  screen:", " / ".join(r for r in rows if r.strip())[-200:])
    print("  on disk, sector 7 head:", open(dsk, "rb").read()[7 * 512:7 * 512 + 12])
    print("=== diskless (vg8020)")
    for tag, body in VG.items():
        cap, _ = run("vg8020", cfgs["vg8020"], tag, trap(tag, body), gap=30.0)
        print(f"  {tag:4} {fence(tag, cap)!r}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
