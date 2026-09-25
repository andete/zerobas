"""D-DETOKBUF S2: does the string collector still take its FAST path after its
sort array left DETOKBUF? (docs/spec-detokbuf-drop.md §2.2.)

The sort array now goes in the variable free area under the live SP; when it
does not fit, the O(n^2) gc_slow runs instead. This program keeps N live
strings in a small pool and reassigns them until the collector has run many
times, and prints the JIFFY ticks it took -- on both machines, so the answer is
a RATIO (TIER 2's bar is 10x) and a correctness check on the final strings.

Diskless pair. Clean room: typed BASIC, screen text.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
# A FEW collections per case: the reference's own collector is O(n^2), and
# the first cut (30 and 15 rounds) was still running on the VG-8020 after 60 s.
CASES = [
    ("n150", 150, 3),
    ("n300", 300, 2),
]


def lines(n, rounds):
    return ["NEW",
            f"10 CLEAR 1000:DIM A$({n}):FOR I=1 TO {n}:A$(I)=\"AB\":NEXT",
            f"20 T=TIME:FOR K=1 TO {rounds}:FOR I=1 TO {n}:A$(I)=LEFT$(A$(I)+\"X\",2):NEXT:NEXT",
            "30 S=0:FOR I=1 TO %d:S=S+LEN(A$(I)):NEXT:PRINT 12345;TIME-T;S" % n,
            "RUN"]


def answer(raw):
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    hit = [r for r in rows if r.startswith("12345 ")]
    return [int(v) for v in hit[-1].split()[1:3]] if hit else None


def main():
    specs = [("direct", lines(n, r)) for _k, n, r in CASES]
    got = {m: [answer(x or "") for x in
               omsx_repl.run_cases(m, specs, batch=False,
                                   reset=("", "SCREEN 0", "NEW"), boot=8.0,
                                   step=60.0, capture="screen")]
           for m in (REF, ZB)}
    for i, (k, n, r) in enumerate(CASES):
        a, b = got[REF][i], got[ZB][i]
        if not a or not b:
            print(f"?? {k} ref={a} zb={b}  <NO OUTPUT on a side>")
            continue
        same = a[1] == b[1]
        print(f"{k}: ticks ref {a[0]} zb {b[0]}  ratio {b[0] / max(a[0], 1):.2f}   "
              f"sum-of-lengths {'SAME' if same else 'DIFF'} ({a[1]} / {b[1]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
