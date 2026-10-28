# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: D-DIVPACK (2026-10-20) -- fp_div over PACKED BCD, on the host Z80,
as a DIFFERENTIAL against the unpacked-digit fp_div it replaced.

The slice changes HOW the quotient digits are found (basic/float-arith.asm
fp_div: packed remainder/divisor, DAA subtraction over the divisor's own span, a
one-digit-divisor binary shortcut) and must change nothing a caller can see:

  V1  fp_div called directly, OLD image vs NEW image, on the same RAM: FAC (8),
      FACTYP, FPERR, ARGA (18), ARGB (18), registers A/F/BC/DE/HL, and EVERY RAM
      byte in $8000-$FFFF except the stack band and fp_div's own scratch (DIVREM,
      DIVPAD and four single cells the old code wrote and nobody reads after it --
      DEAD below, each named) -- and the new one must leave the tails of those
      blocks (DIVPAD+8..14, home of the tokeniser / fp_mul / combine guests, and
      DIVREM+12..14) exactly as it found them. The corpus: hand cases (the timing rows, exact vs
      repeating, x/x, x/1, 1/x, negatives, 0/x, x/0, 0/0, FPERR already set),
      every pair of digit counts 1..14 x 1..14, int/single/double-shaped operands,
      the exponent walls (pre-check 62/63/64 and -62/-63/-64, the a<b shift, a
      rounding carry that crosses 63), unnormalised mantissas and a nonzero guard
      digit in the inputs (both outside what any producer makes; both identical),
      and a seeded random corpus (FPDIV_RANDOM, default 1000; FPDIV_FULL=1 runs
      200000 across all cores).
  V2  the same, end to end through eval(): `X/Y` for every int/single/double
      pairing (token literals, negatives in parentheses), and SQR / EXP / LOG /
      SIN / COS / TAN / ATN / `^` -- the sub-ROM math tenants that call fp_div --
      compared on FAC, FACTYP, FPERR, DE and the same RAM window.
  V3  the new quotient is the true quotient: for normalised inputs the decoded
      FAC equals the exact quotient truncated to 15 digits and rounded half-up
      (an oracle independent of both images).
  K   knives: a difference planted on the new side only (DE, a FAC byte, an ARGB
      byte, a guest cell) must be reported, or the differential is blind.
  V4  T-states (host-counted, M1 waits included, sub-ROM tenant steps included)
      for the rows the item names, before and after; the new must be cheaper.

The OLD image is assembled from git (BASE_SHA, the tree before D-DIVPACK), main
and sub-ROM both; FPDIV_OLD_DIR may name an already-extracted old tree instead.
No openMSX anywhere.
"""

import bisect
import multiprocessing
import os
import random
import subprocess
import sys
import tarfile
import io
from decimal import Decimal as D, getcontext, ROUND_DOWN

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import msxtest  # noqa: E402
from msxtest import Machine  # noqa: E402
from z80 import Z80  # noqa: E402
from test_paintcell import _timing  # noqa: E402

getcontext().prec = 60

BASE_SHA = "1f6e53a3"          # the tree before D-DIVPACK
BASE = 0x2781
NEW_ROM, NEW_SYM = tp("zb_fpdiv_new.rom"), tp("zb_fpdiv_new.sym")
OLD_DIR = tp("zb_fpdiv_old")
OLD_ROM, OLD_SYM = os.path.join(OLD_DIR, "old.rom"), os.path.join(OLD_DIR, "old.sym")
OLD_SUB, OLD_SUBSYM = os.path.join(OLD_DIR, "sub.rom"), os.path.join(OLD_DIR, "sub.sym")
SRC = 0xC200
STACK_BAND = (0xF200, 0xF380)  # the harness stack: old and new push differently
JUNK = (0xF7C5, 0xF858)        # FBUFFR..KEYARG: every float scratch cell, garbage-filled


def build():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"),
                    NEW_ROM, NEW_SYM], check=True, capture_output=True, cwd=ROOT)
    tree = os.environ.get("FPDIV_OLD_DIR")
    if not tree:
        tree = OLD_DIR
        os.makedirs(tree, exist_ok=True)
        r = subprocess.run(["git", "archive", "--format=tar", BASE_SHA, "basic", "sub"],
                           cwd=ROOT, capture_output=True)
        if r.returncode:
            raise SystemExit("FAIL  cannot extract the pre-D-DIVPACK tree "
                             f"({BASE_SHA}) from git: {r.stderr.decode().strip()}\n"
                             "      set FPDIV_OLD_DIR to a checkout of it")
        tarfile.open(fileobj=io.BytesIO(r.stdout)).extractall(tree)
    subprocess.run(["pasmo", "--bin", "basic/main.asm", OLD_ROM, OLD_SYM],
                   check=True, capture_output=True, cwd=tree)
    subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", OLD_SUB, OLD_SUBSYM],
                   check=True, capture_output=True, cwd=tree)


def machines():
    """(old, new). Each carries the sub-ROM of ITS OWN tree: the sub-ROM's math
    tenants reach fp_div through sub/basic-resident-abi.inc, whose address moved."""
    with open(OLD_SUB, "rb") as fh:
        old_sub = fh.read()
    msxtest._SUB_CACHE.clear()
    msxtest._SUB_CACHE.update(bytes=old_sub, sym=msxtest.load_symbols(OLD_SUBSYM))
    old = Machine(OLD_ROM, OLD_SYM, BASE)
    msxtest._SUB_CACHE.clear()                 # the new one assembles the tree's
    new = Machine(NEW_ROM, NEW_SYM, BASE)
    new.trap_raise_now()   # D-DEFERRSTUDY: routines are called, not run (msxtest)
    return old, new


# --- T-state accounting (only while _T["on"]) ---------------------------------
_T = {"on": False, "t": 0}
_orig_step = Z80.step


def _counting_step(self):
    if not _T["on"]:
        return _orig_step(self)
    pc = self.pc
    _orig_step(self)
    t, m1 = _timing(self.m, pc, self.pc)
    _T["t"] += t + m1


Z80.step = _counting_step


# --- operand records ------------------------------------------------------------
# A record is (sign, dexp, digits[15]) -- FPNUM's [sign:1][dexp:2][dig:15].
def rec_of(value):
    value = D(value)
    if value == 0:
        return (0, 0, [0] * 15)
    t = abs(value).normalize().as_tuple()
    digs = list(t.digits)
    assert len(digs) <= 14, value
    return (0x80 if value < 0 else 0, len(digs) + t.exponent, (digs + [0] * 15)[:15])


def rec_bytes(r):
    sign, dexp, digs = r
    return bytes([sign, dexp & 0xFF, (dexp >> 8) & 0xFF] + digs)


def rec_value(r):
    sign, dexp, digs = r
    v = D(int("".join(map(str, digs[:14])))).scaleb(dexp - 14)
    return -v if sign else v


def rnd_digits(r, nd):
    return [r.randint(1, 9)] + [r.randint(0, 9) for _ in range(nd - 1)] + [0] * (15 - nd)


def rnd_rec(r, nd=None, elo=-8, ehi=8, neg=0.3):
    nd = nd or r.choice([r.randint(1, 14), 14, r.randint(1, 6)])
    return (0x80 if r.random() < neg else 0, r.randint(elo, ehi), rnd_digits(r, nd))


def int_rec(n):
    return rec_of(n)


# --- one comparison ---------------------------------------------------------------
# DEAD: cells the OLD fp_div wrote as its own scratch and that nobody reads after
# it (every reader writes them first -- grep FP_LHSVAL / FP_SHIFTAMT / MUL_CARRY /
# FP_RSIGN): the new fp_div does not write them, so they keep what they held.
def dead_set(sym):
    d = set(range(sym["DIVREM"], sym["DIVREM"] + 15))
    d |= set(range(sym["DIVPAD"], sym["DIVPAD"] + 15))
    for k in ("FP_LHSVAL", "FP_SHIFTAMT", "MUL_CARRY", "FP_RSIGN"):
        d.add(sym[k])
    return d


class Pair:
    def __init__(self):
        self.old, self.new = machines()
        assert self.old.sym["DIVREM"] == self.new.sym["DIVREM"]
        self.dead = dead_set(self.new.sym)
        self.s = self.new.sym
        self.untouched = (list(range(self.s["DIVPAD"] + 8, self.s["DIVPAD"] + 15))
                          + list(range(self.s["DIVREM"] + 12, self.s["DIVREM"] + 15)))
        assert all(JUNK[0] <= a < JUNK[1] for a in self.untouched)
        self.seen_dead = set()
        self.seen_code = set()
        self._labs = {}
        for m in (self.old, self.new):
            labs = sorted((v, k) for k, v in m.sym.items()
                          if v < 0x8000 and not k.startswith("__") and not k.isupper())
            self._labs[id(m)] = ([v for v, _ in labs], labs)

    def _where(self, m, addr):
        vs, labs = self._labs[id(m)]
        i = bisect.bisect_right(vs, addr) - 1
        return None if i < 0 else (labs[i][1], addr - labs[i][0])

    def _same_code_ref(self, a):
        """A cell that holds a RETURN ADDRESS into the image (pop_lhs_and_probe's
        PLF_RA, say) differs between two images whose code moved: equal iff both
        words name the same label + offset."""
        for base in (a - 1, a):
            wo = self.old.mem[base] | self.old.mem[base + 1] << 8
            wn = self.new.mem[base] | self.new.mem[base + 1] << 8
            if wo < 0x8000 and wn < 0x8000 and wo != wn:
                lo, ln = self._where(self.old, wo), self._where(self.new, wn)
                if lo is not None and lo == ln:
                    return True
        return False

    def _prime(self, rng_seed, setup):
        r = random.Random(rng_seed)
        junk = self._junk = bytes(r.randrange(256) for _ in range(JUNK[1] - JUNK[0]))
        for m in (self.old, self.new):
            m.mem[JUNK[0]:JUNK[1]] = junk        # same scratch garbage on both
            setup(m)

    def _state(self, m, cpu):
        s = m.sym
        return {
            "FAC": bytes(m.peek(s["FAC"], 8)), "FACTYP": m.peek(s["FACTYP"])[0],
            "FPERR": m.peek(s["FPERR"])[0], "DE": cpu.de,
        }

    def _ram_diff(self):
        a, b = self.old.mem, self.new.mem
        lo, hi = STACK_BAND
        if a[0x8000:lo] == b[0x8000:lo] and a[hi:] == b[hi:]:
            return []
        # TXTCEIL is LAYOUT, not output: msxtest seeds it with each tree's own TXTMAX,
        # and TXTMAX moved after the old tree (D-BOOTKEYS CTRL RAM, 2026-10-27).
        lay = {self.new.sym["TXTCEIL"], self.new.sym["TXTCEIL"] + 1}
        return [i for i in list(range(0x8000, lo)) + list(range(hi, 0x10000))
                if a[i] != b[i] and i not in lay]

    def run(self, setup, call, seed, regs=False, timed=False):
        """-> (ok, old_state, new_state, detail, t_old, t_new)"""
        self._prime(seed, setup)
        out = []
        for m in (self.old, self.new):
            _T["t"] = 0
            _T["on"] = timed
            cpu = call(m)
            _T["on"] = False
            st = self._state(m, cpu)
            if regs:
                st["regs"] = (cpu.a, cpu.f, cpu.bc, cpu.de, cpu.hl)
            out.append((st, _T["t"]))
        (so, to), (sn, tn) = out
        diff = self._ram_diff()
        live = [a for a in diff if a not in self.dead]
        self.seen_dead |= set(diff) - set(live)
        code = [a for a in live if self._same_code_ref(a)]
        self.seen_code |= set(code)
        live = [a for a in live if a not in code]
        if regs:
            # fp_div ALONE: the new one must not write the old blocks' tails at
            # all -- DIVPAD+8..14 hosts the tokeniser / fp_mul / combine guests
            # (TKPOS.., MUL_I, MUL_PP, FP_OPMODE) and DIVREM+12..14 is spare. That
            # is what makes "dead" above a SUBSET claim, not a hope.
            live += [a for a in self.untouched
                     if self.new.mem[a] != self._junk[a - JUNK[0]]]
        if so.get("FPERR") and so.get("FPERR") == sn.get("FPERR"):
            # D-DEFERRSTUDY family 1 (2026-10-27): the SAME fault on both sides, but
            # the new image RAISES it at once -- it leaves VALTYP as the VG-8020 does
            # (scratchpad/herro_run2.out) and returns no DE. Those two are the change
            # itself; FAC and FPERR must still agree.
            so = {k: v for k, v in so.items() if k not in ("FACTYP", "DE")}
            sn = {k: v for k, v in sn.items() if k not in ("FACTYP", "DE")}
            live = [x for x in live if x != self.new.sym["FACTYP"]]
            # ...and the float scratch: family 4 (2026-10-28) raises an overflow found in
            # a math tenant BEFORE fac_dbl_int16 ran over it, so ARGB keeps what it held
            live = [x for x in live if not JUNK[0] <= x < JUNK[1]]
        ok = so == sn and not live
        detail = "" if ok else (f"old={so} new={sn} live RAM diffs="
                                f"{[hex(a) for a in live[:12]]}")
        return ok, so, sn, detail, to, tn


def div_setup(a, b, fperr=0):
    def setup(m):
        s = m.sym
        m.poke(s["ARGA"], rec_bytes(a))
        m.poke(s["ARGB"], rec_bytes(b))
        m.poke(s["FPERR"], fperr)
    return setup


def call_fp_div(m):
    return m.call("fp_div")


# --- V3 oracle ------------------------------------------------------------------
def oracle(a, b):
    """The quotient fp_div must produce for normalised a, b (b != 0, in range):
    15 digits truncated, half-up on the 15th, 14 kept. None if out of range."""
    va, vb = rec_value(a), rec_value(b)
    if va == 0:
        return D(0)
    q = abs(va / vb)
    e = q.adjusted() + 1                       # 0.d1d2.. * 10^e
    m15 = (q.scaleb(15 - e)).to_integral_value(rounding=ROUND_DOWN)
    m14 = (m15 + 5) // 10
    if m14 >= 10 ** 14:
        m14 //= 10
        e += 1
    if e < -63:
        return D(0)                            # silent underflow
    if e > 63:
        return None                            # (FPERR 1: not asked of the oracle)
    v = D(m14).scaleb(e - 14)
    return -v if (a[0] ^ b[0]) & 0x80 else v


def decode_fac(fac, factyp):
    if fac[0] == 0:
        return D(0)
    n = 7 if factyp == 8 else 3
    digs = "".join(f"{x:02X}" for x in fac[1:1 + n])
    v = D(int(digs)).scaleb((fac[0] & 0x7F) - 64 - len(digs))
    return -v if fac[0] & 0x80 else v


# --- the corpora --------------------------------------------------------------------
def hand_cases():
    c = []
    vals = ["1", "2", "3", "7", "9", "10", "300", "0.5", "0.1", "12345.678", "0.0321",
            "1E10", "3.1415926535898", "2.718281828459", "99999999999999",
            "0.99999999999999", "1.0000000000001", "7.0000000000001", "32767", "32768",
            "-32768", "123456", "654321", "0.000001", "1E-30", "9E62", "1E-63", "1E63"]
    for x in vals:
        for y in vals:
            c.append((rec_of(x), rec_of(y), 0))
    for x in vals:                              # x/x, x/1, 1/x, -x/x, x/-1
        c += [(rec_of(x), rec_of(x), 0), (rec_of(x), rec_of(1), 0),
              (rec_of(1), rec_of(x), 0), (rec_of("-" + x.lstrip("-")), rec_of(x), 0),
              (rec_of(x), rec_of(-1), 0)]
    zero = rec_of(0)
    for x in vals[:10] + ["1E-63", "9E62"]:
        c += [(rec_of(x), zero, 0), (zero, rec_of(x), 0), (rec_of(x), zero, 1),
              (rec_of(x), zero, 2), (rec_of(x), zero, 13)]
    c += [(zero, zero, 0), (zero, zero, 5), (rec_of(1), rec_of(3), 1),
          (zero, rec_of("1E-63"), 0)]          # 0/x with a pre-check overflow
    for n in range(1, 301):                     # the timing loop's own rows
        c.append((int_rec(n), int_rec(7), 0))
    return c


def edge_cases(r):
    c = []
    for pre in (-66, -65, -64, -63, -62, -61, 60, 61, 62, 63, 64, 65):
        for _ in range(12):
            ea = r.randint(max(-63, pre - 1 - 63), min(63, pre - 1 + 63))
            eb = ea - pre + 1
            if not -63 <= eb <= 63:
                continue
            a = (r.choice([0, 0x80]), ea, rnd_digits(r, r.randint(1, 14)))
            b = (r.choice([0, 0x80]), eb, rnd_digits(r, r.randint(1, 14)))
            c.append((a, b, 0))
            c.append((a, (b[0], b[1], list(a[2])), 0))      # equal mantissas
    # quotients whose 14 digits round up to 1: the carry renormalises past 63
    for ea in (62, 63, 0, -62, -63):
        for k in range(1, 8):
            a = (0, ea, [9] * 14 + [0])
            b = (0, 0, [9] * (14 - k) + [8] + [9] * (k - 1) + [0])
            c.append((a, b, 0))
            c.append(((0, ea, [1] + [0] * 14), (0, 1, [1] + [0] * 13 + [0]), 0))
    # nonzero guard digit in an input (no producer makes one; both ignore it)
    for _ in range(40):
        a, b = rnd_rec(r), rnd_rec(r)
        a[2][14], b[2][14] = r.randint(1, 9), r.randint(1, 9)
        c.append((a, b, 0))
    # unnormalised mantissas (a leading 0 digit or two): a POKEd variable can
    # carry one; quotient digits above 9 are possible and must match too
    for _ in range(120):
        a, b = rnd_rec(r, 14), rnd_rec(r, 14)
        for i in range(r.randint(0, 2)):
            a[2][i] = 0
        if r.random() < 0.7:
            b[2][0] = 0                         # (two would make the OLD loop crawl)
        if any(b[2][:14]):
            c.append((a, b, 0))
    return c


def digit_count_cases(r, per=2):
    return [(rnd_rec(r, na), rnd_rec(r, nb), 0)
            for na in range(1, 15) for nb in range(1, 15) for _ in range(per)]


def typed_rec(r, kind):
    if kind == "int":
        return int_rec(r.choice([r.randint(-32768, 32767), r.randint(-99, 99)]))
    if kind == "single":
        return rnd_rec(r, r.randint(1, 6), -10, 10)
    return rnd_rec(r, r.randint(1, 14), -20, 20)


def typed_cases(r, per=60):
    kinds = ("int", "single", "double")
    out = []
    for ka in kinds:
        for kb in kinds:
            for _ in range(per):
                b = typed_rec(r, kb)
                while not any(b[2][:14]):
                    b = typed_rec(r, kb)
                out.append((typed_rec(r, ka), b, 0))
    return out


def random_cases(seed, n):
    r = random.Random(seed)
    out = []
    for _ in range(n):
        a = rnd_rec(r, elo=-64, ehi=64) if r.random() < 0.1 else rnd_rec(r)
        b = rnd_rec(r, elo=-64, ehi=64) if r.random() < 0.1 else rnd_rec(r)
        a = (a[0], max(-63, min(63, a[1])), a[2])
        b = (b[0], max(-63, min(63, b[1])), b[2])
        out.append((a, b, 0))
    return out


def check_div(pair, cases, seed0, stats):
    fails = []
    for k, (a, b, fperr) in enumerate(cases):
        ok, so, sn, detail, to, tn = pair.run(div_setup(a, b, fperr), call_fp_div,
                                             seed0 + k, regs=True, timed=True)
        stats["n"] += 1
        stats["t_old"] += to
        stats["t_new"] += tn
        if not ok:
            fails.append(f"{rec_value(a)} / {rec_value(b)} (rec {a} / {b}, FPERR0={fperr}): {detail}")
            continue
        normal = (a[2][0] or not any(a[2][:14])) and b[2][0] and not a[2][14] and not b[2][14]
        if normal and fperr == 0 and sn["FPERR"] == 0:
            want = oracle(a, b)
            got = decode_fac(sn["FAC"], sn["FACTYP"])
            stats["oracle"] += 1
            if want is None or got != want:
                fails.append(f"V3 {rec_value(a)} / {rec_value(b)}: got {got} want {want}")
    return fails


def _worker(args):
    seed, n = args
    pair = Pair()
    stats = {"n": 0, "t_old": 0, "t_new": 0, "oracle": 0}
    fails = check_div(pair, random_cases(seed, n), seed * 7919, stats)
    return stats, fails[:20], len(fails), sorted(pair.seen_dead)


# --- V2: through eval() ---------------------------------------------------------------
def lit(rec, kind):
    """Token bytes of a literal (negative values in parentheses with a unary minus)."""
    sign, dexp, digs = rec
    if kind == "int":
        n = int(rec_value((0, dexp, digs)))
        assert 0 <= n <= 32767
        body = (bytes([0x11 + n]) if n <= 9 else bytes([0x0F, n]) if n <= 255
                else bytes([0x1C, n & 0xFF, n >> 8]))
    else:
        nb = 3 if kind == "single" else 7
        dd = digs[:2 * nb]
        mant = bytes(dd[i] << 4 | dd[i + 1] for i in range(0, 2 * nb, 2))
        lead = (0x40 + dexp) if any(digs[:14]) else 0
        body = bytes([0x1D if kind == "single" else 0x1F, lead]) + (mant if lead else bytes(nb))
    return (b"(\xF2" + body + b")") if sign else body


def eval_setup(tokens):
    def setup(m):
        s = m.sym
        m.poke(SRC, tokens + b"\x00")
        m.poke(s["FACTYP"], 2)
        m.poke(s["FPERR"], 0)
    return setup


def call_eval(m):
    return m.call("eval", hl=SRC, max_steps=20_000_000)


def eval_corpus(r, per_div, per_fn):
    out = []
    kinds = ("int", "single", "double")
    for ka in kinds:
        for kb in kinds:
            for _ in range(per_div):
                a = typed_rec(r, ka)
                b = typed_rec(r, kb)
                if ka == "int" and a[1] > 5 or kb == "int" and b[1] > 5:
                    continue
                if ka == "int" and rec_value((0, a[1], a[2])) > 32767:
                    continue
                if kb == "int" and rec_value((0, b[1], b[2])) > 32767:
                    continue
                out.append((f"{ka}/{kb}", lit(a, ka) + b"\xF4" + lit(b, kb)))
    fns = (("SQR", 0x87, (-6, 20)), ("EXP", 0x8B, (-2, 3)), ("LOG", 0x8A, (-20, 20)),
           ("SIN", 0x89, (-3, 4)), ("COS", 0x8C, (-3, 4)), ("TAN", 0x8D, (-3, 4)),
           ("ATN", 0x8E, (-5, 5)))
    for name, tok, (elo, ehi) in fns:
        for _ in range(per_fn):
            x = rnd_rec(r, None, elo, ehi, neg=0.15 if name in ("SQR", "LOG") else 0.4)
            kind = r.choice(["single", "double"])
            if kind == "single":
                x = (x[0], x[1], x[2][:6] + [0] * 9)
            out.append((name, bytes([0xFF, tok]) + b"(" + lit(x, kind) + b")"))
    for _ in range(per_fn):
        x = rnd_rec(r, None, -2, 3, neg=0.2)
        y = rnd_rec(r, r.randint(1, 4), -1, 2, neg=0.3)
        out.append(("^", b"(" + lit(x, "double") + b")\xF5(" + lit(y, "double") + b")"))
    return out


# --- run ------------------------------------------------------------------------------
def run():
    build()
    full = os.environ.get("FPDIV_FULL") == "1"
    nrand = 200000 if full else int(os.environ.get("FPDIV_RANDOM", "1000"))
    pair = Pair()
    r = random.Random(20261020)
    fails = 0

    def report(label, n, bad, extra=""):
        nonlocal fails
        fails += len(bad)
        print(f"{'PASS' if not bad else 'FAIL'}  {label}: {n - len(bad)}/{n} identical{extra}")
        for b in bad[:12]:
            print(f"      {b}")

    # ---------------------------------------------------------------- V1 + V3
    # ---------------------------------------------------------------- K: the
    # comparator can FAIL. Each knife plants one difference on the NEW side only
    # (a register, a result byte, an operand byte, a guest cell fp_div must not
    # touch) and must be reported; a differential that cannot see them proves
    # nothing.
    print("# --- K: knives -- a planted difference is reported ---")
    s0 = pair.s
    knives = [("register E", lambda m: setattr(m.cpu, "e", m.cpu.e ^ 1)),
              ("FAC+7", lambda m: m.poke(s0["FAC"] + 7, m.peek(s0["FAC"] + 7)[0] ^ 1)),
              ("ARGB+9", lambda m: m.poke(s0["ARGB"] + 9, m.peek(s0["ARGB"] + 9)[0] ^ 1)),
              ("DIVPAD+14 (FP_OPMODE)", lambda m: m.poke(s0["DIVPAD"] + 14,
                                                         m.peek(s0["DIVPAD"] + 14)[0] ^ 1))]
    for label, plant in knives:
        def knifed(m, plant=plant):
            cpu = m.call("fp_div")
            if m is pair.new:
                plant(m)
            return cpu
        ok = pair.run(div_setup(rec_of(1), rec_of(7)), knifed, 3, regs=True)[0]
        fails += ok
        print(f"{'PASS' if not ok else 'FAIL'}  knife {label}: "
              f"{'reported' if not ok else 'NOT SEEN -- the differential is blind'}")
    pair.seen_dead.clear()
    pair.seen_code.clear()

    print("# --- V1/V3: fp_div, old image vs new image (and vs the exact quotient) ---")
    groups = [("hand cases", hand_cases()), ("exponent walls / carry / guard / unnormalised",
              edge_cases(r)), ("digit counts 1..14 x 1..14", digit_count_cases(r)),
              ("int/single/double-shaped operand pairs", typed_cases(r))]
    tot = {"n": 0, "t_old": 0, "t_new": 0, "oracle": 0}
    for label, cases in groups:
        st = {"n": 0, "t_old": 0, "t_new": 0, "oracle": 0}
        bad = check_div(pair, cases, 1000, st)
        for k in tot:
            tot[k] += st[k]
        report(label, st["n"], bad, f" (V3 oracle on {st['oracle']})")
    seen_dead = set(pair.seen_dead)
    if full:
        chunks = [(1000 + i, nrand // 40) for i in range(40)]
        with multiprocessing.Pool(min(10, os.cpu_count() or 1)) as pool:
            res = pool.map(_worker, chunks)
        st = {"n": 0, "t_old": 0, "t_new": 0, "oracle": 0}
        bad, nbad = [], 0
        for s_, f_, nf, sd in res:
            for k in st:
                st[k] += s_[k]
            bad += f_
            nbad += nf
            seen_dead |= set(sd)
        fails += nbad
        print(f"{'PASS' if not nbad else 'FAIL'}  random corpus: {st['n'] - nbad}/{st['n']} "
              f"identical (V3 oracle on {st['oracle']})")
        for b in bad[:12]:
            print(f"      {b}")
    else:
        st = {"n": 0, "t_old": 0, "t_new": 0, "oracle": 0}
        bad = check_div(pair, random_cases(1000, nrand), 50000, st)
        report("random corpus", st["n"], bad, f" (V3 oracle on {st['oracle']})")
        seen_dead |= pair.seen_dead
    print(f"      mean fp_div T-states over the random corpus: old {st['t_old'] / st['n']:.0f}"
          f", new {st['t_new'] / st['n']:.0f} ({st['t_old'] / st['t_new']:.2f}x)")
    if st["t_new"] >= st["t_old"]:
        fails += 1
        print("FAIL  the new fp_div is not cheaper on the random corpus")
    s = pair.s
    names = {}
    for k in ("DIVREM", "DIVPAD"):
        for i in range(15):
            names[s[k] + i] = f"{k}+{i}"
    for k in ("FP_LHSVAL", "FP_SHIFTAMT", "MUL_CARRY", "FP_RSIGN"):
        names[s[k]] = k
    print(f"      RAM that differed, all inside fp_div's own scratch / dead cells: "
          f"{', '.join(names[a] for a in sorted(seen_dead))}")

    # ---------------------------------------------------------------- V2
    print("# --- V2: through eval(): typed '/', SQR/EXP/LOG/SIN/COS/TAN/ATN, '^' ---")
    per_div, per_fn = (300, 120) if full else (25, 6)
    corpus = eval_corpus(r, per_div, per_fn)
    by = {}
    for k, (label, tokens) in enumerate(corpus):
        ok, so, sn, detail, to, tn = pair.run(eval_setup(tokens), call_eval, 90000 + k,
                                              timed=True)
        g = by.setdefault(label, [0, [], 0, 0])
        g[0] += 1
        g[2] += to
        g[3] += tn
        if not ok:
            g[1].append(f"{tokens.hex()}: {detail}")
    for label, (n, bad, to, tn) in by.items():
        report(f"eval {label:14}", n, bad, f"   T old {to // n:7d} new {tn // n:7d}")
    rev = {}
    for k, v in sorted(s.items()):
        if 0xF000 <= v and k.isupper():
            rev.setdefault(v, k)
    print(f"      RAM cells holding a return address into the image (same label+offset "
          f"in both): {', '.join(rev.get(a, hex(a)) for a in sorted(pair.seen_code)) or 'none'}")

    # ---------------------------------------------------------------- V4
    print("# --- V4: T-states, fp_div alone and the whole expression ---")
    rows = [("300/7", "300", "7"), ("1/3", "1", "3"), ("2/3#", "2", "3"),
            ("1E10/7", "1E10", "7"), ("12345.678/0.0321", "12345.678", "0.0321"),
            ("1#/7#", "1", "7"), ("1/7.0000000000001", "1", "7.0000000000001"),
            ("pi/e", "3.1415926535898", "2.718281828459")]
    print(f"      {'fp_div':22} {'old':>8} {'new':>8}")
    for label, a, b in rows:
        _, _, _, _, to, tn = pair.run(div_setup(rec_of(a), rec_of(b)), call_fp_div, 7,
                                      timed=True)
        print(f"      {label:22} {to:8d} {tn:8d}  {to / tn:5.2f}x")
        if tn >= to:
            fails += 1
            print(f"FAIL  {label}: not cheaper")
    i300 = lit(int_rec(300), "int") + b"\xF4" + lit(int_rec(7), "int")
    sq = bytes([0xFF, 0x87]) + b"(" + lit(rec_of(2), "double") + b")"
    sq2 = bytes([0xFF, 0x87]) + b"(" + lit(rec_of("12345.6789"), "double") + b")"
    for label, tokens in (("eval 300/7", i300), ("eval SQR(2#)", sq),
                          ("eval SQR(12345.6789#)", sq2)):
        _, _, _, _, to, tn = pair.run(eval_setup(tokens), call_eval, 7, timed=True)
        print(f"      {label:22} {to:8d} {tn:8d}  {to / tn:5.2f}x")

    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(run())
