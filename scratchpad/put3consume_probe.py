#!/usr/bin/env python3
r"""D-PUT3CONSUME — WHAT does the third `PUT` consume?

D-PUT3 (docs/spec-basic-put3.md) characterised the failure exhaustively: it is
the PUT COUNT and nothing else, it is cumulative across the session, `CLOSE` +
`CLEAR` + reopen does not reset it, and it is untrappable. Its own next step is
the one thing still unknown: **what accumulates?**

🎯 A MEASUREMENT, NOT A CODE READ. The filed path (`fat_rand_put` ->
`frnd_locate` -> `fat_alloc_cluster` / `fat_write_fat_entry` -> the
`fat_dir_update` tail) is all DISK state, and disk state is readable FROM BASIC:
`DSKF` is free space and `LOF` is the file length. If either moves per `PUT` on
zerobas while holding still on the CF-3300, the accumulating resource is named
without a debugger.

🔴 PREDICTIONS, RECORDED BEFORE THE RUN:
  P1  On the CF-3300, DSKF is IDENTICAL after 1 and after 2 writes of the SAME
      record -- rewriting record 1 allocates nothing new. High confidence; this
      is the control that makes any zb movement mean something.
  P2  On zerobas, DSKF DROPS between one write and two. If it does, every `PUT`
      allocates a fresh cluster instead of reusing the file's own -- which would
      also explain why CLOSE does not reset it (the leak is in the FAT, not the
      FCB). Medium confidence.
  P3  If DSKF holds still on BOTH, the consumed resource is NOT disk space and
      the next look is RAM/stack, not the FAT. Naming this now so a null result
      is a finding rather than a dead end.
  ⚠️ NOTE WHAT P2 DOES *NOT* CLAIM: a one-cluster-per-PUT leak on a 720K disk
      could not by itself fail on the THIRD write. So even a confirmed P2 is a
      SYMPTOM, not the cause -- it would say the write path re-allocates, which
      is a different bug that may share a root with the hang.

⚠️ FIXTURE CAVEATS THAT COST EARLIER PROBES (D-PUT3's own list): `MAXFILES=n`
DISARMS `ON ERROR` on both machines; `OPEN ... AS #2` fails under the default
`MAXFILES=1`; two disk channels are `Syntax error` here (D-OPEN2). None of these
rows uses a second channel or MAXFILES.
"""
from __future__ import annotations
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "probes", "basic"))
import basic_probe_fldwidth as F                                  # noqa: E402

OPEN = ['CLEAR 1000', 'OPEN"TS.DAT"AS #1 LEN=128', 'FIELD#1,128 AS A$']
FREE = 'PRINT"[";DSKF(0);"]"'
SIZE = 'PRINT"[";LOF(1);"]"'

CASES = [
    # --- free space, as a function of how many PUTs have happened -----------
    ("d.free0",  "dsk", OPEN + [FREE]),
    ("d.free1",  "dsk", OPEN + ['PUT#1,1', FREE]),
    ("d.free2",  "dsk", OPEN + ['PUT#1,1', 'PUT#1,1', FREE]),
    # --- and the file's own length, same ladder -----------------------------
    ("d.lof0",   "dsk", OPEN + [SIZE]),
    ("d.lof1",   "dsk", OPEN + ['PUT#1,1', SIZE]),
    ("d.lof2",   "dsk", OPEN + ['PUT#1,1', 'PUT#1,1', SIZE]),
    # --- 🟢 CONTROL: DSKF read twice with NO put between. If this moves, the
    # --- reading itself is unstable and every row above is noise.
    ("c.twice",  "dsk", OPEN + [FREE, FREE]),
    # --- 🟢 CONTROL: three GETs are known-fine (spec §3a), so the ladder's
    # --- machinery survives three disk ops that are not PUTs.
    ("c.get3",   "dsk", OPEN + ['GET#1,1', 'GET#1,1', 'GET#1,1', FREE]),
    # --- 🔴 THE SUBJECT, for the record: the third PUT, same session --------
    ("s.put3",   "dsk", OPEN + ['PUT#1,1', 'PUT#1,1', 'PUT#1,1', FREE]),
    # --- does a DIFFERENT record number change the ladder? (1,2,3 vs 1,1,1) --
    ("s.put3n",  "dsk", OPEN + ['PUT#1,1', 'PUT#1,2', 'PUT#1,3', FREE]),
    # --- two puts then a GET: does the GET still work after the leak starts? -
    ("d.getafter", "dsk", OPEN + ['PUT#1,1', 'PUT#1,1', 'GET#1,1', FREE]),

    # ========================================================================
    # ROUND 2 — 🔴 MY OWN FIRST DESIGN CONFOUNDED THE SUBJECT WITH THE PROBE.
    # Every row above that dies on zb ends in DSKF *after* a PUT, and `d.free1`
    # shows ONE put is already enough. So `s.put3`/`s.put3n` cannot speak to the
    # "third PUT" claim at all -- their blank could be either cause. Meanwhile
    # `d.lof2` (two PUTs, LOF instead of DSKF) reads 128 on both.
    # These rows read LOF, never DSKF, so the PUT COUNT is the only variable.
    # [[two-rules-that-coincide-on-every-row-you-have]]
    ("x.put3lof", "dsk", OPEN + ['PUT#1,1', 'PUT#1,1', 'PUT#1,1', SIZE]),
    ("x.put4lof", "dsk", OPEN + ['PUT#1,1', 'PUT#1,1', 'PUT#1,1',
                                 'PUT#1,1', SIZE]),
    # ...and the mirror: how FEW puts does a DSKF need to die after? d.free1
    # says one; this says zero, which must be GREEN (it is d.free0's shape).
    ("x.dskf0",   "dsk", OPEN + [FREE]),
    # 🎯 IS IT THE PUT, OR ANY WRITE? A GET is a disk op that is not a write.
    ("x.getdskf", "dsk", OPEN + ['GET#1,1', FREE]),
    # 🟢 CONTROL REPLACING c.get3, WHICH FAILED ON THE REFERENCE (3 GETs on a
    # freshly-created empty file printed nothing on the CF-3300 -- a control
    # that reddens on the oracle measures nothing). One GET, then LOF.
    ("x.get1lof", "dsk", OPEN + ['GET#1,1', SIZE]),
]

F.CASES = CASES
sides = (sys.argv[1] if len(sys.argv) > 1 else "cf3300,zb").split(",")
res = {s: F.run_side(s, []) for s in sides}
w = max(len(l) for l, _, _ in CASES)
print(f"\n{'row':<{w}}  " + "  ".join(f"{s:>22}" for s in sides))
print("-" * (w + 2 + 24 * len(sides)))
for label, _, _ in CASES:
    print(f"{label:<{w}}  " + "  ".join(f"{str(res[s].get(label)):>22}" for s in sides))
print("\nread: d.free0/1/2 is the whole question -- a DROP on zb with the CF-3300\n"
      "      flat means every PUT allocates instead of reusing.")
