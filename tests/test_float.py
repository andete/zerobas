# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: math float pack slice F1 -- literal crunch + PRINT formatter
(repack build only), docs/spec-basic-float-core.md.

Mirrors tests/test_mid_stmt.py's pattern: assembles basic/main-reloc.asm
(ROM_BASE=$2812; the lean 16 KB build has no float pack, gated out byte-
identical) and drives individual routines directly via the emulator-free
Z80 harness (tests/msxtest.py) -- no openMSX.

Two matrices, both mirroring the oracle capture tables in
docs/spec-basic-float-core.md §9 (basic_probe_floatlit.py /
basic_probe_float_fmt.py, VG-8020, 2026-07-11; the live probes are the
oracle GATE, this is the fast regression layer under it):

  - encode: `tk_float` on a bare literal -> the exact crunched token bytes
    (int forms unchanged, $1D single / $1F double + BCD mantissa), incl. the
    classification walls (int/single/double, %/!/#/D-exponent forcing),
    half-up rounding, and the single-vs-double carry-out quirk (rule 6).
  - format: `flt_out` on a hand-built FAC/FACTYP -> the printed string
    (sign + digits + trailing space; fixed vs E form; trailing-zero
    stripping). FAC bytes for each case are the SAME bytes the encode
    matrix proves `tk_float` produces for the equivalent literal, so the
    two matrices cross-check each other.

Also spot-checks `flt_to_int16` (D-F1-2, half-up + out-of-range -> 0; not
independently oracle-gated -- reasoned from the stated contract and hand-
verified against the encode matrix's own FAC bytes) and `flt_neg`/
`flt_guard`.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = "/tmp/zb_float.rom"
SYM = "/tmp/zb_float.sym"
RELOC_BASE = 0x2812

SRC = 0xC000       # ASCII literal source
TOKBUF = 0xC100    # crunch destination


def build():
    src = os.path.join(ROOT, "basic", "main-reloc.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True, capture_output=True)


# --- encode matrix: literal -> exact crunched bytes (hex, spaces ignored) --
# Oracle-pinned (basic_probe_floatlit.py, VG-8020 KBUF captures, spec §9.2).
ENCODE_CASES = [
    # int forms unchanged (regression anchors)
    ("0",           "11"),
    ("9",           "1A"),
    ("10",          "0F 0A"),
    ("255",         "0F FF"),
    ("256",         "1C 00 01"),
    ("32767",       "1C FF 7F"),
    # decimal >= 32768: the int16 wall -> single
    ("32768",       "1D 45 32 76 80"),
    ("65535",       "1D 45 65 53 50"),
    # digit-count wall (single holds 6 BCD digits; D>=7 -> double)
    ("999999",      "1D 46 99 99 99"),
    ("1000000",     "1F 47 10 00 00 00 00 00 00"),
    ("9999999",     "1F 47 99 99 99 90 00 00 00"),
    # decimal point forms
    (".5",          "1D 40 50 00 00"),
    ("0.5",         "1D 40 50 00 00"),
    ("1.5",         "1D 41 15 00 00"),
    ("1.",          "1D 41 10 00 00"),
    ("3.14159",     "1D 41 31 41 59"),
    ("3.1415926",   "1F 41 31 41 59 26 00 00 00"),
    (".000001",     "1D 3B 10 00 00"),
    ("1234567",     "1F 47 12 34 56 70 00 00 00"),
    # E/D exponent forms
    ("1e5",         "1D 46 10 00 00"),
    ("1e10",        "1D 4B 10 00 00"),
    ("1e-3",        "1D 3E 10 00 00"),
    ("1d5",         "1F 46 10 00 00 00 00 00 00"),
    # exponent range walls (excess-64: +-63)
    ("1e62",        "1D 7F 10 00 00"),
    ("1e-63",       "1D 02 10 00 00"),
    ("1e-64",       "1D 01 10 00 00"),
    ("1e-65",       "1D 00 10 00 00"),      # underflow: lead 0, mantissa retained
    # explicit type suffixes
    ("1!",          "1D 41 10 00 00"),
    ("1#",          "1F 41 10 00 00 00 00 00 00"),
    ("32767#",      "1F 45 32 76 70 00 00 00 00"),
    # rounding half-up, no carry-out
    ("1234567!",    "1D 47 12 34 57"),
    ("1234565!",    "1D 47 12 34 57"),
    ("1234575!",    "1D 47 12 34 58"),
    # rounding carry-out-of-all-digits: single does NOT renormalise,
    # double DOES (dec_exp += 1) -- the oracle-pinned quirk (rule 6)
    ("9999995!",    "1D 47 10 00 00"),                    # single: stays dec_exp=7 -> 1000000
    ("9999999999999999", "1F 51 10 00 00 00 00 00 00"),   # double: dec_exp 16->17
    # zero forms
    ("0!",          "1D 00 00 00 00"),
    ("0#",          "1F 00 00 00 00 00 00 00 00"),
    (".0",          "1D 00 00 00 00"),
    # %-suffix (consumed, no extra byte; same int forms)
    ("1%",          "12"),
    ("100%",        "0F 64"),
    ("30000%",      "1C 30 75"),
]

# Crunch-time overflow (§9.2 rule 7): the literal is rejected, TKOVF set,
# nothing emitted for it.
OVERFLOW_CASES = ["1e63", "65535%"]

# --- format matrix: (FAC hex, FACTYP) -> printed string --------------------
# FAC bytes reused from the encode matrix above (lead + mantissa, i.e. the
# crunched value bytes with the leading $1D/$1F TOKEN stripped); FACTYP
# 4=single/8=double. Expected strings oracle-pinned (basic_probe_float_fmt.py,
# spec §9.3).
FORMAT_CASES = [
    ("41 15 00 00", 4, " 1.5 "),                              # 1.5
    ("C1 15 00 00", 4, "-1.5 "),                               # -1.5 (sign bit set)
    ("40 50 00 00", 4, " .5 "),                                 # .5
    ("41 10 00 00", 4, " 1 "),                                   # 1.0 -> integer-valued
    ("47 12 34 57", 4, " 1234570 "),                               # 1234567! (rounded, padded)
    ("47 10 00 00", 4, " 1000000 "),                               # 9999995! (carry quirk)
    ("3E 10 00 00", 4, " 1E-03 "),                                  # .001
    ("58 60 23 00", 4, " 6.023E+23 "),                               # 6.023e23
    ("00 00 00 00", 4, " 0 "),                                        # 0!
    ("41 12 34 56 78 90 00 00", 8, " 1.23456789 "),                    # 1.23456789#
    ("51 10 00 00 00 00 00 00", 8, " 1E+16 "),                          # 1d16 / carry-out double
    ("52 12 34 56 78 90 12 35", 8, " 1.2345678901235E+17 "),             # 123456789012345678
]


def hx(s):
    return bytes.fromhex(s)


def run():
    build()
    m = Machine(ROM, SYM, rom_base=RELOC_BASE)
    s = m.sym
    FAC = s["FAC"]
    FACTYP = s["FACTYP"]
    TKOVF = s["TKOVF"]

    fails = 0

    def ck(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}: got {got!r} want {want!r}")

    print("# --- encode matrix: tk_float(literal) -> crunched bytes ---")
    # Every source is `<literal>;\0`, not just the bare literal, and the
    # expected crunch is `want + ";\\x00"`: tk_float's own paths all end in
    # `jp tk_loop` (a tail jump, not `ret`), so the harness's "run to return"
    # call keeps going -- tk_loop copies the ';' verbatim and tk_end (a real
    # `ret`) supplies the terminator. This also catches the regression that
    # bit tk_float three times during development: HL is the LIVE source
    # cursor tk_loop needs back, but tkf_int_value / tkf_calc_and_round /
    # tkf_emit_mantissa / tke_ddone's exponent-sign negation all used HL as
    # scratch at some point without saving it first -- corrupting the
    # cursor let tk_loop read garbage "source" bytes after the value, which
    # a bare-literal-only byte check (nothing follows) would never expose.
    for lit, want_hex in ENCODE_CASES:
        want = hx(want_hex) + b";\x00"
        m.poke(SRC, lit.encode("ascii") + b";\x00")
        m.mem[TOKBUF:TOKBUF + 32] = b"\xAA" * 32
        m.call("tk_float", hl=SRC, de=TOKBUF)
        got = m.peek(TOKBUF, len(want))
        ck(f"tk_float({lit!r})", got, want)

    print("# --- crunch-time overflow: TKOVF set, whole literal rejected ---")
    for lit in OVERFLOW_CASES:
        m.mem[TOKBUF:TOKBUF + 32] = b"\xAA" * 32
        m.poke(SRC, lit.encode("ascii") + b"\x00")
        m.poke(TKOVF, 0)
        m.call("tk_float", hl=SRC, de=TOKBUF)
        ck(f"tk_float({lit!r}) sets TKOVF", m.peek(TKOVF)[0], 1)

    print("# --- format matrix: flt_out(FAC,FACTYP) -> printed string ---")
    for fac_hex, factyp, want in FORMAT_CASES:
        facbytes = hx(fac_hex)
        m.poke(FAC, facbytes + b"\x00" * (8 - len(facbytes)))
        m.poke(FACTYP, factyp)
        out = m.capture_chput()
        m.call("flt_out")
        got = "".join(chr(b) for b in out)
        ck(f"flt_out(FAC={fac_hex},FACTYP={factyp})", got, want)

    print("# --- flt_to_int16: half-up, 16-bit address domain (D-F1-2) ---")
    # Range is -32768..65535 (positive -> unsigned bit pattern), matching the
    # published POKE/HEX$ argument domain and the pre-F1 unsigned $1C cruncher
    # (see flt_to_int16's header). Wants are given as ordinary ints and
    # compared as raw 16-bit patterns (want & 0xFFFF), so +32768 and -32768
    # both mean $8000.
    FTI_CASES = [
        ("41 15 00 00", 4, 2),                    # 1.5 -> 2 (half-up)
        ("41 24 00 00", 4, 2),                     # 2.4 -> 2
        ("41 25 00 00", 4, 3),                      # 2.5 -> 3 (half-up)
        ("C1 25 00 00", 4, -3),                      # -2.5 -> -3
        ("49 00 00 00 00 00 00 00", 8, 0),            # dec_exp=9, N>=6 -> out of range -> 0
        ("45 32 76 74", 4, 32767),                     # 32767.4 -> 32767 (no round)
        ("45 32 76 76", 4, 32768),                      # 32767.6 -> 32768 (in domain now)
        ("45 40 00 00", 4, 40000),                       # POKE-address regression anchor
        ("45 65 53 50", 4, 65535),                        # unsigned ceiling
        ("45 65 53 55", 4, 0),                             # 65535.5 -> wraps -> 0
        ("45 99 99 99", 4, 0),                              # 99999 > 65535 -> 0
        ("C5 32 76 80", 4, -32768),                          # negative floor
        ("C5 32 76 85", 4, 0),                                # -32768.5 -> past floor -> 0
        ("C5 32 76 90", 4, 0),                                 # -32769 -> 0
        ("00 00 00 00", 4, 0),                                  # 0
    ]
    for fac_hex, factyp, want in FTI_CASES:
        facbytes = hx(fac_hex)
        m.poke(FAC, facbytes + b"\x00" * (8 - len(facbytes)))
        m.poke(FACTYP, factyp)
        cpu = m.call("flt_to_int16")
        ck(f"flt_to_int16(FAC={fac_hex},FACTYP={factyp})", cpu.de, want & 0xFFFF)

    print("# --- flt_neg / flt_guard ---")
    m.poke(FAC, hx("41150000"))
    m.call("flt_neg")
    ck("flt_neg flips the sign bit", m.peek(FAC)[0], 0xC1)
    m.call("flt_neg")
    ck("flt_neg is its own inverse", m.peek(FAC)[0], 0x41)
    m.poke(FAC, hx("00000000"))
    m.call("flt_neg")
    ck("flt_neg exempts the value-0 lead byte", m.peek(FAC)[0], 0x00)

    ERRMARK = s["ERRMARK"]
    m.poke(FACTYP, 4)
    m.poke(ERRMARK, 0)
    m.call("flt_guard")
    ck("flt_guard: FACTYP<>2 sets ERRMARK", m.peek(ERRMARK)[0], 0xDD)
    ck("flt_guard: FACTYP<>2 resets FACTYP to 2", m.peek(FACTYP)[0], 2)
    m.poke(FACTYP, 2)
    m.poke(ERRMARK, 0)
    m.call("flt_guard")
    ck("flt_guard: FACTYP==2 is a no-op", m.peek(ERRMARK)[0], 0)

    print("# --- FACTYP leak through function factors (F1 review live-catch) ---")
    # `PRINT PEEK(40000.)` printed 40000 (the sticky FAC) instead of the
    # peeked byte: a float ARGUMENT left FACTYP=4, so exp_num dispatched the
    # function's int result to the float formatter. Every int-returning
    # function tail now calls flt_int_result (basic/float.asm). Token
    # stream: PEEK = $FF $97 (sysvars PEEK_PREFIX/PEEK_TOKEN), then
    # '(' <$1D 45 40 00 00 = single 40000> ')'.
    m.poke(SRC, bytes([0xFF, 0x97, ord("(")]) + hx("1D 45 40 00 00") + b")\x00")
    m.poke(40000, 123)                       # the byte PEEK(40000.) must find
    cpu = m.call("eval", hl=SRC)
    ck("PEEK(float 40000) returns the peeked byte", cpu.de, 123)
    ck("...and resets FACTYP to int", m.peek(FACTYP)[0], 2)
    # parens must NOT reset: `PRINT (1.5)` stays a float item
    m.poke(SRC, b"(" + hx("1D 41 15 00 00") + b")\x00")
    cpu = m.call("eval", hl=SRC)
    ck("(1.5) keeps FACTYP=4 (parens preserve floatness)", m.peek(FACTYP)[0], 4)
    ck("(1.5) still yields the rounded int in DE", cpu.de, 2)

    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(run())
