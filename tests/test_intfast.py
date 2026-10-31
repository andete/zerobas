# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: D-INTFAST (D-LOOPPROF lever 1, 2026-10-20) -- a float `+ - *` whose
operands both hold exact int16 values runs on the int path and packs its answer as
the BCD path would (basic/float-arith.asm: caddsub_float / cmul_float -> fx_cvt ->
caddsub_int / cmul_int -> fx_tail), on the host Z80, as a DIFFERENTIAL against the
image before the slice (git BASE_SHA, main and sub-ROM both).

  V1  combine_add / combine_sub / combine_mul called on a pushed lhs frame
      (push_lhs_frame, exactly as the climber pushes it) and a live rhs, OLD image
      vs NEW image, on the same garbage-filled float scratch: FAC (8), FACTYP,
      FPERR, registers A/F/BC/DE/HL on return, and EVERY RAM byte in $8000-$FFFF
      except the harness stack band and the float scratch the old BCD path writes
      and the new one does not (DEAD below, each named -- and every cell that DID
      differ is printed). Corpus: every type pairing (int16 / single / double) x
      + - * over hand values (0, +-1, +-32767, -32768, +-16384, 32768, sums and
      products crossing the int16 walls, fractions, values past int16, the int16
      $8000 under '-'), a pre-set FPERR, and a seeded random corpus
      (INTFAST_RANDOM, default 1500; INTFAST_FULL=1 runs 120000 across cores).
  V2  whole statements through the interpreter (tokenise / store_line /
      run_prog), old vs new: at EVERY statement boundary the variable region, FAC,
      FACTYP, FPERR, CURLINE, CSP, and everything the program printed -- `A=I+7`,
      `A=I*7`, `B=A-I`, `A=I*7+J-3`, `A=I-J`, `A=1.5+I`, `A#=I#*J#`, suffixed
      literals, with I / J / A of every type (%, !, #, default, DEFINT / DEFSNG /
      DEFDBL) over the int16 walls, fractions and large values; and the timing
      loops.
  P   the new path is TAKEN where it should be (exact operands, in-range answer)
      and NOT where it must not be (a fraction, past int16, $8000 under '-').
  K   knives: a difference planted on the new side only must be reported.
  T   T-states (host, M1 waits included) old vs new, per leaf and per statement.

No openMSX anywhere.
"""

import io
import multiprocessing
import os
import random
import subprocess
import sys
import tarfile
from decimal import Decimal as D, getcontext

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import msxtest  # noqa: E402
from msxtest import Machine  # noqa: E402
from z80 import Z80  # noqa: E402
from test_paintcell import _timing  # noqa: E402

getcontext().prec = 60

BASE_SHA = "2659f210"          # the tree before D-INTFAST
BASE = 0x2781
NEW_ROM, NEW_SYM = tp("zb_intfast_new.rom"), tp("zb_intfast_new.sym")
OLD_DIR = tp("zb_intfast_old")
OLD_ROM, OLD_SYM = os.path.join(OLD_DIR, "old.rom"), os.path.join(OLD_DIR, "old.sym")
OLD_SUB, OLD_SUBSYM = os.path.join(OLD_DIR, "sub.rom"), os.path.join(OLD_DIR, "sub.sym")
STACK_BAND = (0xF200, 0xF380)  # the harness stack: old and new push differently
JUNK = (0xF7C5, 0xF858)        # FBUFFR..KEYARG: every float scratch cell, garbage-filled
STUB, STG = 0xC200, 0xC300     # the V1 driver and its operand staging
SRC, TOKB = 0xC000, 0xC100     # V2: source line / tokenised line
POOL_TOP, POOL_FLOOR = 0xD000, 0x9000
VARTAB, STREND = 0xF6C2, 0xF6C6


def build():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"),
                    NEW_ROM, NEW_SYM], check=True, capture_output=True, cwd=ROOT)
    tree = os.environ.get("INTFAST_OLD_DIR")
    if not tree:
        tree = OLD_DIR
        os.makedirs(tree, exist_ok=True)
        r = subprocess.run(["git", "archive", "--format=tar", BASE_SHA, "basic", "sub"],
                           cwd=ROOT, capture_output=True)
        if r.returncode:
            raise SystemExit("FAIL  cannot extract the pre-D-INTFAST tree "
                             f"({BASE_SHA}) from git: {r.stderr.decode().strip()}\n"
                             "      set INTFAST_OLD_DIR to a checkout of it")
        tarfile.open(fileobj=io.BytesIO(r.stdout)).extractall(tree)
    subprocess.run(["pasmo", "--bin", "basic/main.asm", OLD_ROM, OLD_SYM],
                   check=True, capture_output=True, cwd=tree)
    subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", OLD_SUB, OLD_SUBSYM],
                   check=True, capture_output=True, cwd=tree)


def machines():
    """(old, new), each with the sub-ROM of ITS OWN tree (the resident ABI moved)."""
    with open(OLD_SUB, "rb") as fh:
        old_sub = fh.read()
    msxtest._SUB_CACHE.clear()
    msxtest._SUB_CACHE.update(bytes=old_sub, sym=msxtest.load_symbols(OLD_SUBSYM))
    old = Machine(OLD_ROM, OLD_SYM, BASE)
    msxtest._SUB_CACHE.clear()
    new = Machine(NEW_ROM, NEW_SYM, BASE)
    new.trap_raise_now()   # D-DEFERRSTUDY: a float overflow now RAISES (msxtest)
    return old, new


# --- T-state accounting -----------------------------------------------------------
# Counting is switched ON when the PC reaches _T["start"] and OFF at _T["stop"]
# (V1: the leaf's entry and the stub's `ret`), or by hand (V2).
_T = {"on": False, "t": 0, "start": None, "stop": None, "hits": None}
_orig_step = Z80.step


def _counting_step(self):
    pc = self.pc
    if pc == _T["start"]:
        _T["on"] = True
    elif pc == _T["stop"]:
        _T["on"] = False
    h = _T["hits"]
    if h is not None and pc in h:
        h[pc] += 1
    if not _T["on"]:
        return _orig_step(self)
    _orig_step(self)
    t, m1 = _timing(self.m, pc, self.pc)
    _T["t"] += t + m1


Z80.step = _counting_step


# --- packed values ------------------------------------------------------------------
def pack(value, nbytes):
    """Canonical packed BCD (what every store makes): [sign|$40+exp][digit pairs]."""
    value = D(value)
    if value == 0:
        return bytes(nbytes)
    t = abs(value).normalize().as_tuple()
    digs = list(t.digits)
    nd = 2 * (nbytes - 1)
    assert len(digs) <= nd, (value, nbytes)
    exp = len(digs) + t.exponent
    assert -63 <= exp <= 63, value
    digs = (digs + [0] * nd)[:nd]
    lead = (0x80 if value < 0 else 0) | (0x40 + exp)
    return bytes([lead] + [digs[i] << 4 | digs[i + 1] for i in range(0, nd, 2)])


def fits(kind, v):
    v = D(v)
    if kind == 2:
        return v == v.to_integral_value() and -32768 <= v <= 32767
    if v == 0:
        return True
    t = abs(v).normalize().as_tuple()
    nd = 6 if kind == 4 else 14
    return len(t.digits) <= nd and -63 <= len(t.digits) + t.exponent <= 63


def decode(fac, typ):
    if fac[0] == 0:
        return D(0)
    n = 7 if typ == 8 else 3
    digs = "".join(f"{x:02X}" for x in fac[1:1 + n])
    v = D(int(digs)).scaleb((fac[0] & 0x7F) - 64 - len(digs))
    return -v if fac[0] & 0x80 else v


# An operand is (type, value): type 2 -> DE = value (FAC is stale junk), 4 / 8 ->
# FAC = pack(value) (DE = junk, as no reader of a float rhs's DE exists).
def operand_bytes(r, op):
    typ, v = op
    junk = bytes(r.randrange(256) for _ in range(8))
    if typ == 2:
        return typ, junk, int(D(v)) & 0xFFFF
    p = pack(v, typ)
    return typ, p + junk[len(p):], r.randrange(0x10000)


# --- the V1 driver -------------------------------------------------------------------
def stub_bytes(s, leaf):
    def w(a):
        return [a & 0xFF, a >> 8]
    code = ([0x3A] + w(STG + 0) + [0x32] + w(s["FACTYP"])
            + [0x21] + w(STG + 1) + [0x11] + w(s["FAC"]) + [0x01, 8, 0, 0xED, 0xB0]
            + [0xED, 0x5B] + w(STG + 9) + [0xCD] + w(s["push_lhs_frame"])
            + [0x3A] + w(STG + 11) + [0x32] + w(s["FACTYP"])
            + [0x21] + w(STG + 12) + [0x11] + w(s["FAC"]) + [0x01, 8, 0, 0xED, 0xB0]
            + [0xED, 0x5B] + w(STG + 20) + [0xED, 0x4B] + w(STG + 22)
            + [0x2A] + w(STG + 24) + [0xCD] + w(s[leaf]) + [0xC9])
    return bytes(code), STUB + len(code) - 1      # (bytes, address of the `ret`)


LEAVES = {"+": "combine_add", "-": "combine_sub", "*": "combine_mul"}


def dead_set(sym):
    """Float scratch the OLD BCD path writes as its own and the new path need not:
    every reader writes it first (grep each name; tests/test_fpdiv_fast.py's DEAD
    is the same argument for four of them)."""
    d = set()
    for k, n in (("ARGA", 18), ("ARGB", 18), ("MULPROD", 28), ("MUL_I", 1), ("MUL_PP", 2),
                 ("WSRC", 2), ("FP_LHSVAL", 2), ("FP_TMP_B", 2), ("FP_RSIGN", 1),
                 ("MUL_ADIG", 1), ("MUL_CARRY", 1)):
        d |= set(range(sym[k], sym[k] + n))
    return d


def cell_names(sym):
    names = {}
    for k, n in (("ARGA", 18), ("ARGB", 18), ("MULPROD", 28)):
        for i in range(n):
            names.setdefault(sym[k] + i, f"{k}+{i}")
    for k in ("FP_SHIFTAMT", "PLF_RA", "PLF_RA2", "MULCAND", "MULTPLR", "MUL32"):
        for i in range(2 if k != "MUL32" else 4):
            names[sym[k] + i] = f"{k}+{i}"
    for k in ("MUL_I", "MUL_PP", "WSRC", "FP_LHSVAL", "FP_TMP_B", "FP_RSIGN", "MUL_ADIG",
              "MUL_CARRY"):
        names[sym[k]] = k
        names.setdefault(sym[k] + 1, k + "+1")
    return names


class Pair:
    def __init__(self):
        self.old, self.new = machines()
        for k in ("FAC", "FACTYP", "FPERR", "ARGA", "MULPROD", "LHS_FAC"):
            assert self.old.sym[k] == self.new.sym[k], k
        self.s = self.new.sym
        self.dead = dead_set(self.s)
        self.seen_dead = set()
        self.stubs = {}
        for m in (self.old, self.new):
            for op, leaf in LEAVES.items():
                self.stubs[(id(m), op)] = stub_bytes(m.sym, leaf)
        ns = self.new.sym
        # fx_tail: the detour was taken; fxt_int: it SUCCEEDED -- the int path's
        # own answer is packed (an overflow leaves fx_tail before it)
        self.fx_ok = ns["fxt_int"]
        self.fast_pcs = {ns["fx_tail"]: 0, self.fx_ok: 0}

    def _ram_diff(self):
        a, b = self.old.mem, self.new.mem
        lo, hi = STACK_BAND
        if a[0x8000:lo] == b[0x8000:lo] and a[hi:] == b[hi:]:
            return []
        # the driver itself differs (it calls each image's own leaf address); and
        # TXTCEIL is LAYOUT, not output: msxtest seeds it with each tree's own TXTMAX,
        # and TXTMAX moved after the old tree (D-BOOTKEYS CTRL RAM, 2026-10-27).
        lay = {self.new.sym["TXTCEIL"], self.new.sym["TXTCEIL"] + 1}
        return [i for i in list(range(0x8000, lo)) + list(range(hi, 0x10000))
                if a[i] != b[i] and not STUB <= i < STG + 32 and i not in lay]

    def run(self, op, lhs, rhs, seed, fperr=0, plant=None):
        """-> (ok, old_state, new_state, detail, t_old, t_new, fast_taken)"""
        r = random.Random(seed)
        junk = bytes(r.randrange(256) for _ in range(JUNK[1] - JUNK[0]))
        lt, lfac, lde = operand_bytes(r, lhs)
        rt, rfac, rde = operand_bytes(r, rhs)
        bc, hl = r.randrange(0x10000), r.randrange(0x10000)
        stg = (bytes([lt]) + lfac + bytes([lde & 0xFF, lde >> 8]) + bytes([rt]) + rfac
               + bytes([rde & 0xFF, rde >> 8, bc & 0xFF, bc >> 8, hl & 0xFF, hl >> 8]))
        out = []
        fast = False
        for m in (self.old, self.new):
            code, ret_at = self.stubs[(id(m), op)]
            m.mem[JUNK[0]:JUNK[1]] = junk
            m.poke(STUB, code)
            m.poke(STG, stg)
            m.poke(m.sym["FPERR"], fperr)
            _T.update(t=0, on=False, start=m.sym[LEAVES[op]], stop=ret_at)
            if m is self.new:
                for k in self.fast_pcs:
                    self.fast_pcs[k] = 0
                _T["hits"] = self.fast_pcs
            cpu = m.call(STUB)
            _T.update(on=False, start=None, stop=None, hits=None)
            if m is self.new:
                fast = bool(self.fast_pcs[self.fx_ok])
                self.tried = bool(self.fast_pcs[self.s["fx_tail"]])
                if plant:
                    plant(m)
            s = m.sym
            st = {"FAC": bytes(m.peek(s["FAC"], 8)), "FACTYP": m.peek(s["FACTYP"])[0],
                  "FPERR": m.peek(s["FPERR"])[0],
                  # DE only: A, F, BC and HL are clobbers in combine_*'s contract
                  # ("Clobbers A, B, C, D, E, H, L"; cl_after's ev_sp reloads A
                  # and F, it sets B and C, and pops HL). D-REREAD batches 3-4
                  # (2026-10-31) left different but dead values there: cmul_int's
                  # sign in C, fp_add's x-x path, domain_convert_core's exits.
                  "regs": (cpu.de,)}
            out.append((st, _T["t"]))
        (so, to), (sn, tn) = out
        diff = self._ram_diff()
        live = [a for a in diff if a not in self.dead]
        self.seen_dead |= set(diff) - set(live)
        if so.get("FPERR") and so.get("FPERR") == sn.get("FPERR"):
            # D-DEFERRSTUDY family 2 (2026-10-28): the SAME fault on both sides, but the
            # new image RAISES it at once (fp_mul_raise) -- no registers come back and
            # VALTYP is the reference's; FAC and FPERR must still agree.
            so = {k: v for k, v in so.items() if k not in ("FACTYP", "regs")}
            sn = {k: v for k, v in sn.items() if k not in ("FACTYP", "regs")}
            live = [x for x in live if x != self.new.sym["FACTYP"]]
        ok = so == sn and not live
        detail = "" if ok else (f"old={so} new={sn} live RAM diffs="
                                f"{[hex(a) for a in live[:12]]}")
        return ok, so, sn, detail, to, tn, fast


def exact16(v):
    v = D(v)
    return v == v.to_integral_value() and -32768 <= v <= 32767


def expect_fast(op, lhs, rhs):
    """The new path must be taken iff both are exact int16 (a float -32768 is not
    taken: nx_pki leaves it to the general path), the rhs is not the int16 $8000,
    and the int answer is in range."""
    (lt, lv), (rt, rv) = lhs, rhs
    if not (exact16(lv) and exact16(rv)):
        return False
    if lt == 2 and rt == 2:
        return None                       # int + int: the unchanged int path
    if (lt != 2 and D(lv) == -32768) or (rt != 2 and D(rv) == -32768):
        return False
    if rt == 2 and D(rv) == -32768:
        return False
    a, b = int(D(lv)), int(D(rv))
    res = a + b if op == "+" else a - b if op == "-" else a * b
    return -32768 <= res <= 32767


# --- corpora ----------------------------------------------------------------------------
HAND = ["0", "1", "-1", "2", "7", "-7", "10", "99", "100", "181", "-181", "255", "256",
        "1000", "4681", "4682", "9999", "10000", "16383", "16384", "-16384", "-16385",
        "32766", "32767", "-32767", "-32768", "32768", "-32769", "40000", "65535",
        "65536", "99999", "100000", "0.5", "-0.5", "1.5", "2.5", "0.1", "-2.25",
        "12345.6", "123456", "1E10", "1E-10", "7.0000001", "32767.5"]


HAND_CORE = ["0", "1", "-1", "7", "181", "4682", "-16384", "32767", "-32768", "32768",
             "1.5", "1E10"]


def hand_cases(values=HAND):
    out = []
    for op in "+-*":
        for a in values:
            for b in values:
                for lt in (2, 4, 8):
                    for rt in (2, 4, 8):
                        if fits(lt, a) and fits(rt, b):
                            out.append((op, (lt, a), (rt, b), 0))
    # the walls, pointed: sums and products that land on / just past +-32767/-32768
    walls = [("+", 32767, 1), ("+", 32766, 1), ("+", -32768, -1), ("+", -32767, -1),
             ("+", 16384, 16384), ("+", 16383, 16384), ("+", -16384, -16384),
             ("+", -16384, -16385), ("-", -32767, 1), ("-", -32767, 2), ("-", 32767, -1),
             ("-", 0, -32768), ("-", 1, -32768), ("-", -1, -32768), ("-", 32767, -32768),
             ("-", 0, 32767), ("-", -1, 32767), ("-", -2, 32767), ("-", 5, 5), ("+", 5, -5),
             ("*", 181, 181), ("*", 182, 180), ("*", 128, 256), ("*", -128, 256),
             ("*", -256, 128), ("*", 255, 129), ("*", -1, -32768), ("*", 1, -32768),
             ("*", -1, 32767), ("*", 2, 16384), ("*", -2, 16384), ("*", 2, -16384),
             ("*", 0, -32768), ("*", 0, 7), ("*", 7, 0), ("*", 4681, 7), ("*", 4682, 7),
             ("*", -4681, 7), ("*", -4682, 7), ("*", 32767, 1), ("*", -32768, 1),
             ("*", 3, -10923), ("*", 3, -10922), ("+", 0, 0), ("-", 0, 0), ("*", 0, 0)]
    for op, a, b in walls:
        for lt in (2, 4, 8):
            for rt in (2, 4, 8):
                out.append((op, (lt, str(a)), (rt, str(b)), 0))
    for f in (1, 2, 6):                      # a pending FPERR survives the leaf
        for op in "+-*":
            out.append((op, (8, "33"), (2, "7"), f))
            out.append((op, (4, "1.5"), (8, "7"), f))
            out.append((op, (8, "30000"), (8, "30000"), f))
    return out


def rnd_value(r):
    c = r.random()
    if c < 0.35:
        return str(r.randint(-99, 99))
    if c < 0.55:
        return str(r.randint(-32768, 32767))
    if c < 0.65:
        return str(r.choice([32767, -32768, -32767, 16384, -16384, 32766, 0, 1, -1]))
    if c < 0.72:
        return str(r.randint(-300, 300))
    if c < 0.80:                              # just past int16, int-valued
        return str(r.choice([1, -1]) * r.randint(32768, 99999))
    if c < 0.92:                              # a fraction
        return str(D(r.randint(-99999, 99999)).scaleb(-r.randint(1, 4)))
    return str(D(r.randint(1, 999999)).scaleb(r.randint(-12, 12)) * r.choice([1, -1]))


def random_cases(seed, n):
    r = random.Random(seed)
    out = []
    while len(out) < n:
        op = r.choice("+-*")
        lt, rt = r.choice((2, 4, 8)), r.choice((2, 4, 8))
        a, b = rnd_value(r), rnd_value(r)
        if op == "*" and r.random() < 0.5:    # products near the walls
            a = str(r.choice([1, -1]) * r.randint(1, 400))
            b = str(r.choice([1, -1]) * r.randint(1, 400))
        if fits(lt, a) and fits(rt, b):
            out.append((op, (lt, a), (rt, b), 0))
    return out


def check(pair, cases, seed0, stats):
    fails = []
    for k, (op, lhs, rhs, fperr) in enumerate(cases):
        ok, so, sn, detail, to, tn, fast = pair.run(op, lhs, rhs, seed0 + k, fperr)
        want = expect_fast(op, lhs, rhs)
        key = ("int" if want is None else "fast" if want else
               "ovf" if exact16(lhs[1]) and exact16(rhs[1]) else "slow")
        st = stats.setdefault(key, [0, 0, 0])
        st[0] += 1
        st[1] += to
        st[2] += tn
        stats["n"] = stats.get("n", 0) + 1
        if not ok:
            fails.append(f"{lhs} {op} {rhs} FPERR0={fperr}: {detail}")
        elif want is not None and fast != want and fperr == 0:
            fails.append(f"P {lhs} {op} {rhs}: fast path {'taken' if fast else 'NOT taken'}"
                         f", expected {'taken' if want else 'not'}")
        elif key == "slow" and pair.tried:
            fails.append(f"P {lhs} {op} {rhs}: a non-exact operand reached the int path")
        if ok and fperr == 0 and want:
            exp = D(int(D(lhs[1])) + int(D(rhs[1])) if op == "+" else
                    int(D(lhs[1])) - int(D(rhs[1])) if op == "-" else
                    int(D(lhs[1])) * int(D(rhs[1])))
            if decode(sn["FAC"], sn["FACTYP"]) != exp or sn["FACTYP"] != 8:
                fails.append(f"V3 {lhs} {op} {rhs}: FAC {sn['FAC'].hex()} is not {exp}")
    return fails


def _worker(args):
    seed, cases = args
    pair = Pair()
    stats = {}
    fails = check(pair, cases if cases else random_cases(seed, 3000), seed * 7919, stats)
    return stats, fails[:20], len(fails), sorted(pair.seen_dead)


def merge(tot, st):
    for k, v in st.items():
        if k == "n":
            tot["n"] = tot.get("n", 0) + v
        else:
            t = tot.setdefault(k, [0, 0, 0])
            for i in range(3):
                t[i] += v[i]


# --- V2: whole programs ------------------------------------------------------------------
class Runner:
    """One image; snapshots at every statement boundary (tests/test_forfast.py's)."""

    def __init__(self, m):
        self.m = m
        m.untrap_raise_now()   # programs RUN: a raise must reach ON ERROR (msxtest)
        s = self.s = m.sym
        self.out = []
        m.trap("BREAKX", lambda mm: setattr(mm.cpu, "f", mm.cpu.f & ~0x01))
        m.trap("CHPUT", lambda mm: self.out.append(mm.cpu.a))
        m.trap("ctl_reset", self._seed_pool)
        for cell, cold in (("CSRX", 1), ("LINLEN", 40)):
            if cell in s:
                m.poke(s[cell], cold)
        # FN_FEND as cold boot's clear_usrtab leaves it (tests/test_forfast.py F4)
        m.poke(s["FN_FEND"], s["FN_PAREA"] & 0xFF)
        self.exec_pc = s["exec_stmt"]
        self.snaps = []
        self.stmt_t = []
        self.timing = False
        cpu = m.cpu
        step = cpu.step

        def hooked():
            if cpu.pc == self.exec_pc:
                if self.timing:
                    self.stmt_t.append(_T["t"])
                self.snaps.append(self.snapshot())
            step()
        cpu.step = hooked

    def _seed_pool(self, m):
        for cell in ("CTLTOP", "CSP", "GSP", "FSP", "TSP"):
            m.poke_w(m.addr(cell), POOL_TOP)
        m.poke_w(m.addr("CTLLIM"), POOL_FLOOR)

    def w(self, a):
        return self.m.mem[a] | self.m.mem[a + 1] << 8

    def snapshot(self):
        s, mem = self.s, self.m.mem
        lo, hi = self.w(VARTAB), self.w(STREND)
        return (self.w(s["CURLINE"]), self.w(s["CSP"]), mem[s["FACTYP"]], mem[s["FPERR"]],
                bytes(mem[s["FAC"]:s["FAC"] + 8]),
                bytes(mem[lo:hi]) if lo <= hi else b"?")

    def run(self, lines):
        m, s = self.m, self.s
        self.out.clear()
        self.snaps = []
        self.stmt_t = []
        self._seed_pool(m)
        m.call("new_prog")
        for lineno, body in lines:
            m.poke(SRC, body.encode("ascii") + b"\x00")
            m.mem[TOKB:TOKB + 192] = b"\x00" * 192
            m.call("tokenise", hl=SRC, de=TOKB)
            m.poke_w(s["SL_CEIL"], s["TXTMAX"])
            m.call("store_line", bc=lineno, hl=TOKB)
        _T.update(t=0, on=self.timing)
        m.call("run_prog", max_steps=30_000_000)
        _T["on"] = False
        self.snaps.append(self.snapshot())
        return bytes(self.out).decode("latin-1")


def prog(text):
    rows = []
    for ln in text.strip().splitlines():
        n, _, body = ln.strip().partition(" ")
        rows.append((int(n), body))
    return rows


TYPES = ["", "%", "!", "#"]
VALS = ["0", "1", "-1", "5", "33", "181", "4681", "4682", "16384", "-16384", "32767",
        "-32767", "-32768", "1.5", "-2.5", "40000", "1E10", ".001"]


def v2_program(ti, tj, ta, vi, vj, pre="REM"):
    I, J, A = "I" + ti, "J" + tj, "A" + ta
    return prog(f"""
        5 {pre}
        6 ON ERROR GOTO 900
        10 {I}={vi}:{J}={vj}:I#={vi}:J#={vj}
        20 {A}={I}+7:B={A}-{I}:C={I}*7+{J}-3:D={I}-{J}:E=1.5+{I}:F#={I}*{J}
        30 G={I}*7:H=7*{I}:K={I}+7!:L={I}*7#:M=7%-{J}:N={J}-&H8000:O={I}*{J}+{J}*{I}
        40 A#=I#*J#:P=I#-J#:Q=-{I}*-{J}:R={I}*0:S={I}-{I}
        50 PRINT {A};B;C;D;E;F#;G;H;K;L;M;N;O;A#;P;Q;R;S
        60 END
        900 PRINT "E";ERR;ERL:RESUME NEXT
    """)


def v2_corpus(r, n, vals=VALS):
    out = []
    for pre in ("REM", "DEFINT A-Z", "DEFSNG A-Z", "DEFDBL A-Z"):
        for ti in TYPES:
            for tj in TYPES:
                for ta in TYPES:
                    out.append((pre, ti, tj, ta))
    progs = []
    for _ in range(n):
        pre, ti, tj, ta = r.choice(out)
        progs.append((f"{pre}|I{ti} J{tj} A{ta}", v2_program(ti, tj, ta, r.choice(VALS),
                                                              r.choice(VALS), pre)))
    for vi in vals:                           # each value once, default types
        progs.append((f"vals I={vi}", v2_program("", "", "", vi, "3")))
    progs += [("loop A=I+7", prog("10 FOR I=1 TO 40:A=I+7:NEXT:PRINT A;I")),
              ("loop A=I*7", prog("10 FOR I=1 TO 40:A=I*7:NEXT:PRINT A;I")),
              ("loop chain", prog("10 FOR I=-5 TO 40:J=I*2:A=I*7+J-3:B=A-I:NEXT:PRINT A;B;J")),
              ("loop big", prog("10 FOR I=4670 TO 4690:A=I*7:B=A+A:NEXT:PRINT A;B")),
              ("loop wall", prog("10 FOR I=32760 TO 32767:A=I+1:B=-I-1:C=B-1:NEXT:PRINT A;B;C")),
              ("loop sgl", prog("10 FOR I!=1 TO 20:A!=I!*3:B#=A!-I!:NEXT:PRINT A!;B#")),
              ("loop frac", prog("10 FOR I=0 TO 3 STEP .5:A=I+7:B=I*2:NEXT:PRINT A;B")),
              # a string operand where a number belongs (Type mismatch, resumed).
              # `:G=0` keeps every RESUME NEXT on line 20: since D-RESNEXTDIRECT an
              # end-of-line resume steps through the run loop (one empty statement,
              # as the VG-8020's TRON shows), which the old image does not, and this
              # case is about the arithmetic, not RESUME.
              ("string operand", prog("""
                  10 ON ERROR GOTO 900
                  20 I=5:A=I+"X":B="X"*I:C=I-"7":D=7*"Y":E=I#*"Z":F=I%+"Q":G=0
                  30 PRINT A;B;C;D;E;F:END
                  900 PRINT "E";ERR;ERL:RESUME NEXT
              """)),
              # arrays, and a NEXT that bails off the fast NEXT into combine_add
              ("array/next", prog("""
                  10 DIM V(5):FOR I=1 TO 5:V(I)=I*3:NEXT
                  20 FOR I=1 TO 9:A=I*7+V(I MOD 5):IF I=4 THEN I=I+.5
                  30 NEXT:PRINT A;I;V(3)
              """))]
    return progs


def v2_check(old, new, corpus):
    bad = []
    for label, lines in corpus:
        oo = old.run(lines)
        on = new.run(lines)
        if oo != on or old.snaps != new.snaps:
            if oo != on:
                bad.append(f"{label}: output old={oo!r} new={on!r}")
            else:
                k = next((i for i, (a, b) in enumerate(zip(old.snaps, new.snaps)) if a != b),
                         min(len(old.snaps), len(new.snaps)))
                bad.append(f"{label}: snap #{k}/{len(old.snaps)},{len(new.snaps)} old="
                           f"{old.snaps[k] if k < len(old.snaps) else None} new="
                           f"{new.snaps[k] if k < len(new.snaps) else None}")
    return bad


def _v2_worker(corpus):
    pair = Pair()
    return v2_check(Runner(pair.old), Runner(pair.new), corpus)


def stmt_time(runner, setup, stmt):
    """Host T of ONE statement: `10 <setup>` then `20 <stmt>`; the boundaries are
    exec_stmt arrivals, so this is the statement's whole cost (dispatch included)."""
    runner.timing = True
    runner.run(prog(f"10 {setup}\n20 {stmt}\n30 END"))
    runner.timing = False
    ts, lines = runner.stmt_t, [sn[0] for sn in runner.snaps]
    # exec_stmt is reached more than once a statement; a LINE's cost is from the
    # first arrival with its CURLINE to the first arrival with the next one
    first = [i for i in range(len(ts)) if i == 0 or lines[i] != lines[i - 1]]
    return ts[first[2]] - ts[first[1]]


# --- run --------------------------------------------------------------------------------
def run():
    build()
    full = os.environ.get("INTFAST_FULL") == "1"
    nrand = 120000 if full else int(os.environ.get("INTFAST_RANDOM", "1500"))
    pair = Pair()
    fails = 0

    def report(label, n, bad, extra=""):
        nonlocal fails
        fails += len(bad)
        print(f"{'PASS' if not bad else 'FAIL'}  {label}: {n - len(bad)}/{n} identical{extra}")
        for b in bad[:12]:
            print(f"      {b}")

    # ------------------------------------------------------------------ K
    print("# --- K: knives -- a planted difference is reported ---")
    s0 = pair.s
    knives = [("register E", lambda m: setattr(m.cpu, "e", m.cpu.e ^ 1)),  # was C:
              # BC left the compared set (D-REREAD batch 3) -- DE is the result
              ("register D", lambda m: setattr(m.cpu, "d", m.cpu.d ^ 1)),  # was the flag byte: F left the compared set
              ("FAC+7", lambda m: m.poke(s0["FAC"] + 7, m.peek(s0["FAC"] + 7)[0] ^ 1)),
              ("FACTYP", lambda m: m.poke(s0["FACTYP"], 2)),
              ("CVT_MODE", lambda m: m.poke(s0["CVT_MODE"], m.peek(s0["CVT_MODE"])[0] ^ 1)),
              ("FP_OPMODE", lambda m: m.poke(s0["FP_OPMODE"], m.peek(s0["FP_OPMODE"])[0] ^ 1))]
    for label, plant in knives:
        ok = pair.run("+", (8, "33"), (2, "7"), 3, plant=plant)[0]
        fails += ok
        print(f"{'PASS' if not ok else 'FAIL'}  knife {label}: "
              f"{'reported' if not ok else 'NOT SEEN -- the differential is blind'}")
    pair.seen_dead.clear()

    # ------------------------------------------------------------------ V1 / P
    print("# --- V1/P: combine_add / combine_sub / combine_mul, old image vs new ---")
    tot = {}
    seen = set()
    if full:
        hc = hand_cases(HAND)
        rc = random_cases(5000, nrand)
        jobs = [(1000 + i, hc[i::40]) for i in range(40)] + \
               [(5000 + i, rc[i::40]) for i in range(40)]
        with multiprocessing.Pool(min(10, os.cpu_count() or 1)) as pool:
            res = pool.map(_worker, jobs)
        for (label, part) in (("hand values x every type pairing x + - *", res[:40]),
                              ("random corpus", res[40:])):
            st, bad, nbad = {}, [], 0
            for s_, f_, nf, sd in part:
                merge(st, s_)
                bad += f_
                nbad += nf
                seen |= set(sd)
            merge(tot, st)
            fails += nbad
            print(f"{'PASS' if not nbad else 'FAIL'}  {label}: {st['n'] - nbad}/{st['n']} identical")
            for b in bad[:12]:
                print(f"      {b}")
    else:
        for label, cases, seed in (("hand values x every type pairing x + - *",
                                    hand_cases(HAND_CORE), 1000),
                                   ("random corpus", random_cases(5000, nrand), 50000)):
            st = {}
            bad = check(pair, cases, seed, st)
            merge(tot, st)
            report(label, st["n"], bad)
        seen |= pair.seen_dead
    for key, what in (("fast", "both exact int16, answer in range: the NEW path"),
                      ("ovf", "both exact int16, answer past int16 (or rhs $8000)"),
                      ("slow", "a fraction / a value past int16: the float path"),
                      ("int", "int16 op int16: the int path")):
        if key in tot:
            n, to, tn = tot[key]
            print(f"      {what:52} {n:7d} cases, mean leaf T old {to / n:7.0f} "
                  f"new {tn / n:7.0f} ({tn / n - to / n:+6.0f})")
    names = cell_names(s0)
    print("      RAM that differed, all inside the declared float scratch: "
          f"{', '.join(sorted({names.get(a, hex(a)).split('+')[0] for a in seen}))}")
    if tot.get("fast", [0, 1, 0])[2] >= tot.get("fast", [0, 1, 0])[1]:
        fails += 1
        print("FAIL  the new path is not cheaper on its own cases")

    # ------------------------------------------------------------------ V2
    print("# --- V2: whole statements through the interpreter, old vs new ---")
    old, new = Runner(pair.old), Runner(pair.new)
    if full:
        corpus = v2_corpus(random.Random(20261020), 400)
        with multiprocessing.Pool(min(10, os.cpu_count() or 1)) as pool:
            res = pool.map(_v2_worker, [corpus[i::20] for i in range(20)])
        bad = [b for part in res for b in part]
    else:
        corpus = v2_corpus(random.Random(20261020), 4,
                           ["0", "-1", "33", "4682", "-32768", "1.5", "40000"])
        bad = v2_check(old, new, corpus)
    report("programs (I/J/A of every type and DEF, int16 walls, fractions, loops)",
           len(corpus), bad)

    # ------------------------------------------------------------------ T
    print("# --- T: host T-states of one statement (dispatch, lookups, store included) ---")
    setup = "I=33:J=12:I#=33:J#=12:A=1"
    rows = ["A=I+7", "A=I*7", "A=I-J", "A=1.5+I", "A#=I#*J#", "A=I+7.5", "A%=I%+7",
            "A=I*7+J-3", "A=I*4682"]
    print(f"      {'statement (I=33, J=12)':24} {'old':>8} {'new':>8}")
    for stmt in rows:
        to, tn = stmt_time(old, setup + ":I%=33", stmt), stmt_time(new, setup + ":I%=33", stmt)
        print(f"      {stmt:24} {to:8d} {tn:8d}  {tn - to:+7d}")
    print(f"\n{'ALL PASS' if not fails else f'{fails} FAILED'}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(run())
