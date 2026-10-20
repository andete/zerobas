# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""Unit test: D-FORINT (2026-10-20) -- NEXT's int16 arm for a `%` loop
(basic/program.asm nx_fast's `%` arm nx_fint / nx_fput, and the `%` guard that
moved from nx_have into nx_demote), on the host Z80, as a DIFFERENTIAL against the
image built from the tree BEFORE the slice (git BASE_SHA, main and sub-ROM both).

  I1  every program in the corpus runs IDENTICALLY on the old image and the new:
      at EVERY statement boundary (exec_stmt) the whole variable region
      [VARTAB, STREND) -- every scalar's packed bytes and type byte --, CSP,
      CURLINE, FACTYP, ERRFLG and ERRLIN are the same, and so is everything the
      program printed (values, and ERR/ERL from its ON ERROR handler, or the
      error message when there is none).
      The corpus: tests/test_forfast.py's whole corpus (every loop type, so the
      float fast path and the BCD path are held to the old image too), plus `%`
      loops -- STEP positive / negative / 0 / large / -32768, limits at +-32767
      and -32768, a NEXT that overflows (`FOR I%=32760 TO 32767 STEP 5`, and
      `TO 32767` stepping onto 32768) bare, under ON ERROR and with RESUME NEXT,
      a body that writes I% (including onto the edge), nested `%` and float loops,
      NEXT I%,J lists, bare NEXT, DEFINT, two-letter names, a float limit / step
      (`TO 3.7`, `STEP .5`: slots that stay BCD, the general path), CLEAR in the
      body -- and a seeded random corpus of `%` loops over int16 edges.
  I2  the `%` arm is actually TAKEN on a plain `%` loop, and NOT completed where
      a slot is not int16.
  I3  host T-states of one NEXT (ex_next -> the next exec_stmt), old and new: the
      `%` NEXT must be cheaper (also `FOR I%=1 TO N` with N a double: FOR keeps an
      exact-int16 float slot as an int16 now, for a `%` loop too); the float fast
      path and the BCD path must not be slower beyond a few T. A `%` loop with a
      FRACTIONAL slot (still the general path) is printed only: it now pays
      nx_demote's `%` guard (a call, ~70 T on ~9400).

Set FORINT_OLD_DIR to a checkout of BASE_SHA to skip the git extraction.
"""

import io
import os
import random
import subprocess
import sys
import tarfile

from _tmp import tp

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import msxtest  # noqa: E402
from test_forfast import Runner, prog, loop, CORPUS, rand_corpus  # noqa: E402

BASE_SHA = "508043a2"          # the tree before D-FORINT
NEW_ROM, NEW_SYM = tp("zb_forint_new.rom"), tp("zb_forint_new.sym")
OLD_DIR = tp("zb_forint_old")
OLD_ROM, OLD_SYM = os.path.join(OLD_DIR, "old.rom"), os.path.join(OLD_DIR, "old.sym")
OLD_SUB, OLD_SUBSYM = os.path.join(OLD_DIR, "sub.rom"), os.path.join(OLD_DIR, "sub.sym")


def build():
    subprocess.run(["pasmo", "--bin", os.path.join(ROOT, "basic", "main.asm"),
                    NEW_ROM, NEW_SYM], check=True, capture_output=True, cwd=ROOT)
    tree = os.environ.get("FORINT_OLD_DIR")
    if not tree:
        tree = OLD_DIR
        os.makedirs(tree, exist_ok=True)
        r = subprocess.run(["git", "archive", "--format=tar", BASE_SHA, "basic", "sub"],
                           cwd=ROOT, capture_output=True)
        if r.returncode:
            raise SystemExit("FAIL  cannot extract the pre-D-FORINT tree "
                             f"({BASE_SHA}) from git: {r.stderr.decode().strip()}\n"
                             "      set FORINT_OLD_DIR to a checkout of it")
        tarfile.open(fileobj=io.BytesIO(r.stdout)).extractall(tree)
    os.makedirs(OLD_DIR, exist_ok=True)
    subprocess.run(["pasmo", "--bin", "basic/main.asm", OLD_ROM, OLD_SYM],
                   check=True, capture_output=True, cwd=tree)
    subprocess.run(["pasmo", "-I", "sub", "--bin", "sub/sub.asm", OLD_SUB, OLD_SUBSYM],
                   check=True, capture_output=True, cwd=tree)


class ErrRunner(Runner):
    """test_forfast's Runner, with ERR / ERL added to every statement snapshot."""

    def snapshot(self):
        s, mem = self.s, self.m.mem
        return super().snapshot() + (mem[s["ERRFLG"]], self.w(s["ERRLIN"]))


def runners():
    """(old, new), each with the sub-ROM of ITS OWN tree."""
    with open(OLD_SUB, "rb") as fh:
        old_sub = fh.read()
    msxtest._SUB_CACHE.clear()
    msxtest._SUB_CACHE.update(bytes=old_sub, sym=msxtest.load_symbols(OLD_SUBSYM))
    old = ErrRunner(OLD_ROM, OLD_SYM)
    msxtest._SUB_CACHE.clear()
    new = ErrRunner(NEW_ROM, NEW_SYM)
    return old, new


PCT = {
    "p.plain":     loop("I%", 1, 6),
    "p.named":     prog("10 FOR I%=1 TO 5:S%=S%+I%:NEXT I%:PRINT S%;I%"),
    "p.step3":     loop("I%", 1, 10, 3),
    "p.neg":       loop("I%", 10, 1, -3),
    "p.negb":      loop("I%", 5, -5, -2),
    "p.step0":     loop("I%", 1, 3, 0),
    "p.step0b":    loop("I%", 5, 3, 0),
    "p.step0c":    loop("I%", 3, 5, 0),
    "p.large":     loop("I%", 0, 30000, 16000),
    "p.largen":    loop("I%", 0, -30000, -16000),
    "p.stepmax":   loop("I%", 0, 32767, 32767),
    "p.stepmaxb":  loop("I%", -32767, 32767, 32767),
    "p.stepmin":   loop("I%", 0, -32768, -32768),
    "p.stepminb":  loop("I%", 32767, -32768, "-32768"),
    "p.stepmin%":  loop("I%", 1, "-32767-1", "S%", pre="S%=-32768"),
    "p.stepmini":  loop("I%", 0, "-32767-1", "-32767-1"),
    "p.top":       loop("I%", 32760, 32767),
    "p.topstep":   loop("I%", 32760, 32767, 3),
    "p.top1":      loop("I%", 32766, 32767),
    "p.ovf5":      loop("I%", 32760, 32767, 5),
    "p.botlit":    loop("I%", -32760, -32768, -1),
    "p.bot":       loop("I%", -32760, "-32767-1", -1),
    "p.bot1":      loop("I%", -32767, "-32767-1", -1),
    "p.botup":     loop("I%", -32768, -32765),
    "p.botovf":    loop("I%", -32766, "-32767-1", -5),
    "p.limmax":    loop("I%", 0, 32767, 10000),
    "p.limmin":    loop("I%", 0, -32768, -10000),
    "p.limmini":   loop("I%", 0, "-32767-1", -10000),
    "p.zero":      loop("I%", 0, 0),
    "p.cross":     loop("I%", -3, 3),
    "p.empty":     loop("I%", 5, 1),
    "p.emptyn":    loop("I%", 1, 5, -1),
    "p.defint":    loop("A", 1, 6, pre="DEFINT A"),
    "p.defint2":   loop("AB", 9, 1, -2, pre="DEFINT A-C"),
    "p.two":       loop("IJ%", 1, 6),
    "p.bodyw":     loop("I%", 1, 9, body="I%=I%+2"),
    "p.bodyset":   loop("I%", 1, 9, body="IF I%=3 THEN I%=7"),
    "p.bodyneg":   loop("I%", 1, 9, body="I%=-I%"),
    "p.bodyedge":  loop("I%", 1, 9, body="IF I%=2 THEN I%=32767"),
    "p.bodyedgn":  loop("I%", 1, -9, -1, body="IF I%=-2 THEN I%=-32768"),
    "p.bodyflt":   loop("I%", 1, 9, body="I%=I%+.6"),
    "p.flim":      loop("I%", 1, 3.7),
    "p.flimn":     loop("I%", 5, 1.2, -1),
    "p.finit":     loop("I%", 1.7, 3),
    "p.fstep":     loop("I%", 1, 3, .5),
    "p.fstep15":   loop("I%", 1, 6, 1.5),
    "p.dbllim":    loop("I%", 1, "N", pre="N=12"),
    "p.dblstep":   loop("I%", 1, 12, "N", pre="N=2"),
    "p.sngboth":   loop("I%", 1, "N!", "S!", pre="N!=12:S!=3"),
    "p.dblovf":    loop("I%", 32700, "N", "S#", pre="N=32767:S#=30"),
    "p.dblfrac":   loop("I%", 1, "N", "S", pre="N=12:S=1.5"),
    "p.dblfrac2":  loop("I%", 1, "N", "S", pre="N=8.5:S=2"),
    "p.lim32767f": loop("I%", 32765, "32767!"),
    "p.lim32768f": loop("I%", 32765, "32768!"),
    "p.pctlim":    loop("I%", 1, "N%", "S%", pre="N%=12:S%=3"),
    "p.biglim":    loop("I%", 32000, 40000, 300),
    "p.biglimn":   loop("I%", -32000, -40000, -300),
    "p.strlim":    loop("I%", 1, '"A"'),
    "p.ovfnext":   prog("""
        10 ON ERROR GOTO 100
        20 FOR I%=32760 TO 32767 STEP 5:PRINT I%:NEXT:PRINT "A";I%
        30 PRINT "D";I%:END
        100 PRINT "E";ERR;ERL;I%:RESUME NEXT
    """),
    "p.ovfbare":   prog("""
        10 FOR I%=32760 TO 32767 STEP 5:PRINT I%:NEXT
        20 PRINT "D";I%
    """),
    "p.ovfres":    prog("""
        10 ON ERROR GOTO 100:N=0
        20 FOR I%=32765 TO 32767:PRINT I%:NEXT I%:PRINT "A";I%
        30 PRINT "D";I%;N:END
        100 N=N+1:PRINT "E";ERR;ERL;I%:IF N<3 THEN RESUME ELSE RESUME NEXT
    """),
    "p.ovflist":   prog("""
        10 ON ERROR GOTO 100
        20 FOR J=1 TO 2:FOR I%=32766 TO 32767:PRINT J;I%:NEXT I%,J:PRINT "A"
        30 END
        100 PRINT "E";ERR;ERL;I%;J:RESUME NEXT
    """),
    "p.nested":    prog("""
        10 FOR I%=1 TO 3:FOR J=1 TO 2:FOR K%=3 TO 1 STEP -1:N=N+1:NEXT K%:NEXT J:NEXT I%
        20 PRINT I%;J;K%;N
    """),
    "p.nestbare":  prog("""
        10 FOR I%=1 TO 3:FOR J%=-2 TO 2 STEP 2:K=K+I%*J%:NEXT:NEXT:PRINT I%;J%;K
    """),
    "p.list":      prog("""
        10 FOR I%=1 TO 3:FOR J=1 TO 2:K=K+1:NEXT J,I%:PRINT I%;J;K
    """),
    "p.list2":     prog("""
        10 FOR I=1 TO 3:FOR J%=1 TO 2:K=K+1:NEXT J%,I:PRINT I;J%;K
    """),
    "p.listtrail": prog("""
        10 ON ERROR GOTO 100
        20 FOR I%=1 TO 2:FOR J%=1 TO 2:NEXT J%,:PRINT "A"
        30 END
        100 PRINT "E";ERR;ERL;I%;J%:END
    """),
    "p.inner":     prog("""
        10 FOR I%=1 TO 3:FOR J%=1 TO 9:IF J%=2 THEN NEXT I% ELSE NEXT J%
        20 PRINT I%;J%
    """),
    "p.xtype":     prog("""
        10 ON ERROR GOTO 100
        20 FOR A%=1 TO 3:NEXT A
        30 END
        100 PRINT "E";ERR;ERL;A%:END
    """),
    "p.clear":     prog("""
        10 ON ERROR GOTO 100
        20 FOR I%=1 TO 3:CLEAR:NEXT
        30 END
        100 PRINT "E";ERR;ERL;I%:END
    """),
    "p.gosub":     prog("""
        10 FOR I%=1 TO 4:GOSUB 100:NEXT:PRINT I%;S:END
        100 S=S+I%:RETURN
    """),
    "p.onerr":     prog("""
        10 ON ERROR GOTO 100
        20 FOR I%=1 TO 5:X=10/(I%-3):PRINT I%;X:NEXT
        30 PRINT "D";I%:END
        100 PRINT "E";ERR;ERL;I%:RESUME NEXT
    """),
    "p.ary":       prog("""
        10 ON ERROR GOTO 100:DIM A%(3)
        20 FOR I%=1 TO 3:NEXT A%(1)
        30 END
        100 PRINT "E";ERR;ERL;I%:END
    """),
    "p.manyvars":  prog("""
        10 A%=1:B=2:C1%=3:FOR X%=1 TO 5:Y%=X%*2:Z#=X%/3:NEXT:PRINT X%;Y%;Z#
    """),
    "p.newvar":    prog("""
        10 FOR I%=1 TO 4:IF I%=2 THEN Q%=5:DIM R(3)
        20 NEXT:PRINT I%;Q%
    """),
    "p.unset":     prog("10 FOR I%=I% TO 3:NEXT:PRINT I%"),
}


def rand_pct(n, seed=20261021):
    rnd = random.Random(seed)
    pool = ["0", "1", "-1", "2", "-2", "3", "7", "-7", "10", "100", "-100", "255",
            "32767", "-32767", "-32768", "32766", "-32766", "16384", "-16384",
            "16383", "32000", "-32000", "9999", "10000", "-10000", "32760", "-32760",
            "N", "-N", "N*2", "N%", "-N%",
            ".5", "-.5", "1.5", "2.7", "40000", "-40000", "3!", "3#"]
    vars_ = ["I%", "A%", "AB%"]
    rows = {}
    for k in range(n):
        v = rnd.choice(vars_)
        i, lim, st = rnd.choice(pool), rnd.choice(pool), rnd.choice(pool + [None] * 8)
        body = rnd.choice(["", "", "", f"{v}={v}+1", f"{v}={v}*2", f"{v}=-{v}",
                           f"IF C=2 THEN {v}=32767", f"IF C=2 THEN {v}=-32768",
                           f"IF C=3 THEN {v}=30000"])
        rows[f"q{k:03d}"] = loop(v, i, lim, st, body, cap=6,
                                 pre=rnd.choice(["N=6", "N%=9", "N%=-4", "N=2.5",
                                                 "N%=32767"]))
    return rows


def run():
    build()
    old, new = runners()
    fails = 0

    def check(label, ok, detail=""):
        nonlocal fails
        fails += not ok
        if not ok:
            print(f"FAIL  {label}" + (f"  [{detail}]" if detail else ""))
        return ok

    print("# --- I1/I2 differential: the pre-D-FORINT image vs this one ---")
    corpus = dict(CORPUS)
    corpus.update(rand_corpus(int(os.environ.get("FORFAST_RANDOM", "30"))))
    corpus.update(PCT)
    corpus.update(rand_pct(int(os.environ.get("FORINT_RANDOM", "120"))))
    ident = bounds = 0
    pct_taken = 0
    must_take = {"pct", "defint", "edgepct", "p.plain", "p.named", "p.step3", "p.neg",
                 "p.step0", "p.large", "p.top", "p.ovf5", "p.bot", "p.defint",
                 "p.defint2", "p.two", "p.bodyw", "p.bodyset", "p.bodyedge",
                 "p.nested", "p.list", "p.list2", "p.inner", "p.ovfnext", "p.ovfres",
                 "p.ovflist", "p.gosub", "p.onerr", "p.pctlim", "p.stepmin%",
                 "p.stepmini", "p.bot1", "p.limmini", "p.dbllim", "p.dblstep",
                 "p.sngboth", "p.dblovf", "p.lim32767f"}
    must_not = {"p.flim", "p.flimn", "p.fstep", "p.fstep15", "p.biglim",
                "p.biglimn", "p.strlim", "p.botlit", "p.dblfrac", "p.dblfrac2",
                "p.lim32768f"}
    for name, lines in corpus.items():
        o_out = old.run(lines)
        o_snaps = old.snaps
        n_out = new.run(lines)
        n_snaps = new.snaps
        same = o_out == n_out and o_snaps == n_snaps
        detail = ""
        if not same:
            if o_out != n_out:
                detail = f"out old={o_out!r} new={n_out!r}"
            else:
                k = next((i for i, (a, b) in enumerate(zip(o_snaps, n_snaps)) if a != b),
                         min(len(o_snaps), len(n_snaps)))
                detail = (f"snap #{k} of {len(o_snaps)}/{len(n_snaps)}: "
                          f"old={o_snaps[k] if k < len(o_snaps) else None} "
                          f"new={n_snaps[k] if k < len(n_snaps) else None}")
        check(f"I1 {name}: identical", same, detail)
        ident += same
        bounds += len(n_snaps)
        done = new.fast_hits - new.fslow_hits
        if name in PCT or name.startswith("q"):
            pct_taken += done > 0
        if name in must_take:
            check(f"I2 {name}: int path taken", done > 0)
        if name in must_not:
            check(f"I2 {name}: int path NOT completed", done == 0)
        if name in ("p.ovf5", "p.ovfnext"):
            print(f"      ({name} prints {n_out.strip()!r})")
    print(f"{'PASS' if ident == len(corpus) else 'FAIL'}  I1 {ident}/{len(corpus)} "
          f"programs identical ({bounds} statement boundaries); the int path "
          f"completed a NEXT in {pct_taken} of the {len(PCT)} + random `%` programs")

    print("# --- I3 host T-states of one NEXT (tenant steps in, CALSLT out) ---")
    rows = [
        ("FOR I%=1 TO 12", "10 FOR I%=1 TO 12:NEXT", True),
        ("FOR I%=300 TO 312", "10 FOR I%=300 TO 312:NEXT", True),
        ("FOR I%=12 TO 1 STEP -1", "10 FOR I%=12 TO 1 STEP -1:NEXT", True),
        ("N=12:FOR I%=1 TO N (dbl limit)", "10 N=12:FOR I%=1 TO N:NEXT", True),
        ("FOR I%=1 TO 13.7 (BCD limit)", "10 FOR I%=1 TO 13.7:NEXT", None),
        # (STEP 1.5, not .5: I% truncates, so `STEP .5` never ends -- both images)
        ("FOR I%=1 TO 9 STEP 1.5 (BCD)", "10 FOR I%=1 TO 9 STEP 1.5:NEXT", None),
        ("FOR I=1 TO 12 (float fast)", "10 FOR I=1 TO 12:NEXT", False),
        ("FOR I!=1 TO 12 (float fast)", "10 FOR I!=1 TO 12:NEXT", False),
        ("FOR I=1 TO 7 STEP .5 (BCD)", "10 FOR I=1 TO 7 STEP .5:NEXT", False),
        ("FOR I#=.5 TO 12 (BCD)", "10 FOR I#=.5 TO 12:NEXT", False),
    ]
    old.timing = new.timing = True
    for label, text, gated in rows:
        lines = prog(text)
        old.run(lines)
        new.run(lines)
        ot, nt = old.next_t[1:-1], new.next_t[1:-1]
        o, n = sum(ot) / len(ot), sum(nt) / len(nt)
        osub, nsub = old.next_sub[1], new.next_sub[1]
        print(f"      {label:32s} old {o:7.0f} T ({osub} sub)  new {n:7.0f} T "
              f"({nsub} sub)  {n - o:+7.0f}")
        if gated:
            check(f"I3 {label}: the `%` NEXT is cheaper", n < o * 0.7, f"{n} vs {o}")
        elif gated is False:
            check(f"I3 {label}: not slower beyond a few T", n <= o + 8, f"{n} vs {o}")
    old.timing = new.timing = False

    print(f"\n{'ALL PASS' if fails == 0 else f'{fails} FAIL(S)'}")
    return fails


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
