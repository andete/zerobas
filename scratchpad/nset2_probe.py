"""D-ADDR29, the rest of the N set: what do the reference's interpreter-scratch
cells READ after an operation, against what zerobas leaves there?

RAMFOOT (scratchpad/ramfoot_probe.py) saw the VG-8020 WRITE these during the
operations below; a write a program can never see after the fact costs nothing
to skip, as S3 (CNSDFG) and the first N-set probe (PTRFIL/ESCCNT/GRPHED) found.
So each cell is captured into an array element on the operation's OWN line --
one loop, no string built -- and printed after.

  DIMFLG $F662   ENDFOR $F6A1 (2)   SUBFLG $F6A5   TEMP $F6A7 (2)
  PRMFLG $F7B4   ARYTA2 $F7B5 (2)   DECCNT $F7F4 (2)   DSCTMP $F698 (3)
  PRTFLG $F416   ARG    $F847 (first 2 of 16)

Byte-wise, 16 bytes per case. Diskless pair, fresh boot per case. Clean room:
typed BASIC, documented work-area cells, screen text. No ROM byte.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
# (name, address) per BYTE, so a 2-byte cell is two rows
BYTES = [("DIMFLG", 0xF662), ("ENDFOR", 0xF6A1), ("ENDFOR+1", 0xF6A2),
         ("SUBFLG", 0xF6A5), ("TEMP", 0xF6A7), ("TEMP+1", 0xF6A8),
         ("PRMFLG", 0xF7B4), ("ARYTA2", 0xF7B5), ("ARYTA2+1", 0xF7B6),
         ("DECCNT", 0xF7F4), ("DECCNT+1", 0xF7F5), ("DSCTMP", 0xF698),
         ("DSCTMP+1", 0xF699), ("DSCTMP+2", 0xF69A), ("PRTFLG", 0xF416),
         ("ARG", 0xF847)]
OPS = [("ctl", ""), ("num", "A=1"), ("int", "A%=1"), ("str", 'A$="AB"'),
       ("dim", "DIM Z(5)"), ("for", "FOR I=1 TO 2:NEXT"), ("print", "PRINT 1"),
       ("rnd", "X=RND(1)"), ("sin", "X=SIN(1)"), ("strd", "A$=STR$(5)"),
       ("left", 'A$=LEFT$("AB",1)'), ("fre", "X=FRE(0)")]


def line(op):
    hexs = "".join(f"{a:04X}" for _n, a in BYTES)
    n = len(BYTES)
    dim = f"DIM W({n - 1}):"
    # 🔴 DIM FIRST: 16 elements is past the default 10 -- the first run had
    # every case raise `Subscript out of range` on BOTH machines, and the
    # scorer called all 16 cells SAME on zero readings (fixed below too).
    # The DIM happens BEFORE the op, so the op's own writes are what is read.
    grab = f'FORK=0TO{n - 1}:W(K)=PEEK(VAL("&H"+MID$("{hexs}",K*4+1,4))):NEXT'
    show = f"PRINT:PRINT12345;:FORK=0TO{n - 1}:PRINTW(K);:NEXT"
    return dim + (op + ":" if op else "") + grab + ":" + show


def answer(raw):
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS] for r in range(omsx_repl.ROWS)]
    text = "".join(r[2:39] for r in rows)       # the output wraps: join the text area
    i = text.rfind(" 12345 ")
    if i < 0:
        return None
    vals = text[i + 7:].split()
    return vals[:len(BYTES)] if len(vals) >= len(BYTES) else None


def main():
    specs = [("direct", [line(op)]) for _k, op in OPS]
    got = {m: [answer(r or "") for r in
               omsx_repl.run_cases(m, specs, batch=False,
                                   reset=("", "SCREEN 0", "NEW"), boot=8.0,
                                   capture="screen")]
           for m in (REF, ZB)}
    diff = {n: [] for n, _a in BYTES}
    unread = 0
    for i, (k, op) in enumerate(OPS):
        r, z = got[REF][i], got[ZB][i]
        if r is None or z is None:
            print(f"?? {k:6s} ref={r} zb={z}  <NO OUTPUT on a side>")
            unread += 1
            continue
        for (n, _a), a, b in zip(BYTES, r, z):
            if a != b:
                diff[n].append(f"{k}:{a}|{b}")
    for n, _a in BYTES:
        print(f"{'SAME' if not diff[n] else 'DIFF'} {n:9s} {len(diff[n])}/{len(OPS)}  "
              f"{' '.join(diff[n][:6])}")
    print(f"\nDIFF: {sum(1 for v in diff.values() if v)}/{len(BYTES)} bytes")
    # 🔴 A CASE WITH NO READING IS NOT AN AGREEMENT: refuse rather than let a
    # SAME stand on cases that were never read.
    if unread:
        print(f"REFUSED: {unread}/{len(OPS)} case(s) produced no reading -- "
              f"the SAME rows above do not cover them")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
