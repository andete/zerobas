"""WHERE DOES THE 6030 B GO? (TIER 4, goal (a); Joost 2026-09-25: *"Scout where
it goes"*.) scratchpad/fremem_probe.py measured zerobas's FRE(0) a constant
6030 B below the VG-8020's in every state. This reads each machine's memory
LAYOUT at boot -- the pointers that bound the free area -- so the gap can be
accounted for region by region.

Both diskless, a fresh boot, one typed line each. Clean room: work-area RAM
contents only (PEEK of documented cells on the reference; zerobas's own cells,
named from basic/sysvars.inc, on zerobas). No ROM byte is read.

  VG-8020 (MSX2 TH work-area table): TXTTAB $F676, VARTAB $F6C2, STREND $F6C6,
      STKTOP $F674, MEMSIZ $F672, FRETOP $F69B, HIMEM $FC4A.
  zerobas: TXTTAB $F676, PRGEND $E026, CSP $E050, CTLTOP $E052, POOLSIZE
      $E232, HIMEM $FC4A; TXTMAX is the constant $DB00 (sysvars.inc).
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
# the DISK pair: the CF-3300 reserves its disk work area below $F380 (HIMEM),
# so the gap there is a different number -- fremem measured diskless only.
REF_D, ZB_D = "National_CF-3300", "C-BIOS_MSX1_EU_REPACK_DISK"


def line(cells):
    """One typed line under the 254-char buffer: loop over the addresses as a
    hex string, printing each 16-bit cell as 4 hex digits, in `cells` order.
    🔴 CHR$ FENCES, NOT "[" "]": the TYPED line must not carry the brackets
    the answer is fenced by, or its echo reads as the answer. And the answer
    must not WRAP -- a wrapped row carries the margin into the middle of a
    number -- so the cells go on one row (4 digits each, no separator) and
    FRE(0) on its own row, fenced by { }."""
    hexes = "".join(f"{a:04X}" for _n, a in cells)
    return (f'PRINTCHR$(91);:FORI=0TO{len(cells) - 1}:A=VAL("&H"+MID$("{hexes}",I*4+1,4)):'
            f'PRINTRIGHT$("000"+HEX$(PEEK(A)+256*PEEK(A+1)),4);:NEXT:'
            f'PRINTCHR$(93):PRINTCHR$(123);FRE(0);CHR$(125)')


REF_CELLS = [("TXTTAB", 0xF676), ("VARTAB", 0xF6C2), ("STREND", 0xF6C6),
             ("STKTOP", 0xF674), ("MEMSIZ", 0xF672), ("FRETOP", 0xF69B),
             ("HIMEM", 0xFC4A)]
ZB_CELLS = [("TXTTAB", 0xF676), ("PRGEND", 0xE026), ("CSP", 0xE050),
            ("CTLTOP", 0xE052), ("POOLSIZE", 0xE232), ("HIMEM", 0xFC4A)]


def answer(raw):
    """(the fenced hex row, the fenced FRE row) -- each fits one screen row."""
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    cells = [r[1:-1] for r in rows if r.startswith("[") and r.endswith("]")]
    fre = [r[1:-1].strip() for r in rows if r.startswith("{") and r.endswith("}")]
    return (cells[-1], fre[-1]) if cells and fre else None


def main():
    got = {}
    pairs = ((REF, REF_CELLS), (ZB, ZB_CELLS), (REF_D, REF_CELLS), (ZB_D, ZB_CELLS))
    for m, cells in pairs:
        res = omsx_repl.run_cases(m, [("direct", [line(cells)])], batch=False,
                                  reset=("", "SCREEN 0", "NEW"), boot=8.0, capture="screen")
        got[m] = answer(res[0] or "")
    for m, cells in pairs:
        print(f"{m}:")
        if not got[m]:
            print("   <NO OUTPUT>")
            continue
        hexrow, fre = got[m]
        vals = [hexrow[k:k + 4] for k in range(0, len(hexrow), 4)]
        for (n, a), v in zip(cells, vals):
            print(f"   {n:9s} ${a:04X} = ${int(v, 16):04X}")
        print(f"   FRE(0) = {fre}")
    return 0 if all(got.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
