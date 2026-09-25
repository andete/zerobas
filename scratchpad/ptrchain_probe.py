"""D-ADDR29 S2, the premise: does zerobas already KEEP the pointer chain the
reference publishes -- VARTAB, ARYTAB, STREND -- in some cell of its own,
with the same value in every state? (docs/spec-basic-addr29.md §2/§5.)

If a zerobas cell equals the reference's pointer in every state, S2 is an
EQUATE move (0 ROM bytes). A state where it does not is the price.

  reference (MSX2 TH work area):  VARTAB $F6C2  ARYTAB $F6C4  STREND $F6C6
  zerobas candidates (sysvars.inc): PRGEND $E026 (+2)  ARYTAB $E1C0  CTLLIM $E056

Each case is typed on a fresh boot (VG-8020 vs zerobas NODISK, both diskless)
and ends with one fenced line of 4-digit hex cells. The printing loop creates
`I` and `A` on BOTH machines in the same order, so they are part of every
state, identically. Clean room: typed BASIC, documented work-area cells and
zerobas's own cells, screen text. No ROM byte is read.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
REF_CELLS = [("VARTAB", 0xF6C2), ("ARYTAB", 0xF6C4), ("STREND", 0xF6C6)]
ZB_CELLS = [("PRGEND", 0xE026), ("ARYTAB", 0xE1C0), ("CTLLIM", 0xE056)]

CASES = [
    ("boot",        []),
    ("scalar",      ["A=1"]),
    ("two",         ["A=1:B=2"]),
    ("dim",         ["DIM B(5)"]),
    ("dim_then_sc", ["DIM B(5):C=3"]),
    ("string",      ['A$="HELLO"']),
    ("erase",       ["DIM B(5):ERASE B"]),
    ("program",     ["10 A=1", "20 B=2"]),
    ("run",         ["10 A=1:DIM B(5)", "RUN"]),
]


def show(cells):
    hexes = "".join(f"{a:04X}" for _n, a in cells)
    return (f'PRINTCHR$(91);:FORI=0TO{len(cells) - 1}:A=VAL("&H"+MID$("{hexes}",I*4+1,4)):'
            f'PRINTRIGHT$("000"+HEX$(PEEK(A)+256*PEEK(A+1)),4);:NEXT:PRINTCHR$(93)')


def answer(raw):
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    hit = [r[1:-1] for r in rows if r.startswith("[") and r.endswith("]")]
    if not hit:
        return None
    h = hit[-1]
    return [int(h[k:k + 4], 16) for k in range(0, len(h), 4)]


# 🧵 THE STRING HALF (spec §2: FRETOP/MEMSIZ move with the chain). The two
# string areas sit at different addresses (zerobas's ceiling is TXTMAX $DB00,
# the VG-8020's MEMSIZ $F168), so the comparable quantity is the USED string
# bytes: MEMSIZ - FRETOP there, $DB00 - FRETOP here (zerobas FRETOP $E268,
# "heap low boundary").
REF_S = [("FRETOP", 0xF69B), ("MEMSIZ", 0xF672)]
ZB_S = [("FRETOP", 0xE268)]
ZB_CEIL = 0xDB00


def strings():
    got = {}
    for m, cells in ((REF, REF_S), (ZB, ZB_S)):
        specs = [("direct", pre + [show(cells)]) for _k, pre in CASES]
        res = omsx_repl.run_cases(m, specs, batch=False,
                                  reset=("", "SCREEN 0", "NEW"), boot=8.0,
                                  capture="screen")
        got[m] = [answer(r or "") for r in res]
    bad = 0
    print(f"\n{'case':12s}  used string bytes: ref MEMSIZ-FRETOP   zb $DB00-FRETOP")
    for i, (k, _pre) in enumerate(CASES):
        r, z = got[REF][i], got[ZB][i]
        if r is None or z is None:
            bad += 1
            print(f"DIFF {k:12s} ref={r} zb={z}  <NO OUTPUT on a side>")
            continue
        ru, zu = r[1] - r[0], ZB_CEIL - z[0]
        bad += ru != zu
        print(f"{'SAME' if ru == zu else 'DIFF'} {k:12s} {ru:6d} (FRETOP ${r[0]:04X})"
              f"   {zu:6d} (FRETOP ${z[0]:04X})")
    print(f"\nSTRINGS DIFF: {bad}/{len(CASES)}")


def main():
    if "--strings" in sys.argv:
        strings()
        return 0
    # --after (S2 built): read zerobas's PUBLISHED cells, the same three the
    # reference is read at, and compare them DIRECTLY -- no +2, no twin.
    after = "--after" in sys.argv
    zb_cells = REF_CELLS if after else ZB_CELLS
    got = {}
    for m, cells in ((REF, REF_CELLS), (ZB, zb_cells)):
        specs = [("direct", pre + [show(cells)]) for _k, pre in CASES]
        res = omsx_repl.run_cases(m, specs, batch=False,
                                  reset=("", "SCREEN 0", "NEW"), boot=8.0,
                                  capture="screen")
        got[m] = [answer(r or "") for r in res]
    bad = 0
    zhead = "VARTAB/ARYTAB/STREND (published)" if after else "PRGEND+2/ARYTAB/CTLLIM"
    print(f"{'case':12s}  ref VARTAB/ARYTAB/STREND    zb {zhead}")
    for i, (k, _pre) in enumerate(CASES):
        r, z = got[REF][i], got[ZB][i]
        if r is None or z is None:
            bad += 1
            print(f"DIFF {k:12s} ref={r} zb={z}  <NO OUTPUT on a side>")
            continue
        zz = list(z) if after else [z[0] + 2, z[1], z[2]]
        marks = ["=" if a == b else "≠" for a, b in zip(r, zz)]
        same = all(m == "=" for m in marks)
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:12s} "
              f"${r[0]:04X} ${r[1]:04X} ${r[2]:04X}   "
              f"${zz[0]:04X}{marks[0]} ${zz[1]:04X}{marks[1]} ${zz[2]:04X}{marks[2]}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
