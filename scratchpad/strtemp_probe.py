"""D-ADDR29 S2b, the premise: WHERE does zerobas's constant 12 B of extra
"used" string space come from? (scratchpad/ptrchain_str.out: 4 used on the
VG-8020 vs 16 on zerobas at boot, +5 on both for A$="HELLO".)

Hypothesis: temporaries. ptrchain's readout loop itself built MID$/HEX$/RIGHT$
temporaries; if the reference hands a released temporary's bytes back while it
is the newest thing in the string area and zerobas keeps them until a
collection, the readout alone makes the offset. So this readout builds NO
string at all -- two PEEK sums printed after a numeric fence (12345) -- and the
cases separate "a string that stays" from "a temporary that is released".

Used bytes: MEMSIZ - FRETOP on the VG-8020 ($F672, $F69B); $DB00 - FRETOP on
zerobas (its FRETOP $E268 below the ceiling -- read as the published HIMEM
$FC4A, which boots = TXTMAX; it was a hard-coded $DB00, stale since D-DETOKBUF
S3 moved TXTMAX to $E000: every row read 64256). Diskless
pair, fresh boot per case. Clean room: typed BASIC, documented cells and
zerobas's own, screen text. No ROM byte.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", "C-BIOS_MSX1_EU_REPACK_NODISK"
READ = {REF: "PRINT12345;PEEK(&HF672)+256*PEEK(&HF673)-PEEK(&HF69B)-256*PEEK(&HF69C)",
        ZB: "PRINT12345;PEEK(&HFC4A)+256*PEEK(&HFC4B)-PEEK(&HE268)-256*PEEK(&HE269)"}
CASES = [
    ("boot",       []),
    ("literal",    ['A$="HELLO"']),
    ("mid_kept",   ['A$=MID$("ABCDEF",2,3)']),
    ("concat",     ['A$="AB"+"CD"']),
    ("concat_var", ['A$="AB":B$=A$+"CD"']),
    ("temp_print", ['PRINT MID$("XYZ",2)']),
    ("temp_len",   ['X=LEN(MID$("ABCDEF",2,3))']),
    ("temp_two",   ['X=LEN(MID$("ABCDEF",2,3)+"Q")']),
]


def answer(raw):
    rows = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
            for r in range(omsx_repl.ROWS)]
    hit = [r for r in rows if r.startswith("12345 ")]
    if not hit:
        return None
    # &HDB00 is NEGATIVE in MSX BASIC (-9472): fold back to 16 bits
    return int(float(hit[-1].split()[1])) & 0xFFFF


def main():
    got = {}
    for m in (REF, ZB):
        specs = [("direct", pre + [READ[m]]) for _k, pre in CASES]
        res = omsx_repl.run_cases(m, specs, batch=False,
                                  reset=("", "SCREEN 0", "NEW"), boot=8.0,
                                  capture="screen")
        got[m] = [answer(r or "") for r in res]
    bad = 0
    print(f"{'case':11s} used: ref   zb")
    for i, (k, pre) in enumerate(CASES):
        r, z = got[REF][i], got[ZB][i]
        same = r is not None and r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k:11s} {r!s:>5} {z!s:>5}   {' / '.join(pre)}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
