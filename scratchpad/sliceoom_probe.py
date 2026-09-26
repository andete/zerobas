"""D-SLICEOOM: do LEFT$/RIGHT$/MID$ of a large string fit a tight pool as they do
on the reference -- and still return the right bytes?

Found 2026-09-26: `CLEAR 60:A$=STRING$(50,"A"):B$=MID$(A$,2,3)` raised `Out of
string space` on zerobas and left FRE("") 7 on the VG-8020 -- zerobas copied
the WHOLE source before slicing it. The fix keeps a SCALAR source as-is and
allocates only the result (sub/strheap.asm op 21 + she_slice_new).

Cases: the tight-pool shapes; exact VALUES of each verb; a collection forced
DURING the argument evaluation (the kept source's body moves before the copy);
a slice of a slice (the in-place path); and an ARRAY-element source, which
still takes the full-copy path (its descriptor moves on a region shift) -- that
row is expected to keep diverging and says so.

Diskless pair, fresh boot per case. Clean room: typed BASIC, screen text.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
AZ = 'A$="ABCDEFGHIJKLMNOPQRST"'
CASES = [
    ("mid50",    'CLEAR 60:A$=STRING$(50,"A"):B$=MID$(A$,2,3):PRINT12345;LEN(B$);FRE("")'),
    ("left50",   'CLEAR 60:A$=STRING$(50,"A"):B$=LEFT$(A$,5):PRINT12345;LEN(B$);FRE("")'),
    ("lenmid50", 'CLEAR 60:A$=STRING$(50,"A"):X=LEN(MID$(A$,2,3)):PRINT12345;X;FRE("")'),
    ("mid40",    'CLEAR 60:A$=STRING$(40,"A"):B$=MID$(A$,2,3):PRINT12345;LEN(B$);FRE("")'),
    ("vals",     AZ + ':PRINT12345;LEFT$(A$,2);RIGHT$(A$,3);MID$(A$,3,4);MID$(A$,19)'),
    ("gcargs",   'CLEAR 60:' + AZ + ':B$=MID$(A$,LEN(A$+A$)-30,3):PRINT12345;B$;FRE("")'),
    ("nested",   AZ + ':PRINT12345;MID$(LEFT$(A$,10),3,2);RIGHT$(MID$(A$,5,6),2)'),
    ("array50",  'CLEAR 70:DIM A$(1):A$(1)=STRING$(50,"A"):B$=MID$(A$(1),2,3):PRINT12345;LEN(B$)'),
]


def answer(raw):
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    hit = [r for r in rows if r.startswith("12345 ")]
    if hit:
        return " ".join(hit[-1].split()[1:])
    err = [r for r in rows if "space" in r.lower() or "memory" in r.lower()
           or "complex" in r.lower()]
    return err[-1] if err else None


def main():
    specs = [("direct", [line]) for _k, line in CASES]
    got = {m: [answer(r or "") for r in
               omsx_repl.run_cases(m, specs, batch=False,
                                   reset=("", "SCREEN 0", "NEW"), boot=8.0,
                                   capture="screen")]
           for m in (REF, ZB)}
    bad = 0
    for i, (k, _l) in enumerate(CASES):
        r, z = got[REF][i], got[ZB][i]
        same = r is not None and r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:9s} ref: {r}   zb: {z}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
