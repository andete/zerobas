"""D-PAINTSP acceptance: does PAINT's span stack run out when MEMORY does?

Joost ruled (2026-09-27) that PAINT's span stack grow below SP, as the
reference's does, instead of the fixed 120-span array. The filed item's own
acceptance shape: THE SAME FILL AT TWO HIMEMs ON BOTH MACHINES.

The fill is a box with a vertical line every STEP pixels, open at the bottom, so
ONE connected region holds ~250/STEP channels -- each a span the stack must hold
at once. It runs under an `ON ERROR` handler and reports ERR (0 = completed):

    CLEAR 200[,<himem>] : SCREEN 2 : box + comb : PAINT : SCREEN 0 : [ERR]

Rows, per machine: the comb at STEP 2 (~126 channels, above the old array's
120) at the default ceiling, and the same under a low ceiling. Fresh boot per
row. Clean room: typed BASIC and the screen.
"""
import os, re, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"


def prog(step, himem):
    clr = f"CLEAR 200,{himem}" if himem else "CLEAR 200"
    return ["NEW", f"10 {clr}:ON ERROR GOTO 90:E=0",
            "20 SCREEN 2:LINE(0,0)-(255,191),15,B",
            f"30 FOR X={step} TO 255-{step} STEP {step}:LINE(X,0)-(X,180),15:NEXT",
            # 🔴 COLOUR 8, NOT 4: the default background IS colour 4, so the first
            # cut asked PAINT to fill a colour-4 seed with colour 4 -- "not
            # admissible", nothing painted, and every row "completed" vacuously
            # on both machines and on the OLD build too (the knife said so).
            "40 PAINT(1,100),8,15",
            '50 SCREEN 0:PRINT"[";E;"]":END',
            "90 E=ERR:RESUME 50", "RUN"]


def tight(left):
    # D-PAINTSP's discriminating direction: fill a SIMPLE box with only `left`
    # bytes of FRE(0) to spare (a DIM eats the rest). The old fixed array always
    # had room here; a stack that grows below SP runs out as memory does.
    return ["NEW", f"10 CLEAR 200:X=INT((FRE(0)-{left})/8):DIM A(X):ON ERROR GOTO 90:E=0",
            "20 SCREEN 2:LINE(0,0)-(255,191),15,B",
            "40 PAINT(100,100),8,15",
            '50 SCREEN 0:PRINT"[";E;FRE(0);"]":END',
            "90 E=ERR:RESUME 50", "RUN"]


# The comb rows are NON-DISCRIMINATING (measured: zerobas's PAINT holds <= 2
# spans at once on them, old build and new alike); they stay as both-machine
# agreement rows. The `tight-*` rows are the discriminator.
CASES = [("comb2-default", prog(2, None)), ("comb2-8500", prog(2, "&H8500")),
         ("comb4-default", prog(4, None)), ("comb2-8800", prog(2, "&H8800")),
         ("tight-1200", tight(1200)), ("tight-600", tight(600)),
         ("tight-300", tight(300)), ("tight-100", tight(100))]


def val(raw):
    m = re.findall(r"\[([^\]]*)\]", raw or "")
    return " ".join(m[-1].split()) if m else None


def main():
    res = {m: omsx_repl.run_cases(m, [("direct", c) for _k, c in CASES], batch=False,
                                  reset=("CLS",), boot=8.0, step=3.0, run_gap=60.0,
                                  capture="screen")
           for m in (REF, ZB)}
    print(f"{'row':16} {'VG-8020':>8} {'zerobas':>8}   (ERR; 0 = the fill completed)")
    for i, (k, _c) in enumerate(CASES):
        r, z = val(res[REF][i]), val(res[ZB][i])
        # compare the ERR only; the tight rows also print FRE(0), whose ~30 B
        # gap is the known RAM-economy difference, not PAINT's
        er = r.split()[0] if r and r[0].isdigit() else r
        ez = z.split()[0] if z and z[0].isdigit() else z
        print(f"{'SAME' if er == ez else 'DIFF'} {k:16} {str(r):>10} {str(z):>10}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
