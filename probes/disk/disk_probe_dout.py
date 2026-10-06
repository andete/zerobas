#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""S10.B (gate: dout-acceptance): a disk file open FOR OUTPUT is an MSX-DOS FCB
in disk.rom -- does every observable of the channel still read as on the
CF-3300?

Each case runs on a fresh test720 copy, on the CF-3300 and on ours, and prints
one fenced reading `R<...>#` (quoted text is the echoed SOURCE, never output),
with `e<err>@<erl>` inside it for each error the trap caught.

  lofloc   LOF / LOC after 0, 10, 300 and 600 B; then the file's size reopened
           (the FCB's size moves at each WHOLE 256 B record; +1 for Ctrl-Z)
  twochan  two OUTPUT channels written in alternation across several 256 B
           records, inside FOR and GOSUB; both read back (length + a checksum)
  append   an OUTPUT channel alternating with an APPEND one (main's engine)
           on another file; both read back
  input    an OUTPUT channel alternating with an INPUT one; both read back
  openchk  with a file open FOR OUTPUT: OPEN it again (54), KILL it (64),
           NAME it (64? measured); then CLOSE and read it back
  empty    OPEN FOR OUTPUT + CLOSE, nothing written: the size reopened
  exact    exactly 256 B then CLOSE: the Ctrl-Z starts a second record
  trunc    a file OPENed FOR OUTPUT over an existing longer one: the old
           tail is gone
  app6     APPEND to a 6 B file: LOF/LOC after the OPEN, 10 B and 300 B; the size
           and checksum after (LOF and LOC DIFFER on an APPEND channel)
  app256   the same on a 256 B file whose Ctrl-Z is the record's last byte

Exit 0 all agree; 1 a divergence; 2 the CF-3300 gave no reading for a case.

    python3 -u probes/disk/disk_probe_dout.py [CASE ...]
"""
import os, re, shutil, sys
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl                                   # noqa: E402
import probe_tmp                                   # noqa: E402

# read file F$ back: N = its length, C = a checksum of its first N-1 bytes
# (mod 4093: MOD takes integers, and C*7 must stay under 32768) -- the last is the Ctrl-Z, which INPUT$ may refuse
RB = ['OPEN F$ FOR INPUT AS#1:N=LOF(1):C=0:FOR J=2 TO N:C=(C*7+ASC(INPUT$(1,#1))) MOD 4093:NEXT:CLOSE#1']
CASES = {
    "lofloc": ['OPEN"LF.TXT"FOR OUTPUT AS#1', "DIM L(8)", "L(0)=LOF(1):L(1)=LOC(1)",
               'PRINT#1,"ABCDEFGH"', "L(2)=LOF(1):L(3)=LOC(1)",
               'FOR I=1 TO 29:PRINT#1,"ABCDEFGH":NEXT', "L(4)=LOF(1):L(5)=LOC(1)",
               'FOR I=1 TO 30:PRINT#1,"ABCDEFGH":NEXT', "L(6)=LOF(1):L(7)=LOC(1)",
               'CLOSE#1:OPEN"LF.TXT"FOR INPUT AS#1:L(8)=LOF(1):CLOSE#1',
               'PRINT"R<";:FOR I=0 TO 8:PRINT MID$(STR$(L(I)),2);",";:NEXT:PRINT">#"'],
    "twochan": ["MAXFILES=2", 'OPEN"A1.TXT"FOR OUTPUT AS#1', 'OPEN"A2.TXT"FOR OUTPUT AS#2',
                'FOR I=1 TO 70:PRINT#1,"X";I;:GOSUB 700:NEXT', "CLOSE",
                'F$="A1.TXT"', "GOSUB 800:P=N:Q=C", 'F$="A2.TXT"', "GOSUB 800",
                'PRINT"R<";P;Q;N;C;">#"'],
    "append": ["MAXFILES=2", 'OPEN"B1.TXT"FOR OUTPUT AS#1:PRINT#1,"OLD":CLOSE#1',
               'OPEN"B2.TXT"FOR OUTPUT AS#1', 'OPEN"B1.TXT"FOR APPEND AS#2',
               'FOR I=1 TO 60:PRINT#1,"OUT";I:PRINT#2,"APP";I:NEXT', "CLOSE",
               'F$="B1.TXT"', "GOSUB 800:P=N:Q=C", 'F$="B2.TXT"', "GOSUB 800",
               'PRINT"R<";P;Q;N;C;">#"'],
    "input": ["MAXFILES=2", 'OPEN"C1.TXT"FOR OUTPUT AS#1', 'FOR I=1 TO 40:PRINT#1,"LINE";I:NEXT', "CLOSE#1",
              'OPEN"C1.TXT"FOR INPUT AS#1', 'OPEN"C2.TXT"FOR OUTPUT AS#2',
              'FOR I=1 TO 40:LINE INPUT#1,A$:PRINT#2,A$;"+":NEXT', "CLOSE",
              'F$="C2.TXT"', "GOSUB 800", 'PRINT"R<";N;C;">#"'],
    "openchk": ["MAXFILES=2", 'OPEN"D1.TXT"FOR OUTPUT AS#1', 'PRINT#1,"HELLO"',
                'OPEN"D1.TXT"FOR INPUT AS#2', 'KILL"D1.TXT"', 'NAME"D1.TXT"AS"D2.TXT"',
                'PRINT#1,"WORLD"', "CLOSE", 'F$="D1.TXT"', "GOSUB 800", 'PRINT"R<";N;C;">#"'],
    "empty": ['OPEN"E1.TXT"FOR OUTPUT AS#1', "CLOSE#1", 'F$="E1.TXT"', "GOSUB 800",
              'PRINT"R<";N;C;">#"'],
    "exact": ['OPEN"E2.TXT"FOR OUTPUT AS#1', 'FOR I=1 TO 32:PRINT#1,"ABCDEFGH";:NEXT',
              "L=LOF(1)", "CLOSE#1", 'F$="E2.TXT"', "GOSUB 800", 'PRINT"R<";L;N;C;">#"'],
    "trunc": ['OPEN"T1.TXT"FOR OUTPUT AS#1', 'FOR I=1 TO 50:PRINT#1,"LONGLINE";I:NEXT', "CLOSE#1",
              'OPEN"T1.TXT"FOR OUTPUT AS#1', 'PRINT#1,"SHORT"', "CLOSE#1",
              'F$="T1.TXT"', "GOSUB 800", 'PRINT"R<";N;C;">#"'],
}
# S10.B increment 2: APPEND on the same writer. LOF is the FCB's size, LOC its
# random record -- they differ on APPEND (scratchpad/applof_run.out): after OPEN
# FOR APPEND on a 6 B file LOF 6 / LOC 0; on a 256 B one (its Ctrl-Z the 256th
# byte) 256 / 0, and the first appended byte overwrites that Ctrl-Z, completing
# the record: 256 / 256. Then the size reopened and the content's checksum.
for _tag, _first in (("app6", 'PRINT#1,"OLD"'), ("app256", 'PRINT#1,STRING$(255,"A");')):
    CASES[_tag] = ["CLEAR 400", 'OPEN"AP.TXT"FOR OUTPUT AS#1', _first, "CLOSE#1", "DIM L(5)",
                   'OPEN"AP.TXT"FOR APPEND AS#1:L(0)=LOF(1):L(1)=LOC(1)',
                   'PRINT#1,"ABCDEFGH":L(2)=LOF(1):L(3)=LOC(1)',
                   'FOR I=1 TO 29:PRINT#1,"ABCDEFGH":NEXT:L(4)=LOF(1):L(5)=LOC(1)',
                   'CLOSE#1:F$="AP.TXT":GOSUB 800',
                   'PRINT"R<";:FOR I=0 TO 5:PRINT MID$(STR$(L(I)),2);",";:NEXT:PRINT N;C;">#"']


# `append` alternates an OUTPUT channel (disk.rom's record writer) with an
# APPEND one (main's engine), which flushes and re-stages its sector on every
# switch: ours needs more than 60 s where the CF-3300 needs less (2026-10-06,
# a speed reading, not a face), so its capture waits longer.
GAP = {"append": 240.0}


def prog(body):
    """The case body as lines 10.., a GOSUB 700 that writes channel 2 (twochan),
    the read-back at 800, and a trap that collects `e<err>@<erl>` in E$ and
    resumes. The trap is armed AFTER a MAXFILES, which clears it (as CLEAR
    does), and every reading prints from a fresh line with E$ inside the fence,
    so no reading wraps at the screen edge mid-number."""
    if body[0].startswith(("MAXFILES", "CLEAR")):     # both clear the trap
        body = [body[0], "ON ERROR GOTO 900"] + body[1:]
    else:
        body = ["ON ERROR GOTO 900"] + body
    # (a reading still longer than the line would wrap a NUMBER mid-digits on
    # ours and whole on the references -- D-PRNUMWRAP, found by this probe's
    # first lofloc -- so lofloc prints its values comma-joined, as strings)
    body = [b.replace('PRINT"R<";', 'PRINT:PRINT"R<";E$;') for b in body]
    lines = ["NEW"]
    lines += [f"{10 + 10 * i} {s}" for i, s in enumerate(body)]
    lines += ["690 END", '700 PRINT#2,"Y";I*3;:RETURN', f"800 {RB[0]}:RETURN",
              '900 E$=E$+"e"+MID$(STR$(ERR),2)+"@"+MID$(STR$(ERL),2)+" ":RESUME NEXT', "RUN"]
    return lines


def main():
    want = sys.argv[1:] or list(CASES)
    out = {}
    for tag, machine in (("CF-3300", "National_CF-3300"),
                         ("OURS", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK"))):
        for case in want:
            dsk = probe_tmp.tmp(f"dout_{case}_{tag}.dsk")
            shutil.copyfile(os.path.join(REPO, "disk", "test720.dsk"), dsk)
            raw = omsx_repl.run_cases(machine, [("direct", prog(CASES[case]))], batch=False,
                                      reset=("", "SCREEN 0"), boot=14.0, step=1.5,
                                      run_gap=GAP.get(case, 60.0), diska=dsk)[0] or ""
            scr = re.sub(r"\s+", " ", re.sub(r'"[^"\n]*"', "", raw))
            m = re.findall(r"R<([^>#]*)>#", scr)
            out[(tag, case)] = " ".join(("R<" + m[-1] + ">").split()) if m else None
            print(f"== {tag:8} {case:8} {out[(tag, case)]!r}", flush=True)
            if not m:
                print(f"   screen tail: {scr[-200:]}", flush=True)
    print()
    bad = 0
    for case in want:
        a, b = out[("CF-3300", case)], out[("OURS", case)]
        if a is None:
            print(f"INSTRUMENT FAULT: the CF-3300 gave no reading for {case} -- no reference")
            return 2
        bad += a != b
        print(f"{'AGREE   ' if a == b else 'DIVERGES'} {case:8} CF-3300 {a!r}  ours {b!r}")
    print(f"\n{'PASS' if not bad else 'FAIL'}: {len(want) - bad}/{len(want)} OUTPUT-channel cases agree with the CF-3300")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
