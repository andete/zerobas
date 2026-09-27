"""D-DIMRESERVE's measurement: how deep does zerobas's MACHINE STACK go below
its base, the pool frontier CSP?

CTL_STACK_MARGIN (256) is the reserve between the arrays and CSP, and zerobas
refuses a DIM that would eat into it -- where the VG-8020 reserves ~130 B
(scratchpad/dimedge_run.out). Before that margin may shrink, its WORST CASE must
be known. Stack painting, on zerobas's OWN RAM:

    10 C%=<CSP>:L%=C%-400:H%=C%-48     (CSP = $E050, zerobas's own cell)
    20 FOR A%=L% TO H%:POKE A%,&HA5:NEXT (paint the band below the frontier)
    30 <one heavy statement, no FOR/GOSUB>
    40 scan [L,H] for the lowest byte that is no longer &HA5 -> depth = C - it

The painting loop's own FOR frame (11 B) and up to three nested FN frames sit
above H (C-48), so they cannot be mistaken for stack. Interrupts (PLAY, the
timer hook) run on the same stack and are counted too.

    python3 -u scratchpad/stackhw_probe.py
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

ZB = "C-BIOS_MSX1_EU_REPACK_NODISK"
P20 = "(" * 20 + "1" + "+1)" * 20
P32 = "(" * 32 + "1" + "+1)" * 32                       # parennest's deepest row
F32 = "ABS(" * 32 + "1" + ")" * 32
S16 = "LEN(" + "CHR$(ASC(" * 16 + "CHR$(65)" + "))" * 16 + ")"
# 🔴 THE BAND WAS 400 B AND parens20 SATURATED IT (the first honest run): the
# depth is read against a 1500 B band now, and a reading of BAND is "at least".
BAND = 1500
WORK = [
    ("idle",      "A=1"),
    ("parens20",  f"A={P20}"),
    ("parens32",  f"A={P32}"),
    ("abs32",     f"A={F32}"),
    ("str16",     f"A={S16}"),
    ("transcend", "A=SIN(COS(TAN(ATN(EXP(LOG(SQR(2)))))))"),
    ("strings",   'A$=MID$(LEFT$(RIGHT$(STRING$(50,65),40),30),5,10)+CHR$(65)+HEX$(255)+STR$(1.5)'),
    ("using",     'PRINT USING "###.##";12.345'),
    ("graphics",  'SCREEN 2:CIRCLE(128,96),50,15:PAINT(128,96),8,15:DRAW"U10R10D10L10":SCREEN 0'),
    ("play",      'PLAY"CDEFGAB":FOR W=1 TO 300:NEXT'),
    ("fn3",       "DEF FNA(X)=X*2+1:A=FNA(FNA(FNA(3)))"),
    ("fn6",       "DEF FNA(X)=X*2+1:A=FNA(FNA(FNA(FNA(FNA(FNA(3))))))"),
    ("errtrap",   "ON ERROR GOTO 50:A=1/0"),
]


def prog(stmt):
    # 🔴 THE WALK IS AN INTEGER VARIABLE OVER NEGATIVE ADDRESSES. The first run
    # walked `FOR A=L TO H` with L/H near 56700 and read depths of ~65665: a FOR
    # loop is int16 arithmetic here and wrapped the addresses (D-FORFLOAT, found by
    # this very probe). C% = CSP - 65536 is the same address as a signed int16,
    # which PEEK/POKE accept, and an int16 loop over it is exact.
    return ["NEW", f"10 C=PEEK(&HE050)+256*PEEK(&HE051):C%=C-65536:L%=C%-{BAND}:H%=C%-48",
            "20 FOR A%=L% TO H%:POKE A%,&HA5:NEXT",
            f"30 {stmt}",
            "40 M%=H%+1:FOR A%=L% TO H%:IF PEEK(A%)<>&HA5 THEN IF A%<M% THEN M%=A%",
            "45 NEXT:SCREEN 0:PRINT CHR$(91);C%-M%;CHR$(93):END",
            "50 RESUME 40", "RUN"]


def main():
    got = omsx_repl.run_cases(ZB, [("direct", prog(s)) for _k, s in WORK], batch=False,
                              reset=("CLS",), boot=8.0, step=3.0, run_gap=90.0,
                              capture="screen")
    print(f"zerobas machine-stack depth below CSP (bytes; 48 = nothing reached the band, "
          f"{BAND} = AT LEAST the band):")
    for (k, s), raw in zip(WORK, got):
        m = re.findall(r"\[\s*(-?\d+)\s*\]", raw or "")
        print(f"  {k:10} {m[-1] if m else 'NO READING':>6}   {s[:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
