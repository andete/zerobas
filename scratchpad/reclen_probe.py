#!/usr/bin/env python3
# Copyright (c) 2026 Joost Yervante Damad
# SPDX-License-Identifier: 0BSD
"""D-RECLEN follow-up — what does the CF-3300 actually DO with a STRADDLING record?

TODO's item (D-RECLEN, filed 2026-08-19) records that `OPEN"TS.DAT"AS #1 LEN=100`
is `Syntax error` on zerobas and `OK` on the CF-3300: `oo_parse_reclen`
(basic/files.asm) requires a power of two in 1..256 "so records tile the
512-byte sector with no straddle".

🎯 AND THE ITEM NAMES ITS OWN NEXT STEP RATHER THAN A FIX: *"the straddle
argument is a REAL design constraint, so 'just widen the validator' is exactly
the cheap wrong answer -- what the reference DOES with a straddling record is
unmeasured, and GET/PUT round-trip rows come before any byte."* This is those
rows.

🔴 THE DISCRIMINATING RECORD IS NUMBER 6, AND ONLY NUMBER 6. At LEN=100 record 1
occupies bytes 0..99 and record 5 occupies 400..499 -- both wholly inside the
first 512-byte sector, so both would round-trip even on an implementation that
cannot straddle at all. Record 6 occupies **500..599** and crosses the boundary.
A probe that wrote only records 1..5 would report a clean round trip and say
NOTHING about the constraint the validator exists to enforce.
[[a-coverage-row-whose-geometry-cannot-reach-the-case]]

⚠️ AND THE NEIGHBOURS ARE THE SECOND HALF OF THE QUESTION. "Record 6 reads back"
is compatible with a straddling write that CORRUPTED 5 or 7 on the way, so the
neighbour rows are not decoration -- if the reference accepts LEN=100 but mangles
an adjacent record, its acceptance is not something to copy.

⚠️ ONE REFERENCE: Disk BASIC. A diskless VG-8020 cannot express any of this, and
zerobas REFUSES LEN=100 at the OPEN, which is the divergence itself -- so the zb
column is expected to read `Syntax error` on every `s.*` row and is included to
show the refusal, not as an oracle. `ctl.*` uses LEN=128, which zerobas accepts,
so the round-trip machinery is proved on BOTH sides before any of it is believed.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_fldwidth as F                                  # noqa: E402

RD = 'GET#1,{n}:PRINT"[";LEFT$(A$,1);MID$(A$,50,1);RIGHT$(A$,1);"]"'


# 🔴 `CLEAR 1000` IS NOT DECORATION, AND ITS ABSENCE FAKED A DIVERGENCE. The
# first run of this probe read `<NO OUTPUT>` for every zerobas ctl.* row -- the
# rows whose whole job is to prove the round-trip machinery works on BOTH sides
# before anything else is believed. A ladder (one rung per statement) then showed
# every step passing on zerobas, `GET#1,6` included: the failure needed all THREE
# `LSET A$=STRING$(n,...)` temps, i.e. it was the STRING POOL, not the records.
# 🎯 A CONTROL THAT FAILS FOR A REASON UNRELATED TO ITS SUBJECT IS WORSE THAN NO
# CONTROL: it invites reading a pool exhaustion as a record-layout divergence.
# [[a-case-that-agrees-can-agree-for-the-wrong-reason]]
def write_three(reclen):
    return ['CLEAR 1000',
            f'OPEN"TS.DAT"AS #1 LEN={reclen}',
            f'FIELD#1,{reclen} AS A$',
            f'LSET A$=STRING$({reclen},"A"):PUT#1,5',
            f'LSET A$=STRING$({reclen},"B"):PUT#1,6',
            f'LSET A$=STRING$({reclen},"C"):PUT#1,7',
            'CLOSE',
            f'OPEN"TS.DAT"AS #1 LEN={reclen}',
            f'FIELD#1,{reclen} AS A$']


W = 'LSET A$=STRING$(128,"B"):PUT#1,{n}'
B128 = ['OPEN"TS.DAT"AS #1 LEN=128', 'FIELD#1,128 AS A$']
LS = 'LSET A$=STRING$(128,"B")' 
OK = 'PRINT"[";"OK";"]"'

CASES = [
    # === 🟢 THE POSITIVE CONTROL THE "UNTRAPPABLE" CLAIM NEEDED ==============
    # The first write-up said "not a trappable error" because p.trap3 printed
    # NOTHING with a handler in place. That is an ABSENCE, and an absence is what
    # a broken fixture also looks like. k.puttrap arms the same handler, does TWO
    # PUTs, then forces a KNOWN `ERROR 7` -- and it traps (`ERR 7 AT 60`) on both
    # machines. So the handler is demonstrably ARMED AND LIVE after two PUTs, and
    # k.put3 -- the same program with the third PUT in place of the forced error
    # -- still dies. The claim now rests on a live handler, not on silence.
    # ⚠️ AND THE FIXTURE CAVEAT THAT COST A WHOLE PROBE: `MAXFILES=n` DISARMS
    # `ON ERROR` -- on BOTH machines (k.mfwipes, correct behaviour, not a
    # divergence). An earlier attempt put `MAXFILES=2` between the handler and
    # the subject and read the resulting untrapped error as a finding.
    ("k.puttrap",  "dsk", ['ONERRORGOTO70', 'OPEN"TS.DAT"AS #1 LEN=128',
                           'FIELD#1,128 AS A$', 'PUT#1,1', 'PUT#1,1',
                           'ERROR 7:PRINT"[";"NOTRAP";"]":END',
                           'PRINT"[ERR";ERR;"AT";ERL;"]":END']),
    ("k.put3",     "dsk", ['ONERRORGOTO70', 'OPEN"TS.DAT"AS #1 LEN=128',
                           'FIELD#1,128 AS A$', 'PUT#1,1', 'PUT#1,1',
                           'PUT#1,1:PRINT"[";"OK";"]":END',
                           'PRINT"[ERR";ERR;"AT";ERL;"]":END']),
    ("k.mfwipes",  "dsk", ['ONERRORGOTO50', 'MAXFILES=2', 'ERROR 7',
                           'PRINT"[";"NOTRAP";"]":END',
                           'PRINT"[ERR";ERR;"AT";ERL;"]":END']),
    ("k.mfctl",    "dsk", ['ONERRORGOTO50', 'REM', 'ERROR 7',
                           'PRINT"[";"NOTRAP";"]":END',
                           'PRINT"[ERR";ERR;"AT";ERL;"]":END']),

    # === 🔴 THE MINIMAL REPRODUCER: THREE `PUT`s, NO STRINGS ANYWHERE ========
    # 🎯 EVERY ROW BELOW PAIRED AN `LSET ... STRING$` WITH EACH `PUT`, so "the
    # third PUT" and "the third LSET" coincided on all of them -- two rules, one
    # row set. These four separate them, and the answer is the PUT:
    #   x.l3p1  three LSETs, ONE put   -> OK      (LSET is not it)
    #   x.l3p0  three LSETs, NO put    -> OK      (nor STRING$ + LSET alone)
    #   x.l1p3  ONE LSET, three puts   -> DIES
    #   x.l0p3  NO LSET AT ALL, three  -> DIES    (the minimal form)
    # [[two-rules-that-coincide-on-every-row-you-have]]
    ("x.l3p1",    "dsk", B128 + [LS, LS, LS, 'PUT#1,1', OK]),
    ("x.l3p0",    "dsk", B128 + [LS, LS, LS, OK]),
    ("x.l1p3",    "dsk", B128 + [LS, 'PUT#1,1', 'PUT#1,1', 'PUT#1,1', OK]),
    ("x.l0p3",    "dsk", B128 + ['PUT#1,1', 'PUT#1,1', 'PUT#1,1', OK]),
    ("x.l2p2",    "dsk", B128 + [LS, 'PUT#1,1', LS, 'PUT#1,1', OK]),

    # === 🔴 THE THIRD `PUT` HANGS ZEROBAS -- found while trying to MEASURE the
    # === straddle question, because the ctl.* rows below could not be read.
    # The bisect is the finding: it is the PUT COUNT and nothing else.
    ("p.put1",    "dsk", B128 + [W.format(n=1), OK]),
    ("p.put2",    "dsk", B128 + [W.format(n=1), W.format(n=2), OK]),
    ("p.put3",    "dsk", B128 + [W.format(n=1), W.format(n=2), W.format(n=3), OK]),
    # 🎯 SAME record three times -- so it is not the record NUMBERS, not the
    # layout, and not the straddle.
    ("p.same3",   "dsk", B128 + [W.format(n=6)] * 3 + [OK]),
    # 🎯 A CLOSE AND REOPEN DOES NOT RESET IT: two PUTs, close, reopen, one more
    # PUT still dies -- so whatever is counted is CUMULATIVE ACROSS THE SESSION,
    # not per open handle. That is the sharpest clue in the set.
    ("p.close3",  "dsk", B128 + [W.format(n=1), W.format(n=2), 'CLOSE']
                         + B128 + [W.format(n=3), OK]),
    # 🔴 AND IT IS NOT A TRAPPABLE ERROR. The handler must be the LAST statement
    # because the harness numbers statements 10,20,30...; an earlier draft said
    # `ON ERROR GOTO 100`, which does not exist, and BOTH sides answered
    # `Undefined line number` -- the row measured the fixture, not the machine.
    # With a reachable handler zerobas still prints NOTHING: no error is raised,
    # the handler never runs. `p.trap2` is the same shape one PUT shorter and
    # answers OK, which is what says the fixture is sound.
    ("p.trap3",   "dsk", ['ONERRORGOTO70'] + B128
                         + [W.format(n=1), W.format(n=2),
                            W.format(n=3) + ':' + OK + ':END',
                            'PRINT"[ERR";ERR;"]"']),
    ("p.trap2",   "dsk", ['ONERRORGOTO70'] + B128
                         + [W.format(n=1), 'REM',
                            W.format(n=2) + ':' + OK + ':END',
                            'PRINT"[ERR";ERR;"]"']),

    # --- 🟢 CONTROLS on a TILING length zerobas also accepts -----------------
    ("ctl.128.r6", "dsk", write_three(128) + [RD.format(n=6)]),
    ("ctl.128.r5", "dsk", write_three(128) + [RD.format(n=5)]),
    ("ctl.128.r7", "dsk", write_three(128) + [RD.format(n=7)]),
    # --- the non-tiling length: does it round-trip AT ALL? -------------------
    ("s.100.r1",   "dsk", [ 'CLEAR 1000', 'OPEN"TS.DAT"AS #1 LEN=100', 'FIELD#1,100 AS A$',
                            'LSET A$=STRING$(100,"D"):PUT#1,1', 'CLOSE',
                            'OPEN"TS.DAT"AS #1 LEN=100', 'FIELD#1,100 AS A$',
                            RD.format(n=1)]),
    # --- 🔴 THE STRADDLE: record 6 is bytes 500..599, across the 512 boundary -
    ("s.100.r6",   "dsk", write_three(100) + [RD.format(n=6)]),
    # --- and whether the straddling write damaged its neighbours -------------
    ("s.100.r5",   "dsk", write_three(100) + [RD.format(n=5)]),
    ("s.100.r7",   "dsk", write_three(100) + [RD.format(n=7)]),
    # --- a length that is neither a power of two NOR straddling at record 6 ---
    # 🎯 SEPARATES "non-power-of-two" from "straddles": at LEN=64 record 6 is
    # 320..383, wholly inside sector 0, and 64 IS a power of two -- so LEN=96
    # (records tile 512 only every 16) is the row that isolates the RULE.
    ("s.96.r6",    "dsk", write_three(96) + [RD.format(n=6)]),
]

F.CASES = CASES
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
res = {s: F.run_side(s, []) for s in sides}
w = max(len(l) for l, _, _ in CASES)
print(f"{'row':<{w}}  " + "  ".join(f"{s:>26}" for s in sides))
for label, _, _ in CASES:
    print(f"{label:<{w}}  " + "  ".join(f"{str(res[s].get(label)):>26}" for s in sides))
print("\n🔴 p.put3 / p.same3 / p.close3 / p.trap3: zerobas prints NOTHING where the")
print("   CF-3300 answers OK -- the THIRD PUT of a session hangs, untrappably, and")
print("   a CLOSE+reopen does not reset it. p.put1/p.put2/p.trap2 are the controls.")
print("   ⚠️ The zb ctl.128.* rows below are BLIND FOR THAT REASON (they write three")
print("   records), so they are NOT evidence about record layout.")
print("\nexpect: ctl.* = BBB / AAA / CCC on the CF-3300 (the machinery works);\n"
      "        s.100.r6 is the whole question -- BBB means the reference straddles\n"
      "        correctly, anything else means its acceptance is not a model to copy.")
