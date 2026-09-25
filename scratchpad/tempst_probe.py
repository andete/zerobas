"""D-ADDR29 TEMPST, the premise (Joost ruled "shrink the pool to 10",
2026-09-24): at what string-expression DEPTH does each machine run out of
temporary descriptors, and what does it say when it does?

The reference's TEMPST ($F67A) holds 10 descriptors of 3 B; zerobas's TEMPPOOL
holds 32. Each case nests d levels of `MID$(A$,1)+( ... )`: every level leaves
one pending temporary while the parenthesised right-hand side is evaluated, so
the depth at which an error first appears is the pool's effective capacity.
A second shape keeps the temporaries as FUNCTION ARGUMENTS instead
(`LEFT$(MID$(...),9)` nesting), because the two may be charged differently.

Diskless pair, fresh boot per case. Clean room: typed BASIC, screen text.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
DEPTHS = list(range(6, 15))


def concat(d):
    e = "A$"
    for _ in range(d):
        e = f"MID$(A$,1)+({e})"
    return e


def nest(d):
    e = "A$"
    for _ in range(d):
        e = f"LEFT$(MID$({e},1),99)"
    return e


SHAPES = [("concat", concat), ("nest", nest)]


def case(expr):
    return f'A$="X":B$={expr}:PRINT12345;LEN(B$)'


def answer(raw):
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    hit = [r for r in rows if r.startswith("12345 ")]
    if hit:
        return "len " + hit[-1].split()[1]
    for r in reversed(rows):
        low = r.lower()
        if "complex" in low or "error" in low or "out of" in low or "illegal" in low:
            return r
    return None


def main():
    specs, keys = [], []
    for name, fn in SHAPES:
        for d in DEPTHS:
            line = case(fn(d))
            if len(line) > 250:
                continue
            specs.append(("direct", [line]))
            keys.append((name, d))
    got = {}
    for m in (REF, ZB):
        got[m] = [answer(r or "") for r in
                  omsx_repl.run_cases(m, specs, batch=False,
                                      reset=("", "SCREEN 0", "NEW"), boot=8.0,
                                      capture="screen")]
    bad = 0
    for i, (name, d) in enumerate(keys):
        r, z = got[REF][i], got[ZB][i]
        same = r is not None and r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {name:6s} depth {d:2d}   ref: {r}   zb: {z}")
    print(f"\nDIFF: {bad}/{len(keys)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
