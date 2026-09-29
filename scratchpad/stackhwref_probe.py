"""D-DIMRESERVE, the economy half: how deep does a STATEMENT's machine stack go
below its statement-level base -- on the VG-8020 AND on zerobas, for the SAME
programs?

The reference fits a DIM down to ~137 B of FRE(0) (scratchpad/dimedge_run.out);
zerobas reserves 256 B, and that reserve is already near the floor its own
stack sets: a flat expression after an edge DIM needs the statement's stack
(~110 B) plus the evaluator's STK_EVAL_RESERVE (128). So whether zerobas CAN
match the reference's edge is a question about per-statement stack use, and
that is measurable on both machines by stack painting (stackhw_probe.py's
method). RAM contents only -- clean room (expansion-protocol.md §7):

    base  VG-8020: STKTOP ($F674, a published work-area cell) -- the stack grows
                   down from it and holds 4 B of interpreter state at statement
                   level (docs/reference-stack-frames.md §1)
          zerobas: CSP ($E050), the pool frontier SP descends from
    10 C=<base>:L%=C%-BAND:H%=C%-48      (int16 walk -- stackhw_probe.py says why)
    20 paint [L,H] with &HA5             (the FOR frame sits above H on both:
                                          25 B on the reference, pool on zerobas)
    30 <the statement>
    40 scan for the lowest overwritten byte -> depth = C - it

The painting and scanning loops run on the same stack, so every reading is at
least the probe's OWN loop depth: `idle` IS that floor, and it is itself the
comparison that matters most -- a FOR/IF/PEEK statement's stack on each machine.

    python3 -u scratchpad/stackhwref_probe.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF = "Philips_VG_8020"
ZB = "C-BIOS_MSX1_EU_REPACK_NODISK"
BASE = {REF: "&HF674", ZB: "&HE050"}
BAND = 1500
WORK = [
    ("idle",     "A=1"),
    ("flat",     "A=B+C*D-E/2"),
    ("paren4",   "A=((((1+1)+1)+1)+1)"),
    ("strings",  'A$=MID$(LEFT$(RIGHT$(STRING$(50,65),40),30),5,10)+CHR$(65)+HEX$(255)+STR$(1.5)'),
    ("print",    'PRINT 1;"X";2.5'),
    ("using",    'PRINT USING "###.##";12.345'),
    ("graphics", 'SCREEN 2:CIRCLE(128,96),50,15:PAINT(128,96),8,15:DRAW"U10R10D10L10":SCREEN 0'),
    ("play",     'PLAY"CDEFGAB":FOR W=1 TO 300:NEXT'),
    ("errtrap",  "ON ERROR GOTO 50:A=1/0"),
]


def prog(base, stmt):
    return ["NEW", f"10 C=PEEK({base})+256*PEEK({base}+1):C%=C-65536:L%=C%-{BAND}:H%=C%-48",
            "20 FOR A%=L% TO H%:POKE A%,&HA5:NEXT",
            f"30 {stmt}",
            "40 M%=H%+1:FOR A%=L% TO H%:IF PEEK(A%)<>&HA5 THEN IF A%<M% THEN M%=A%",
            "45 NEXT:SCREEN 0:PRINT CHR$(91);C%-M%;CHR$(93):END",
            "50 RESUME 40", "RUN"]


def main():
    got = {}
    for m in (REF, ZB):
        raws = omsx_repl.run_cases(m, [("direct", prog(BASE[m], s)) for _k, s in WORK],
                                   batch=False, reset=("CLS",), boot=8.0, step=3.0,
                                   run_gap=90.0, capture="screen")
        for (k, _s), raw in zip(WORK, raws):
            r = re.findall(r"\[\s*(-?\d+)\s*\]", raw or "")
            got[(m, k)] = r[-1] if r else "NO READING"
    print(f"machine-stack depth below the statement-level base (bytes; 48 = nothing "
          f"reached the band, {BAND} = AT LEAST the band):")
    print(f"  {'case':9} {'VG-8020':>8} {'zerobas':>8}")
    for k, s in WORK:
        print(f"  {k:9} {got[(REF, k)]:>8} {got[(ZB, k)]:>8}   {s[:56]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
