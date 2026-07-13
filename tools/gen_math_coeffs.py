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

if __name__ == "__main__":
    import sys
    res, B = fit_atan()
    assert res, "no degree met the ATN fit target"
    deg, coeffs, err = res
    print(f"\nchosen ATAN_COEF degree in g = {deg} ({deg+1} coeffs), max_err={err:.3e}")

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
    text = "".join(out)
    path = "sub/math-coeffs.inc"
    if "--emit" in sys.argv:
        with open(path, "w") as f:
            f.write(text)
        print(f"\nwrote {path} ({deg+1} ATAN coeffs + 4 constants), all round-trips < 1e-13")
    else:
        print("\n(dry run; pass --emit to write sub/math-coeffs.inc)\n")
        print(text)
