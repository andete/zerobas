"""D-ADDR29 N set, observable first (docs/spec-basic-addr29.md §4.1): what does
a PEEK of each cell READ after the operation RAMFOOT saw the VG-8020 write it
in? A write that leaves the value a program would read anyway costs nothing to
skip -- S3 found exactly that for CNSDFG -- so the reading is measured before
anything is priced.

  TTYPOS $F661 (1)  the print column     ESCCNT $FCA7 (1)  CHPUT escape count
  PTRFIL $F864 (2)  current file pointer GRPHED $FCA6 (1)  graphic-char flag
  FNKSWI $FBCD (1)  function-key switch  LINWRK $FC18 (40) CLS scratch (2 B read)

Every cell is captured into a variable FIRST, on the same line as the
operation, so the readout's own PRINT cannot move it. Diskless pair (VG-8020 vs
zerobas NODISK), fresh boot per case. Clean room: typed BASIC, documented
cells, screen text. No ROM byte.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
CELLS = [("TTYPOS", "PEEK(&HF661)"), ("PTRFIL", "PEEK(&HF864)+256*PEEK(&HF865)"),
         ("ESCCNT", "PEEK(&HFCA7)"), ("GRPHED", "PEEK(&HFCA6)"),
         ("FNKSWI", "PEEK(&HFBCD)"), ("LINWRK", "PEEK(&HFC18)+256*PEEK(&HFC19)")]
GRAB = ":".join(f"V{i}={e}" for i, (_n, e) in enumerate(CELLS))
SHOW = ("PRINT:PRINT12345;V0;V1;V2:PRINT12346;V3;V4;V5")
CASES = [
    ("boot",     ""),
    ("print_sc", 'PRINT"ABC";'),
    ("print_nl", 'PRINT"ABCDE"'),
    ("locate",   "LOCATE 5,5"),
    ("cls",      "CLS"),
    ("crt_file", 'OPEN"CRT:"FOR OUTPUT AS#1:PRINT#1,"X";:CLOSE#1'),
    ("grph_chr", 'PRINT CHR$(1);"A";'),
    ("esc_half", 'PRINT CHR$(27);"Y";'),
]


def answer(raw):
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    a = [r for r in rows if r.startswith("12345 ")]
    b = [r for r in rows if r.startswith("12346 ")]
    if not a or not b:
        return None
    return a[-1].split()[1:] + b[-1].split()[1:]


def main():
    got = {}
    for m in (REF, ZB):
        specs = [("direct", [(op + ":" if op else "") + GRAB + ":" + SHOW])
                 for _k, op in CASES]
        res = omsx_repl.run_cases(m, specs, batch=False,
                                  reset=("", "SCREEN 0", "NEW"), boot=8.0,
                                  capture="screen")
        got[m] = [answer(r or "") for r in res]
    names = [n for n, _e in CELLS]
    diff_cells = {n: 0 for n in names}
    for i, (k, op) in enumerate(CASES):
        r, z = got[REF][i], got[ZB][i]
        if r is None or z is None:
            print(f"DIFF {k:9s} ref={r} zb={z}  <NO OUTPUT on a side>  {op}")
            for n in names:
                diff_cells[n] += 1
            continue
        marks = []
        for n, a, b in zip(names, r, z):
            if a != b:
                diff_cells[n] += 1
                marks.append(f"{n} {a}|{b}")
        print(f"{'SAME' if not marks else 'DIFF'} {k:9s} {'; '.join(marks) or '-'}   {op}")
    print("\nper cell, cases differing: " +
          ", ".join(f"{n} {c}/{len(CASES)}" for n, c in diff_cells.items()))
    print(f"DIFF: {sum(1 for c in diff_cells.values() if c)}/{len(names)} cells")
    return 0


if __name__ == "__main__":
    sys.exit(main())
