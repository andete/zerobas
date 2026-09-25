"""D-ADDR29 RNDX, the premise (Joost ruled "RNDX now", 2026-09-24): is
zerobas's 7-byte RND_SEED ($F142, packed BCD, MSD first) the reference's
8-byte RNDX ($F857) at some offset -- so the move is an equate plus one byte --
or a different format?

Each case runs on a fresh boot, captures the bytes into variables on the
operation's own line (the readout's own work cannot move them), then prints
them in hex. Diskless pair. Clean room: typed BASIC, a documented cell and
zerobas's own, screen text. No ROM byte.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
# --after (RNDX moved): read zerobas's PUBLISHED 8 bytes too, and compare whole
AFTER = "--after" in sys.argv
BASE = {REF: 0xF857, ZB: 0xF857 if AFTER else 0xF142}
N = {REF: 8, ZB: 8 if AFTER else 7}
CASES = [
    ("boot",   ""),
    ("rnd1",   "X=RND(1)"),
    ("rnd1x2", "X=RND(1):X=RND(1)"),
    ("rnd0",   "X=RND(1):X=RND(0)"),
    ("rndm1",  "X=RND(-1)"),
    ("rndm5",  "X=RND(-5)"),
    ("rndm5n", "X=RND(-5):X=RND(1)"),
]


def line(m, op):
    # an array and two loops keep the typed line under the 254-char buffer;
    # every byte is captured before any of it is printed
    grab = f"FORI=0TO{N[m] - 1}:B(I)=PEEK(&H{BASE[m]:04X}+I):NEXT"
    show = (f'PRINT:PRINT12345;:FORI=0TO{N[m] - 1}:'
            f'PRINTRIGHT$("0"+HEX$(B(I)),2);:NEXT')
    return (op + ":" if op else "") + grab + ":" + show


def answer(raw):
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    hit = [r for r in rows if r.startswith("12345 ")]
    return hit[-1][6:].replace(" ", "") if hit else None


def main():
    got = {}
    for m in (REF, ZB):
        specs = [("direct", [line(m, op)]) for _k, op in CASES]
        res = omsx_repl.run_cases(m, specs, batch=False,
                                  reset=("", "SCREEN 0", "NEW"), boot=8.0,
                                  capture="screen")
        got[m] = [answer(r or "") for r in res]
    print(f"{'case':7s}  VG-8020 RNDX (8 B)   zerobas RND_SEED (7 B)")
    for i, (k, op) in enumerate(CASES):
        r, z = got[REF][i], got[ZB][i]
        rel = ""
        if r and z:
            if r == z:
                rel = "SAME (all 8 bytes)"
            elif r[2:] == z:
                rel = "zb == ref[1:]"
            elif r[:14] == z:
                rel = "zb == ref[:7]"
        print(f"{k:7s}  {r or '<NO OUTPUT>':18s}  {z or '<NO OUTPUT>':16s}  {rel}   {op}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
