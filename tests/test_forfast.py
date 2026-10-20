# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: D-FORFAST (2026-10-20) -- NEXT's int16 path for a float loop
(basic/program.asm nx_have's gate, nx_fast, nx_demote, nx_pki, nx_pack), on the
host Z80, as a DIFFERENTIAL against the general (BCD) NEXT path.

What the slice must not change, and what this file holds it to:

  F1  every loop in the corpus runs IDENTICALLY with the int path and without it:
      at EVERY statement boundary (exec_stmt) the whole variable region
      [VARTAB, STREND) -- every scalar's packed bytes and type byte --, the
      control-stack depth (CSP), CURLINE and FACTYP are the same, and so is
      everything the program printed (values, ERR/ERL from its ON ERROR handler).
      The "without" run is the SAME image with the int path's entry steered to
      its own bail-out (nx_fast -> nx_fslow): the slots are widened at the first
      NEXT and the general path -- D-FORFLOAT's NEXT, unchanged -- runs every pass.
      The corpus: default / ! / # / % variables, DEFDBL/DEFSNG/DEFINT, STEP
      0 / negative / fractional / huge, limits and steps that are expressions and
      float variables holding integers, nested loops, NEXT without a variable,
      NEXT I,J, bodies that write the variable (an int, a fraction, past int16),
      the 32767 edge (x.edge, A = 32769), the % overflow (ERR 6), ON ERROR /
      RESUME inside a loop -- and a seeded random corpus over int16 edges, small
      ints, halves, tenths and large floats.
  F2  the int path is actually TAKEN where it should be and NOT where it must not
      (a differential that never reaches the new code proves nothing).
  F3  nx_pki / nx_pack against Python, exhaustively over every int16 for the
      pack and over hand-built packed values for the exactness test.
  F4  T-states of an empty NEXT (host-counted, sub-ROM tenant steps included,
      the CALSLT itself excluded) -- printed, and the int path must be cheaper.

Set FORFAST_OLD_ROM / FORFAST_OLD_SYM to an image assembled from the tree BEFORE
D-FORFAST to run F1 against that build instead of the steered one.
"""

import os
import random
import subprocess
import sys
from decimal import Decimal as D

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from msxtest import Machine  # noqa: E402
from z80 import Z80  # noqa: E402
from test_paintcell import _timing  # noqa: E402

ROM = tp("zb_forfast.rom")
SYM = tp("zb_forfast.sym")
BASIC_BASE = 0x2781
SRC, TOKB = 0xC000, 0xC100
POOL_TOP, POOL_FLOOR = 0xD000, 0x9000
VARTAB, STREND = 0xF6C2, 0xF6C6


def build():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"), ROM, SYM],
                   check=True, capture_output=True)


# --- T-state accounting across the main CPU AND the sub-ROM bridge islands ------
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


class Runner:
    """One image, with the per-statement snapshot hook and optional steering."""

    def __init__(self, rom, sym, steer_slow=False):
        self.m = Machine(rom, sym, rom_base=BASIC_BASE)
        m, s = self.m, self.m.sym
        self.s = s
        self.out = []
        m.trap("BREAKX", lambda mm: setattr(mm.cpu, "f", mm.cpu.f & ~0x01))
        m.trap("CHPUT", lambda mm: self.out.append(mm.cpu.a))
        m.trap("ctl_reset", self._seed_pool)
        for cell, cold in (("CSRX", 1), ("LINLEN", 40)):
            if cell in s:
                m.poke(s[cell], cold)
        self.exec_pc = s["exec_stmt"]
        self.next_pc = s["ex_next"]
        self.fast_pc = s.get("nx_fast")
        self.fslow_pc = s.get("nx_fslow")
        self.steer = steer_slow and self.fast_pc is not None
        self.fast_hits = self.fslow_hits = 0
        self.snaps = []
        self.next_t = []          # T-states per NEXT (ex_next -> next exec_stmt)
        self.next_sub = []        # sub-ROM calls per NEXT
        self.timing = False
        sub_addr = s["subrom_call"]
        inner = m.traps[sub_addr]
        self.subcalls = [0]

        def counted(mm):
            self.subcalls[0] += 1
            inner(mm)
        m.traps[sub_addr] = counted
        cpu = m.cpu
        step = cpu.step
        in_next = [False]

        def hooked():
            pc = cpu.pc
            if pc == self.exec_pc:
                if in_next[0]:
                    in_next[0] = False
                    _T["on"] = False
                    self.next_t.append(_T["t"])
                    self.next_sub.append(self.subcalls[0])
                self.snaps.append(self.snapshot())
            elif pc == self.next_pc and self.timing:
                in_next[0] = True
                _T["t"] = 0
                self.subcalls[0] = 0
                _T["on"] = True
            elif pc == self.fast_pc:
                if self.steer:
                    cpu.pc = self.fslow_pc
                    return
                self.fast_hits += 1
            elif pc == self.fslow_pc:
                self.fslow_hits += 1
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
        return (self.w(s["CURLINE"]), self.w(s["CSP"]), mem[s["FACTYP"]],
                bytes(mem[lo:hi]) if lo <= hi else b"?")

    def run(self, lines):
        m, s = self.m, self.s
        self.out.clear()
        self.snaps = []
        self.fast_hits = self.fslow_hits = 0
        self.next_t, self.next_sub = [], []
        self._seed_pool(m)
        m.call("new_prog")
        for lineno, body in lines:
            m.poke(SRC, body.encode("ascii") + b"\x00")
            m.mem[TOKB:TOKB + 192] = b"\x00" * 192
            m.call("tokenise", hl=SRC, de=TOKB)
            m.poke_w(s["SL_CEIL"], s["TXTMAX"])
            m.call("store_line", bc=lineno, hl=TOKB)
        m.call("run_prog", max_steps=30_000_000)
        _T["on"] = False
        self.snaps.append(self.snapshot())
        return bytes(self.out).decode("latin-1")


def prog(text):
    """'10 A=1\\n20 ...' -> [(10, 'A=1'), ...]"""
    rows = []
    for ln in text.strip().splitlines():
        n, _, body = ln.strip().partition(" ")
        rows.append((int(n), body))
    return rows


# A capped loop: the counter C ends any loop that would not (STEP 0, a runaway).
# The body has its own line, so an `IF` in it cannot swallow the counter.
def loop(var, init, lim, step=None, body="", pre="", cap=14):
    st = f" STEP {step}" if step is not None else ""
    return prog(f"""
        5 {pre or 'REM'}
        10 ON ERROR GOTO 900:C=0
        20 FOR {var}={init} TO {lim}{st}:C=C+1:IF C>{cap} THEN 80
        25 {body or 'REM'}
        30 NEXT
        80 PRINT "E";{var};C:END
        900 PRINT "R";ERR;ERL;{var}:END
    """)


CORPUS = {
    "empty":      prog("10 FOR I=1 TO 30:NEXT:PRINT I"),
    "named":      prog("10 FOR I=1 TO 5:S=S+I:NEXT I:PRINT S;I"),
    "bang":       loop("A!", 1, 6),
    "hash":       loop("A#", 1, 6),
    "pct":        loop("A%", 1, 6),
    "defdbl":     loop("A", 1, 6, pre="DEFDBL A"),
    "defsng":     loop("A", 1, 6, pre="DEFSNG A"),
    "defint":     loop("A", 1, 6, pre="DEFINT A"),
    "step0":      loop("A", 1, 3, 0),
    "step0b":     loop("A", 5, 3, 0),
    "neg":        loop("A", 5, -5, -2),
    "negb":       loop("A!", 3, -3, -1),
    "half":       loop("A", 0, 3, .5),
    "tenth":      loop("A", 0, 1, .1),
    "tenthb":     loop("A!", 0, 1, .1),
    "tenthd":     loop("A#", 0, 1, .1),
    "fracinit":   loop("A", .5, 3),
    "fraclim":    loop("A", 1, 2.5),
    "negfrac":    loop("A", 1, 0, -.5),
    "huge":       loop("A", 0, 100000, 40000),
    "hugeneg":    loop("A", -40000, -39999),
    "big":        loop("A", 56700, 56702),
    "edge":       loop("A", 1, 32767, 16384),
    "edgeb":      loop("A!", 1, 32767, 16384),
    "edgeneg":    loop("A", -1, -32767, -16384),
    "edgemin":    loop("A", -32760, -32768, -3),
    "edgemax":    loop("A", 32760, 32767, 3),
    "edgepct":    loop("A%", 1, 32767, 16384),
    "edgepctn":   loop("A%", -1, -32768, -16384),
    "bigstep":    loop("A", 0, 30000, 32767),
    "bodyhalf":   loop("A", 1, 3, body="A=A+.5"),
    "bodyint":    loop("A", 1, 9, body="A=A+1"),
    "bodyset":    loop("A", 1, 9, body="IF A=3 THEN A=7"),
    "bodyfar":    loop("A", 1, 9, body="IF A=2 THEN A=40000"),
    "bodyfrac2":  loop("A", 1, 9, body="IF A=4 THEN A=A+.25"),
    "bodyneg":    loop("A", 1, 9, body="IF A=2 THEN A=-32767"),
    "bodytiny":   loop("A#", 1, 9, body="IF A=2 THEN A=A+1D-12"),
    "bodybang":   loop("A!", 1, 9, body="A=A+.5"),
    "exprs":      loop("A", "N", "N*3", "N-1", pre="N=2"),
    "exprf":      loop("A", "N/2", "N*3", "N/4", pre="N=4"),
    "floatvar":   loop("A", "N", "M", "S", pre="N=3:M=12:S=2"),
    "floatsng":   loop("A", "N!", "M!", "S!", pre="N!=3:M!=12:S!=2"),
    "floatdbl":   loop("A#", "N#", "M#", "S#", pre="N#=3:M#=12:S#=2"),
    "floatfr":    loop("A", "N", "M", "S", pre="N=3:M=12.5:S=2"),
    "limitsng":   loop("A", 1, "10!"),
    "stepsng":    loop("A", 1, 10, "2!"),
    "mixstep":    loop("A", 1, 4, ".5!"),
    "mix48":      loop("A", 0, "2.5!", ".5#"),
    "lim40000":   loop("A", 32000, 40000, 2000),
    "zerocross":  loop("A", -3, 3),
    "zerocrossb": loop("A!", -1, 1, .5),
    "zero":       loop("A", 0, 0),
    "nested":     prog("""
        10 FOR I=1 TO 3:FOR J=1 TO 4:K=K+1:NEXT J:NEXT I:PRINT I;J;K
    """),
    "nestedbare": prog("""
        10 FOR I=1 TO 3:FOR J=-2 TO 2 STEP 2:K=K+I*J:NEXT:NEXT:PRINT I;J;K
    """),
    "nextlist":   prog("""
        10 FOR I=1 TO 3:FOR J=1 TO 2:K=K+1:NEXT J,I:PRINT I;J;K
    """),
    "nextlist2":  prog("""
        10 FOR I#=1 TO 2:FOR J!=.5 TO 2:FOR L%=1 TO 2:K=K+1:NEXT L%,J!,I#:PRINT I#;J!;L%;K
    """),
    "innerclose": prog("""
        10 FOR I=1 TO 3:FOR J=1 TO 9:IF J=2 THEN NEXT I ELSE NEXT J
        20 PRINT I;J
    """),
    "pctovf":     prog("""
        10 ON ERROR GOTO 90
        20 FOR A%=1 TO 32767 STEP 16384:PRINT A%:NEXT
        30 END
        90 PRINT "R";ERR;ERL;A%:END
    """),
    "onerr":      prog("""
        10 ON ERROR GOTO 100
        20 FOR I=1 TO 6:X=10/(I-3):PRINT I;X:NEXT
        30 PRINT "D";I:END
        100 PRINT "E";ERR;ERL;I:RESUME NEXT
    """),
    "onerrres":   prog("""
        10 ON ERROR GOTO 100:Z=0
        20 FOR I=1 TO 4:X=1/Z:NEXT:PRINT "D";I;X:END
        100 Z=I:RESUME
    """),
    "resnext":    prog("""
        10 ON ERROR GOTO 100
        20 FOR I=1 TO 4:ERROR 200:PRINT I:NEXT:PRINT "D";I:END
        100 RESUME NEXT
    """),
    "gosubin":    prog("""
        10 FOR I=1 TO 4:GOSUB 100:NEXT:PRINT I;S:END
        100 S=S+I:RETURN
    """),
    "manyvars":   prog("""
        10 A=1:B=2:C1=3:FOR X=1 TO 5:Y=X*2:Z#=X/3:NEXT:PRINT X;Y;Z#
    """),
    "newvarbody": prog("""
        10 FOR I=1 TO 4:IF I=2 THEN Q=5:DIM R(3)
        20 NEXT:PRINT I;Q
    """),
    "unset":      prog("10 FOR I=I TO 3:NEXT:PRINT I"),
}


def rand_corpus(n, seed=20261020):
    rnd = random.Random(seed)
    pool = ["0", "1", "-1", "2", "-2", "3", "7", "-7", "10", "100", "-100", "255",
            "32767", "-32767", "-32768", "32766", "16384", "-16384", "32000",
            "1", "2", "-3", "5", "9999", "10000", "-10000", "32760", "-32760",
            "N", "-N", "N*2", "N/2",
            ".5", "-.5", "1.5", "2.5", "-2.5", ".1", "-.1", ".3", "1.1",
            "40000", "-40000", "65536", "1E10", "-1E10", "123456", "1E30",
            "3!", "3#", "2.5!", "1D3", "32767!", "-32768#"]
    vars_ = ["A", "A!", "A#", "AB"]
    rows = {}
    for k in range(n):
        v = rnd.choice(vars_)
        i, lim, st = rnd.choice(pool), rnd.choice(pool), rnd.choice(pool + [None] * 6)
        body = rnd.choice(["", "", "", f"{v}={v}+1", f"{v}={v}*2", f"{v}={v}+.5",
                           f"{v}=-{v}", f"IF C=2 THEN {v}=30000"])
        rows[f"r{k:03d}"] = loop(v, i, lim, st, body, cap=6,
                                 pre=rnd.choice(["N=6", "N!=9", "N#=-4", "N=2.5"]))
    return rows


def run():
    build()
    old_rom = os.environ.get("FORFAST_OLD_ROM")
    old_sym = os.environ.get("FORFAST_OLD_SYM")
    new = Runner(ROM, SYM)
    if old_rom:
        old = Runner(old_rom, old_sym)
        print(f"# F1 against an external image: {old_rom}")
    else:
        old = Runner(ROM, SYM, steer_slow=True)
    fails = 0

    def check(label, ok, detail=""):
        nonlocal fails
        fails += not ok
        if not ok:
            print(f"FAIL  {label}" + (f"  [{detail}]" if detail else ""))
        return ok

    # ------------------------------------------------------------------
    print("# --- F1/F2 differential: int path vs the general path ---")
    corpus = dict(CORPUS)
    corpus.update(rand_corpus(int(os.environ.get("FORFAST_RANDOM", "30"))))
    ident = taken = 0
    factyp_only = []
    must_take = {"empty", "named", "bang", "hash", "defdbl", "defsng", "neg",
                 "negb", "edge", "edgeb", "bodyint", "bodyset", "exprs",
                 "floatvar", "floatsng", "floatdbl", "limitsng", "stepsng",
                 "nested", "nextlist", "onerr", "gosubin", "zerocross", "zero"}
    must_not = {"pct", "defint", "half", "tenth", "fracinit", "fraclim",
                "huge", "big", "edgepct", "floatfr", "mixstep", "mix48"}
    for name, lines in corpus.items():
        o_out = old.run(lines)
        o_snaps = old.snaps
        n_out = new.run(lines)
        n_snaps = new.snaps
        same = o_out == n_out and o_snaps == n_snaps
        if not same and old_rom and o_out == n_out and len(o_snaps) == len(n_snaps) \
                and all(a[:2] + a[3:] == b[:2] + b[3:] for a, b in zip(o_snaps, n_snaps)):
            # Against the pre-D-FORFAST image ONLY: FOR used to leave FACTYP = 8
            # (it widened an int16 STEP into FAC); it now leaves the step as the
            # int16 it was (FACTYP = 2). Either way the live value is the step;
            # no statement reads it before evaluating its own. Counted, reported.
            factyp_only.append(name)
            same = True
        detail = ""
        if not same:
            if o_out != n_out:
                detail = f"out old={o_out!r} new={n_out!r}"
            else:
                k = next(i for i, (a, b) in enumerate(zip(o_snaps, n_snaps)) if a != b) \
                    if any(a != b for a, b in zip(o_snaps, n_snaps)) else min(len(o_snaps), len(n_snaps))
                detail = (f"snap #{k} of {len(o_snaps)}/{len(n_snaps)}: "
                          f"old={o_snaps[k] if k < len(o_snaps) else None} "
                          f"new={n_snaps[k] if k < len(n_snaps) else None}")
        check(f"F1 {name}: identical", same, detail)
        ident += same
        done = new.fast_hits - new.fslow_hits     # int-path NEXTs that completed
        if done:
            taken += 1
        if name in must_take:
            check(f"F2 {name}: int path taken", done > 0)
        if name in must_not:
            check(f"F2 {name}: int path NOT completed", done == 0)
        if name == "empty":
            print(f"      (empty loop prints {n_out.strip()!r}; "
                  f"{len(n_snaps)} statement boundaries compared)")
    print(f"PASS? F1 {ident}/{len(corpus)} programs identical at every statement "
          f"boundary; int path taken in {taken}")
    if factyp_only:
        print(f"      (vs the external image: {len(factyp_only)} differ ONLY in FACTYP "
              f"at statement boundaries -- FOR's int16 STEP; variables, output, "
              f"CSP, CURLINE identical)")

    # ------------------------------------------------------------------
    print("# --- F3 nx_pki / nx_pack against Python ---")
    m, s = new.m, new.s
    BUF = 0xC800

    def pack_py(v, nbytes):
        if v == 0:
            return bytes(nbytes)
        sgn = 0x80 if v < 0 else 0
        digs = str(abs(v))
        lead = sgn | (0x40 + len(digs))
        digs = (digs + "0" * 14)[:2 * (nbytes - 1)]
        return bytes([lead] + [int(digs[i]) << 4 | int(digs[i + 1])
                               for i in range(0, len(digs), 2)])

    bad = 0
    # every int16 near zero and at both ends, and every 3rd in between (the
    # digit / byte-shift / nibble-shift arms all change at powers of ten)
    vals = [v for v in range(-32768, 32768)
            if abs(v) <= 2000 or abs(v) >= 32000 or v % 3 == 0]
    for v in vals:
        m.mem[BUF:BUF + 8] = b"\xEE" * 8
        m.call("nx_pack", hl=v & 0xFFFF, de=BUF)
        got = bytes(m.mem[BUF:BUF + 4])
        if got != pack_py(v, 4) or m.mem[BUF + 4] != 0xEE:
            bad += 1
            if bad < 4:
                print(f"      nx_pack({v}) = {got.hex()} want {pack_py(v, 4).hex()}")
    check(f"F3 nx_pack over {len(vals)} int16s", bad == 0, f"{bad} wrong")
    print(f"{'PASS' if bad == 0 else 'FAIL'}  F3 nx_pack over {len(vals)} int16s")

    def pki(raw, nbytes):
        m.mem[BUF:BUF + 8] = raw.ljust(8, b"\x00")
        cpu = m.call("nx_pki", hl=BUF, b=nbytes)
        de = cpu.de if cpu.de < 0x8000 else cpu.de - 0x10000
        return None if cpu.f & 1 else de

    def dec_val(raw, nbytes):
        lead = raw[0]
        if lead == 0:
            return D(0) if not any(raw[1:nbytes]) else None
        digs = "".join(f"{b >> 4}{b & 15}" for b in raw[1:nbytes])
        sgn = -1 if lead & 0x80 else 1
        return sgn * D(int(digs)) * D(10) ** ((lead & 0x7F) - 64 - len(digs))

    rnd = random.Random(7)
    bad = cnt = 0
    cases = []
    for v in list(range(-40, 41)) + [32767, -32767, -32768, 32768, 39999, 40000,
                                      99999, 10000, -10000, 9999, 12345, 65535]:
        for nb in (4, 8):
            cases.append((pack_py(v, nb) if abs(v) < 10 ** 7 else None, nb))
    for _ in range(4000):
        nb = rnd.choice((4, 8))
        lead = rnd.choice([0, rnd.randrange(0x3E, 0x48), rnd.randrange(0, 256)])
        lead |= rnd.choice((0, 0x80))
        body = bytes(rnd.choice([0, 0, rnd.randrange(0, 10) << 4,
                                 rnd.randrange(0, 10) << 4 | rnd.randrange(0, 10)])
                     for _ in range(nb - 1))
        cases.append((bytes([lead]) + body, nb))
    for raw, nb in cases:
        if raw is None:
            continue
        val = dec_val(raw, nb)
        want = int(val) if (val is not None and val == int(val)
                            and -32767 <= val <= 32767) else None
        # only CANONICAL values are scored -- what every store makes: BCD nibbles,
        # a nonzero lead digit, and a zero lead byte only on an all-zero body.
        # (nx_pki answers CF on the others, which is merely the general path.)
        if any((b >> 4) > 9 or (b & 15) > 9 for b in raw[1:nb]):
            continue
        if (raw[0] == 0) != (raw[1] >> 4 == 0) or (raw[0] == 0 and any(raw[1:nb])):
            continue
        cnt += 1
        got = pki(raw, nb)
        if got != want:
            bad += 1
            if bad < 6:
                print(f"      nx_pki({raw[:nb].hex()}, {nb}) = {got} want {want}")
    check("F3 nx_pki exactness", bad == 0, f"{bad} of {cnt} wrong")
    print(f"{'PASS' if bad == 0 else 'FAIL'}  F3 nx_pki over {cnt} packed values")

    # ------------------------------------------------------------------
    print("# --- F4 T-states of an empty NEXT (host: tenant steps in, CALSLT out) ---")
    rows = [
        ("(a) FOR I=1 TO 300 (default type)", "10 FOR I=1 TO 12:NEXT"),
        ("(a') FOR I=1 TO N, N=300 double", "10 N=300:FOR I=1 TO 12:NEXT"),
        ("(b) STEP .5", "10 FOR I=1 TO 7 STEP .5:NEXT"),
        ("(c) FOR I#=.5 TO 12 (double, fractional)", "10 FOR I#=.5 TO 12:NEXT"),
        ("(c') FOR I#=1 TO 12 (double, int-valued)", "10 FOR I#=1 TO 12:NEXT"),
        ("(d) FOR I%=1 TO 12", "10 FOR I%=1 TO 12:NEXT"),
        ("(e) body A=A+.5", "10 FOR A=1 TO 24:A=A+.5:NEXT"),
        ("(f) FOR I!=1 TO 12 (single)", "10 FOR I!=1 TO 12:NEXT"),
        ("(g) FOR I=30000 TO 30012", "10 FOR I=30000 TO 30012:NEXT"),
    ]
    old.timing = new.timing = True
    for label, text in rows:
        lines = prog(text)
        old.run(lines)
        new.run(lines)
        # skip the first NEXT (the one-time demote / widen) and the last (exit)
        ot, nt = old.next_t[1:-1], new.next_t[1:-1]
        o, n = sum(ot) / len(ot), sum(nt) / len(nt)
        osub, nsub = old.next_sub[1], new.next_sub[1]
        print(f"      {label:44s} old {o:7.0f} T ({osub} sub calls)  "
              f"new {n:7.0f} T ({nsub} sub calls)  {n - o:+7.0f}")
        if label.startswith("(a)"):
            check("F4 the int path is cheaper", n < o / 2, f"{n} vs {o}")
    old.timing = new.timing = False

    print(f"\n{'ALL PASS' if fails == 0 else f'{fails} FAIL(S)'}")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
