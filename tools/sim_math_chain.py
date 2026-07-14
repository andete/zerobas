#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Simulate the math-pack transcendental op chains at EXACT 14-digit BCD
precision and measure end-to-end accuracy vs high-precision truth
(docs/spec-basic-mathpack-slice2.md §12 -- the slice-2a lesson §11.10: the
FIT error is not the story, the CHAIN accumulation is; 2a only discovered
that after the asm was written, so 2b proves it BEFORE).

Model: every resident fp_add/fp_sub/fp_mul/fp_div is exact-then-round-to-14-
significant-digits HALF_UP (Decimal localcontext prec=14) -- the model that
reproduced fp_atan's emitted digits bit-for-bit in the 2a investigation.
Known modelling limit: the real core keeps 14+1 guard digits through
alignment and drops the rest (no sticky digit), which can differ from
exact-then-round by 1 ulp only when an add/sub crosses a power-of-10
boundary with an operand-exponent gap of ~15 -- measure-zero in these
chains; the on-hardware gate (basic_probe_math_conv.py) is the final
arbiter and its bounds carry that margin.

Constants/coefficients are PARSED FROM sub/math-coeffs.inc -- the sim
validates the artifact that actually ships, not a recomputation.

Run: python3 tools/sim_math_chain.py            (report + assert bounds)
     python3 tools/sim_math_chain.py --verbose  (also list every deviation)
"""
from __future__ import annotations
import decimal, re, sys, os
from decimal import Decimal as D

decimal.getcontext().prec = 60

INC = os.path.join(os.path.dirname(__file__), "..", "sub", "math-coeffs.inc")

# Bounds asserted by this sim (and mirrored by the gate probe): measured on
# the batteries below, they are the DOCUMENTED bounded-deviation envelopes
# (§12; ATN precedent §11.10). Measured 2026-07-13: EXP worst 1 ulp / 92.0%
# correctly-rounded (the implicit-1 E(r) reconstruction); LOG worst 4 ulp /
# 87.3% correctly-rounded, every >2-ulp case in the j=8 FOLD path
# (x in [0.866,1)) where den=m'+1 needs 15 digits and dr/ds=2 doubles the
# division rounding -- irreducible without extended precision (the same
# clean-room wall as §11.10/division). EXP bound carries +1 margin over the
# measured worst for the sim's known no-sticky-digit modelling limit.
EXP_MAX_ULP = 2
LOG_MAX_ULP = 4

# POW (`^`, §13): the positive-y int path is REFERENCE-IDENTICAL by
# construction (square-and-multiply over the reference-identical fp_mul; the
# POW_REF_ANCHORS assert it bit-for-bit), so vs TRUTH it inherits the
# structure's squaring amplification: each s := s*s DOUBLES the accumulated
# relative error, so the truth deviation grows ~2^bitlen(n) -- that is the
# reference's own error, not ours to fix (bug-for-bug principle). The sim
# asserts a PER-ROW structural tripwire d <= POW_INT_ROW_K * 2^bitlen(n)
# instead of a flat bound. The frac path (EXP(y*LOG(x))) deviation scales
# with |t| = |y*log x| (result rel err ~= Delta t = t * rel-err(LOG)):
# per-row cap POW_FRAC_T_K * max(1, |t|) + POW_FRAC_T_C. Measured worst
# 2026-07-14: 7.2 ulp per unit t (835 ulp @ t=117); caps carry ~1.7x margin.
POW_INT_ROW_K = 3
POW_FRAC_T_K = 12
POW_FRAC_T_C = 10

# Correctly-rounded floors (drift tripwires, ATN_EXACT_FLOOR precedent):
# a uniform 1-2 ulp degradation would pass the bounds silently without these.
EXP_EXACT_FLOOR_PCT = 90        # measured 92.0%
LOG_EXACT_FLOOR_PCT = 85        # measured 87.3%

MAXV = D("9.9999999999999E+62")     # FPNUM magnitude ceiling (dexp +63)
MINV = D("1E-64")                   # smallest positive normal (dexp -63)


# ---- parse sub/math-coeffs.inc ----------------------------------------------
def parse_inc(path=INC):
    """Return {label: Decimal | [Decimal, ...]} from the generated include.
    Count-prefixed coefficient tables come back as ASCENDING c[0..deg]."""
    labels = {}
    cur = None            # (name, kind) kind: 'coef' (count-prefixed) | 'recs'
    pend_sign = pend_dexp = None
    counts = {}
    with open(path) as f:
        for line in f:
            line = line.rstrip()
            m = re.match(r"^(\w+):\s*(db\s+(\d+)\s*;\s*term count.*|;.*)?$", line)
            if m and not line.lstrip().startswith(";"):
                name = m.group(1)
                if m.group(3):                       # count-prefixed coef table
                    cur = (name, "coef")
                    counts[name] = int(m.group(3))
                    labels[name] = []
                else:
                    cur = (name, "recs")
                    labels[name] = []
                continue
            t = line.strip()
            if re.match(r"^db\s+0[0-9A-Fa-f]{2}h", t):
                pend_sign = -1 if int(t.split()[1].rstrip(";h"), 16) & 0x80 else 1
            elif re.match(r"^dw\s+\d+", t):
                v = int(t.split()[1])
                pend_dexp = v - 65536 if v >= 32768 else v
            elif re.match(r"^db\s+\d+\s*,", t) and pend_sign is not None:
                digs = [int(x) for x in re.findall(r"\d+", t.split(";")[0])]
                assert len(digs) == 15 and digs[14] == 0, line
                mant = sum(D(d) * D(10) ** (-i) for i, d in enumerate(digs[:14]))
                val = pend_sign * mant * D(10) ** (pend_dexp - 1)
                if mant == 0:
                    val = D(0)
                labels[cur[0]].append(val)
                pend_sign = pend_dexp = None
    out = {}
    for name, vals in labels.items():
        if name in counts:
            assert len(vals) == counts[name], name
            out[name] = list(reversed(vals))         # emitted c[deg]..c[0]
        elif len(vals) == 1:
            out[name] = vals[0]
        else:
            out[name] = vals
    return out


# ---- the 14-digit BCD op model ----------------------------------------------
def fp14(v):
    if v == 0:
        return D(0)
    with decimal.localcontext() as c:
        c.prec = 14
        c.rounding = decimal.ROUND_HALF_UP
        return +v

def op(a, b, kind):
    with decimal.localcontext() as c:
        c.prec = 14
        c.rounding = decimal.ROUND_HALF_UP
        if kind == "+": return a + b
        if kind == "-": return a - b
        if kind == "*": return a * b
        if kind == "/": return a / b
    raise AssertionError(kind)

def horner14(x, coeffs_asc):
    """acc := c[top]; acc := acc*x + c[i] -- each step rounded to 14, exactly
    fp_poly_horner's fp_mul/fp_add sequence."""
    acc = coeffs_asc[-1]
    for c in reversed(coeffs_asc[:-1]):
        acc = op(op(acc, x, "*"), c, "+")
    return acc


# ---- EXP chain (§12) ---------------------------------------------------------
def exp_chain(K, x):
    """x: 14-digit Decimal. Returns Decimal result, 'Overflow', or D(0)."""
    if abs(x) >= 1000:                     # main-side coarse dexp>=4 disposition
        return "Overflow" if x > 0 else D(0)
    q = op(x, K["EXP_RC"], "*")
    # nearest-int, HALF-AWAY on the magnitude (the tenant reads the digit at
    # the dexp boundary -- identical to floor(|q|+0.5) with the sign restored)
    n8 = int((abs(q) + D("0.5")).to_integral_value(rounding=decimal.ROUND_FLOOR))
    if q < 0:
        n8 = -n8
    if n8 > 552:
        return "Overflow"
    if n8 < -552:
        return D(0)
    n, m = n8 >> 3, n8 & 7
    n8fp = D(n8)
    r = op(x, op(n8fp, K["EXP_C1"], "*"), "-")
    r = op(r, op(n8fp, K["EXP_C2"], "*"), "-")
    if m:
        r = op(r, K["EXP_TCOR"][m - 1], "-")
    # exp(r) = 1 + r*E(r) with the leading 1 implicit-exact; reconstruct as
    # T-hat + T-hat*(r*E) so the poly error is amplified by T*r (~1.1x), not
    # by T (up to 7.5x) -- see gen_math_coeffs.expm1_over_r.
    e_val = horner14(r, K["EXP_COEF"])
    w = op(r, e_val, "*")
    if m:
        t = K["POW8_TBL"][m]
        p = op(t, op(t, w, "*"), "+")
    else:
        p = op(D(1), w, "+")
    res = op(p, D(10) ** n, "*")           # exact decimal scaling
    if abs(res) > MAXV:
        return "Overflow"
    if res != 0 and abs(res) < MINV:
        return D(0)
    return res

def exp_truth(x):
    t = fp14(x.exp())
    if t > MAXV:
        return "Overflow"
    if t != 0 and abs(t) < MINV:
        return D(0)
    return t


# ---- LOG chain (§12) ---------------------------------------------------------
def log_chain(K, x):
    """x: positive 14-digit Decimal (x<=0 rejected main-side)."""
    e = x.adjusted()                       # e' = dexp-1, read off the record
    mant = x.scaleb(-e)                    # m in [1,10), exact
    j = sum(1 for bp in K["LOG_BP"] if mant > bp)
    if j == 8:
        mant = mant.scaleb(-1)             # m/10, exact (dexp decrement)
        e += 1
        j = 0
    k = K["POW8_TBL"][j]
    s = op(op(mant, k, "-"), op(mant, k, "+"), "/")
    g = op(s, s, "*")
    r = op(s, horner14(g, K["LOG_COEF"]), "*")
    if e == -1:
        # the e'=-1 decade: ONE merged scale-matched add (ln(K-hat)-ln10) --
        # the split e'*C1 + LNK path cancels a decade above the result and
        # costs up to 10 result-ulps per intermediate rounding.
        return op(r, K["NEGLNK_TBL"][j], "+")
    if e:
        r = op(r, op(D(e), K["LN10_C2"], "*"), "+")
    if j:
        r = op(r, K["LNK_TBL"][j - 1], "+")
    if e:
        r = op(r, op(D(e), K["LN10_C1"], "*"), "+")
    return r

def log_truth(x):
    return fp14(x.ln())


# ---- POW (`^`) chain (§13) ---------------------------------------------------
# Integer path: the black-box-pinned reference structure (char_pow rounds 1-5,
# 2026-07-14): acc := 1; per SET bit of n=|y| acc := fp_mul(acc, s); n >>= 1;
# if n != 0, s := fp_mul(s, s).  Every fp_mul carries the E1+E2 >= 64
# PRE-normalisation Overflow gate (E = offset exponent of 0.m*10^E == our
# dexp) -- the same check_preexp_bounds our fp_mul already has, CONFIRMED in
# the reference's own `*` (1D61*10 / 1D31*1D31 / 2D62*4 all Overflow though
# 2D62*4's product fits; 9D61*9 fine).  This makes the reference's odd
# overflow surface (10^62 Overflow yet 2^207=2.06e62 fine, 1D62^1 Overflow)
# an emergent property we reproduce for free.  Negative y: p := x^|y| FIRST,
# then reciprocal -- p==0 (underflow) => Overflow error (.5^-2000), else 1/p.
# Fractional path: EXP(y*LOG(x)) (bit-for-bit the reference's own derivation,
# math-pack spec 5.1); x<0 => Illegal function call; zero-base and y==0
# dispositions precede everything (0^0=1, 0^neg => Division by zero).

def fpE(v):
    """Offset decimal exponent: v = 0.m * 10^E (== the FPNUM dexp field)."""
    return v.adjusted() + 1

def mul_chk(a, b):
    """fp_mul with the pre-normalisation E-sum gate + underflow-to-zero."""
    if not isinstance(a, D) or not isinstance(b, D):
        return "Overflow"                      # propagate
    if a == 0 or b == 0:
        return D(0)
    if fpE(a) + fpE(b) >= 64:
        return "Overflow"
    p = op(a, b, "*")
    if p != 0 and abs(p) < MINV:
        return D(0)
    return p

def pow_int_core(x, n):
    """x^n for n in 0..32768 via the pinned LSB-first square-and-multiply."""
    acc, s = D(1), x
    while n:
        if n & 1:
            acc = mul_chk(acc, s)
            if acc == "Overflow":
                return "Overflow"
        n >>= 1
        if n:
            s = mul_chk(s, s)
            if s == "Overflow":
                return "Overflow"
    return acc

def pow_chain(K, x, y):
    """Full `^` model. Returns Decimal, 'Overflow', 'Division by zero',
    or 'Illegal function call'."""
    if y == 0:
        return D(1)                            # incl. 0^0 = 1
    if x == 0:
        return D(0) if y > 0 else "Division by zero"
    if y == y.to_integral_value() and -32768 <= y <= 32767:
        p = pow_int_core(x, int(abs(y)))
        if y > 0 or p == "Overflow":
            return p
        if p == 0:
            return "Overflow"                  # reciprocal of underflowed 0
        r = op(D(1), p, "/")                   # our fp_div: correctly rounded
        if abs(r) > MAXV:
            return "Overflow"
        return r
    if x < 0:
        return "Illegal function call"
    lg = log_chain(K, x)
    t = mul_chk(y, lg)
    if t == "Overflow":
        return "Overflow"
    return exp_chain(K, t)

def pow_truth(x, y):
    """14-digit-rounded true x^y with the FPNUM range mapping."""
    if y == 0:
        return D(1)
    if x == 0:
        return D(0) if y > 0 else "Division by zero"
    if y == y.to_integral_value():
        with decimal.localcontext() as c:
            c.prec = 80
            t = x ** int(y)
    else:
        if x < 0:
            return "Illegal function call"
        with decimal.localcontext() as c:
            c.prec = 60
            t = (y * x.ln()).exp()
    t = fp14(t)
    if abs(t) > MAXV:
        return "Overflow"
    if t != 0 and abs(t) < MINV:
        return D(0)
    return t


# The captured reference outputs (char_pow rounds 1-5, VG-8020 2026-07-14):
# positive-y integer-path rows are asserted BIT-FOR-BIT -- our fp_mul is
# reference-identical, so the composition must be too; this pins the loop
# structure. Negative-y and fractional rows are NOT asserted against the
# reference (our correctly-rounded div / own EXP+LOG deviate by design).
POW_REF_ANCHORS = [
    ("2",      40,     D("1099511627776")),
    ("3",      20,     D("3486784401")),
    ("2",      50,     D("1.1258999068426E+15")),
    ("3",      33,     D("5.5590605665554E+15")),
    ("7",      19,     D("1.1398895185373E+16")),
    ("1.1",    20,     D("6.7274999493256")),
    ("1.01",   100,    D("2.7048138294216")),
    ("5",      27,     D("7.4505805969238E+18")),
    ("5",      88,     D("3.2311742677853E+61")),
    ("2",      127,    D("1.7014118346047E+38")),
    ("2",      207,    D("2.0568806966517E+62")),
    ("10",     31,     D("1E+31")),
    ("10",     32,     D("1E+32")),
    ("10",     47,     D("1E+47")),
    ("0.1",    63,     D("1E-63")),
    ("-2",     3,      D("-8")),
    ("-2",     10,     D("1024")),
    ("-1",     32767,  D("-1")),
    ("-1",     32768,  "Illegal function call"),   # past int16 -> frac path
    ("10",     62,     "Overflow"),    # acc(10^30)*s5(10^32): E 31+33 = 64
    ("10",     63,     "Overflow"),
    ("2",      210,    "Overflow"),    # true overflow (1.6e63 > ceiling)
    ("-10",    63,     "Overflow"),
    ("1E62",   1,      "Overflow"),    # acc=1*x: E 1+63 = 64
    ("1E31",   3,      "Overflow"),    # square chain: E 32+32 = 64
    ("1E12",   5,      D("1E+60")),
    ("0.5",    2000,   D(0)),
    ("0.5",    -2000,  "Overflow"),    # reciprocal of underflowed 0
    ("2",      -32768, "Overflow"),    # 2^32768 overflows first
    ("10",     -63,    "Overflow"),    # 10^63 overflows before the reciprocal
    ("10",     -31,    D("1E-31")),
    ("10",     -32,    D("1E-32")),
]


def battery_pow_int():
    """(x, n) truth battery for the integer path (chain-error growth ~log2 n)."""
    pairs = []
    seed = 0x77
    for i in range(3000):
        seed = (seed * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        u = D(seed % 10 ** 14) / D(10 ** 14)
        mant = fp14(u * 9 + 1)                     # [1,10) 14-digit
        ex = (seed >> 24) % 7 - 3                  # modest decades
        x = fp14(mant * D(10) ** ex)
        n = (seed >> 40) % 300 + 2
        if i % 3 == 0:
            n = -n
        # keep the pair inside the representable envelope (with margin for
        # the square chain: it reaches x^(2^ceil(log2 n)))
        span = abs(D(n) * x.ln() / D(10).ln())
        if span > 55:
            continue
        pairs.append((x, D(n)))
    pairs += [(D("0.99999999999999"), D(32767)),
              (D("1.0000000000001"), D(32767)),
              (D("1.0000000000001"), D(-32768)),
              (D("2"), D(-40)), (D("3"), D(-5)), (D("2"), D(-10))]
    return pairs

def battery_pow_frac():
    """(x, y) truth battery for the EXP(y*LOG(x)) path."""
    pairs = [(D("2"), D("0.5")), (D("7"), D("2.5")), (D("10"), D("-2.5")),
             (D("123.456"), D("7.89")), (D("10"), D("62.5")),
             (D("1.0000000000001"), D("1234.5")), (D("0.5"), D("-100.25"))]
    seed = 0x5C
    for i in range(3000):
        seed = (seed * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        u = D(seed % 10 ** 14) / D(10 ** 14)
        x = fp14((u * 9 + 1) * D(10) ** ((seed >> 20) % 11 - 5))
        v = D((seed >> 32) % 10 ** 8) / D(10 ** 8)
        y = fp14((v - D("0.5")) * 40)              # [-20, 20)
        if y == y.to_integral_value():
            y += D("0.5")
        span = abs(y * x.ln() / D(10).ln())
        if span > 62:
            continue
        pairs.append((x, y))
    return pairs


# ---- ulp + batteries ----------------------------------------------------------
def ulp_dist(val, truth):
    if truth == 0:
        return None if val == 0 else 10 ** 9
    if not isinstance(val, D) or not isinstance(truth, D):
        return None if val == truth else 10 ** 9
    return abs(val - truth) / D(10) ** (truth.adjusted() - 13)

def battery_exp():
    xs = ["0", "1", "-1", "2", "-2", "0.5", "-0.5", "0.001", "-0.001",
          "1e-9", "-1e-9", "1e-13", "-1e-13", "10", "-10", "20", "-20",
          "88", "100", "142.7", "145", "145.06", "145.062", "145.063",
          "146", "-147", "-147.3", "-147.4", "-148",
          "0.14391156831213", "0.14391156831214", "-0.14391156831213",
          "6.28", "8.8", "2.3025850929940", "-2.3025850929940",
          "4.6051701859881", "23.025850929940"]
    seed = 0x2B
    for i in range(4000):
        seed = (seed * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        u = D(seed % 10 ** 14) / D(10 ** 14)
        if i % 2:
            v = (u - D("0.5")) * 10                       # uniform [-5,5)
        else:
            ex = int(u * 100) % 145                        # log-uniform-ish
            v = (u * 9 + 1) * D(10) ** (ex % 3) * (1 if i % 4 < 2 else -1)
            if v < -147 or v > 145:
                v = v % 100
        xs.append(str(fp14(v)))
    return [fp14(D(x)) for x in xs]

def battery_log():
    xs = ["1", "2", "3", "10", "0.5", "0.1", "0.99", "1.01",
          "2.7182818284590", "9.9999999999999E62", "1E-64", "1E62",
          "1.0676350345268E-64", "0.001", "1000", "7", "0.25"]
    for kk in range(1, 14):                       # 1 +- 10^-k (near-1 accuracy)
        xs += [str(fp14(1 + D(10) ** -kk)), str(fp14(1 - D(10) ** -kk))]
    for ee in range(-64, 63, 7):                  # exact decades
        xs.append(f"1E{ee}")
    seed = 0x10
    for i in range(4000):
        seed = (seed * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        u = D(seed % 10 ** 14) / D(10 ** 14)
        mant = u * 9 + 1                          # [1,10)
        ex = (seed >> 32) % 127 - 64              # dexp-1 in [-64,62]
        if i % 2:
            ex = (seed >> 32) % 5 - 2             # half the draws near 1
        xs.append(str(fp14(mant * D(10) ** ex)))
    return [fp14(D(x)) for x in xs]

def battery_log_breakpoints(K):
    """BP straddles (both scan outcomes) + exact K-hat hits (s=0 fast rail)."""
    xs = []
    for bp in K["LOG_BP"]:
        u = bp.adjusted() - 13
        xs += [bp, bp - D(10) ** u, bp + D(10) ** u]
    xs += [k for k in K["POW8_TBL"]]
    return [fp14(x) for x in xs]


def run(name, xs, chain, truth, bound, verbose, floor_pct=0):
    worst, worst_x, exact, total, dev = D(0), None, 0, 0, []
    hist = {}
    for x in xs:
        got, want = chain(x), truth(x)
        d = ulp_dist(got, want)
        if d is None:
            exact += 1
            total += 1
            continue
        total += 1
        b = int(d.to_integral_value(rounding=decimal.ROUND_CEILING)) \
            if isinstance(d, D) else d
        hist[b] = hist.get(b, 0) + 1
        if b == 0:
            exact += 1
        else:
            dev.append((d, x, got, want))
        if isinstance(d, D) and d > worst:
            worst, worst_x = d, x
    dev.sort(reverse=True)
    print(f"\n--- {name}: {total} inputs ---")
    print(f"worst {worst} ulp @ x={worst_x}; correctly-rounded {exact}/{total} "
          f"({100.0 * exact / total:.1f}%)")
    print(f"ulp histogram: " + ", ".join(f"{k}:{v}" for k, v in sorted(hist.items())))
    if verbose:
        for d, x, got, want in dev[:40]:
            print(f"  {d} ulp  x={x}  got={got}  truth={want}")
    assert worst <= bound, f"{name} worst {worst} ulp exceeds bound {bound}"
    assert 100.0 * exact / total >= floor_pct, \
        f"{name} correctly-rounded {100.0 * exact / total:.1f}% under floor {floor_pct}%"
    return worst, exact, total


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv
    K = parse_inc()
    # identity anchors the asm relies on (§12): EXP(0)=1 and LOG(1)=0 EXACT
    assert exp_chain(K, D(0)) == 1, "EXP(0) must be exactly 1"
    assert log_chain(K, D(1)) == 0, "LOG(1) must be exactly 0"
    # range-end dispositions match the characterized reference (task-1 capture)
    assert exp_chain(K, fp14(D("145.063"))) == "Overflow"
    assert isinstance(exp_chain(K, fp14(D("145.062"))), D)
    assert exp_chain(K, fp14(D("-147.4"))) == 0
    assert isinstance(exp_chain(K, fp14(D("-147.3"))), D)
    assert exp_chain(K, D(1000)) == "Overflow" and exp_chain(K, D(-1000)) == 0

    run("EXP", battery_exp(), lambda x: exp_chain(K, x), exp_truth,
        EXP_MAX_ULP, verbose, EXP_EXACT_FLOOR_PCT)
    run("LOG", battery_log() + battery_log_breakpoints(K),
        lambda x: log_chain(K, x), log_truth, LOG_MAX_ULP, verbose,
        LOG_EXACT_FLOOR_PCT)

    # --- POW (§13) -----------------------------------------------------------
    # 1) the reference anchors, BIT-FOR-BIT (positive-y int path + the whole
    #    disposition surface): this is the loop-structure proof.
    bad = []
    for xs_, n_, want in POW_REF_ANCHORS:
        got = pow_chain(K, fp14(D(xs_)), D(n_))
        if isinstance(want, D):
            okrow = isinstance(got, D) and got == want
        else:
            okrow = got == want
        if not okrow:
            bad.append((xs_, n_, got, want))
    for xs_, n_, got, want in bad:
        print(f"POW ANCHOR MISS: {xs_}^{n_}: got {got}, reference {want}")
    assert not bad, f"{len(bad)} POW reference anchors missed"
    print(f"\nPOW: all {len(POW_REF_ANCHORS)} reference anchors reproduced "
          f"bit-for-bit")
    # 2) int-path truth battery: PER-ROW structural tripwire (see bound notes)
    pairs = battery_pow_int()
    worst_ratio, worst_pair, worst_d, total = D(0), None, D(0), 0
    for x_, y_ in pairs:
        got = pow_chain(K, x_, y_)
        want = pow_truth(x_, y_)
        d = ulp_dist(got, want)
        if d is None:
            total += 1
            continue
        total += 1
        cap = D(POW_INT_ROW_K * (1 << int(abs(y_)).bit_length()))
        assert d <= cap, \
            f"POW-int {x_}^{y_}: {d} ulp exceeds structural cap {cap}"
        if isinstance(d, D):
            ratio = d / cap
            if ratio > worst_ratio:
                worst_ratio, worst_pair, worst_d = ratio, (x_, y_), d
    print(f"\n--- POW-int: {total} inputs, per-row caps HELD "
          f"(K={POW_INT_ROW_K} * 2^bitlen(n)) ---")
    if worst_pair:
        print(f"worst cap-fraction {worst_ratio:.2f} "
              f"({worst_d} ulp) @ {worst_pair[0]}^{worst_pair[1]}")
    # 3) frac-path truth battery: per-row t-scaled cap (see bound notes)
    fpairs = battery_pow_frac()
    worst_ratio, worst_pair, worst_d, total = D(0), None, D(0), 0
    for x_, y_ in fpairs:
        got = pow_chain(K, x_, y_)
        want = pow_truth(x_, y_)
        d = ulp_dist(got, want)
        total += 1
        if d is None:
            continue
        with decimal.localcontext() as c:
            c.prec = 30
            t_ = abs(y_ * x_.ln())
        cap = D(POW_FRAC_T_K) * max(D(1), t_) + POW_FRAC_T_C
        assert d <= cap, \
            f"POW-frac {x_}^{y_} (t={t_:.1f}): {d} ulp exceeds cap {cap:.0f}"
        if isinstance(d, D):
            ratio = d / cap
            if ratio > worst_ratio:
                worst_ratio, worst_pair, worst_d = ratio, (x_, y_), d
    print(f"\n--- POW-frac: {total} inputs, per-row t-scaled caps HELD "
          f"({POW_FRAC_T_K}*max(1,|t|)+{POW_FRAC_T_C}) ---")
    if worst_pair:
        print(f"worst cap-fraction {worst_ratio:.2f} "
              f"({worst_d} ulp) @ {worst_pair[0]}^{worst_pair[1]}")
    print("\nsim_math_chain: ALL BOUNDS HELD")
