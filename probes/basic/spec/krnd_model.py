#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: BSD-2-Clause
"""The model and the rules of docs/keywords/RND.md, over probes/basic/spec/krnd.py's cases (D-KWSPEC).

THE GENERATOR, stated on the bytes (every constant below is the reference's, recovered black-box in 2026-07 --
docs/spec-basic-mathpack-slice2.md §15.1 -- and here re-checked against every step krnd measured):
  state   S, a 14-digit decimal number 0 <= S < 10^14, held in RNDX ($F857..$F85E) as 00 followed by S's 14 digits
          in packed BCD (two a byte, the most significant first; leading zeros kept)
  next    S' = (A * S + C) mod 10^14,   A = 21132486540519,  C = 14389820420821
  reset   S0 = 40649651372358 (power-on, CLEAR, NEW, RUN, a program line entered)
  RND(x)  x positive: S := next(S);  x zero: S unchanged;  x negative: S := next(m), m = x's 14 mantissa digits
          (a single's 6 then 8 zeros; an integer's decimal digits left-aligned) -- the exponent and the sign play no
          part. "Negative" is the sign BIT (a single 80 10 00 00, exponent byte 0, reseeds from 10 00 00); a number
          without it whose exponent byte is 0 is zero.
  result  the DOUBLE S / 10^14, normalised: S's digits shifted left past their leading zeros, the exponent byte
          &H40 minus that count; S = 0 gives 8 zero bytes.

Two prediction modes, so no rule replays the reference's own output:
  local   each step from the state the PREVIOUS record read in RNDX (one step of the recurrence);
  chain   each group from its start (power-on or CLEAR: S0) and the arguments alone, reading no measured state.
"""
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(HERE))), "tools"))
import krnd  # noqa: E402
import ramrec  # noqa: E402
from spec_rules import Rule  # noqa: E402

M14 = 10 ** 14
GEN = dict(A=21132486540519, C=14389820420821, S0=40649651372358)
R_SENT = bytes([0xC5, 0x12, 0x34, 0x50, 0, 0, 0, 0])     # R = -12345 (a double) before every step
FIELDS = ["e", "rbytes", "vt", "res", "rndx"]
OUTPUTS = {g: FIELDS for g in krnd.ORDER}
OUTPUTS_DESC = ("each step's error, R's 8 bytes, the result's type and own bytes as USR saw them, and RNDX's 8 bytes "
                "after the step")
NB = {"I": 2, "S": 4, "D": 8}


# ---- numbers ----------------------------------------------------------------------------------------------------
def bcd(digits):
    return bytes(int(digits[i:i + 2], 16) for i in range(0, len(digits), 2))


def enc(text, ty):
    """a literal's own bytes as a variable of type ty holds it (exact decimals; the rules' inputs, never outputs)"""
    v = Fraction(text.replace("D", "E")) if "E" not in text.replace("D", "E") else _efrac(text)
    if ty == "I":
        n = int(v)
        return bytes([n & 255, (n >> 8) & 255])
    if v == 0:
        return bytes(NB[ty])
    nd = 6 if ty == "S" else 14
    a, e = abs(v), 0
    while a >= 1:
        a /= 10
        e += 1
    while a < Fraction(1, 10):
        a *= 10
        e -= 1
    m = a * 10 ** nd
    assert m.denominator == 1, text
    return bytes([(0x80 if v < 0 else 0) | (64 + e)]) + bcd(f"{int(m):0{nd}d}")


def _efrac(text):
    t = text.replace("D", "E")
    mant, ex = t.split("E")
    return Fraction(mant) * Fraction(10) ** int(ex)


def state_of(rndx):
    """S from RNDX's bytes, or None when they are not 00 + 14 BCD digits"""
    if rndx[0] != 0:
        return None
    h = rndx[1:].hex()
    return int(h) if h.isdigit() else None


def cell(S):
    return bytes([0]) + bcd(f"{S:014d}")


def result(S):
    """the double S / 10^14, normalised; 0 gives 8 zero bytes"""
    if S == 0:
        return bytes(8)
    d = f"{S:014d}"
    k = len(d) - len(d.lstrip("0"))
    return bytes([0x40 - k]) + bcd(d[k:] + "0" * k)


def classify(ty, b):
    """("pos" | "zero" | "seed", m): how RND takes an argument of type ty with own bytes b"""
    if ty == "I":
        n = ramrec.number(b)
        if n == 0:
            return "zero", None
        return ("seed" if n < 0 else "pos"), int(str(abs(n)).ljust(14, "0"))
    m = int(b[1:].hex().ljust(14, "0"))
    if b[0] & 0x80:
        return "seed", m
    return ("zero" if b[0] & 0x7F == 0 else "pos"), m


# ---- one RND call -------------------------------------------------------------------------------------------------
def call(S, kind, m, g=GEN, alt=frozenset()):
    """the state after RND of an argument of this kind (m: its 14 digits) from state S; `alt` names a control's
    deliberate alteration"""
    A, C = g["A"], g["C"]
    nxt = lambda s: (A * s + C) % M14           # noqa: E731
    if kind == "zero":
        return nxt(S) if "zero-steps" in alt else S
    if kind == "pos":
        return nxt(m) if "pos-reseeds" in alt else nxt(S)
    return nxt(m)


def out(S, alt=frozenset()):
    """the result's bytes from state S (a control may alter how)"""
    if "unnormalised" in alt and S:
        return bytes([0x40]) + bcd(f"{S:014d}")
    if "zero-keeps-digits" in alt and S == 0:
        return bytes([0, 0x30, 0x49, 0x48, 0x97, 0x91, 0x41, 0x41])      # zerobas's, KRN FX 54
    return result(S)


# ---- what each step is --------------------------------------------------------------------------------------------
# FX rows' arguments (stmt -> (type, own bytes)); the literal types are R-RND-LIT's, measured by the "lit" rows
FX_ARG = {"R=RND(1)": ("I", "1"), "R=RND (1)": ("I", "1"), "R=RND( 1 )": ("I", "1"), "R=RND(0)": ("I", "0"),
          "R=RND(-0)": ("I", "0"), "R=RND(-1)": ("I", "-1"), "R=RND(-.001)": ("S", "-.001"),
          "R=RND(-1E9)": ("S", "-1E9"), "R=RND(-1/3)": ("D", None), "R=RND(-1!/3)": ("D", None),
          "R=RND(&HFFFF)": ("I", "-1"), "R=RND(&H8000)": ("I", "-32768"), "R=RND(-32768)": ("S", "-32768"),
          "R=RND(.5)": ("S", ".5"), "R=RND(1E-64)": ("S", "1E-64"), "Q=USR(RND(1))": ("I", "1"),
          "Q=USR(RND(0))": ("I", "0"), "Q=USR(RND(-1))": ("I", "-1"), "Q=USR(RND(1%))": ("I", "1"),
          "Q=USR(RND(1!))": ("S", "1"), "R=RND(-.30494897914141#)": ("D", "-.30494897914141")}
THIRD = bytes.fromhex("c033333333333333")              # -1/3 and -1!/3: a double (R-RND-LIT)
LIT = {"-1": ("I", "-1"), "-.001": ("S", "-.001"), "-1E9": ("S", "-1E9"), "-1/3": ("D", THIRD),
       "-1!/3": ("D", THIRD), "&HFFFF": ("I", "-1"), "&H8000": ("I", "-32768"), "-32768": ("S", "-32768")}
ODD = {krnd.PRE0: ("S", bytes.fromhex("00100000")), krnd.PRE80: ("S", bytes.fromhex("80100000")),
       krnd.PRE0D: ("D", bytes.fromhex("0012345678901234")), krnd.PRE80D: ("D", bytes.fromhex("8012345678901234"))}


def _argb(ty, b):
    return b if isinstance(b, bytes) else enc(b, ty)


def lit_of(stmt):
    """a "lit" row's literal text and its expected (type, bytes)"""
    t = stmt[len("Q=USR("):-1]
    ty, b = LIT[t]
    return t, ty, _argb(ty, b)


def fx_calls(c):
    """the RND calls a FX / BOOT / RUN row makes, in order: [(kind, m) | ("res", k)] ("res", k): a reseed from the
    digits of the k-th call's own result, negated"""
    s = c.stmt
    for pre, (ty, b) in ODD.items():
        if s.startswith(pre):
            return [classify(ty, b)]
    if s == "R=RND(-RND(0))" and c.why.startswith("a reseed from RND(0) in state 0"):
        return [("zero", None), ("res", 0)]
    if s in ("R=RND(RND(1))",):
        return [("pos", None), ("pos", None)]
    if s == "R=RND(RND(0))":
        return [("zero", None), ("pos", None)]
    if s == "R=RND(-RND(1))":
        return [("pos", None), ("res", 0)]
    if s == "R=RND(-RND(0))":
        return [("zero", None), ("res", 0)]
    if s == "R=RND(1)-RND(0)":
        return [("pos", None), ("zero", None)]
    if s == "R=RND(0)-RND(1)":
        return [("zero", None), ("pos", None)]
    if s == "R=RND(-1/3)" or s == "R=RND(-1!/3)":
        return [classify("D", THIRD)]
    if s in FX_ARG:
        ty, t = FX_ARG[s]
        return [classify(ty, enc(t, ty))]
    if s == "R#=RND(-RND(0))":                 # EDIT
        return [("zero", None), ("res", 0)]
    if s == "R#=RND(Z!)":                       # EDIT: a single 80 00 00 00
        return [classify("S", bytes.fromhex("80000000"))]
    if s.startswith("R#=RND("):                 # BOOT / EDIT: integer literals
        t = s[len("R#=RND("):-1]
        return [classify("I", enc(t, "I"))]
    raise KeyError(s)


def resets(c):
    """True when the statement itself resets the state (CLEAR)"""
    return c.stmt is not None and c.stmt.startswith(("CLEAR", "CLEAR:"))


def kind_of(c):
    """'val' | 'err' | 'peek' | 'lit' | 'order' | 'id' | 'other'"""
    if c.op == "FX":
        if c.src == "FX":
            return c.kind
        return "val" if "RND(" in c.stmt else "peek"
    return {"R": "val", "U": "val", "OTHER": "other", "PEEK": "peek", "ID": "id"}[c.op]


def fx_err(c):
    return krnd.FX[int(c.id.split()[-1])][3] if c.src == "FX" and c.kind == "err" else None


# ---- the prediction ----------------------------------------------------------------------------------------------
def predict(c, S, g=GEN, alt=frozenset()):
    """(the expected record {e, rbytes, vt, res, rndx}, the state after) for case c from state S"""
    k = kind_of(c)
    rec = dict(e=0, rbytes=R_SENT, vt=255, res=None)
    if k in ("peek", "other"):
        pass
    elif k == "id":
        nb = NB[c.ty]
        rec.update(vt=nb, res=c.arg[:nb])
    elif k == "lit":
        _t, ty, b = lit_of(c.stmt)
        rec.update(vt=NB[ty], res=b)
    elif k == "err":
        code = fx_err(c)
        if c.stmt == "R$=RND(1)" and "type-first" not in alt:
            S = call(S, "pos", None, g, alt)          # RND runs, THEN the assignment refuses its type
        if "zb-order" in alt and c.stmt in ('R=RND("A"', 'R=RND("A",2)'):
            code = 13
        rec.update(e=code)
    else:                                            # one or more RND calls
        if c.op in ("R", "U"):
            calls = [classify(c.ty, c.arg[:NB[c.ty]])]
        else:
            calls = fx_calls(c)
        if k == "order" and "right-to-left" in alt:
            calls = calls[::-1]
        vals = []
        for kd, m in calls:
            if kd == "res":
                b = vals[m]
                kd, m = ("zero", None) if b[0] == 0 else classify("D", bytes([b[0] | 0x80]) + b[1:])
                if "sign-only" in alt and b[0] == 0:
                    kd = "seed"
            S = call(S, kd, m, g, alt)
            vals.append(out(S, alt))
        if k == "order":
            v = ramrec.number(vals[0]) - ramrec.number(vals[1]) if "right-to-left" not in alt else \
                ramrec.number(vals[1]) - ramrec.number(vals[0])
            r = bytes(8) if v == 0 else _dbl(v)
        else:
            r = vals[-1]
        if (c.op == "U") or (c.stmt or "").startswith("Q=USR("):
            vt = 8
            if "type-follows" in alt and c.op == "U":
                vt = NB[c.ty]
            rec.update(vt=vt, res=r[:vt] if vt != 2 else r[:2])
        else:
            rec.update(rbytes=r)
    if resets(c) and "no-clear-reset" not in alt:
        S = g["S0"]
    if "rndx-result" in alt:
        rec["rndx"] = out(S)
    else:
        rec["rndx"] = cell(S)
    return rec, S


def _dbl(v):
    """a nonzero Fraction with <= 14 significant digits as a double's bytes (else None: not exact)"""
    a, e = abs(v), 0
    while a >= 1:
        a /= 10
        e += 1
    while a < Fraction(1, 10):
        a *= 10
        e -= 1
    m = a * M14
    if m.denominator != 1:
        return None
    return bytes([(0x80 if v < 0 else 0) | (64 + e)]) + bcd(f"{int(m):014d}")


def same(c, rec):
    return (c.e, c.rbytes, c.vt, c.res, c.rndx) == (rec["e"], rec["rbytes"], rec["vt"], rec["res"], rec["rndx"])


# ---- the events between recorded steps (BOOT's unrecorded lines, RUN / GOTO's direct steps) ------------------------
def boot_events(group="BOOT"):
    """a direct-mode group (BOOT, EDIT): for each recorded step, the unrecorded lines typed before it"""
    ev, cur = [], []
    for stmt, why in krnd.DIRECT[group]:
        if why is None:
            cur.append(stmt)
        else:
            ev.append(cur)
            cur = []
    return ev


def apply_event(line, S, g=GEN, alt=frozenset()):
    if line[0].isdigit():                       # a program line typed: new, re-typed, replaced or deleted
        return S if "line-keeps" in alt else g["S0"]
    if line in ("NEW", "RUN") or line.startswith("RUN "):
        return S if f"no-{line.split()[0].lower()}-reset" in alt else g["S0"]
    if line.startswith("MAXFILES"):
        return S if "no-maxfiles-reset" in alt else g["S0"]
    if line.startswith("POKE &HF85"):            # a POKE into RNDX: the cell IS the state (R-RND-CELL)
        a, v = line[len("POKE "):].split(",")
        b = bytearray(cell(S))
        b[int(a[2:], 16) - krnd.RNDX] = int(v[2:], 16)
        return S if "rndx-copy" in alt else state_of(bytes(b))
    return S


def start_state(group, g=GEN, alt=frozenset()):
    """the state before a group's first record, from power-on, with nothing measured"""
    S = g["S0"]
    if group in ("RUNR", "GOTO", "GOTO2"):
        for kd, m in (("pos", None), ("pos", None), ("seed", 70000000000000)):   # krnd.RUN_PERTURB
            S = call(S, kd, m, g, alt)
        if group == "GOTO2":
            S = apply_event("99 REM", S, g, alt)
        if group == "RUNR":
            S = apply_event("RUN", S, g, alt)
    return S


def chain(cases, g=GEN, alt=frozenset()):
    """{case id: expected record} for one group's cases from start_state, reading no measured state"""
    if not cases:
        return {}
    grp = cases[0].src
    S = start_state(grp, g, alt)
    ev = boot_events(grp) if grp in krnd.DIRECT else None
    exp = {}
    for i, c in enumerate(cases):
        if ev:
            for line in ev[i]:
                S = apply_event(line, S, g, alt)
        rec, S = predict(c, S, g, alt)
        exp[c.id] = rec
    return exp


# ---- loading ------------------------------------------------------------------------------------------------------
def check_args(cs):
    """the SQ rows' argument bytes are their DATA text's (the rules work from the value given); else exits"""
    for c in cs["ref"] + cs["zb"]:
        if c.op in ("R", "U", "ID", "OTHER", "PEEK") and c.arg[:NB[c.ty]] != enc(c.text, c.ty):
            sys.exit(f"FAIL: {c.id}'s argument bytes {c.arg.hex()} are not {c.text!r}'s")


def load():
    out = {"ref": [], "zb": []}
    for g in krnd.ORDER:
        cs = krnd.load(g)
        if g.startswith("SQ"):
            check_args(cs)
        for who in out:
            prev = None
            exp = chain(cs[who])
            for c in cs[who]:
                c.prev = prev                       # the state the previous record read (None: the group's first)
                c.chain = exp[c.id]
                prev = state_of(c.rndx)
                out[who].append(c)
    return out


def local(c, g=GEN, alt=frozenset()):
    """the expected record from the previous record's measured state (None for a group's first record)"""
    if c.prev is None:
        return None
    if c.src in krnd.DIRECT:
        S = c.prev
        for line in boot_events(c.src)[int(c.id.split()[-1])]:
            S = apply_event(line, S, g, alt)
        return predict(c, S, g, alt)[0]
    return predict(c, c.prev, g, alt)[0]


# ---- selections ---------------------------------------------------------------------------------------------------
def kinds(c):
    """the argument kinds of the RND calls a step makes"""
    k = kind_of(c)
    if k not in ("val", "order"):
        return set()
    if c.op in ("R", "U"):
        return {classify(c.ty, c.arg[:NB[c.ty]])[0]}
    return {kd if kd != "res" else "res" for kd, _m in fx_calls(c)}


def plain(c):
    return c.op in ("R", "U") or (c.src in ("FX", "BOOT", "EDIT", "RUNR", "GOTO", "GOTO2") and kind_of(c) == "val"
                                  and len(fx_calls(c)) == 1 and not any(c.stmt.startswith(p) for p in ODD))


def local_ok(c):
    rec = local(c)
    return rec is not None and same(c, rec)


def chain_ok(c):
    return same(c, c.chain)


def is_fx(c, *stmts):
    return c.src == "FX" and c.stmt in stmts


def rules():
    R = []

    def add(rid, sec, text, sel, exp):
        R.append(Rule(rid, sec, text, sel, exp))

    s1 = "1. The generator"
    add("R-RND-CELL", s1, "The state is a 14-digit number S held in RNDX ($F857, 8 bytes; C-BIOS's source names the "
        "address): byte 0 is 00 and bytes 1-7 are S's 14 digits in packed BCD, the most significant first, leading "
        "zeros kept (S = 1 is 00 00 00 00 00 00 00 01). Read after every step. It IS the state, not a copy: after "
        "`POKE &HF858,&H12` RND(0) returns .12389820420821 and RND(1) steps from that (KRN EDIT 11, 12).",
        lambda c: True, lambda c: state_of(c.rndx) is not None and (c.id not in ("KRN EDIT 11", "KRN EDIT 12")
                                                                     or local_ok(c)))
    add("R-RND-NEXT", s1, "A positive argument -- any type, any value: 1, 7, 32767, .3, .5, 1E-64, 9.99999E62, "
        "9.9999999999999D62 -- steps the state once (nested, R-RND-NESTED): S' = (21132486540519 * S + 14389820420821) "
        "mod 10^14, S the state RNDX held before the call; the argument's value plays no part.",
        lambda c: c.prev is not None and plain(c) and kinds(c) == {"pos"}, local_ok)
    add("R-RND-REPEAT", s1, "A zero argument (0%, 0!, 0#, and the literals 0 and -0 -- `-0`, `-0!` and `-0#` "
        "give 8 zero bytes like 0) leaves the state as it is, and RND returns the CURRENT state's number, S / 10^14: "
        "the last number returned, or, before any (at power-on, after CLEAR, NEW or a typed line), S0's "
        ".40649651372358, never returned before (KRN BOOT 1).",
        lambda c: c.prev is not None and plain(c) and kinds(c) == {"zero"}, local_ok)
    add("R-RND-SEED", s1, "A negative argument sets the state from its own digits, whatever the state was: S' = "
        "(21132486540519 * m + 14389820420821) mod 10^14, m the argument's 14 mantissa digits -- a double's 14, a "
        "single's 6 followed by 8 zeros, an integer's decimal digits left-aligned (-12345% gives m = "
        "12345000000000). Neither the exponent nor the sign counts: RND(-1), RND(-.001), RND(-1E9), RND(-1D-64) and "
        "RND(&HFFFF) restart at the same place; -.333333! and -.33333333333333# at different ones.",
        lambda c: c.prev is not None and plain(c) and kinds(c) == {"seed"}, local_ok)
    add("R-RND-SIGN", s1, "What counts as negative is the sign BIT: a single 80 10 00 00 or a double 80 12 34 56 78 "
        "90 12 34 (exponent byte &H80) reseeds from its digit bytes (10 00 00 ..., 12 34 56 78 90 12 34); without "
        "the sign bit an exponent byte of 0 is a zero (00 10 00 00 and 00 12 34 ... repeat the last number). A sign-bit "
        "zero, 80 00 00 00, reseeds from m = 0: the state becomes C, 14389820420821 (KRN EDIT 15).",
        lambda c: (c.src == "FX" and any(c.stmt.startswith(p) for p in ODD)) or (c.src == "EDIT" and c.stmt == "R#=RND(Z!)"),
        local_ok)
    add("R-RND-NESTED", s1, "An RND inside RND's argument runs first, and the outer call takes its result as any "
        "other argument: RND(RND(1)) steps twice, RND(RND(0)) once, and RND(-RND(1)) reseeds from the digits of the "
        "number RND(1) returned (normalised, R-RND-VALUE: after RND(-1), state 04389820420821, RND(-RND(0)) reseeds "
        "from 43898204208210, KRN EDIT 14); RND(-RND(0)) in state 0 is RND(-0), which repeats the 0.",
        lambda c: c.src in ("FX", "EDIT") and kind_of(c) == "val" and c.stmt.startswith(("R=RND(", "R#=RND("))
        and "RND(" in c.stmt[6:],
        local_ok)
    add("R-RND-ORDER", s1, "Two calls in one expression run left to right: RND(1)-RND(0) is exactly 0 (8 zero bytes) "
        "and steps once; RND(0)-RND(1) is the old number minus the new one, exactly.",
        lambda c: c.src == "FX" and c.kind == "order", local_ok)
    add("R-RND-CHAIN", s1, "Every group's whole sequence -- each result's bytes and each RNDX -- follows from the "
        "start-up state 40649651372358 and the arguments alone, by R-RND-NEXT, R-RND-REPEAT, R-RND-SEED and "
        "R-RND-START, reading no measured state (SQ3: RND(-1) then 200 steps of RND(1)).",
        lambda c: True, chain_ok)

    s2 = "2. The result"
    add("R-RND-VALUE", s2, "The number returned is S / 10^14 as a DOUBLE, normalised: S's 14 digits shifted left "
        "past their leading zeros, the exponent byte &H40 minus the count (S = 4389820420821 is .04389820420821, "
        "3F 43 89 82 04 20 82 10; S = 1 is 1E-14, 33 10 00 ...); S = 0 gives 8 zero bytes. Read on every step "
        "that assigns R.",
        lambda c: kind_of(c) == "val" and c.op != "U" and not (c.stmt or "").startswith("Q=USR("),
        lambda c: c.e == 0 and c.vt == 255 and c.rbytes == result(state_of(c.rndx)))
    add("R-RND-TYPE", s2, "The result is always a double, whatever the argument's type (USR sees VALTYP 8 and the "
        "same 8 bytes R-RND-VALUE gives): RND(1%), RND(1!), RND(1#), RND(0), RND(-1), RND(0) in state 0 (8 zero "
        "bytes).",
        lambda c: kind_of(c) == "val" and (c.op == "U" or (c.stmt or "").startswith("Q=USR(")),
        lambda c: c.vt == 8 and c.res == result(state_of(c.rndx)) and c.rbytes == R_SENT and c.e == 0)
    add("R-RND-ASSIGN", s2, "`R=RND(x)` with R a double stores the result's 8 bytes; a step that assigns nothing "
        "(an error, `Q=USR(...)`, another statement) leaves R's sentinel -12345. Read in every case.",
        lambda c: True, lambda c: c.rbytes == (c.chain["rbytes"]))

    s3 = "3. Start-up and resets"
    add("R-RND-START", s3, "At power-on RNDX holds 00 40 64 96 51 37 23 58: S0 = 40649651372358, so the first "
        "RND(1) is .59521943994623 and RND(0) before it .40649651372358. CLEAR (with or without arguments), NEW, RUN "
        "(also `RUN 20`), MAXFILES= and ENTERING A PROGRAM LINE in direct mode -- a new line, the same line re-typed "
        "unchanged, a line replaced, a line deleted by its number alone -- each put S0 back; CLS and GOTO do not.",
        lambda c: c.src in ("BOOT", "EDIT", "RUNR", "GOTO", "GOTO2") and kind_of(c) == "peek", chain_ok)
    add("R-RND-OTHER", s3, "Statements that do not call RND leave the state alone: other maths (SIN, EXP, SQR, LOG, "
        "ATN, INT, ABS, STR$, HEX$), READ, POKE (outside RNDX), VARPTR, USR of a number (the errors: R-RND-ERR).",
        lambda c: c.prev is not None and kind_of(c) in ("other", "peek", "id", "lit")
        and not resets(c) and c.src not in krnd.DIRECT,
        lambda c: state_of(c.rndx) == c.prev and local_ok(c))

    s4 = "4. Forms, errors and literals"
    add("R-RND-ERR", s4, "A string argument (`RND(\"A\")`, `RND(S$)`) is error 13; no argument, an extra one (also "
        "after a negative first), no `)` (also after a negative first), the name alone, and `RANDOMIZE 1` (not MSX1 "
        "BASIC) are error 2; `RND(1/0)` and `RND(-1/0)` raise the argument's own 11. None of them assigns R or moves "
        "the state.",
        lambda c: c.src == "FX" and c.kind == "err" and c.stmt not in ('R=RND("A"', 'R=RND("A",2)', "R=RND(1/0",
                                                                      "R$=RND(1)"),
        local_ok)
    add("R-RND-CHECKS", s4, "The argument is worked out first, the `)` checked next, the type last: `RND(1/0` (no "
        "`)`) is error 11; `RND(\"A\"` and `RND(\"A\",2)` are error 2, not 13.",
        lambda c: is_fx(c, 'R=RND("A"', 'R=RND("A",2)', "R=RND(1/0"), local_ok)
    add("R-RND-STRTARGET", s4, "`R$=RND(1)` is error 13 -- but RND has already run: the state steps, and R is not "
        "assigned.", lambda c: is_fx(c, "R$=RND(1)"), local_ok)
    add("R-RND-FORMS", s4, "A space before the parenthesis and spaces around the argument are allowed; a literal's "
        "own type is the argument's (R-RND-LIT), and each form does what R-RND-NEXT / -REPEAT / -SEED say for it.",
        lambda c: is_fx(c, "R=RND (1)", "R=RND( 1 )", "R=RND(-0)", "R=RND(&HFFFF)", "R=RND(&H8000)",
                        "R=RND(-32768)", "R=RND(-1!/3)", "R=RND(-1/3)", "R=RND(.5)", "R=RND(1E-64)"), local_ok)
    add("R-RND-LIT", s4, "The literals' own types (apparatus, `Q=USR(x)` with no RND): -1 and &HFFFF the integer -1, "
        "&H8000 the integer -32768, -.001 / -1E9 / -32768 singles, -1/3 AND -1!/3 doubles (c0 33 33 33 33 33 33 33: "
        "`/` gives a double even from a single).",
        lambda c: c.src == "FX" and c.kind == "lit", local_ok)
    return R


RULES_ALL = None


def get_rules():
    global RULES_ALL
    if RULES_ALL is None:
        RULES_ALL = rules()
    return RULES_ALL
