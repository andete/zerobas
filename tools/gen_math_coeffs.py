#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Generate own-derived decimal minimax coefficients + constants for the math
pack slice-2 transcendentals (docs/spec-basic-mathpack-slice2.md §11.3).

PROVENANCE: OWN approximation, fitted here at high precision against
mathematical truth (Python `Decimal` series). Cross-checked in METHOD against
the published Cody & Waite / Hart approximation structure (admissible sources);
NEVER derived from the MSX ROM (which is a binary-format black box anyway --
[[no-reference-rom-disasm]]). The fit spec (function, domain, degree, target)
below IS the provenance trail; the emitted sub/math-coeffs.inc is a generated
artifact, regenerated deterministically by this tool.

Method: Chebyshev-node interpolation on the reduced domain (near-minimax for an
analytic function on a tiny interval), max-error-verified on a fine grid. The
domain is so small (ATN: g in [0, 0.0718]) that Chebyshev interpolation is
within a hair of the true minimax; the gate (basic_probe_math_conv.py) is the
final arbiter of end-to-end accuracy.

Slice 2a emits: ATAN_COEF (P(g) ~= atan(sqrt g)/sqrt g), PI_2, PI_6, SQRT3, BREAK.

Slice 2b (EXP+LOG, spec §12) adds -- all reductions DECIMAL-NATIVE (the FPNUM
is a base-10 float, so x10^n scaling and the mantissa/exponent split are EXACT,
which is the whole accuracy story of this design):
  EXP_COEF  minimax for exp(r) on |r| <= ln10/16 (+pad), evaluated by the
            shared fp_poly_horner; EXP_RC = 8/ln10 (n8 := nearest-int(x*RC));
            EXP_C1/EXP_C2 = the Cody-Waite split of C = ln10/8 (C1 10 sig
            digits so n8*C1 is EXACT in 14 for |n8|<=3475, proven below by
            assert); POW8_TBL[m] = round14(10^(m/8)) m=0..7 (record 0 exactly
            1.0; shared with LOG as its K-hat table); EXP_TCOR[m] =
            round14(ln(POW8_TBL[m]) - m*C) m=1..7 -- the tiny additive
            correction that ABSORBS the table records' own 14-digit
            representation error (same Cody-Waite absorption trick as
            LOG's LNK below), applied as r := r - TCOR[m].
  LOG_COEF  minimax for 2*atanh(sqrt g)/sqrt g on g in [0, gmax], gmax
            COMPUTED FROM THE EMITTED (rounded) BP/K records so the fitted
            domain provably covers every runtime s; LOG_BP[j] =
            round14(10^((2j-1)/16)) j=1..8 (the j-scan breakpoints);
            LNK_TBL[j] = round14(ln(POW8_TBL[j])) j=1..7 (ln OF THE ROUNDED
            record, absorbing its representation error); LN10_C1 (12 sig
            digits, so e'*C1 is EXACT in 14 for |e'|<=64) + LN10_C2.
"""
from __future__ import annotations
import decimal
from decimal import Decimal as D

decimal.getcontext().prec = 60

# ---- high-precision truth ---------------------------------------------------
def _sqrt(x): return x.sqrt()

def atan_over_arg_of_g(g):
    """f(g) = atan(sqrt(g))/sqrt(g) = sum_{k>=0} (-1)^k g^k/(2k+1), exact to prec."""
    s = D(0); term = D(1); k = 0; sign = 1
    gk = D(1)
    while True:
        contrib = D(sign) * gk / (2*k + 1)
        s += contrib
        if k > 3 and abs(contrib) < D(10) ** (-58):
            break
        k += 1; sign = -sign; gk *= g
    return s

PI = D("3.14159265358979323846264338327950288419716939937510582097494")

# ---- Decimal linear solve (Gaussian elimination, partial pivot) -------------
def solve(A, b):
    n = len(A)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        piv = M[c][c]
        for r in range(n):
            if r == c: continue
            f = M[r][c] / piv
            if f == 0: continue
            for k in range(c, n + 1):
                M[r][k] -= f * M[c][k]
    return [M[i][n] / M[i][i] for i in range(n)]

def _cos(theta):
    """cos(theta) in Decimal (Taylor). Deterministic -- avoids host libm so the
    committed math-coeffs.inc regenerates byte-identically anywhere (review #5)."""
    s = D(0); term = D(1); t2 = theta * theta; k = 0; sign = 1
    while abs(term) > D(10) ** (-55):
        s += sign * term
        term = term * t2 / ((k + 1) * (k + 2)); k += 2; sign = -sign
    return s

def cheb_interp_coeffs(f, a, b, deg):
    """Interpolate f at deg+1 Chebyshev nodes on [a,b]; return monomial coeffs
    c[0..deg] (ascending, for Horner). Solve the Vandermonde in Decimal."""
    n = deg + 1
    # Chebyshev nodes of the 1st kind mapped to [a,b]; cos computed in Decimal
    # (fully deterministic -- no host math dependency).
    nodes = []
    for i in range(n):
        t = _cos(D(2 * i + 1) * PI / (2 * n))
        nodes.append((a + b) / 2 + (b - a) / 2 * t)
    V = [[x ** j for j in range(n)] for x in nodes]
    y = [f(x) for x in nodes]
    return solve(V, y)

def poly_eval(coeffs, x):
    acc = D(0)
    for c in reversed(coeffs):
        acc = acc * x + c
    return acc

def max_err(coeffs, f, a, b, N=4000):
    m = D(0); worst = a
    for i in range(N + 1):
        x = a + (b - a) * D(i) / N
        e = abs(poly_eval(coeffs, x) - f(x))
        if e > m: m, worst = e, x
    return m, worst

# ---- ATN fit ----------------------------------------------------------------
def fit_atan():
    B = (D(2) - D(3).sqrt()) ** 2      # g domain upper bound = (2-sqrt3)^2
    print(f"ATN: g in [0, {B}]  (a in [0, 2-sqrt3])")
    print(f"     target max|P(g)-f(g)| <= ~1e-16 (so 14-digit Horner rounding dominates)")
    chosen = None
    for deg in range(4, 13):
        c = cheb_interp_coeffs(atan_over_arg_of_g, D(0), B, deg)
        m, w = max_err(c, atan_over_arg_of_g, D(0), B)
        flag = ""
        if chosen is None and m <= D("1e-16"):
            chosen = (deg, c, m); flag = "  <== CHOSEN (minimal degree meeting target)"
        print(f"  deg(g)={deg:2d}  terms={deg+1:2d}  max_err={m:.3e} @g={float(w):.4f}{flag}")
    return chosen, B

# ---- slice 2b: EXP + LOG (docs/spec-basic-mathpack-slice2.md §12) ------------
LN10 = D(10).ln()                      # correctly rounded at prec 60 (decimal spec)
C_LN10_8 = LN10 / 8                    # the EXP reduction constant C

def round14(v):
    """Round to the FPNUM's 14 significant digits, HALF_UP -- the value a
    stored record actually carries (fpconst_fields does the same)."""
    if v == 0:
        return D(0)
    with decimal.localcontext() as c:
        c.prec = 14
        c.rounding = decimal.ROUND_HALF_UP
        return +v

def exp_dec(x):
    return x.exp()                     # correctly rounded at prec 60

def ln_dec(x):
    return x.ln()

def pow10_frac(num, den):
    """10^(num/den) at prec 60 (Decimal power: correctly rounded)."""
    return D(10) ** (D(num) / D(den))

# EXP: n8 := nearest-int(x*RC) with RC = 8/ln10; r := (x - n8*C1) - n8*C2 then
# r := r - TCOR[m]. |x| < 1000 is guaranteed by the main-side stub's coarse
# dexp check, so |n8| <= round(999.99.. * RC) = 3475.
EXP_N8_MAX = 3475
EXP_C1 = round14(C_LN10_8).quantize(D("1e-10"), rounding=decimal.ROUND_HALF_UP)
EXP_C2 = round14(C_LN10_8 - EXP_C1)

def expm1_over_r(r):
    """E(r) = (exp(r)-1)/r, E(0)=1 -- the fitted function. exp(r) = 1 + r*E(r)
    with the leading 1 IMPLICIT and EXACT, so the tenant reconstructs
    result-mantissa = T-hat + T-hat*(r*E) (m != 0) or 1 + r*E (m == 0): the
    polynomial's rounding error is then amplified only by T*r (~1.1x), not by
    T (up to 7.5x for m=7) -- the 14-digit chain sim showed the direct
    exp-poly form loses ~2 extra ulp to exactly that decade-crossing
    multiply (worst m=6/7 offenders), same op count either way."""
    if r == 0:
        return D(1)
    return (exp_dec(r) - 1) / r

def fit_exp():
    # poly domain: |r| <= C/2 plus slack for (a) the RC-multiply picking n8 off
    # by one quantum at a half-boundary and (b) the TCOR nudge (~1e-13); a
    # relative 1e-6 pad dwarfs both.
    B = C_LN10_8 / 2 * (1 + D("1e-6"))
    print(f"EXP: r in [-{B}, +{B}]  (C/2 = ln10/16, padded)")
    print(f"     fitting E(r) = (exp(r)-1)/r  (exp = 1 + r*E, implicit exact 1)")
    print(f"     target max|E-fit| <= ~1e-16 (so 14-digit Horner rounding dominates)")
    chosen = None
    for deg in range(6, 15):
        c = cheb_interp_coeffs(expm1_over_r, -B, B, deg)
        m, w = max_err(c, expm1_over_r, -B, B)
        flag = ""
        if chosen is None and m <= D("1e-16"):
            chosen = (deg, c, m); flag = "  <== CHOSEN (minimal degree meeting target)"
        print(f"  deg(r)={deg:2d}  terms={deg+1:2d}  max_err={m:.3e} @r={float(w):+.4f}{flag}")
    return chosen, B

# LOG: x = m*10^e' with m in [1,10) read EXACTLY off the FPNUM (dexp:=1);
# j-scan vs BP[j]; j==8 folds to (m/10 exact, e'+1, j=0); then
# s := (m - K[j])/(m + K[j]) (numerator EXACT: same-dexp 14-digit subtract),
# r := s * Q(s^2), + e'*C2 + LNK[j] + e'*C1 (ascending magnitude).
POW8 = [round14(pow10_frac(j, 8)) for j in range(8)]          # K-hat / T-hat
LOG_BP = [round14(pow10_frac(2 * j - 1, 16)) for j in range(1, 9)]
LNK = [round14(ln_dec(POW8[j])) for j in range(1, 8)]         # ln of the ROUNDED K
EXP_TCOR = [round14(ln_dec(POW8[m]) - m * C_LN10_8) for m in range(1, 8)]
LN10_C1 = round14(LN10).quantize(D("1e-11"), rounding=decimal.ROUND_HALF_UP)
LN10_C2 = round14(LN10 - LN10_C1)
# The e' == -1 decade (x in [0.0866.., 1)) cancels e'*ln10 against LNK[j] --
# the intermediate r+LNK sits up to a full decade ABOVE the result, so its
# rounding costs up to 10 result-ulps (chain sim: worst 9). Merged constants
# kill the cancellation: ONE scale-matched add of ln(K-hat[j]) - ln10.
NEGLNK = [round14(ln_dec(POW8[j]) - LN10) for j in range(8)]  # j = 0..7

def log_gmax():
    """Max s^2 the runtime can feed the LOG poly, computed from the EMITTED
    (rounded) BP/K records over each scale's CLOSED m-interval (boundary
    equality can land on either side of an fp_cmp, so cover both)."""
    gmax = D(0)
    intervals = [(D(1), LOG_BP[0], POW8[0])]                       # j = 0
    intervals += [(LOG_BP[j - 1], LOG_BP[j], POW8[j]) for j in range(1, 8)]
    intervals += [(LOG_BP[7] / 10, D(1), POW8[0])]                 # j = 8 fold
    for lo, hi, k in intervals:
        for m in (lo, hi):
            s = (m - k) / (m + k)
            gmax = max(gmax, s * s)
    return gmax

def two_atanh_over_arg_of_g(g):
    """f(g) = 2*atanh(sqrt g)/sqrt g = 2*sum_{k>=0} g^k/(2k+1), exact to prec."""
    s = D(0); k = 0; gk = D(1)
    while True:
        contrib = 2 * gk / (2 * k + 1)
        s += contrib
        if k > 3 and abs(contrib) < D(10) ** (-58):
            break
        k += 1; gk *= g
    return s

def fit_log():
    G = log_gmax() * (1 + D("1e-6"))
    print(f"LOG: g in [0, {G}]  (max s^2 over the emitted BP/K records, padded)")
    print(f"     target max|Q(g)-f(g)| <= ~1e-16 (so 14-digit Horner rounding dominates)")
    chosen = None
    for deg in range(4, 11):
        c = cheb_interp_coeffs(two_atanh_over_arg_of_g, D(0), G, deg)
        m, w = max_err(c, two_atanh_over_arg_of_g, D(0), G)
        flag = ""
        if chosen is None and m <= D("1e-16"):
            chosen = (deg, c, m); flag = "  <== CHOSEN (minimal degree meeting target)"
        print(f"  deg(g)={deg:2d}  terms={deg+1:2d}  max_err={m:.3e} @g={float(w):.5f}{flag}")
    return chosen, G

def check_2b_invariants(exp_coeffs, log_coeffs):
    """The exactness preconditions the §12 asm design RELIES on -- assert them
    here so a constant tweak can never silently break them."""
    # n8*C1 exact in 14 digits: C1 has 10 significant digits, |n8| <= 3475 (4
    # digits) -> product needs <= 14. Verify digit count directly.
    assert EXP_C1 == C_LN10_8.quantize(D("1e-10"), rounding=decimal.ROUND_HALF_UP)
    assert (EXP_N8_MAX * EXP_C1) == round14(EXP_N8_MAX * EXP_C1), "n8*C1 not exact"
    # e'*LN10_C1 exact in 14 digits: C1 has 12 significant digits, |e'| <= 64.
    assert (64 * LN10_C1) == round14(64 * LN10_C1), "e'*LN10_C1 not exact"
    # POW8[0] is exactly 1 (the j=0 / m=0 identity record).
    assert POW8[0] == 1
    # EXP(0)=1 and LOG(1)=0 exactness hang on the rounded lead coefficients
    # (EXP's leading 1 is implicit-exact; E(0)=c0=1 keeps r*E well-behaved).
    assert round14(exp_coeffs[0]) == 1, "EXP E-c0 must round to exactly 1"
    assert round14(log_coeffs[0]) == 2, "LOG c0 must round to exactly 2"
    # TCOR really is tiny (absorption correction, not a real term).
    assert all(abs(t) < D("1e-12") for t in EXP_TCOR)
    assert abs(EXP_C2) < D("1e-10") and abs(LN10_C2) < D("1e-11")

# ---- FPNUM (18-byte) record emission ----------------------------------------
# Layout (basic/sysvars.inc): sign(1) + dexp LE word(2) + dig[0..13] (14 sig,
# one decimal digit per byte) + guard(1). value = d0.d1d2... x 10^(dexp-1).
def fpconst_fields(v):
    if v == 0:
        return 0, 0, [0]*14, 0
    sign = 0x80 if v < 0 else 0
    a = abs(v)
    adj = a.adjusted()                      # exponent of the MSD
    with decimal.localcontext() as c:
        c.prec = 14
        c.rounding = decimal.ROUND_HALF_UP
        a14 = +a                            # round to 14 significant digits
    adj = a14.adjusted()                    # re-read (a rounding carry can bump it)
    scaled = (a14.scaleb(13 - adj)).quantize(D(1), rounding=decimal.ROUND_HALF_UP)
    s = str(int(scaled)).rjust(14, "0")
    assert len(s) == 14, (v, s)
    digits = [int(ch) for ch in s]
    dexp = adj + 1
    return sign, dexp, digits, 0

def reconstruct(sign, dexp, digits, guard):
    m = sum(D(d) * D(10) ** (-i) for i, d in enumerate(digits))  # d0.d1d2...
    v = m * D(10) ** (dexp - 1)
    return -v if sign else v

def emit_record(name, v):
    sign, dexp, digs, guard = fpconst_fields(v)
    r = reconstruct(sign, dexp, digs, guard)
    rel = abs(r - v) / (abs(v) if v else D(1))
    assert rel < D("1e-13"), f"{name} round-trip {rel:.2e}"   # 14-sig self-check
    dexp_u = dexp & 0xFFFF
    dl = ", ".join(str(d) for d in digs)
    return (f"{name}:\n"
            f"                db 0{sign:02X}h            ; sign  ({'+' if not sign else '-'})\n"
            f"                dw {dexp_u:<5d}          ; dexp  (value = d0.d1.. x 10^(dexp-1))\n"
            f"                db {dl}, 0   ; dig[0..13], guard=0\n"), r

HEADER = ("; Copyright (c) 2026 Joost Yervante Damad\n"
          "; SPDX-License-Identifier: 0BSD\n;\n"
          "; GENERATED FILE -- do not hand-edit. Produced by tools/gen_math_coeffs.py\n"
          "; (own decimal minimax + constants; cross-checked vs Cody & Waite METHOD,\n"
          "; NEVER the MSX ROM). docs/spec-basic-mathpack-slice2.md §11.3.\n;\n"
          "; FPNUM 18-byte records: sign(1) + dexp LE word(2) + dig[0..13] + guard(1).\n\n")

def emit_coef_table(out, name, deg, coeffs, comment):
    """Count-prefixed Horner table, HIGH-to-LOW (c[deg]..c[0]) -- the
    fp_poly_horner input format (sub/fp_atan.asm)."""
    out.append(f"{name}_DEG{' ' * max(1, 12 - len(name))}equ {deg}\n")
    out.append(f"{name}:{' ' * (15 - len(name))}db {deg+1}                ; term count (c[{deg}]..c[0]){comment}\n")
    for i in range(deg, -1, -1):
        rec, _ = emit_record(f"__{name}_c{i}", coeffs[i])
        rec = rec.replace(f"__{name}_c{i}:\n", f"                ; c[{i}]\n")
        out.append(rec)

def emit_rec_table(out, name, values, comment, first_index=0):
    """A runtime-indexed table of plain 18-byte records (base + 18*rel_index);
    `first_index` documents the caller-visible index of record 0."""
    out.append(f"{name}:{' ' * (15 - len(name))}{comment}\n")
    for k, v in enumerate(values):
        rec, _ = emit_record(f"__{name}_{k}", v)
        rec = rec.replace(f"__{name}_{k}:\n",
                          f"                ; [{first_index + k}]\n")
        out.append(rec)

if __name__ == "__main__":
    import sys
    res, B = fit_atan()
    assert res, "no degree met the ATN fit target"
    deg, coeffs, err = res
    print(f"\nchosen ATAN_COEF degree in g = {deg} ({deg+1} coeffs), max_err={err:.3e}\n")

    res_e, BE = fit_exp()
    assert res_e, "no degree met the EXP fit target"
    deg_e, coeffs_e, err_e = res_e
    print(f"\nchosen EXP_COEF degree in r = {deg_e} ({deg_e+1} coeffs), max_err={err_e:.3e}\n")

    res_l, GL = fit_log()
    assert res_l, "no degree met the LOG fit target"
    deg_l, coeffs_l, err_l = res_l
    print(f"\nchosen LOG_COEF degree in g = {deg_l} ({deg_l+1} coeffs), max_err={err_l:.3e}")

    check_2b_invariants(coeffs_e, coeffs_l)

    out = [HEADER]
    # ATAN_COEF: Horner table, HIGH-to-LOW (c[deg]..c[0]); count byte first.
    out.append(f"ATAN_DEG        equ {deg}\n")
    out.append(f"ATAN_COEF:      db {deg+1}                ; term count (c[{deg}]..c[0])\n")
    maxrel = D(0)
    for i in range(deg, -1, -1):
        rec, r = emit_record(f"__atan_c{i}", coeffs[i])
        # inline the record bytes under the table (label kept as a comment)
        rec = rec.replace(f"__atan_c{i}:\n", f"                ; c[{i}]\n")
        out.append(rec)
    for name, v in [("PI_2", PI/2), ("PI_6", PI/6),
                    ("SQRT3", D(3).sqrt()), ("BREAK", D(2)-D(3).sqrt())]:
        rec, r = emit_record(name, v)
        out.append(rec)

    # ---- slice 2b: EXP + LOG (spec §12) --------------------------------------
    out.append("\n; ---- math pack slice 2b: EXP + LOG (docs/spec-basic-mathpack-"
               "slice2.md §12) ----\n")
    emit_coef_table(out, "EXP_COEF", deg_e, coeffs_e,
                    " -- E(r)=(exp(r)-1)/r, |r|<=ln10/16+pad")
    emit_coef_table(out, "LOG_COEF", deg_l, coeffs_l,
                    " -- 2*atanh(sqrt g)/sqrt g")
    for name, v, cm in [
            ("EXP_RC", 8 / LN10, "; 8/ln10 (n8 := nearest-int(x*RC))"),
            ("EXP_C1", EXP_C1, "; ln10/8 hi split, 10 sig (n8*C1 EXACT)"),
            ("EXP_C2", EXP_C2, "; ln10/8 lo split (C - C1)"),
            ("LN10_C1", LN10_C1, "; ln10 hi split, 12 sig (e'*C1 EXACT)"),
            ("LN10_C2", LN10_C2, "; ln10 lo split (ln10 - C1)")]:
        rec, _ = emit_record(name, v)
        rec = rec.replace("\n", f"  {cm}\n", 1)
        out.append(rec)
    emit_rec_table(out, "POW8_TBL", POW8,
                   "; [m] = round14(10^(m/8)), m=0..7 ([0] exactly 1.0;"
                   " EXP's T-hat AND LOG's K-hat)")
    emit_rec_table(out, "EXP_TCOR", EXP_TCOR,
                   "; [m] = round14(ln(POW8[m]) - m*ln10/8), m=1..7"
                   " (T-hat representation-error absorber)", first_index=1)
    emit_rec_table(out, "LNK_TBL", LNK,
                   "; [j] = round14(ln(POW8[j])), j=1..7 (ln of the ROUNDED"
                   " K-hat -- absorption)", first_index=1)
    emit_rec_table(out, "NEGLNK_TBL", NEGLNK,
                   "; [j] = round14(ln(POW8[j]) - ln10), j=0..7 (the e'=-1"
                   " decade's merged additive -- kills the cancellation)")
    emit_rec_table(out, "LOG_BP", LOG_BP,
                   "; [j] = round14(10^((2j-1)/16)), j=1..8 (j-scan"
                   " breakpoints)", first_index=1)

    text = "".join(out)
    path = "sub/math-coeffs.inc"
    if "--emit" in sys.argv:
        with open(path, "w") as f:
            f.write(text)
        print(f"\nwrote {path} ({deg+1} ATAN + {deg_e+1} EXP + {deg_l+1} LOG "
              f"coeffs + constants/tables), all round-trips < 1e-13")
    else:
        print("\n(dry run; pass --emit to write sub/math-coeffs.inc)\n")
        print(text)
