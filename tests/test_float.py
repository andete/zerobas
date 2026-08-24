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
from _tmp import tp
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402

ROM = tp("zb_float.rom")
SYM = tp("zb_float.sym")
RELOC_BASE = 0x2812

# The float PRINT formatter (flt_out) was evicted to the sub-ROM (subrom S2b):
# it now lives in build/sub.rom's page 0 and ends in `ret` (writing FOUTBUF in
# RAM) rather than tail-calling print_string. The format matrix therefore runs
# against a second Machine loaded from sub.rom and reads FOUTBUF directly.
SUB_ROM = tp("zb_sub.rom")
SUB_SYM = tp("zb_sub.sym")

SRC = 0xC000       # ASCII literal source
TOKBUF = 0xC100    # crunch destination


def build():
    src = os.path.join(ROOT, "basic", "main.asm")
    subprocess.run(["pasmo", "--bin", src, ROM, SYM], check=True, capture_output=True)
    # sub.rom (formatter tenant); -I sub for its includes, cwd=ROOT for basic/sysvars.inc
    subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", SUB_ROM, SUB_SYM],
                   check=True, capture_output=True, cwd=ROOT)


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
# ⚠️ TKOVF IS 6, NOT 1, SINCE 2026-08-02 (D-MSGMIGRATE) -- and this expectation
# was STALE, not broken. TKOVF's contract is "0 = ok, else the ERR CODE of the
# crunch-time reject" (basic/tokenise.inc tke_fits already stored 25 for the
# body-too-long arm). The float arm stored a bare flag 1, which forced
# dl_overflow to special-case it, and that special case SKIPPED the ERRFLG store
# -- so `PRINT ERR` after `20 A=1E99` read a stale code. Both references read 6
# there (measured, boot-per-case, 2026-08-02). Making the two arms symmetric
# fixed the defect AND deleted dl_overflow's branch.
TKOVF_FLOAT_REJECT = 6          # = ERR 6, `Overflow`
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


# =============================================================================
# F2 additions: arithmetic + relationals + signed-int migration
# (docs/spec-basic-float-core.md §10). Drives float-arith.asm's routines
# directly (fp_add/fp_sub/fp_mul/fp_div, fac_to_int_strict/fac_to_int_addr,
# signed_div_de_bc/signed_mod_de_bc, fp_cmp) plus a handful of eval()
# integration cases for int-overflow promotion. Mirrors every §10.2/§10.3/
# §10.4 pin cited in the spec; this is the fast regression layer under the
# oracle gate (make float-acceptance ARITH half), not a replacement for it.
# =============================================================================

import decimal
decimal.getcontext().prec = 40
D = decimal.Decimal


def poke_fpnum(m, base, value):
    """Write an FPNUM record (sign:1, dexp:2, dig:15) at `base` representing
    the exact decimal `value` (a Decimal or int; 0 -> canonical zero)."""
    value = D(value)
    if value == 0:
        m.poke(base, bytes(18))
        return
    sign = 0x80 if value < 0 else 0x00
    mag = -value if value < 0 else value
    digits, exp = mag.as_tuple().digits, mag.as_tuple().exponent
    # digits is the significant-digit tuple MSD-first; the value's dec_exp
    # (0.d1d2...*10^dec_exp convention) = (len(digits) + exp).
    dec_exp = len(digits) + exp
    dig14 = (list(digits) + [0] * 14)[:14]
    m.poke(base, bytes([sign]))
    m.poke_w(base + 1, dec_exp & 0xFFFF)
    m.poke(base + 3, bytes(dig14 + [0]))  # 14 sig + 1 guard(always 0 on load)


def decode_fac(m, s):
    """Read FAC/FACTYP -> exact Decimal value (0 for the canonical-zero lead
    byte)."""
    FAC = s["FAC"]
    lead = m.peek(FAC)[0]
    if lead == 0:
        return D(0)
    factyp = m.peek(s["FACTYP"])[0]
    nbytes = 7 if factyp == 8 else 3
    mant = m.peek(FAC + 1, nbytes)
    digits = []
    for b in mant:
        digits.append(b >> 4)
        digits.append(b & 0xF)
    sign = -1 if (lead & 0x80) else 1
    dec_exp = (lead & 0x7F) - 64
    mantissa_int = int("".join(str(d) for d in digits)) if digits else 0
    return sign * D(mantissa_int) * (D(10) ** (dec_exp - len(digits)))


def enc_int(n):
    """Encode a 0..32767 int as its crunched token bytes (no unary minus;
    interp.asm tk_number's own shapes)."""
    assert 0 <= n <= 32767
    if n <= 9:
        return bytes([0x11 + n])
    if n <= 255:
        return bytes([0x0F, n])
    return bytes([0x1C, n & 0xFF, (n >> 8) & 0xFF])


def run_f2(m, s, ck):
    fails = 0

    def ckf(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}: got {got!r} want {want!r}")

    ARGA = s["ARGA"]
    ARGB = s["ARGB"]
    FACTYP = s["FACTYP"]
    FPERR = s["FPERR"]

    def do_op(routine, a, b):
        """poke ARGA<-a, ARGB<-b, call the BCD op, return (decoded FAC value
        or None if FPERR set, FPERR byte)."""
        poke_fpnum(m, ARGA, a)
        poke_fpnum(m, ARGB, b)
        m.poke(FPERR, 0)
        m.call(routine)
        err = m.peek(FPERR)[0]
        if err:
            return None, err
        return decode_fac(m, s), err

    print("# --- F2: fp_add / fp_sub (spec §10.2) ---")
    ADD_CASES = [
        ("fp_add", D("1"), D("5E-14"), D("1.0000000000001")),   # tie up
        ("fp_add", D("1"), D("4E-14"), D("1")),                  # no round
        ("fp_add", D("1"), D("-1E-15"), D("1")),                  # carry thru 14 nines
        ("fp_add", D("99999999999999"), D("1"), D("1E+14")),       # mantissa carry
        ("fp_add", D("1E+62"), D("0"), D("1E+62")),
        ("fp_add", D("123456"), D("0.5"), D("123456.5")),           # single+single->double exact
        ("fp_add", D("1000000"), D("1"), D("1000001")),
        ("fp_sub", D("2.00001"), D("1.000005"), D("1.000005")),
        ("fp_sub", D("0"), D("0"), D("0")),
    ]
    for routine, a, b, want in ADD_CASES:
        got, err = do_op(routine, a, b)
        ckf(f"{routine}({a},{b})", got, want)
        ckf(f"{routine}({a},{b}) FPERR", err, 0)

    print("# --- F2: fp_add/fp_sub overflow (spec §10.2) ---")
    got, err = do_op("fp_add", D("9E+62"), D("9E+62"))
    ckf("fp_add(9e62,9e62) FPERR=overflow", err, 1)

    print("# --- F2: fp_mul (spec §10.2) ---")
    MUL_CASES = [
        (D("3125"), D("625"), D("1953125")),
        (D("123456"), D("654321"), D("80779853376")),
        (D("9E+61"), D("9"), D("8.1E+62")),                       # 62+1=63 passes
        (D("1E-32"), D("1E-32"), D("1E-64")),                       # underflow boundary
        (D("2.5"), D("1.0000000000001"), D("2.5000000000003")),      # mul tie up
    ]
    for a, b, want in MUL_CASES:
        got, err = do_op("fp_mul", a, b)
        ckf(f"fp_mul({a},{b})", got, want)
        ckf(f"fp_mul({a},{b}) FPERR", err, 0)
    got, err = do_op("fp_mul", D("2E+62"), D("4"))
    ckf("fp_mul(2e62,4) FPERR=overflow (63+1=64, pre-check)", err, 1)
    got, err = do_op("fp_mul", D("1E-33"), D("1E-32"))
    ckf("fp_mul(1e-33,1e-32) -> 0 (underflow, silent)", got, D(0))
    ckf("fp_mul(1e-33,1e-32) FPERR", err, 0)

    print("# --- F2: fp_div (spec §10.2) ---")
    DIV_CASES = [
        (D("1"), D("3"), D("0.33333333333333")),
        (D("2"), D("3"), D("0.66666666666667")),
        (D("-2"), D("3"), D("-0.66666666666667")),                  # magnitude rounding
        (D("1.0000000000003"), D("4"), D("0.25000000000008")),        # div tie up
        (D("1"), D("512"), D("0.001953125")),
    ]
    for a, b, want in DIV_CASES:
        got, err = do_op("fp_div", a, b)
        ckf(f"fp_div({a},{b})", got, want)
        ckf(f"fp_div({a},{b}) FPERR", err, 0)
    got, err = do_op("fp_div", D("2E+62"), D("0.4"))
    ckf("fp_div(2e62,.4) FPERR=overflow (63-0+1=64, pre-check)", err, 1)
    got, err = do_op("fp_div", D("1"), D("0"))
    ckf("fp_div(1,0) FPERR=division by zero", err, 2)
    got, err = do_op("fp_div", D("1E-40"), D("1E+30"))
    ckf("fp_div(1e-40,1e30) -> 0 (underflow, silent)", got, D(0))
    ckf("fp_div(1e-40,1e30) FPERR", err, 0)

    print("# --- F2: fp_cmp (spec §10.1) ---")
    CMP_CASES = [
        (D("1.5"), D("1.5"), 2), (D("1.5"), D("1.4"), 4), (D("1.4"), D("1.5"), 1),
        (D("-1.5"), D("-1"), 1), (D("2"), D("1.5"), 4), (D("0"), D("0"), 2),
        (D("0"), D("1"), 1), (D("1"), D("0"), 4), (D("0"), D("-1"), 4),
        (D("-1"), D("0"), 1), (D("40000"), D("40000"), 2),
        (D(".1"), D(".1"), 2),
    ]
    for a, b, want in CMP_CASES:
        poke_fpnum(m, ARGA, a)
        poke_fpnum(m, ARGB, b)
        cpu = m.call("fp_cmp")
        ckf(f"fp_cmp({a},{b})", cpu.a, want)

    print("# --- F2: fac_to_int_strict (spec §10.3, strict int16 domain) ---")
    STRICT_CASES = [
        (D("2.9"), 2), (D("-2.9"), -2), (D("32767.5"), 32767),
        (D("-32768.5"), -32768), (D("40000"), None),   # overflow
        (D("-32769"), None),                             # overflow (excluded bound)
    ]
    for value, want in STRICT_CASES:
        _poke_fac_from_decimal(m, s, value)
        m.poke(FPERR, 0)
        cpu = m.call("fac_to_int_strict")
        err = m.peek(FPERR)[0]
        if want is None:
            ckf(f"fac_to_int_strict({value}) overflow", err, 1)
        else:
            ckf(f"fac_to_int_strict({value})", cpu.de & 0xFFFF, want & 0xFFFF)
            ckf(f"fac_to_int_strict({value}) FPERR", err, 0)

    print("# --- F2: fac_to_int_addr (spec §10.3, address domain + wrap) ---")
    ADDR_CASES = [
        (D("2.9"), 2), (D("-2.5"), -2), (D("32767.5"), 32767),
        (D("40000.1"), 0x9C41), (D("40000.5"), 0x9C41), (D("65535.5"), 0),
        (D("65536"), None), (D("-32768.9"), -32768 & 0xFFFF),
        (D("100000"), None), (D("40000"), 40000),
    ]
    for value, want in ADDR_CASES:
        _poke_fac_from_decimal(m, s, value)
        m.poke(FPERR, 0)
        cpu = m.call("fac_to_int_addr")
        err = m.peek(FPERR)[0]
        if want is None:
            ckf(f"fac_to_int_addr({value}) overflow", err, 1)
        else:
            ckf(f"fac_to_int_addr({value})", cpu.de & 0xFFFF, want & 0xFFFF)
            ckf(f"fac_to_int_addr({value}) FPERR", err, 0)

    print("# --- F2: signed \\ and MOD (spec §10.4, D-C migration) ---")
    SDIV_CASES = [
        (7, 2, 3), (-7, 2, -3), (7, -2, -3), (-7, -2, 3), (32767, -1, -32767),
    ]
    for a, b, want in SDIV_CASES:
        m.poke(FPERR, 0)
        cpu = m.call("signed_div_de_bc", de=a & 0xFFFF, bc=b & 0xFFFF)
        ckf(f"signed_div_de_bc({a}\\{b})", to_signed(cpu.de), want)
        ckf(f"signed_div_de_bc({a}\\{b}) FPERR", m.peek(FPERR)[0], 0)
    SMOD_CASES = [
        (7, 2, 1), (-7, 2, -1), (7, -2, 1), (-7, -2, -1),
    ]
    for a, b, want in SMOD_CASES:
        m.poke(FPERR, 0)
        cpu = m.call("signed_mod_de_bc", de=a & 0xFFFF, bc=b & 0xFFFF)
        ckf(f"signed_mod_de_bc({a} mod {b})", to_signed(cpu.de), want)
        ckf(f"signed_mod_de_bc({a} mod {b}) FPERR", m.peek(FPERR)[0], 0)
    # div-by-zero
    m.poke(FPERR, 0)
    cpu = m.call("signed_div_de_bc", de=1, bc=0)
    ckf("signed_div_de_bc(1\\0) FPERR=division by zero", m.peek(FPERR)[0], 2)
    ckf("signed_div_de_bc(1\\0) DE", cpu.de, 0)
    m.poke(FPERR, 0)
    cpu = m.call("signed_mod_de_bc", de=1, bc=0)
    ckf("signed_mod_de_bc(1 mod 0) FPERR=division by zero", m.peek(FPERR)[0], 2)
    # the -32768\-1 escape quirk: true magnitude 32768 doesn't fit int16 ->
    # promoted to double (FAC=32768.0, FACTYP=8), DE = silent flt_to_int16
    m.poke(FPERR, 0)
    cpu = m.call("signed_div_de_bc", de=(-32768) & 0xFFFF, bc=(-1) & 0xFFFF)
    ckf("signed_div_de_bc(-32768\\-1) FPERR (no error, quirk)", m.peek(FPERR)[0], 0)
    ckf("signed_div_de_bc(-32768\\-1) promotes to double", m.peek(FACTYP)[0], 8)
    ckf("signed_div_de_bc(-32768\\-1) FAC value", decode_fac(m, s), D(32768))

    print("# --- F2: int-overflow promotion (eval() integration, spec §10.2) ---")
    PROMOTE_CASES = [
        (enc_int(32767) + bytes([0xF1]) + enc_int(1), D(32768)),        # 32767+1
        (enc_int(32000) + bytes([0xF1]) + enc_int(32000), D(64000)),     # 32000+32000
        (enc_int(32767) + bytes([0xF3]) + enc_int(2), D(65534)),          # 32767*2
        (enc_int(300) + bytes([0xF3]) + enc_int(300), D(90000)),           # 300*300
    ]
    SRC2 = 0xC200
    for tokens, want in PROMOTE_CASES:
        m.poke(SRC2, tokens + b"\x00")
        m.poke(FACTYP, 2)
        cpu = m.call("eval", hl=SRC2)
        ckf(f"eval(overflow case) FACTYP", m.peek(FACTYP)[0], 8)
        ckf(f"eval(overflow case) value", decode_fac(m, s), want)

    # --- F2 review: float relationals must PRESERVE ev_rel's requested ------
    # relation bits in C across the widen/fp_cmp core (combine_cmp pushes BC
    # on its float path). Caught by the full differential gate: with C
    # trashed to a value holding the =/> bits, every float `=`/`>` compare
    # passed by luck and every `<`/`<>`/`<=` answered wrong (spec §10.1).
    print("# --- F2: float relational requested-bits preservation (eval) ---")
    SNG15 = bytes.fromhex("1D41150000")   # 1.5  (ENCODE_CASES above)
    SNG14 = bytes.fromhex("1D41140000")   # 1.4
    REL_CASES = [
        ("1.5<1.4",  SNG15 + b"\xF0" + SNG14, 0),
        ("1.5>1.4",  SNG15 + b"\xEE" + SNG14, -1),
        ("1.5=1.5",  SNG15 + b"\xEF" + SNG15, -1),
        ("1.5<>1.5", SNG15 + b"\xF0\xEE" + SNG15, 0),
        ("1.5<=1.4", SNG15 + b"\xF0\xEF" + SNG14, 0),
        ("-1.5<-1",  b"\xF2" + SNG15 + b"\xF0\xF2\x12", -1),
    ]
    for name, tokens, want in REL_CASES:
        m.poke(SRC2, tokens + b"\x00")
        m.poke(FACTYP, 2)
        m.poke(FPERR, 0)
        cpu = m.call("eval", hl=SRC2)
        ckf(f"eval({name}) FACTYP int", m.peek(FACTYP)[0], 2)
        ckf(f"eval({name})", to_signed(cpu.de), want)

    return fails


def to_signed(v):
    v &= 0xFFFF
    return v - 0x10000 if v >= 0x8000 else v


def _poke_fac_from_decimal(m, s, value):
    """Populate FAC/FACTYP (double) directly from a Decimal, for converter
    tests that read FAC/FACTYP rather than ARGA/ARGB."""
    ARGA = s["ARGA"]
    poke_fpnum(m, ARGA, value)
    # ARGA is [sign:1][dexp:2][dig:15]; FAC/FACTYP want the packed format,
    # so route through fp_add(ARGA,0) to get a clean packed FAC via the
    # already-verified pack path (round_and_finalize).
    poke_fpnum(m, s["ARGB"], D(0))
    m.poke(s["FPERR"], 0)
    m.call("fp_add")


def run():
    build()
    m = Machine(ROM, SYM, rom_base=RELOC_BASE)
    s = m.sym
    FAC = s["FAC"]
    FACTYP = s["FACTYP"]
    TKOVF = s["TKOVF"]

    # Second machine for the evicted literal CRUNCH (sub.rom, page-0 tenant,
    # subrom S2b). Same RAM cell addresses (shared sysvars.inc), so SRC/TOKBUF/
    # TKOVF poke/peek align. The formatter (flt_out) stays RESIDENT in main-reloc.
    ms = Machine(SUB_ROM, SUB_SYM, rom_base=0x0000)

    fails = 0

    def ck(label, got, want):
        nonlocal fails
        ok = got == want
        fails += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {label}: got {got!r} want {want!r}")

    print("# --- encode matrix: tokenise(literal;) -> crunched bytes (sub-ROM crunch) ---")
    # WAVE 2: the WHOLE tokeniser is the sub-ROM tenant now, and tk_float is an
    # internal `jp tk_loop`/`jp tk_end` callee again (the wave-1 disposition-return
    # protocol was reverted, spec §5), so we drive the whole body by calling
    # `tokenise` directly in the sub machine. A bare literal line "<lit>;" crunches
    # to [value bytes][';' verbatim][00]: check the value bytes AND that the byte
    # right after them is ';' ($3B) -- the latter proves the loop resumed at the
    # correct source position after the literal (the same cursor-integrity
    # regression the old post-tk_float HL check caught: tkf_int_value/
    # tkf_calc_and_round/tkf_emit_mantissa/tke_ddone using HL as scratch).
    for lit, want_hex in ENCODE_CASES:
        want = hx(want_hex)
        ms.poke(SRC, lit.encode("ascii") + b";\x00")
        ms.mem[TOKBUF:TOKBUF + 32] = b"\xAA" * 32
        ms.call("tokenise", hl=SRC, de=TOKBUF)
        ck(f"tokenise({lit!r};) bytes", ms.peek(TOKBUF, len(want)), want)
        ck(f"tokenise({lit!r};) resume", ms.peek(TOKBUF + len(want), 2), b";\x00")

    print("# --- crunch-time overflow: TKOVF set, line rejected ---")
    for lit in OVERFLOW_CASES:
        ms.mem[TOKBUF:TOKBUF + 32] = b"\xAA" * 32
        ms.poke(SRC, lit.encode("ascii") + b"\x00")
        ms.poke(TKOVF, 0)
        ms.call("tokenise", hl=SRC, de=TOKBUF)
        ck(f"tokenise({lit!r}) sets TKOVF", ms.peek(TKOVF)[0],
           TKOVF_FLOAT_REJECT)

    print("# --- format matrix: flt_out(FAC,FACTYP) -> printed string (resident) ---")
    # flt_out stays RESIDENT in the main ROM (runtime-hot PRINT path, not evicted),
    # ending in print_string -> CHPUT; capture what it emits.
    for fac_hex, factyp, want in FORMAT_CASES:
        facbytes = hx(fac_hex)
        m.poke(FAC, facbytes + b"\x00" * (8 - len(facbytes)))
        m.poke(FACTYP, factyp)
        out = m.capture_chput()
        m.call("flt_out")
        got = "".join(chr(b) for b in out)
        ck(f"flt_out(FAC={fac_hex},FACTYP={factyp})", got, want)

    print("# --- flt_to_int16: TRUNCATING, address domain (spec §10.3, F2) ---")
    # F2 correction (spec §10.3): the reference TRUNCATES toward zero (not F1's
    # reasoned-not-pinned half-up); a value >=32768 wraps by -65536 first, any
    # fractional remainder then rounds the wrapped magnitude UP by one. Range
    # is -32769<x<65536; out of domain -> silent 0 (this converter has no
    # error flag -- flt_to_int16 runs eagerly on every float factor). Wants
    # are ordinary ints, compared as raw 16-bit patterns (want & 0xFFFF).
    FTI_CASES = [
        ("41 15 00 00", 4, 1),                    # 1.5 -> 1 (truncate)
        ("41 24 00 00", 4, 2),                     # 2.4 -> 2
        ("41 25 00 00", 4, 2),                      # 2.5 -> 2 (truncate, not half-up)
        ("C1 25 00 00", 4, -2),                      # -2.5 -> -2 (truncate toward 0)
        ("49 00 00 00 00 00 00 00", 8, 0),            # dec_exp=9, N>=6 -> out of range -> 0
        ("45 32 76 74", 4, 32767),                     # 32767.4 -> 32767
        ("45 32 76 76", 4, 32767),                      # 32767.6 -> 32767 (truncate)
        ("45 40 00 00", 4, 40000),                       # POKE-address regression anchor
        ("45 65 53 50", 4, 65535),                        # unsigned ceiling
        ("45 65 53 55", 4, 0),                             # 65535.5 -> wrap -> -0.5 -> 0
        ("45 99 99 99", 4, 0),                              # 99999 > 65535 -> out of domain -> 0
        ("C5 32 76 80", 4, -32768),                          # negative floor, exact
        ("C5 32 76 85", 4, -32768),                           # -32768.5 -> truncate -> -32768
                                                                # (magnitude 32768 <= bound, in
                                                                # domain -- same shape as the
                                                                # -32768.9 pin below)
        ("C5 32 76 89", 4, -32768),                            # -32768.9 -> truncate -> -32768
                                                                 # (spec §10.3 pin: hex$(-32768.9)
                                                                 # -> "8000")
        ("C5 32 76 90", 4, 0),                                  # -32769 exact -> out of domain -> 0
        ("00 00 00 00", 4, 0),                                  # 0
        ("45 40 00 05", 4, 0x9C41),                              # 40000.5 -> wrap+frac -> 40001
                                                                   # (spec §10.3 pin: hex$(40000.5))
    ]
    for fac_hex, factyp, want in FTI_CASES:
        facbytes = hx(fac_hex)
        m.poke(FAC, facbytes + b"\x00" * (8 - len(facbytes)))
        m.poke(FACTYP, factyp)
        cpu = m.call("flt_to_int16")
        ck(f"flt_to_int16(FAC={fac_hex},FACTYP={factyp})", cpu.de, want & 0xFFFF)

    print("# --- flt_neg ---")
    m.poke(FAC, hx("41150000"))
    m.call("flt_neg")
    ck("flt_neg flips the sign bit", m.peek(FAC)[0], 0xC1)
    m.call("flt_neg")
    ck("flt_neg is its own inverse", m.peek(FAC)[0], 0x41)
    m.poke(FAC, hx("00000000"))
    m.call("flt_neg")
    ck("flt_neg exempts the value-0 lead byte", m.peek(FAC)[0], 0x00)

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
    ck("(1.5) still yields the truncated int in DE", cpu.de, 1)

    fails += run_f2(m, s, ck)

    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(run())
