"""Do USR machine code's `rst $10` (CHRGTR) and `rst $18` (OUTDO) behave as on
the VG-8020? (MAKING ROOM lever A, 2026-09-25 -- the vectors are now zerobas's
own published-contract routines in basic/islands.asm.)

Each case POKEs a hand-authored stub at $D000 from BASIC, runs it through
`DEFUSR`/`USR`, and prints what it observed; the printed line is compared
between the machines. Clean room: the stubs are authored here from the Z80
opcode tables; the RST entry CONTRACTS (CHRGTR, OUTDO) are the published MSX
BIOS ones; only screen output is read. No ROM byte is read.

  OUTDO stub:   3E 58 DF 3E 59 DF C9      ld a,'X' / rst 18h / ld a,'Y' / rst 18h / ret
                -> the screen shows XY before the `]` BASIC prints.
  CHRGTR stub:  21 FF D0 D7 F5 C1 ED 43 10 D1 22 12 D1 C9
                ld hl,$D0FF / rst 10h / push af / pop bc / ld ($D110),bc /
                ld ($D112),hl / ret
                with $D100 = ' ' and $D101 = the case's byte: CHRGTR increments
                to $D100, skips the blank and stops at $D101. Printed: the
                C and Z flags (F AND &H41), A, and HL - &HD000 -- and &HD000 is
                NEGATIVE (-12288) in MSX BASIC, so HL = $D101 prints as 65793.

Measured 2026-09-25 (scratchpad/rstvec_run.out): DIFF: 0/5.
"""
import os, sys
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "probes", "lib"))
import omsx_repl

REF, ZB = "Philips_VG_8020", os.environ.get("ZEROBAS_BASIC_MACHINE", "C-BIOS_MSX1_EU_REPACK_DISK")


def pokes(addr, data):
    return ":".join(f"POKE&H{addr + i:04X},{b}" for i, b in enumerate(data))


OUTDO = [0x3E, 0x58, 0xDF, 0x3E, 0x59, 0xDF, 0xC9]
CHRGTR = [0x21, 0xFF, 0xD0, 0xD7, 0xF5, 0xC1, 0xED, 0x43, 0x10, 0xD1,
          0x22, 0x12, 0xD1, 0xC9]
SHOW = ('PRINT"[";PEEK(&HD110)AND&H41;PEEK(&HD111);'
        'PEEK(&HD112)+256*PEEK(&HD113)-&HD000;"]"')


def chrgtr_case(byte):
    return [pokes(0xD000, CHRGTR), pokes(0xD100, [32, byte]),
            "DEFUSR=&HD000:A=USR(0):" + SHOW]


CASES = [
    ("outdo",         [pokes(0xD000, OUTDO), 'DEFUSR=&HD000:A=USR(0):PRINT"]"']),
    ("chrgtr_digit",  chrgtr_case(ord("5"))),
    ("chrgtr_colon",  chrgtr_case(ord(":"))),
    ("chrgtr_eol",    chrgtr_case(0)),
    ("chrgtr_letter", chrgtr_case(ord("A"))),
]


def answer(raw):
    """The last screen row carrying `]` that is not a typed line."""
    rs = [raw[r * omsx_repl.COLS:(r + 1) * omsx_repl.COLS].strip()
          for r in range(omsx_repl.ROWS)]
    hits = [r for r in rs if "]" in r and "PRINT" not in r and "POKE" not in r]
    return hits[-1] if hits else None


def main():
    specs = [("direct", lines) for _k, lines in CASES]
    got = {}
    for m in (REF, ZB):
        got[m] = omsx_repl.run_cases(m, specs, batch=False, reset=("CLS",),
                                     boot=8.0, capture="screen")
    bad = 0
    for i, (k, _l) in enumerate(CASES):
        r, z = answer(got[REF][i] or ""), answer(got[ZB][i] or "")
        same = r is not None and r == z
        bad += not same
        print(f"{'SAME' if same else 'DIFF'} {k}")
        print(f"   ref: {r or '<NO OUTPUT>'}")
        print(f"   zb : {z or '<NO OUTPUT>'}")
    print(f"\nDIFF: {bad}/{len(CASES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
