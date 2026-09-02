#!/usr/bin/env python3
r"""D-DSKFSLOW — is `DSKF` after a `PUT` HUNG, or merely very SLOW?

D-PUT1AFTER localised the failure to `fat_count_free` (after ONE `PUT`, `DSKF`
is the only casualty of seven operations tested). Reading the body refuted the
first mechanism guess -- it RESETS its cache key (`FWR_FIRST = $FFFF`) on entry,
so it does not inherit stale write-side state.

🎯 BUT ITS LOOP IS BOUNDED BY A NUMBER IT COMPUTES: `fat_total_clusters` -> DE ->
`FAT_WRTMP`, and `fcf_loop` runs cluster 2 .. total. If a `PUT` leaves that total
WRONG AND LARGE, the loop is not stuck -- it is scanning tens of thousands of
clusters, which at a few cross-slot reads apiece would present to any probe as a
hang. "Hung" and "slow" are the same observation at a fixed step, and they have
completely different fixes.

🔴 THE DISCRIMINATOR IS THE STEP, AND NOTHING ELSE CHANGES. Identical program,
identical machine; only how long the harness waits. If a long step produces a
NUMBER, it was never a hang and the bug is the bound. If it still produces
nothing at 90 s of emulated wall, "hang" survives a real test instead of being
the default reading of a blank.

⚠️ A NUMBER THAT ARRIVES LATE IS ALSO EVIDENCE ABOUT *WHICH* NUMBER: 707 would
mean the count is right and only the walk is slow; anything else names the
corrupted bound directly.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_fldwidth as F                                  # noqa: E402

STEP = float(sys.argv[2]) if len(sys.argv) > 2 else 90.0
F.SIDES["zb"] = dict(F.SIDES["zb"], step=STEP)
F.SIDES["cf3300"] = dict(F.SIDES["cf3300"], step=STEP)

OPEN = ['CLEAR 1000', 'OPEN"TS.DAT"AS #1 LEN=128', 'FIELD#1,128 AS A$']
CASES = [
    # 🟢 CONTROL: no PUT. Must answer promptly at any step -- if this needs the
    # long step too, the step is measuring the harness, not the subject.
    ("s.nodput", "dsk", OPEN + ['PRINT"[";DSKF(0);"]"']),
    # THE SUBJECT, with the long step.
    ("s.dskf1",  "dsk", OPEN + ['PUT#1,1', 'PRINT"[";DSKF(0);"]"']),
    # 🎯 AND THE BOUND ITSELF, read without DSKF: LOF after a PUT is known-good,
    # so a marker here proves the program reached the end and the machine lives.
    ("s.alive",  "dsk", OPEN + ['PUT#1,1', 'PRINT"[";LOF(1);"]"']),

    # 🔴 THE FAR BIGGER QUESTION, AND THE SAME TEST. D-PUT3 is filed as an
    # UNTRAPPABLE HANG on the third PUT -- "a random-access write loop is an
    # ordinary MSX BASIC program". Every reading behind that claim was taken at a
    # 2.5 s step, and s.dskf1 above has just shown that a 2.5 s blank can be a
    # 90 s SUCCESS. If these answer at a long step, the item is a PERFORMANCE
    # defect, not a hang, and its severity and its fix both change.
    ("h.put3",   "dsk", OPEN + ['PUT#1,1', 'PUT#1,1', 'PUT#1,1',
                                'PRINT"[";LOF(1);"]"']),
    ("h.put4",   "dsk", OPEN + ['PUT#1,1', 'PUT#1,1', 'PUT#1,1', 'PUT#1,1',
                                'PRINT"[";LOF(1);"]"']),
    # the reclen_probe p.put3 shape, which is what the filing rests on
    ("h.p3orig", "dsk", OPEN + ['LSET A$=STRING$(128,"B"):PUT#1,1',
                                'LSET A$=STRING$(128,"B"):PUT#1,2',
                                'LSET A$=STRING$(128,"B"):PUT#1,3',
                                'PRINT"[OK]"']),

    # 🎯 IS EACH `PUT` LEAKING A CLUSTER? That would explain everything at once:
    # a growing chain makes each frnd_locate walk longer, so PUT n+1 costs more
    # than PUT n -- which is exactly the shape observed (1 and 2 pass at a 2.5 s
    # step, 3 does not). Read at a LONG step so the answer arrives.
    # 707 free before any write; if these read 706 / 705 / 704 the chain is
    # growing by one cluster PER WRITE OF THE SAME RECORD.
    ("k.free1",  "dsk", OPEN + ['PUT#1,1', 'PRINT"[";DSKF(0);"]"']),
    ("k.free2",  "dsk", OPEN + ['PUT#1,1', 'PUT#1,1', 'PRINT"[";DSKF(0);"]"']),
    ("k.free3",  "dsk", OPEN + ['PUT#1,1', 'PUT#1,1', 'PUT#1,1',
                                'PRINT"[";DSKF(0);"]"']),
]
F.CASES = CASES
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
res = {s: F.run_side(s, []) for s in sides}
w = max(len(l) for l, _, _ in CASES)
print(f"\nstep={STEP}s")
print(f"{'row':<{w}}  " + "  ".join(f"{s:>24}" for s in sides))
for label, _, _ in CASES:
    print(f"{label:<{w}}  " + "  ".join(f"{str(res[s].get(label)):>24}" for s in sides))
